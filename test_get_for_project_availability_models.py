import json
from django.utils import timezone
from django.test import TestCase
from django.apps import apps
from transcriptions import models as transcription_models
from collation import models as collation_models
from citations import models as citation_models
from accounts.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory
from unittest import skip


class MyAPITestCase(TestCase):

    def add_user(self, credentials):
        if 'display_name' in credentials:
            display_name = credentials['display_name']
            del credentials['display_name']
            user = User.objects.create_user(**credentials)
            user.save()
            user.display_name = display_name
            user.save()
        else:
            user = User.objects.create_user(**credentials)
            user.save()
        return user

    def add_collation_superuser(self, credentials):
        g1 = Group(name='collation_superusers')
        g1.save()
        if 'display_name' in credentials:
            display_name = credentials['display_name']
            del credentials['display_name']
            user = User.objects.create_user(**credentials)
            user.groups.add(g1)
            user.save()
            user.display_name = display_name
            user.save()
        else:
            user = User.objects.create_user(**credentials)
            user.groups.add(g1)
            user.save()
        return user

    def add_collation_data(self):

        collection_data = {'identifier': 'NT',
                           'name': 'The New Testament',
                           'abbreviation': 'NT'
                           }
        self.collection = transcription_models.Collection.objects.create(**collection_data)

        corpus_data = {'identifier': 'NT_GRC',
                       'collection': self.collection,
                       'language': 'grc'
                       }
        self.corpus = transcription_models.Corpus.objects.create(**corpus_data)

        work2_data = {'identifier': 'NT_Mark',
                      'name': 'Mark',
                      'collection': self.collection,
                      'sort_value': 2,
                      'abbreviation': 'Mark'
                      }
        self.work2 = transcription_models.Work.objects.create(**work2_data)

        work4_data = {'identifier': 'NT_John',
                      'name': 'John',
                      'collection': self.collection,
                      'sort_value': 4,
                      'abbreviation': 'John'
                      }
        self.work4 = transcription_models.Work.objects.create(**work4_data)

        t1_data = {'identifier': 'NT_GRC_01_John',
                   'corpus': self.corpus,
                   'document_id': '20001',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '01',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 7,
                   'total_unique_verses': 6,
                   # 'user': ,
                   'work': self.work4,
                   'public': True
                   }
        self.t1 = transcription_models.Transcription.objects.create(**t1_data)

        t2_data = {'identifier': 'NT_GRC_01_mark',
                   'corpus': self.corpus,
                   'document_id': '20002',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '01',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 7,
                   'total_unique_verses': 6,
                   # 'user': ,
                   'work': self.work2,
                   'public': True
                   }
        self.t2 = transcription_models.Transcription.objects.create(**t2_data)

        self.u1 = self.add_user({'username': 'User1', 'password': 'secret'})
        self.u2 = self.add_user({'username': 'User2', 'password': 'secret'})
        self.u3 = self.add_user({'username': 'User3', 'password': 'secret'})
        self.u4 = self.add_user({'username': 'User4', 'password': 'secret'})
        self.u5 = self.add_collation_superuser({'username': 'User5', 'password': 'secret'})

        project1_data = {'identifier': 'ECM_04',
                         'name': 'ECM John',
                         'collection': self.collection,
                         'corpus': self.corpus,
                         'language': 'grc',
                         'work': self.work4,
                         'managing_editor': self.u1,
                         'basetext': self.t1,
                         'configuration': {}
                         }
        self.p1 = collation_models.Project.objects.create(**project1_data)
        self.p1.editors.add(self.u2)
        self.p1.editors.add(self.u3)

        self.p1.witnesses.add(self.t1)

        project2_data = {'identifier': 'ECM_02',
                         'name': 'ECM Mark',
                         'collection': self.collection,
                         'corpus': self.corpus,
                         'language': 'grc',
                         'work': self.work2,
                         'managing_editor': self.u4,
                         'basetext': self.t2,
                         'configuration': {}
                         }
        self.p2 = collation_models.Project.objects.create(**project2_data)
        self.p2.editors.add(self.u3)
        self.p2.editors.add(self.u5)

        self.p2.witnesses.add(self.t2)

        decision1_data = {'type': 'regularisation',
                          'scope': 'once',
                          'classification': 'regularised',
                          'context': {'unit':  'John.1.1', 'witness': '01', 'word': 2},
                          'conditions': {},
                          'exceptions': [],
                          't': 'orig',
                          'n': 'norm',
                          'user': self.u1,
                          'project': self.p1
                          }
        self.d1 = collation_models.Decision.objects.create(**decision1_data)

        decision2_data = {'type': 'regularisation',
                          'scope': 'once',
                          'classification': 'regularised',
                          'context': {'unit':  'John.1.1', 'witness': '01', 'word': 4},
                          'conditions': {},
                          'exceptions': [],
                          't': 'orig',
                          'n': 'norm',
                          'user': self.u2,
                          'project': self.p1
                          }
        self.d2 = collation_models.Decision.objects.create(**decision2_data)

        decision3_data = {'type': 'regularisation',
                          'scope': 'once',
                          'classification': 'regularised',
                          'context': {'unit':  'John.1.1', 'witness': '01', 'word': 4},
                          'conditions': {},
                          'exceptions': [],
                          't': 'orig',
                          'n': 'norm',
                          'user': self.u3,
                          'project': self.p2
                          }
        self.d3 = collation_models.Decision.objects.create(**decision3_data)

        collation1_data = {'identifier': 'John.1.1_regularised_%s_%s' % (self.u2.id, self.p1.id),
                           'work': self.work4,
                           'chapter_number': 1,
                           'verse_number': 1,
                           'context': 'John.1.1',
                           'structure': {},
                           'display_settings': {},
                           'data_settings': {},
                           'algorithm_settings': {},
                           'user': self.u2,
                           'project': self.p1,
                           'status': 'regularised'
                           }
        self.c1 = collation_models.Collation.objects.create(**collation1_data)

        collation2_data = {'identifier': 'John.1.1_regularised_%s_%s' % (self.u1.id, self.p1.id),
                           'work': self.work4,
                           'chapter_number': 1,
                           'verse_number': 1,
                           'context': 'John.1.1',
                           'structure': {},
                           'display_settings': {},
                           'data_settings': {},
                           'algorithm_settings': {},
                           'user': self.u1,
                           'project': self.p1,
                           'status': 'regularised'
                           }
        self.c2 = collation_models.Collation.objects.create(**collation2_data)


class APIItemListTestsProjectsBadConfiguration(MyAPITestCase):
    base_url = '/api/{}/{}/'
    # There are no models which fit this so I manipulating a transcription model
    # which will allow the error to be tested
    # none of the transcription or collation models can be used because of reverse
    # foreign keys to project which show up as normal keys so uaing citation model here

    def setUp(self):
        citation_models.Citation.AVAILABILITY = 'project'

    def tearDown(self):
        citation_models.Citation.AVAILABILITY = 'public'

    def test_error_returned_if_model_availability_project_and_no_project_flag(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User2', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('citations', 'citation'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response_json['message'], 'Internal server error - model configuation incompatible with API (code 10003)')


class APIItemListTestsProjectModels(MyAPITestCase):
    base_url = '/api/{}/{}/'

    def test_get_project_list_returns_401_for_anonymous_user(self):
        self.add_collation_data()
        response = self.client.get(self.base_url.format('collation', 'decision'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_project_list_returns_400_if_no_project__id_in_request(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User2', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('collation', 'decision'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_json['message'], 'Query not complete - Project must be specified')

    def test_get_project_list_returns_decisions_if_user_in_project_users(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User2', password='secret')
        self.assertEqual(login, True)
        response = client.get('%s?project__id=%s' % (self.base_url.format('collation', 'decision'), self.p1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 200)
        # user 2 is only in p1 and p1 has 2 decisions so show both (only one is owned by u2)
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)

    def test_get_project_list_returns_decisions_if_user_in_multiple_projects(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User3', password='secret')
        self.assertEqual(login, True)
        response = client.get('%s?project__id=%s' % (self.base_url.format('collation', 'decision'), self.p1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 200)
        # user 3 is in 2 projects but is asking for p1 and p1 has 2 decisions so show both
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)

    def test_get_project_list_returns_no_decisions_if_user_not_in_projects(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User4', password='secret')
        self.assertEqual(login, True)
        response = client.get('%s?project__id=%s' % (self.base_url.format('collation', 'decision'), self.p1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 200)
        # user4 is not in any projects so no data returned
        self.assertEqual(response_json['count'], 0)
        self.assertEqual(len(response_json['results']), 0)

    def test_get_project_list_returns_all_decisions_if_user_is_superuser_but_not_in_requested_project(self):
        self.add_collation_data()
        client = APIClient()
        login = client.login(username='User5', password='secret')
        self.assertEqual(login, True)
        response = client.get('%s?project__id=%s' % (self.base_url.format('collation', 'decision'), self.p1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 200)
        # user5 is not in requested project but is superuser so gets decisions for this project only
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
