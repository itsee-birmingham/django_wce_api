from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse

from api.search_helpers import get_query_tuple

# TODO: might want something similar so people can only write to their own data in some models
# this only deals with getting things back since all writing requires login so it not open


def apply_model_get_restrictions(function):
    """Apply model restrictions to the data returned by the API."""
    def wrap(request, *args, **kwargs):
        target = apps.get_model(kwargs['app'], kwargs['model'])

        # first see if we are looking for an item that does not exist
        if 'pk' in kwargs:
            try:
                target.objects.get(pk=kwargs['pk'])
            except target.DoesNotExist:
                return JsonResponse({'message': "Item does not exist"}, status=404)

        # if we get this far we are looking either for a list or a single item which
        # does exist (even if permissions mean we can't view it)

        try:
            availability = target.AVAILABILITY
        except AttributeError:
            availability = 'private'

        if availability is None:
            # this is the safest default
            availability = 'private'

        if availability == 'public':
            # open means anyone can read everything - citations data for example
            return function(request, *args, **kwargs)

        elif availability == 'logged_in':
            # anyone logged in can see it
            if request.user.is_authenticated:
                return function(request, *args, **kwargs)
            return JsonResponse({'message': "Authentication required"}, status=401)

        elif availability == 'public_or_project':
            # anyone can see it if it has a public flag set to True
            # if not then only a member of the project or a superuser
            # this is for mixed tables like transcriptions and verses
            # All hybrid public models need a 'public' entry in the schema
            # return server error if not
            if 'public' not in target.get_fields() or 'project' not in target.get_fields():
                return JsonResponse(
                    {'message': "Internal server error - model configuation incompatible with API (code 10002)"},
                    status=500,
                )

            if not request.user.is_authenticated:  # we are not logged in
                # then you only get the public ones
                # assumes a public boolean attribute on the model (which is okay because we have checked above)
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            if request.user.groups.filter(name='%s_superusers' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            if 'project__id' not in request.GET and 'project' not in request.GET:
                # if no project specified you can only have the public ones
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            # Here we need to grab the user fields and add them to the query against the user
            project_model = apps.get_model(kwargs['app'], 'Project')
            user_fields = project_model.get_user_fields()

            query = Q()
            query |= Q(('public', True))
            for field in user_fields:
                query_tuple = get_query_tuple(user_fields[field], field, request.user)
                query |= Q(('project__%s' % (query_tuple[0]), query_tuple[1]))

            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        elif availability == 'project':
            if not request.user.is_authenticated:  # we are not logged in
                # You get nothing
                return JsonResponse({'message': "Authentication required"}, status=401)

            if 'project' not in target.get_fields():
                return JsonResponse(
                    {'message': "Internal server error - model configuation incompatible with API (code 10003)"},
                    status=500,
                )

            # a project must be specified in any request to a model of this type
            if 'project__id' not in request.GET and 'project' not in request.GET:
                return JsonResponse({'message': "Query not complete - Project must be specified"}, status=400)

            if 'project' in request.GET and 'project__id' not in request.GET:
                print('WARNING: project should be project__id to make sure this works')

            if request.user.groups.filter(name='%s_superusers' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            # Here we need to grab the user fields and add them to the query against the user
            try:
                project_model = apps.get_model(kwargs['app'], 'Project')
            except LookupError:
                # then this app doesn't have a project but maybe we specfied a different app in the model
                try:
                    project_app = target.PROJECT_APP
                    project_model = apps.get_model(project_app, 'Project')
                except (AttributeError, LookupError):
                    raise

            user_fields = project_model.get_user_fields()

            query = Q()
            for field in user_fields:
                query_tuple = get_query_tuple(user_fields[field], field, request.user)
                query |= Q(('project__%s' % (query_tuple[0]), query_tuple[1]))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        elif availability == 'project_or_user':
            if not request.user.is_authenticated:  # we are not logged in
                # You get nothing
                return JsonResponse({'message': "Authentication required"}, status=401)

            if 'project' not in target.get_fields():
                return JsonResponse(
                    {'message': "Internal server error - model configuation incompatible with API (code 10003)"},
                    status=500,
                )

            # a project must be specified in any request to a model of this type
            if 'project__id' not in request.GET and 'project' not in request.GET:
                return JsonResponse({'message': "Query not complete - Project must be specified"}, status=400)

            if request.user.groups.filter(name='%s_superusers' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            # Here we need to grab the user fields and add them to the query against the user
            project_model = apps.get_model(kwargs['app'], 'Project')
            user_fields = project_model.get_user_fields()

            # first add the user as a field since this is project_or_user
            query = Q(get_query_tuple('ForeignKey', 'user', request.user))
            for field in user_fields:
                query_tuple = get_query_tuple(user_fields[field], field, request.user)
                query |= Q(('project__%s' % (query_tuple[0]), query_tuple[1]))

            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        elif availability == 'public_or_user':
            # anyone can see it if it has a public flag set to True if not then only owner or superuser
            # this is for mixed tables like transcriptions and verses
            # All hybrid public models need a 'public' entry in the schema
            # return server error if not
            if 'public' not in target.get_fields():
                return JsonResponse(
                    {'message': "Internal server error - model configuation incompatible with API (code 10004)"},
                    status=500,
                )

            if not request.user.is_authenticated:  # we are not logged in
                # then you only get the public ones
                # assumes a public boolean attribute on the model (which is okay because we have checked above)
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            if request.user.groups.filter(name='%s_superusers' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            query = Q()
            query |= Q(('public', True))
            query |= Q(('user', request.user))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        elif availability == 'private':
            # only the owner or a superuser can see it - working and draft transcriptions
            if not request.user.is_authenticated:  # we are not logged in
                # You get nothing
                return JsonResponse({'message': "Authentication required"}, status=401)

            if request.user.groups.filter(name='%s_superusers' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            query = Q(('user', request.user))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        else:
            # just to be sure
            return JsonResponse(
                {'message': "Internal server error - model availability incompatible with API (code 10005)"}, status=500
            )

    return wrap
