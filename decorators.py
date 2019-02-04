from django.http import JsonResponse
from django.apps import apps
from django.db.models import Q
from django.contrib.auth.models import User


def object_is_public_or_user_is_owner_or_superuser(function):
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

        if availability == 'open':
            #open means anyone can read everything - citations data for example
            return function(request, *args, **kwargs)


        elif availability == 'restricted':
            #anyone can see it if it has a public flag set to True if not then only owner or superuser
            #this is for mixed tables like transcriptions and verses
            #All restricted models need a 'public' entry in the schema
            #return server error if not
            if not 'public' in target.get_fields():
                return JsonResponse({'message': "Internal server error - model configuation incompatible with API"}, status=500)


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
