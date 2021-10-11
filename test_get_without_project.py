import json
from django.utils import timezone
from django.test import TestCase
from django.apps import apps
from transcriptions import models as transcription_models
from accounts.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from rest_framework.test import APIClient
# from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory
from unittest import skip


class MyAPITestCase(TestCase):

    def add_user(self, credentials):
        if 'public_name' in credentials:
            public_name = credentials['public_name']
            del credentials['public_name']
            user = User.objects.create_user(**credentials)
            user.save()
            user.public_name = public_name
            user.save()
        else:
            user = User.objects.create_user(**credentials)
            user.save()
        return user

    def add_transcriptions_superuser(self, credentials):
        g1 = Group(name='transcriptions_superusers')
        g1.save()
        if 'public_name' in credentials:
            public_name = credentials['public_name']
            del credentials['public_name']
            user = User.objects.create_user(**credentials)
            user.groups.add(g1)
            user.save()
            user.public_name = public_name
            user.save()
        else:
            user = User.objects.create_user(**credentials)
            user.groups.add(g1)
            user.save()
        return user

    def add_transcription_data(self):

        collection_data = {'identifier': 'NT',
                           'name': 'The New Testament',
                           'abbreviation': 'NT'
                           }
        self.collection = transcription_models.Collection.objects.create(**collection_data)

        work3_data = {'identifier': 'NT_Luke',
                      'name': 'Luke',
                      'collection': self.collection,
                      'sort_value': 3,
                      'abbreviation': 'Luke'
                      }
        self.work3 = transcription_models.Work.objects.create(**work3_data)

        work4_data = {'identifier': 'NT_John',
                      'name': 'John',
                      'collection': self.collection,
                      'sort_value': 4,
                      'abbreviation': 'John'
                      }
        self.work4 = transcription_models.Work.objects.create(**work4_data)

        corpus_data = {'identifier': 'NT_GRC',
                       'collection': self.collection,
                       'language': 'grc'
                       }
        self.corpus = transcription_models.Corpus.objects.create(**corpus_data)

        structure_data = {'work': self.work4,
                          'corpus': self.corpus,
                          'position_in_corpus': 4,
                          'total_chapters': 2,
                          'verses_per_chapter': {'1': 3, '2': 4},
                          'abbreviation': 'John'
                          }
        self.structure = transcription_models.Structure.objects.create(**structure_data)

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

        t2_data = {'identifier': 'NT_GRC_02_John',
                   'corpus': self.corpus,
                   'document_id': '20002',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '02',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 5,
                   'total_unique_verses': 5,
                   # 'user': ,
                   'work': self.work4,
                   'public': True
                   }
        self.t2 = transcription_models.Transcription.objects.create(**t2_data)

        # add users
        self.u1 = self.add_user({'username': 'User1', 'email': 'user1@example.com', 'password': 'secret'})
        self.u2 = self.add_user({'username': 'User2', 'email': 'user2@example.com', 'password': 'secret'})
        self.u3 = self.add_transcriptions_superuser({'username': 'User3', 'email': 'user3@example.com', 'password': 'secret'})
        self.u4 = self.add_user({'username': 'User4', 'email': 'user4@example.com', 'password': 'secret'})

        t3_data = {'identifier': 'NT_GRC_03_John',
                   'corpus': self.corpus,
                   'document_id': '20003',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '03',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 5,
                   'total_unique_verses': 5,
                   'user': self.u1,
                   'work': self.work4,
                   'public': False
                   }
        self.t3 = transcription_models.Transcription.objects.create(**t3_data)

        t4_data = {'identifier': 'NT_GRC_04_John',
                   'corpus': self.corpus,
                   'document_id': '20004',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '04',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 5,
                   'total_unique_verses': 5,
                   'user': self.u2,
                   'work': self.work4,
                   'public': False
                   }
        self.t4 = transcription_models.Transcription.objects.create(**t4_data)

        t5_data = {'identifier': 'NT_GRC_05_John',
                   'corpus': self.corpus,
                   'document_id': '20005',
                   'tei': '<TEI/>',
                   'source': 'upload',
                   'siglum': '05',
                   'document_type': 'majuscule',
                   'language': 'grc',
                   # 'corrector_order': ,
                   'total_verses': 5,
                   'total_unique_verses': 5,
                   'user': self.u3,
                   'work': self.work4,
                   'public': False
                   }
        self.t5 = transcription_models.Transcription.objects.create(**t5_data)


class APIItemListTestsPublicModels(MyAPITestCase):
    base_url = '/api/{}/{}/'

    def test_get_list_returns_json_200(self):
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'work'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_list_returns_correct_data(self):
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'work'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertEqual(response_json['results'][0]['abbreviation'], self.work3.abbreviation)
        self.assertEqual(response_json['results'][1]['abbreviation'], self.work4.abbreviation)

    def test_get_list_returns_correct_data_with_sort(self):
        self.add_transcription_data()
        response = self.client.get('%s?_sort=abbreviation' % self.base_url.format('transcriptions', 'work'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertEqual(response_json['results'][0]['abbreviation'], self.work4.abbreviation)
        self.assertEqual(response_json['results'][1]['abbreviation'], self.work3.abbreviation)

    def test_get_list_returns_correct_data_with_field_filtering(self):
        self.add_transcription_data()
        response = self.client.get('%s?_fields=id,abbreviation' % self.base_url.format('transcriptions', 'work'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertIn('abbreviation', response_json['results'][0])
        self.assertIn('id', response_json['results'][0])
        self.assertNotIn('collection', response_json['results'][0])
        self.assertNotIn('name', response_json['results'][0])

    def test_get_list_returns_correct_data_with_pagination(self):
        self.add_transcription_data()
        response = self.client.get('%s?limit=1' % self.base_url.format('transcriptions', 'work'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 1)


class APIItemDetailTestsPublicModels(MyAPITestCase):
    base_url = '/api/{}/{}/{}'

    def test_get_list_returns_json_200(self):
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'work', self.work3.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')

    def test_get_list_returns_correct_data(self):
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'work', self.work3.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['id'], self.work3.id)
        self.assertEqual(response_json['name'], 'Luke')


class APIItemListTestsPublicOrUserModels(MyAPITestCase):
    base_url = '/api/{}/{}/'

    def test_get_restricted_list_returns_all_public_for_anonymous_user(self):
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertEqual(response_json['results'][0]['identifier'], 'NT_GRC_01_John')
        self.assertEqual(response_json['results'][1]['identifier'], 'NT_GRC_02_John')

    def test_get_restricted_list_returns_all_public_for_anonymous_user_with_sort(self):
        self.add_transcription_data()
        response = self.client.get('%s?_sort=total_verses' % self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertEqual(response_json['results'][0]['identifier'], 'NT_GRC_02_John')
        self.assertEqual(response_json['results'][1]['identifier'], 'NT_GRC_01_John')

    def test_get_restricted_list_returns_all_public_for_anonymous_user_with_filters(self):
        self.add_transcription_data()
        response = self.client.get('%s?total_verses=5' % self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 1)
        self.assertEqual(len(response_json['results']), 1)
        self.assertEqual(response_json['results'][0]['identifier'], 'NT_GRC_02_John')

    def test_get_restricted_list_returns_nothing_for_anonymous_user_if_no_public_items(self):
        self.add_transcription_data()
        # now make the two public ones private
        self.t1.public = False
        self.t1.save()
        self.t2.public = False
        self.t2.save()
        response = self.client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 0)
        self.assertEqual(len(response_json['results']), 0)

    def test_get_restricted_list_returns_public_and_owned_for_logged_in_regular_user(self):
        self.add_transcription_data()
        client = APIClient()
        login = client.login(username='user2@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 3)
        self.assertEqual(len(response_json['results']), 3)
        self.assertEqual(response_json['results'][0]['identifier'], self.t1.identifier)
        self.assertEqual(response_json['results'][1]['identifier'], self.t2.identifier)
        self.assertEqual(response_json['results'][2]['identifier'], self.t4.identifier)

    def test_get_restricted_list_returns_public_only_for_logged_in_regular_user_if_no_owned(self):
        self.add_transcription_data()
        client = APIClient()
        login = client.login(username='user4@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 2)
        self.assertEqual(len(response_json['results']), 2)
        self.assertEqual(response_json['results'][0]['identifier'], self.t1.identifier)
        self.assertEqual(response_json['results'][1]['identifier'], self.t2.identifier)

    def test_get_restricted_list_returns_all_for_app_superuser(self):
        self.add_transcription_data()
        client = APIClient()
        login = client.login(username='user3@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 5)
        self.assertEqual(len(response_json['results']), 5)
        self.assertEqual(response_json['results'][0]['identifier'], self.t1.identifier)
        self.assertEqual(response_json['results'][1]['identifier'], self.t2.identifier)
        self.assertEqual(response_json['results'][2]['identifier'], self.t3.identifier)
        self.assertEqual(response_json['results'][3]['identifier'], self.t4.identifier)
        self.assertEqual(response_json['results'][4]['identifier'], self.t5.identifier)


class APIItemDetailTestsPublicOrUserModels(MyAPITestCase):
    base_url = '/api/{}/{}/{}'

    def setUp(self):
        self.add_transcription_data()

    def test_public_item_returned_for_anonymous_user(self):
        response = self.client.get(self.base_url.format('transcriptions', 'transcription', self.t1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_json['public'], True)
        self.assertEqual(response_json['siglum'], self.t1.siglum)

    def test_404_returned_if_no_item_for_anonymous_user(self):
        # stupidly high id number so its not likely to exist
        response = self.client.get(self.base_url.format('transcriptions', 'transcription', 100001))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_404_returned_for_private_item_for_anonymous_user(self):
        # ideally this would return 401 but that would means much more code being added into the decorator
        # The 404 is returned from the api class view
        response = self.client.get(self.base_url.format('transcriptions', 'transcription', self.t5.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_public_item_returned_for_logged_in_user(self):
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], True)
        self.assertEqual(response_json['siglum'], self.t1.siglum)

    def test_private_item_returned_for_logged_in_user_if_owner(self):
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t3.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], False)
        self.assertEqual(response_json['siglum'], self.t3.siglum)

    def test_404_returned_for_logged_in_user_if_not_owner(self):
        # ideally this would return 403 but the filtering we use for item level permissions
        # means it doesn't get found
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t4.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_404_returned_if_no_item_for_logged_in_user(self):
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', 100001))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_public_item_returned_for_logged_in_superuser(self):
        client = APIClient()
        login = client.login(username='user3@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t1.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], True)
        self.assertEqual(response_json['siglum'], self.t1.siglum)

    def test_private_item_returned_for_logged_in_superuser_if_not_owner(self):
        client = APIClient()
        login = client.login(username='user3@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t3.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], False)
        self.assertEqual(response_json['siglum'], self.t3.siglum)


class APIItemListTestsPublicOrUserNoPublicField(MyAPITestCase):
    base_url = '/api/{}/{}/'
    # NB: There is no model that conforms to being 'public_or_user' availability
    # and with no public field because that should never happen. So I will
    # temporarily make an public one with no public field into a public_or_user one
    # using setUp and tearDown (which is why this test is in its own class)

    def setUp(self):
        transcription_models.Work.AVAILABILITY = 'public_or_user'

    def tearDown(self):
        transcription_models.Work.AVAILABILITY = 'public'

    def test_get_restricted_list_returns_500_for_anonymous_user_if_no_public_field_on_model(self):
        # 500 because it makes no sense and is a server config error really
        self.add_transcription_data()
        response = self.client.get(self.base_url.format('transcriptions', 'work'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 500)


class APIItemListTestsPrivateModels(MyAPITestCase):
    base_url = '/api/{}/{}/'
    # I don't want the tests to be dependent on too many apps
    # As the transcription app is one of the requirements of most of the others
    # it would be good if tests were restricted to this app only.
    # We don't have any private models in this app so instead I will change the
    # status of the transcription model in these tests (and put it back at the end).

    def setUp(self):
        transcription_models.Transcription.AVAILABILITY = 'private'

    def tearDown(self):
        transcription_models.Transcription.AVAILABILITY = 'public_or_user'

    def test_get_private_list_returns_401_for_anonymous_user(self):
        response = self.client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 401)

    def test_get_private_list_returns_owned_only_for_logged_in_regular_user(self):
        self.add_transcription_data()
        client = APIClient()
        login = client.login(username='user2@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 1)
        self.assertEqual(len(response_json['results']), 1)
        self.assertEqual(response_json['results'][0]['identifier'], self.t4.identifier)

    def test_get_private_list_returns_all_for_app_superuser(self):
        self.add_transcription_data()
        client = APIClient()
        login = client.login(username='user3@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription'))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['count'], 5)
        self.assertEqual(len(response_json['results']), 5)
        self.assertEqual(response_json['results'][0]['identifier'], self.t1.identifier)
        self.assertEqual(response_json['results'][1]['identifier'], self.t2.identifier)
        self.assertEqual(response_json['results'][2]['identifier'], self.t3.identifier)
        self.assertEqual(response_json['results'][3]['identifier'], self.t4.identifier)
        self.assertEqual(response_json['results'][4]['identifier'], self.t5.identifier)


class APIItemDetailTestsPrivateModels(MyAPITestCase):
    base_url = '/api/{}/{}/{}'
    # I don't want the tests to be dependent on too many apps
    # As the transcription app is one of the requirements of most of the others
    # it would be good if tests were restricted to this app only.
    # We don't have any private models in this app so instead I will change the
    # status of the transcription model in these tests (and put it back at the end).

    def setUp(self):
        transcription_models.Work.AVAILABILITY = 'public_or_user'
        self.add_transcription_data()

    def tearDown(self):
        transcription_models.Work.AVAILABILITY = 'public'

    def test_404_returned_if_no_item_for_anonymous_user(self):
        # use stupidly high id number so its not likely to exist
        response = self.client.get(self.base_url.format('transcriptions', 'transcription', 100001))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_404_returned_for_existing_item_for_anonymous_user(self):
        # ideally this would return 401
        response = self.client.get(self.base_url.format('transcriptions', 'transcription', self.t5.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_private_item_returned_for_logged_in_user_if_owner(self):
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t3.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], False)
        self.assertEqual(response_json['user'], self.u1.id)
        self.assertEqual(response_json['siglum'], self.t3.siglum)

    def test_404_returned_for_logged_in_user_if_not_owner(self):
        # ideally this would return 403
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t5.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_404_returned_if_no_item_for_logged_in_user(self):
        client = APIClient()
        login = client.login(username='user1@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', 100001))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response.status_code, 404)

    def test_private_item_returned_for_logged_in_superuser_if_not_owner(self):
        client = APIClient()
        login = client.login(username='user3@example.com', password='secret')
        self.assertEqual(login, True)
        response = client.get(self.base_url.format('transcriptions', 'transcription', self.t3.id))
        response_json = json.loads(response.content.decode('utf8'))
        self.assertEqual(response_json['public'], False)
        self.assertNotEqual(response_json['user'], self.u3.id)
        self.assertEqual(response_json['siglum'], self.t3.siglum)
