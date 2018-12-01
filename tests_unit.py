import json
from django.utils import timezone
from django.test import TestCase
from django.test.client import RequestFactory
from rest_framework.request import Request
from django.db.models import Q
from citations import models
from api import views
from api.views import SelectPagePaginator
from citations import serializers
from api.serializers import SimpleSerializer

class APIHelperTests(TestCase):

    def test_getCount(self):
        #with a query set
        a1_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA1',
                   'full_name': 'Test Author 1',
                   'language': 'grc'
                   }
        a1 = models.Author.objects.create(**a1_data)
        a2_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA2',
                   'full_name': 'Test Author 2',
                   'language': 'lat'
                   }
        a2 = models.Author.objects.create(**a2_data)

        query_set = models.Author.objects.all()
        count = views._getCount(query_set)
        self.assertEqual(count, 2)

        #and with a list
        test_list = ['item', 'item']
        count = views._getCount(test_list)
        self.assertEqual(count, 2)

    def test_getQueryTuple(self):
        #this is testing the code and a few random selections from the operator_lookup dictionary
        #it is not really designed to test the dictionary - I think it is a constant
        expected_return = ('full_name__istartswith', 'Test')
        query_tuple = views.getQueryTuple('TextField', 'full_name', 'Test*|i')
        self.assertEqual(expected_return, query_tuple)

        expected_return = ('born', False)
        query_tuple = views.getQueryTuple('BooleanField', 'born', 'false')
        self.assertEqual(expected_return, query_tuple)

        expected_return = ('source__contains', ['biblindex'])
        query_tuple = views.getQueryTuple('ArrayField', 'source', 'biblindex')
        self.assertEqual(expected_return, query_tuple)

        expected_return = ('test', 'value')
        query_tuple = views.getQueryTuple('OtherField', 'test', 'value')
        self.assertEqual(expected_return, query_tuple)

        expected_return = None
        query_tuple = views.getQueryTuple('OtherField', 'test', '')
        self.assertEqual(expected_return, query_tuple)

    def test_getRelatedModel(self):
        model_instance = views.getRelatedModel(models.Work, 'author__abbreviation')
        self.assertEqual(model_instance, models.Author)

    def test_getRelatedFieldType(self):
        related_field_type = views.getRelatedFieldType(models.Work, 'title')
        self.assertEqual(related_field_type, None)

        related_field_type = views.getRelatedFieldType(models.Work, 'author__abbreviation')
        self.assertEqual(related_field_type, 'TextField')

        related_field_type = views.getRelatedFieldType(models.Edition, 'work__author__abbreviation')
        self.assertEqual(related_field_type, 'TextField')

        related_field_type = views.getRelatedFieldType(models.Work, 'author__nonsense')
        self.assertEqual(related_field_type, None)

    def test_getFieldFilters(self):
        rf = RequestFactory()

        #I will test most of the code with simple author abbreviation searches
        #it gives us decent line coverage and keeps the test code readable
        #to get better branch combination coverage there probably needs to be some complex test cases

        #positive value in filter mode
        expected_query = Q()
        expected_query &= Q(('abbreviation__startswith', 'T'))
        request = rf.get('/api/citations/author?abbreviation=T*')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Author, 'filter')
        self.assertEqual(str(expected_query), str(query))

        #negative value in exclude mode
        expected_query = Q()
        expected_query &= Q(('abbreviation__startswith', 'T'))
        request = rf.get('/api/citations/author?abbreviation=!T*')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Author, 'exclude')
        self.assertEqual(str(expected_query), str(query))

        #negative value in filter mode - which should return an empty query
        expected_query = Q()
        request = rf.get('/api/citations/author?abbreviation=!T*')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Author, 'filter')
        self.assertEqual(str(expected_query), str(query))

        #now test list filters
        expected_query = Q()
        subquery = Q()
        subquery |= Q(('abbreviation', 'TA1'))
        subquery |= Q(('abbreviation', 'TA2'))
        expected_query &= subquery
        request = rf.get('/api/citations/author?abbreviation=TA1,TA2')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Author, 'filter')
        self.assertEqual(str(expected_query), str(query))

        #positive value in filter mode with foreign key
        expected_query = Q()
        expected_query &= Q(('author__abbreviation__startswith', 'T'))
        request = rf.get('/api/citations/work/?author__abbreviation=T*')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Work, 'filter')
        self.assertEqual(str(expected_query), str(query))

        #positive value in filter mode with nonsense field
        #should produce empty query so it does not stop results returning
        expected_query = Q()
        expected_query &= Q()
        request = rf.get('/api/citations/work/?nonsense=T*')
        requestQuery = dict(request.GET)
        query = views.getFieldFilters(requestQuery, models.Work, 'filter')
        self.assertEqual(str(expected_query), str(query))

    def test_SelectPagePaginator(self):
        #with a query set
        a1_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA1',
                   'full_name': 'Test Author 1',
                   'language': 'grc'
                   }
        a1 = models.Author.objects.create(**a1_data)
        a2_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA2',
                   'full_name': 'Test Author 2',
                   'language': 'lat'
                   }
        a2 = models.Author.objects.create(**a2_data)
        a3_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA3',
                   'full_name': 'Test Author 3',
                   'language': 'lat'
                   }
        a3 = models.Author.objects.create(**a3_data)

        rf = RequestFactory()
        request = Request(rf.get('/api/citations/author/?limit=2'))
        paginator = SelectPagePaginator()
        result = paginator.paginate_queryset_and_get_page(models.Author.objects.all(), request, index_required=3)
        self.assertIn(a3, result[0])
        self.assertEqual(result[1], 2)

        #if we are showing all records anyway (this will actually default to 100 because of your default)
        request = Request(rf.get('/api/citations/author'))
        paginator = SelectPagePaginator()
        result = paginator.paginate_queryset_and_get_page(models.Author.objects.all(), request, index_required=3)
        self.assertEqual(len(result[0]), 3)

        #if we are showing all records anyway (this will actually default to 100 because of your default)
        request = Request(rf.get('/api/citations/works'))
        paginator = SelectPagePaginator()
        result = paginator.paginate_queryset_and_get_page(models.Work.objects.all(), request, index_required=3)
        self.assertEqual(result, [])


#these are tests for specific functions in the model class I want to check
#rather than testing the whole view at once
class ItemListUnitTests(TestCase):

    def test_get_serializer_class(self):

        item_list_view = views.ItemList()
        item_list_view.kwargs = {'app': 'citations', 'model': 'citation'}
        serializer_class = item_list_view.get_serializer_class()
        self.assertEqual(serializer_class, serializers.CitationSerializer)

        item_list_view = views.ItemList()
        item_list_view.kwargs = {'app': 'citations', 'model': 'privatecitation'}
        serializer_class = item_list_view.get_serializer_class()
        self.assertEqual(serializer_class, serializers.PrivateCitationSerializer)

    def test_get_offset_required(self):
        #with a query set
        a1_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA1',
                   'full_name': 'Test Author 1',
                   'language': 'grc'
                   }
        a1 = models.Author.objects.create(**a1_data)
        a2_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA2',
                   'full_name': 'My Test Author 2',
                   'language': 'lat'
                   }
        a2 = models.Author.objects.create(**a2_data)
        a3_data = {'created_by': 'cat',
                   'created_time': timezone.now(),
                   'abbreviation': 'TA3',
                   'full_name': 'A Test Author 3',
                   'language': 'lat'
                   }
        a3 = models.Author.objects.create(**a3_data)
        item_list_view = views.ItemList()

        queryset = models.Author.objects.all().order_by('full_name')
        position = item_list_view.get_offset_required(queryset, a1.id)
        self.assertEqual(position, 2)

        position = item_list_view.get_offset_required(queryset, a3.id)
        self.assertEqual(position, 0)

        position = item_list_view.get_offset_required(queryset, 99)
        self.assertEqual(position, 0)

class ItemDetailUnitTests(TestCase):

    def test_get_serializer_class(self):

        item_detail_view = views.ItemDetail()
        item_detail_view.kwargs = {'app': 'citations', 'model': 'citation'}
        serializer_class = item_detail_view.get_serializer_class()
        self.assertEqual(serializer_class, serializers.CitationSerializer)

        item_detail_view = views.ItemList()
        item_detail_view.kwargs = {'app': 'citations', 'model': 'privatecitation'}
        serializer_class = item_detail_view.get_serializer_class()
        self.assertEqual(serializer_class, serializers.PrivateCitationSerializer)
