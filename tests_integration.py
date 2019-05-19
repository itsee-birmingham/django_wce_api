import json
from django.utils import timezone
from django.test import TestCase
from citations import models
from accounts.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory
from unittest import skip

class APIPostTests(APITestCase):
    base_url = '/api/{}/{}/'
    def addCitationManagerUser(self, credentials):
        g2 = Group(name='citation_managers')
        g2.save()
        self.add_citation_manager_permissions(g2)
        user = User.objects.create_user(**credentials)
        user.groups.add(g2)
        user.save()
        return user

    def add_citation_manager_permissions(self, group):
        group.permissions.add(Permission.objects.get(codename='add_citation'))
        group.permissions.add(Permission.objects.get(codename='change_citation'))
        group.permissions.add(Permission.objects.get(codename='add_dependency'))
        group.permissions.add(Permission.objects.get(codename='change_dependency'))
        group.permissions.add(Permission.objects.get(codename='add_author'))
        group.permissions.add(Permission.objects.get(codename='change_author'))
        group.permissions.add(Permission.objects.get(codename='add_edition'))
        group.permissions.add(Permission.objects.get(codename='change_edition'))
        group.permissions.add(Permission.objects.get(codename='add_series'))
        group.permissions.add(Permission.objects.get(codename='change_series'))
        group.permissions.add(Permission.objects.get(codename='add_onlinecorpus'))
        group.permissions.add(Permission.objects.get(codename='change_onlinecorpus'))
        #work has to take into account content type because of a clash with the transcriptions.work model
        content_type = ContentType.objects.get_for_model(models.Work)
        permission = Permission.objects.get(content_type=content_type, codename='add_work')
        group.permissions.add(permission)
        permission = Permission.objects.get(content_type=content_type, codename='change_work')
        group.permissions.add(permission)
        group.save()

    base_url = '/api/{}/{}/'

    #@skip('')
    def test_POSTAuthor(self):
        authors = models.Author.objects.all()
        self.assertTrue(len(authors) == 0)
        a1_data = {"created_by": 'cat',
                   "created_time": str(timezone.now()),
                   "abbreviation": 'TA1',
                   "full_name": 'Test Author 1',
                   "language": 'grc',
                   "identifier": 'TA1'
                   }
        response = self.client.post('%screate' % self.base_url.format('citations', 'author'), a1_data)
        #we should not be able to create unless we are logged in - 403 Authentication credentials were not provided.
        self.assertEqual(response.status_code, 403)

        #now login
        user = self.addCitationManagerUser({'username': 'testuser', 'password': 'xyz'})
        self.assertTrue(user.has_perm('citations.add_author'))
        client = APIClient()
        login = client.login(username='testuser', password='xyz')
        self.assertEqual(login, True)

        response = client.post('%screate' % self.base_url.format('citations', 'author'), json.dumps(a1_data), content_type='application/json')
        self.assertEqual(response.status_code, 201)
        authors = models.Author.objects.all()
        self.assertTrue(len(authors) == 1)
        self.assertEqual(authors[0].abbreviation, 'TA1')

    #@skip('')
    def test_PATCHAuthorPartial(self):
        #make an author to modify
        a1_data = {"created_by": 'cat',
                   "created_time": str(timezone.now()),
                   "abbreviation": 'TA1',
                   "full_name": 'Test Author 1',
                   "language": 'grc'
                   }
        a1 = models.Author.objects.create(**a1_data)

        response = self.client.patch('%supdate/%s' % (self.base_url.format('citations', 'author'), a1.id), json.dumps({'full_name': 'My new name'}), content_type='application/json')
        #we should not be able to modify unless we are logged in - 403 Authentication credentials were not provided.
        self.assertEqual(response.status_code, 403)

        #now login
        user = self.addCitationManagerUser({'username': 'testuser', 'password': 'xyz'})
        self.assertTrue(user.has_perm('citations.add_author'))
        client = APIClient()
        login = client.login(username='testuser', password='xyz')
        self.assertEqual(login, True)

        response = client.patch('%supdate/%s' % (self.base_url.format('citations', 'author'), a1.id), json.dumps({'full_name': 'My new name'}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        authors = models.Author.objects.all()
        self.assertTrue(len(authors) == 1)
        self.assertEqual(authors[0].full_name, 'My new name')
        self.assertEqual(authors[0].last_modified_by, 'testuser')

    def test_PUTAuthorNoChange(self):
        #make an author to modify
        a1_data = {"created_time": str(timezone.now()),
                   "created_by": 'cat',
                   "last_modified_time": None,
                   "last_modified_by": '',
                   "identifier": 'TA1',
                   "abbreviation": 'TA1',
                   "biblindex_identifiers": None,
                   "biblia_patristica_identifiers": None,
                   "full_name": 'Test Author 1',
                   "born": None,
                   "born_is_approximate": None,
                   "died": None,
                   "died_is_approximate": None,
                   "language": 'grc',
                   "century_active": None,
                   "clavis": '',
                   "place": '',
                   "pseudonymous": None,
                   "anonymous_collective": None,
                   "transmitted_by_another": None,
                   "translated_source": None,
                   "obsolete": None,
                   "comments": '',
                   "created_for_biblindex": None
                   }
        a1 = models.Author.objects.create(**a1_data)
        #we need to get the stored version because otherwise the creation time strings are different!
        response = self.client.get(self.base_url.format('citations', 'author', a1.id))
        response_json = json.loads(response.content.decode('utf8'))

        user = self.addCitationManagerUser({'username': 'testuser', 'password': 'xyz'})
        self.assertTrue(user.has_perm('citations.add_author'))
        client = APIClient()
        login = client.login(username='testuser', password='xyz')
        self.assertEqual(login, True)
        a1_data['id'] = a1.id
        response = client.put('%supdate/%s' % (self.base_url.format('citations', 'author'), a1.id), json.dumps(response_json['results'][0]), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        authors = models.Author.objects.all()
        self.assertTrue(len(authors) == 1)
        self.assertEqual(authors[0].full_name, 'Test Author 1')
        self.assertEqual(authors[0].last_modified_by, '')


    #@skip('')
    def test_PUTAuthorChange(self):
        #make an author to modify
        a1_data = {"created_time": str(timezone.now()),
                   "created_by": 'cat',
                   "last_modified_time": None,
                   "last_modified_by": '',
                   "identifier": 'TA1',
                   "abbreviation": 'TA1',
                   "biblindex_identifiers": None,
                   "biblia_patristica_identifiers": None,
                   "full_name": 'Test Author 1',
                   "born": None,
                   "born_is_approximate": None,
                   "died": None,
                   "died_is_approximate": None,
                   "language": 'grc',
                   "century_active": None,
                   "clavis": '',
                   "place": '',
                   "pseudonymous": None,
                   "anonymous_collective": None,
                   "transmitted_by_another": None,
                   "translated_source": None,
                   "obsolete": None,
                   "comments": '',
                   "created_for_biblindex": None
                   }
        a1 = models.Author.objects.create(**a1_data)
        #we need to get the stored version because otherwise the creation time strings are different!
        response = self.client.get(self.base_url.format('citations', 'author', a1.id))
        response_json = json.loads(response.content.decode('utf8'))
        response_json['results'][0]['full_name'] = 'My new name'

        user = self.addCitationManagerUser({'username': 'testuser', 'password': 'xyz'})
        self.assertTrue(user.has_perm('citations.add_author'))
        client = APIClient()
        login = client.login(username='testuser', password='xyz')
        self.assertEqual(login, True)
        a1_data['id'] = a1.id
        response = client.put('%supdate/%s' % (self.base_url.format('citations', 'author'), a1.id), json.dumps(response_json['results'][0]), content_type='application/json')

        self.assertEqual(response.status_code, 200)
        authors = models.Author.objects.all()
        self.assertTrue(len(authors) == 1)
        self.assertEqual(authors[0].full_name, 'My new name')
        self.assertEqual(authors[0].last_modified_by, 'testuser')
        self.assertNotEqual(authors[0].last_modified_time, None)
