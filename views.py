from django.http import Http404
from django.apps import apps
from accounts.models import User
from accounts.serializers import UserSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import mixins
from rest_framework import generics
from rest_framework import permissions
from api.serializers import SimpleSerializer
from rest_framework.renderers import JSONRenderer
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from django.db.models.deletion import ProtectedError
from django.db.models.deletion import Collector
from django.contrib.admin.utils import NestedObjects
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.decorators import detail_route
import re
import importlib
import datetime
import json as jsontools
import copy
from django.views.decorators.http import etag
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from django.http import JsonResponse
from api.decorators import apply_model_get_restrictions


def get_etag(request, app=None, model=None, pk=None):
    try:
        etag = str(apps.get_model(app, model).objects.get(pk=pk).version_number)
        return etag
    except AttributeError:
        return "*"


def _getCount(queryset):
    """
    Determine an object count, supporting either querysets or regular lists.
    """
    try:
        return queryset.count()
    except (AttributeError, TypeError):
        return len(queryset)


def getQueryTuple(field_type, field, value):
    operator_lookup = {
                       'CharField': [[r'^([^*|]+)\*$', '__startswith'], [r'^([^*|]+)\*\|i$', '__istartswith'],
                                     [r'^\*([^*|]+)$', '__endswith'], [r'^\*([^*|]+)\|i$', '__iendswith'],
                                     [r'^\*([^*|]+)\*$', '__contains'], [r'^\*([^*|]+)\*\|i$', '__icontains'],
                                     [r'^([^*|]+)\|i$', '__iexact']],
                       'TextField': [[r'^([^*|]+)\*$', '__startswith'], [r'^([^*|]+)\*\|i$', '__istartswith'],
                                     [r'^\*([^*|]+)$', '__endswith'], [r'^\*([^*|]+)\|i$', '__iendswith'],
                                     [r'^\*([^*|]+)\*$', '__contains'], [r'^\*([^*|]+)\*\|i$', '__icontains'],
                                     [r'^([^*|]+)\|i$', '__iexact']],
                       'IntegerField': [[r'^>([0-9]+)$', '__gt'], [r'^>=([0-9]+)$', '__gte'],
                                        [r'^<([0-9]+)$', '__lt'], [r'^<=([0-9]+)$', '__lte']],
                       'ArrayField': [[r'^(.+)$', '__contains']],
                       'NullBooleanField': [[r'^([tT]rue)$', '', True], [r'^([fF]alse)$', '', None]],
                       'BooleanField': [[r'^([tT]rue)$', '', True], [r'^([fF]alse)$', '', False]],
                       # this assumes that the search is for the value in the JSON field and that that
                       # values is text or char there are more searches specific to JSON fields such as
                       # presence of key which we do not support yet
                       'JSONField': [[r'^([^*|]+)\*$', '__startswith'], [r'^([^*|]+)\*\|i$', '__istartswith'],
                                     [r'^\*([^*|]+)$', '__endswith'], [r'^\*([^*|]+)\|i$', '__iendswith'],
                                     [r'^\*([^*|]+)\*$', '__contains'], [r'^\*([^*|]+)\*\|i$', '__icontains'],
                                     [r'^([^*|]+)\|i$', '__iexact']],
                       'ForeignKey': [],
                       'ManyToManyField': []
                       }
    options = []

    if field_type in operator_lookup:
        options = operator_lookup[field_type]
    for option in options:
        if re.search(option[0], value):
            if len(option) > 2:
                return ('%s%s' % (field, option[1]), option[2])
            elif field_type == 'ArrayField':
                return ('%s%s' % (field, option[1]), [value])
            else:
                return ('%s%s' % (field, option[1]), re.sub(option[0], '\\1', value))
    if value != '' and field != '' and field_type:
        return (field, value)
    return None


def getRelatedModel(model_instance, field_name):
    if '__' in field_name:
        field_name = field_name.split('__')[0]
    return model_instance._meta.get_field(field_name).related_model


def getRelatedFieldType(model, field):
    if len(field.split('__')) < 2:
        return None
    related_model = getRelatedModel(model, field)
    if related_model.__name__ == 'User':  # this is nasty but its not safe to rely on duck typing here
        related_fields = {'id': 'AutoField'}  # TODO: complete a full list of User fields
    else:
        related_fields = related_model.get_fields()
    if '__' in field and field.split('__')[1] in related_fields:
        field_type = related_fields[field.split('__')[1]]
        if field_type != 'ForeignKey':
            return field_type
        else:
            return getRelatedFieldType(related_model, '__'.join(field.split('__')[1:]))
    else:
        return None


def getFieldFilters(queryDict, model_instance, type):
    model_fields = model_instance.get_fields()
    query = Q()
    query_tuple = None
    for field in queryDict:
        if field == 'project':
            # project used to be in the list below and I have removed it because
            # we might need to filter by project for some things
            print('Project used to be filtered out - check why it was needed and adjust query if necessary!')
        if field not in ['offset', 'limit'] and field[0] != '_':
            if field in model_fields:
                field_type = model_fields[field]
            elif '__' in field and field.split('__')[0] in model_fields:
                field_type = model_fields[field.split('__')[0]]
            else:
                field_type = None
            if field_type == 'ForeignKey':
                field_type = getRelatedFieldType(model_instance, field)
            value_list = queryDict[field]
            # we do not support negation with OR so these are only done when we are filtering
            # I just don't think or-ing negatives on the same field key makes any sense
            for value in value_list:
                if ',' in value:
                    if type == 'filter':
                        subquery = Q()
                        for part in value.split(','):
                            if part != '':
                                query_tuple = getQueryTuple(field_type, field, part)
                                if query_tuple:
                                    subquery |= Q(query_tuple)
                                    query_tuple = None
                        query &= subquery
                else:
                    if value != '':
                        if type == 'exclude' and value[0] == '!':
                            query_tuple = getQueryTuple(field_type, field, value[1:])
                        elif type == 'filter' and value[0] != '!':
                            query_tuple = getQueryTuple(field_type, field, value)
                        if query_tuple:
                            query &= Q(query_tuple)
                            query_tuple = None
    return query


class SelectPagePaginator(LimitOffsetPagination):

    def paginate_queryset_and_get_page(self, queryset, request, view=None, index_required=None):
        self.limit = self.get_limit(request)

        if self.limit is None:
            return None

        self.offset = self.get_offset(request)
        self.count = _getCount(queryset)

        if index_required is not None:
            page = int(index_required/self.limit)
            self.offset = page*self.limit

        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []

        return (list(queryset[self.offset:self.offset + self.limit]), self.offset)


def getUser(request):
    serializer = UserSerializer(request.user)
    return JsonResponse(serializer.data)


"""
While these classes generally use model classes from django-rest-framework there is quite a lot of overriding in
order to make them generic enough to not require one per model.

I have tried to specify things in the model itself and then call them from here

"""


@method_decorator(apply_model_get_restrictions, name='dispatch')
class ItemList(generics.ListAPIView):

    permission_classes = (permissions.AllowAny, )
    renderer_classes = (JSONRenderer, )
    pagination_class = SelectPagePaginator

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except:
            serializer = SimpleSerializer
        return serializer

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        if 'fields' in self.kwargs:
            kwargs['fields'] = self.kwargs['fields']
        return serializer_class(*args, **kwargs)

    def get_queryset(self, fields=None):

        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            related_keys = target.RELATED_KEYS
        except AttributeError:
            related_keys = [None]
        # we only need to use select_related here (and not use prefetch_related) as the lists
        # only show data from a single model and its Foreign keys

        hits = target.objects.all().select_related(*related_keys)

        if 'supplied_filter' in self.kwargs and self.kwargs['supplied_filter'] is not None:
            hits = hits.filter(self.kwargs['supplied_filter'])

        requestQuery = dict(self.request.GET)

        filter_query = getFieldFilters(requestQuery, target, 'filter')
        exclude_query = getFieldFilters(requestQuery, target, 'exclude')
        hits = hits.exclude(exclude_query).filter(filter_query)

        # override fields if required - only used for internal calls from other apps
        if fields:
            self.kwargs['fields'] = fields.split(',')
        elif '_fields' in self.request.GET:
            self.kwargs['fields'] = self.request.GET.get('_fields').split(',')
        # sort them if needed
        if '_sort' in self.request.GET:
            sort_by = self.request.GET.get('_sort').split(',')
            hits = hits.order_by(*sort_by)
        return hits

    def get(self, request, app, model, supplied_filter=None):
        return self.list(request)

    def get_offset_required(self, queryset, item_id):
        try:
            item_position = list(queryset.values_list('id', flat=True)).index(int(item_id))
        except:
            item_position = 0
        return item_position

    def paginate_queryset_and_get_page(self, queryset, index_required=None):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        if index_required is not None:
            return self.paginator.paginate_queryset_and_get_page(queryset, self.request, view=self, index_required=index_required)

# If you do also need post here then this will work - it is disabled now until we need it
#     def post(self, request, app, model):
#         return self.get(request, app, model)

    def get_objects(self, request, **kwargs):
        self.kwargs = kwargs
        self.request = request
        if '_fields' in self.kwargs:
            queryset = self.get_queryset(fields=self.kwargs['_fields'])
        else:
            queryset = self.get_queryset()

        offset = None
        if '_show' in request.GET:
            index = self.get_offset_required(queryset, request.GET.get('_show'))
            (paginated_query_set, offset) = self.paginate_queryset_and_get_page(queryset, index_required=index)
        else:
            index = None
            paginated_query_set = self.paginate_queryset(queryset)
        resp = self.get_paginated_response(paginated_query_set)
        resp.data = dict(resp.data)
        if offset is not None:
            resp.data['offset'] = offset
        return resp.data


# TODO: the get for this for private models has to have a fields keyword in get
# because permissions.DjangoModelPermissions, runs get_queryset before running get
# and get_queryset adds fields to self.kwargs. it doesn't seem to have broken anything
class PrivateItemList(generics.ListAPIView):

    permission_classes = (permissions.DjangoModelPermissions, )
    renderer_classes = (JSONRenderer, )
    pagination_class = SelectPagePaginator

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except:
            serializer = SimpleSerializer
        return serializer

    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        if 'fields' in self.kwargs:
            kwargs['fields'] = self.kwargs['fields']
        return serializer_class(*args, **kwargs)

    def get_queryset(self, fields=None):

        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            related_keys = target.RELATED_KEYS
        except:
            related_keys = [None]
        # we only need to use select_related here (and not use prefetch_related) as the lists only show
        # data from a single model and its Foreign keys
        hits = target.objects.all().select_related(*related_keys)

        if 'supplied_filter' in self.kwargs and self.kwargs['supplied_filter'] is not None:
            hits = hits.filter(self.kwargs['supplied_filter'])
        requestQuery = dict(self.request.GET)
        filter_query = getFieldFilters(requestQuery, target, 'filter')
        exclude_query = getFieldFilters(requestQuery, target, 'exclude')
        hits = hits.exclude(exclude_query).filter(filter_query)

        # override fields if required - only used for internal calls from other apps
        if fields:
            self.kwargs['fields'] = fields.split(',')
        elif '_fields' in self.request.GET:
            self.kwargs['fields'] = self.request.GET.get('_fields').split(',')

        # sort them if needed
        if '_sort' in self.request.GET:
            sort_by = self.request.GET.get('_sort').split(',')
            hits = hits.order_by(*sort_by)
        return hits

    def get(self, request, app, model, fields=None):
        return self.list(request)

    def get_offset_required(self, queryset, item_id):
        try:
            item_position = list(queryset.values_list('id', flat=True)).index(int(item_id))
        except:
            item_position = 0
        return item_position

    def paginate_queryset_and_get_page(self, queryset, index_required=None):
        """
        Return a single page of results, or `None` if pagination is disabled.
        """
        if self.paginator is None:
            return None
        if index_required is not None:
            return self.paginator.paginate_queryset_and_get_page(queryset, self.request, view=self, index_required=index_required)

# If you do also need post here then this will work - it is disabled now until we need it
#     def post(self, request, app, model):
#         return self.get(request, app, model)

    def get_objects(self, request, **kwargs):
        self.kwargs = kwargs
        self.request = request
        if '_fields' in self.kwargs:
            queryset = self.get_queryset(fields=self.kwargs['_fields'])
        else:
            queryset = self.get_queryset()

        offset = None
        if '_show' in request.GET:
            index = self.get_offset_required(queryset, request.GET.get('_show'))
            (paginated_query_set, offset) = self.paginate_queryset_and_get_page(queryset, index_required=index)
        else:
            index = None
            paginated_query_set = self.paginate_queryset(queryset)
        resp = self.get_paginated_response(paginated_query_set)
        resp.data = dict(resp.data)
        if offset is not None:
            resp.data['offset'] = offset
        return resp.data


@method_decorator(apply_model_get_restrictions, name='dispatch')
class ItemDetail(generics.RetrieveAPIView):

    permission_classes = (permissions.AllowAny, )
    renderer_classes = (JSONRenderer, )

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            prefetch_keys = target.PREFETCH_KEYS
        except:
            prefetch_keys = [None]
        try:
            related_keys = target.RELATED_KEYS
        except:
            related_keys = [None]
        hits = target.objects.all().select_related(*related_keys).prefetch_related(*prefetch_keys)
        if 'supplied_filter' in self.kwargs and self.kwargs['supplied_filter'] is not None:
            hits = hits.filter(self.kwargs['supplied_filter'])
        return hits

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except:
            serializer = SimpleSerializer
        return serializer

    # this overrides the function provided by the drf RetrieveModelMixin
    # so I can set the etag header in the response
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        try:
            return Response(serializer.data, headers={'etag': '%d' % instance.version_number})
        except AttributeError:
            return Response(serializer.data)

    # this one is used by the regular api calls
    def get(self, request, app, model, pk, supplied_filter=None):
        return self.retrieve(request)

# If you do also need post here then this will work - it is disabled now until we need it
#     def post(self, request, app, model, pk):
#         return self.get(request, app, model, pk)

    # this one is used by the html interface
    def get_item(self, request, **kwargs):
        self.kwargs = kwargs
        # this next line is what returns the 500 error if the item cannot be viewed
        # in the project - it never gets beyond this line
        item = self.get_queryset().get(pk=kwargs['pk'])
        if 'format' in kwargs and kwargs['format'] == 'json':
            serializer = self.get_serializer_class()
            json = JSONRenderer().render(serializer(item).data).decode('utf-8')
            return json
        elif 'format' in kwargs and kwargs['format'] == 'html':
            return item
        else:
            # this one is used only when we try to get the object we just created from
            # the createItem view in this file the response in that view renders it to json
            serializer = self.get_serializer_class()
            return serializer(item).data


class PrivateItemDetail(generics.RetrieveAPIView):

    permission_classes = (permissions.DjangoModelPermissions, )
    renderer_classes = (JSONRenderer, )

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            prefetch_keys = target.PREFETCH_KEYS
        except:
            prefetch_keys = [None]
        try:
            related_keys = target.RELATED_KEYS
        except:
            related_keys = [None]
        hits = target.objects.all().select_related(*related_keys).prefetch_related(*prefetch_keys)
        if 'supplied_filter' in self.kwargs and self.kwargs['supplied_filter'] is not None:
            hits = hits.filter(self.kwargs['supplied_filter'])
        return hits

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except:
            serializer = SimpleSerializer
        return serializer

    # this one is used by the regular api calls
    def get(self, request, app, model, pk):
        return self.retrieve(request)

# If you do also need post here then this will work - it is disabled now until we need it
#     def post(self, request, app, model, pk):
#         return self.get(request, app, model, pk)

    # this one is used by the html interface
    def get_item(self, request, **kwargs):
        self.kwargs = kwargs
        # this next line is what returns the 500 error if the item cannot be viewed in the
        # project - it never gets beyond this line
        item = self.get_queryset().get(pk=kwargs['pk'])
        if 'format' in kwargs and kwargs['format'] == 'json':
            serializer = self.get_serializer_class()
            json = JSONRenderer().render(serializer(item).data).decode('utf-8')
            return json
        elif 'format' in kwargs and kwargs['format'] == 'html':
            return item
        else:
            # this one is used only when we try to get the object we just created from the createItem view in this file
            # the response in that view renders it to json
            serializer = self.get_serializer_class()
            return serializer(item).data


@method_decorator(etag(get_etag), name='dispatch')
class ItemUpdate(generics.UpdateAPIView):

    permission_classes = (permissions.DjangoModelPermissions, )

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_name = target.SERIALIZER
        serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        return serializer

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_class = self.get_serializer_class()
        fields = copy.deepcopy(target.REQUIRED_FIELDS)
        for key in self.request.data:
            if key not in fields:
                fields.append(key)
        kwargs['fields'] = fields
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def ordered(self, obj):
        if isinstance(obj, dict):
            return sorted((k, ordered(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(ordered(x) for x in obj)
        else:
            return obj

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)

        instance = self.get_object()
        data = request.data
        if not partial:
            new = jsontools.dumps(copy.deepcopy(data), sort_keys=True)
            # check to see if the currently stored version is different from this one
            # and only if it is changed the last modified by time and user
            item = self.get_queryset().get(pk=data['id'])
            serializer = self.get_serializer_class()
            json = serializer(item).data
            current = jsontools.dumps(json, sort_keys=True)
            if self.ordered(current) != self.ordered(new):
                data['last_modified_time'] = datetime.datetime.now()
                if request.user.public_name != '':
                    data['last_modified_by'] = request.user.public_name
                else:
                    data['last_modified_by'] = request.user.username
        else:
            data['last_modified_time'] = datetime.datetime.now()
            if request.user.public_name != '':
                data['last_modified_by'] = request.user.public_name
            else:
                data['last_modified_by'] = request.user.username

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # refresh the instance from the database.
            instance = self.get_object()
            serializer = self.get_serializer(instance)

        # return the full updated object
        updated_instance = ItemDetail().get_item(request, **kwargs)

        try:
            # return Response(serializer(updated_instance).data, headers={'etag': '%s' % updated_instance['version_number']})
            return Response(updated_instance, headers={'etag': '%s' % updated_instance['version_number']})
        except KeyError:
            # return Response(serializer(updated_instance).data)
            return Response(updated_instance)


class ItemCreate(generics.CreateAPIView):

    permission_classes = (permissions.DjangoModelPermissions, )

    def get_serializer_class(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_name = target.SERIALIZER
        serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        return serializer

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_class = self.get_serializer_class()
        fields = copy.deepcopy(target.REQUIRED_FIELDS)
        for key in self.request.data:
            if key not in fields:
                fields.append(key)
        kwargs['fields'] = fields
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def create(self, request, *args, **kwargs):
        self.kwargs = kwargs
        data = request.data
        data['created_time'] = datetime.datetime.now()
        if request.user.public_name != '':
            data['created_by'] = request.user.public_name
        else:
            data['created_by'] = request.user.username
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        new_instance = self.perform_create(serializer)
        instance_id = new_instance.id
        created_instance = ItemDetail().get_item(request, pk=instance_id, **kwargs)
        headers = self.get_success_headers(serializer.data)
        try:
            headers['etag'] = '%s' % created_instance['version_number']
        except:
            pass
        return Response(created_instance, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        instance = serializer.save()
        return instance


class ItemDelete(generics.DestroyAPIView):

    permission_classes = (permissions.DjangoModelPermissions, )

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def delete(self, request, *args, **kwargs):
        try:
            return self.destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({'responseText': 'ProtectedError'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class M2MItemDelete(generics.UpdateAPIView):
    # this is called as a PATCH as although it does delete the link it updates the target object
    permission_classes = (permissions.DjangoModelPermissions, )

    def get_queryset(self):
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        instance = self.get_object()
        deletion_field = getattr(instance, self.kwargs['fieldname'])
        author = apps.get_model(self.kwargs['app'], self.kwargs['itemmodel']).objects.get(pk=self.kwargs['itempk'])
        getattr(instance, self.kwargs['fieldname']).remove(author)
        instance.last_modified_time = datetime.datetime.now()
        if request.user.public_name != '':
            instance.last_modified_by = request.user.public_name
        else:
            instance.last_modified_by = request.user.username
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
