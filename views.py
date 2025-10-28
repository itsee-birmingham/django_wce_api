import copy
import datetime
import importlib
import json as jsontools

from accounts.serializers import UserSerializer
from django.apps import apps
from django.conf import settings as django_settings
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import etag
from rest_framework import generics, permissions, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from api.decorators import apply_model_get_restrictions
from api.search_helpers import get_field_filters
from api.serializers import SimpleSerializer


def _get_etag(request, app=None, model=None, pk=None):
    try:
        etag = str(apps.get_model(app, model).objects.get(pk=pk).version_number)
        return etag
    except AttributeError:
        return "*"


def get_user(request):
    """Return the current user profile information.

    Args:
        request (django.http.HttpRequest): The current request.

    Returns:
        JSONResponse: The profile information for the current user.
    """
    if request.user.is_anonymous:
        return JsonResponse({'message': "Authentication required"}, status=401)
    serializer = UserSerializer(request.user)
    return JsonResponse(serializer.data)


class SelectPagePaginator(LimitOffsetPagination):
    """A paginator which can select a page based on a page number (not offset)."""

    def paginate_queryset_and_get_page(self, queryset, request, view=None, index_required=None):
        """Return the portion of the query set representing the requested page."""
        self.limit = self.get_limit(request)

        if self.limit is None:
            return None

        self.offset = self.get_offset(request)
        self.count = len(queryset)

        if index_required is not None:
            page = int(index_required / self.limit)
            self.offset = page * self.limit

        self.request = request
        if self.count > self.limit and self.template is not None:
            self.display_page_controls = True

        if self.count == 0 or self.offset > self.count:
            return []

        return (list(queryset[self.offset : self.offset + self.limit]), self.offset)


"""
While these classes generally use model classes from django-rest-framework there is quite a lot of overriding in
order to make them generic enough to not require one per model.

I have tried to specify things in the model itself and then call them from here

"""


@method_decorator(apply_model_get_restrictions, name='dispatch')
class ItemList(generics.ListAPIView):
    """Concrete view for listing a queryset."""

    permission_classes = (permissions.AllowAny,)
    renderer_classes = (JSONRenderer,)
    pagination_class = SelectPagePaginator

    def get_serializer_class(self):
        """Return the class to use for the serializer."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except Exception:
            serializer = SimpleSerializer
        return serializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance that should be used for validating and de/serializing input and output."""
        serializer_class = self.get_serializer_class()
        if 'fields' in self.kwargs:
            kwargs['fields'] = self.kwargs['fields']
        return serializer_class(*args, **kwargs)

    def get_queryset(self, fields=None):
        """Get the list of items for this view."""
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

        filter_queries = get_field_filters(requestQuery, target, 'filter')
        exclude_queries = get_field_filters(requestQuery, target, 'exclude')
        hits = hits.exclude(exclude_queries[0]).filter(filter_queries[0]).distinct()
        if len(filter_queries) > 1:
            for query in filter_queries[1:]:
                hits = hits.filter(query)
        if len(exclude_queries) > 1:
            for query in exclude_queries[1:]:
                hits = hits.exclude(query)

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
        """Return the items.

        This one is used by the regular api calls.
        """
        return self.list(request)

    def _get_offset_required(self, queryset, item_id):
        """Get the offset required so the item with `item_id` is on the page returned."""
        try:
            item_position = list(queryset.values_list('id', flat=True)).index(int(item_id))
        except Exception:
            item_position = 0
        return item_position

    def paginate_queryset_and_get_page(self, queryset, index_required=None):
        """Return a single page of results, or `None` if pagination is disabled."""
        if self.paginator is None:
            return None
        if index_required is not None:
            return self.paginator.paginate_queryset_and_get_page(
                queryset, self.request, view=self, index_required=index_required
            )

    # If you do also need post here then this will work - it is disabled now until we need it
    #     def post(self, request, app, model):
    #         return self.get(request, app, model)

    def get_objects(self, request, **kwargs):
        """Return the items.

        This one is used by the html interface.
        """
        self.kwargs = kwargs
        self.request = request
        if '_fields' in self.kwargs:
            queryset = self.get_queryset(fields=self.kwargs['_fields'])
        else:
            queryset = self.get_queryset()

        offset = None
        if '_show' in request.GET:
            index = self._get_offset_required(queryset, request.GET.get('_show'))
            (paginated_query_set, offset) = self.paginate_queryset_and_get_page(queryset, index_required=index)
        else:
            index = None
            paginated_query_set = self.paginate_queryset(queryset)
        resp = self.get_paginated_response(paginated_query_set)
        resp.data = dict(resp.data)
        if offset is not None:
            resp.data['offset'] = offset
        return resp.data


# The get for this for private models has to have a fields keyword because permissions.DjangoModelPermissions
# runs get_queryset before running the get function and get_queryset adds fields to self.kwargs.
# Do not merge this with the ItemList view as it will break it.
class PrivateItemList(ItemList):
    """Concrete view for listing a queryset of a private model."""

    permission_classes = (permissions.DjangoModelPermissions,)

    def get(self, request, app, model, supplied_filter=None, fields=None):
        """Return the items."""
        return self.list(request)


@method_decorator(apply_model_get_restrictions, name='dispatch')
class ItemDetail(generics.RetrieveAPIView):
    """Concrete view for retrieving a model instance."""

    permission_classes = (permissions.AllowAny,)
    renderer_classes = (JSONRenderer,)

    def get_queryset(self):
        """Get the list of items for this view."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            prefetch_keys = target.PREFETCH_KEYS
        except Exception:
            prefetch_keys = [None]
        try:
            related_keys = target.RELATED_KEYS
        except Exception:
            related_keys = [None]
        hits = target.objects.all().select_related(*related_keys).prefetch_related(*prefetch_keys)
        if 'supplied_filter' in self.kwargs and self.kwargs['supplied_filter'] is not None:
            hits = hits.filter(self.kwargs['supplied_filter']).distinct()
        return hits

    def get_serializer_class(self):
        """Return the class to use for the serializer."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        try:
            serializer_name = target.SERIALIZER
            serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        except Exception:
            serializer = SimpleSerializer
        return serializer

    def retrieve(self, request, *args, **kwargs):
        """Retrieve a model instance and set etag header in response.

        This overrides the function provided by the drf RetrieveModelMixin to setthe etag header in the response.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        try:
            return Response(serializer.data, headers={'etag': '%d' % instance.version_number})
        except (AttributeError, TypeError):
            return Response(serializer.data)

    def get(self, request, app, model, pk, supplied_filter=None):
        """Return the item.

        This one is used by the regular api calls.
        """
        return self.retrieve(request)

    # If you do also need post here then this will work - it is disabled now until we need it
    #     def post(self, request, app, model, pk):
    #         return self.get(request, app, model, pk)

    def get_item(self, request, **kwargs):
        """Return the item.

        This one is used by the html interface.
        """
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


class PrivateItemDetail(ItemDetail):
    """Concrete view for retrieving a private model instance."""

    permission_classes = (permissions.DjangoModelPermissions,)


@method_decorator(etag(_get_etag), name='dispatch')
class ItemUpdate(generics.UpdateAPIView):
    """Concrete view for updating a model instance."""

    permission_classes = (permissions.DjangoModelPermissions,)

    def get_serializer_class(self):
        """Return the class to use for the serializer."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_name = target.SERIALIZER
        serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        return serializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance that should be used for validating and de/serializing input and output."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_class = self.get_serializer_class()
        fields = copy.deepcopy(target.REQUIRED_FIELDS)
        for key in self.request.data:
            if key not in fields:
                fields.append(key)
        kwargs['fields'] = fields
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        """Get the list of items for this view."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def update(self, request, *args, **kwargs):
        """Update the item."""
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
            if current != new:
                data['last_modified_time'] = datetime.datetime.now()
                if django_settings.USER_IDENTIFIER_FIELD and (
                    hasattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
                    and getattr(request.user, django_settings.USER_IDENTIFIER_FIELD) != ''
                ):
                    data['last_modified_by'] = getattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
                else:
                    data['last_modified_by'] = request.user.username
        else:
            data['last_modified_time'] = datetime.datetime.now()
            if django_settings.USER_IDENTIFIER_FIELD and (
                hasattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
                and getattr(request.user, django_settings.USER_IDENTIFIER_FIELD) != ''
            ):
                data['last_modified_by'] = getattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
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
            # return Response(serializer(updated_instance).data,
            # headers={'etag': '%s' % updated_instance['version_number']})
            return Response(updated_instance, headers={'etag': '%s' % updated_instance['version_number']})
        except KeyError:
            # return Response(serializer(updated_instance).data)
            return Response(updated_instance)


class ItemCreate(generics.CreateAPIView):
    """Concrete view for creating a model instance."""

    permission_classes = (permissions.DjangoModelPermissions,)

    def get_serializer_class(self):
        """Return the class to use for the serializer."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_name = target.SERIALIZER
        serializer = getattr(importlib.import_module('%s.serializers' % self.kwargs['app']), serializer_name)
        return serializer

    def get_serializer(self, *args, **kwargs):
        """Return the serializer instance that should be used for validating and de/serializing input and output."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        serializer_class = self.get_serializer_class()
        fields = copy.deepcopy(target.REQUIRED_FIELDS)
        for key in self.request.data:
            if key not in fields:
                fields.append(key)
        kwargs['fields'] = fields
        return serializer_class(*args, **kwargs)

    def get_queryset(self):
        """Get the list of items for this view."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def create(self, request, *args, **kwargs):
        """Create an item."""
        self.kwargs = kwargs
        data = request.data
        data['created_time'] = datetime.datetime.now()
        if django_settings.USER_IDENTIFIER_FIELD and (
            hasattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
            and getattr(request.user, django_settings.USER_IDENTIFIER_FIELD) != ''
        ):
            data['created_by'] = getattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
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
        except Exception:
            pass
        return Response(created_instance, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """Create the model instance."""
        instance = serializer.save()
        return instance


class ItemDelete(generics.DestroyAPIView):
    """Concrete view for deleting a model instance."""

    permission_classes = (permissions.DjangoModelPermissions,)

    def get_queryset(self):
        """Get the list of items for this view."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def delete(self, request, *args, **kwargs):
        """Delete the item."""
        try:
            return self.destroy(request, *args, **kwargs)
        except ProtectedError:
            return Response({'responseText': 'ProtectedError'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class M2MItemDelete(generics.UpdateAPIView):
    """Concrete view for delete M2M relation and updating a model instance."""

    # this is called as a PATCH as although it does delete the link, it also updates the target object
    permission_classes = (permissions.DjangoModelPermissions,)

    def get_queryset(self):
        """Get the list of items for this view."""
        target = apps.get_model(self.kwargs['app'], self.kwargs['model'])
        return target.objects.all()

    def update(self, request, *args, **kwargs):
        """Update the target object and delte the linked item."""
        instance = self.get_object()
        author = apps.get_model(self.kwargs['app'], self.kwargs['itemmodel']).objects.get(pk=self.kwargs['itempk'])
        getattr(instance, self.kwargs['fieldname']).remove(author)
        instance.last_modified_time = datetime.datetime.now()
        if django_settings.USER_IDENTIFIER_FIELD and (
            hasattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
            and getattr(request.user, django_settings.USER_IDENTIFIER_FIELD) != ''
        ):
            instance.last_modified_by = getattr(request.user, django_settings.USER_IDENTIFIER_FIELD)
        else:
            instance.last_modified_by = request.user.username
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
