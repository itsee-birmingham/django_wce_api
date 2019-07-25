from django.http import JsonResponse
from django.apps import apps
from django.db.models import Q
from accounts.models import User
from api import views as api_views

#TODO: might want something similar so people can only write to their own data in some models

def apply_model_get_restrictions(function):
    #I think we should have app based superusers
    #to help restrict access so we could have a transcription superuser who only gets to see everything in OTE (Bruce and Amy for example)

    def wrap(request, *args, **kwargs):
        target = apps.get_model(kwargs['app'], kwargs['model'])

        #first see if we are looking for an item that does not exist
        if 'pk' in kwargs:
            try:
                target.objects.get(pk=kwargs['pk'])
            except:
                return JsonResponse({'message': "Item does not exist"}, status=404)

        #if we get this far we are looking either for a list or a single item which does exist (even if permissions mean we can't view it)
        try:
            availability = target.AVAILABILITY
        except:
            #TODO: consider the most sensible default.
            availability = 'private'

        if availability == 'public':
            #open means anyone can read everything - citations data for example
            return function(request, *args, **kwargs)

        elif availability == 'logged_in':
            #anyone logged in can see it
            if request.user.is_authenticated:
                return function(request, *args, **kwargs)
            return JsonResponse({'message': "Authentication required"}, status=401)

        elif availability == 'public_or_project':
            #anyone can see it if it has a public flag set to True if not then only a member of the project or a superuser
            #this is for mixed tables like transcriptions and verses
            #All hybrid public models need a 'public' entry in the schema
            #return server error if not
            if not 'public' in target.get_fields() or not 'project__id' in request.GET:
                return JsonResponse({'message': "Internal server error - model configuation incompatible with API (code 10002)"}, status=500)

            if not request.user.is_authenticated: #we are not logged in
                #then you only get the public ones
                #assumes a public boolean attribute on the model (which is okay because we have checked above)
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            if request.user.groups.filter(name='%s_superuser' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            if not 'project__id' in request.GET:
                #if no project specified you can only have the public ones
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            #Here we need to grab the user fields and add them to the query against the user
            project_model = apps.get_model(kwargs['app'], 'Project')
            user_fields = project_model.get_user_fields()

            query = Q()
            query |= Q(('public', True))
            for field in user_fields:
                query_tuple = api_views.getQueryTuple(user_fields[field], field, request.user)
                query |= Q(('project__%s' % (query_tuple[0]), query_tuple[1]))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)


        elif availability == 'project':

            if not request.user.is_authenticated: #we are not logged in
                #You get nothing
                return JsonResponse({'message': "Authentication required"}, status=401)

            if not 'project' in target.get_fields():

                return JsonResponse({'message': "Internal server error - model configuation incompatible with API (code 10003)"}, status=500)

            #a project must be specified in any request to a model of this type
            if not 'project__id' in request.GET:
                return JsonResponse({'message': "Query not complete - Project must be specified"}, status=400)

            if request.user.groups.filter(name='%s_superuser' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            #Here we need to grab the user fields and add them to the query against the user
            project_model = apps.get_model(kwargs['app'], 'Project')
            user_fields = project_model.get_user_fields()
            query = Q()
            for field in user_fields:
                query_tuple = api_views.getQueryTuple(user_fields[field], field, request.user)
                query |= Q(('project__%s' % (query_tuple[0]), query_tuple[1]))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)


        elif availability == 'public_or_user':
            #anyone can see it if it has a public flag set to True if not then only owner or superuser
            #this is for mixed tables like transcriptions and verses
            #All hybrid public models need a 'public' entry in the schema
            #return server error if not
            if not 'public' in target.get_fields():
                return JsonResponse({'message': "Internal server error - model configuation incompatible with API (code 10004)"}, status=500)


            if not request.user.is_authenticated: #we are not logged in
                #then you only get the public ones
                #assumes a public boolean attribute on the model (which is okay because we have checked above)
                query = Q(('public', True))
                kwargs['supplied_filter'] = query
                return function(request, *args, **kwargs)

            if request.user.groups.filter(name='%s_superuser' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            query = Q()
            query |= Q(('public', True))
            query |= Q(('user', request.user))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)


        elif availability == 'private':
            #only the owner or a superuser can see it - working and draft transcriptions
            if not request.user.is_authenticated: #we are not logged in
                #You get nothing
                return JsonResponse({'message': "Authentication required"}, status=401)

            if request.user.groups.filter(name='%s_superuser' % kwargs['app']).count() > 0:
                return function(request, *args, **kwargs)

            query = Q(('user', request.user))
            kwargs['supplied_filter'] = query
            return function(request, *args, **kwargs)

        else:
            #just to be sure
            return JsonResponse({'message': "Permission required"}, status=403)

    return wrap
