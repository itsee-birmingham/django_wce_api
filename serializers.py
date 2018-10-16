from rest_framework import serializers
from django.apps import apps

#TODO: check why we are using this in api.views
class SimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = None
        fields = ()

    def __init__(self, instance=None, fields=None, context=None, data=None):
        
        if instance:
            if isinstance(instance, list):
                self.Meta.model = type(instance[0])
            else:
                self.Meta.model = type(instance)
            if fields:
                self.Meta.fields = fields
            else:
                self.Meta.fields = self.Meta.model.getSerializationFields()

        elif 'app' in context and 'model' in context:
            self.Meta.model = apps.get_model(context['app'], context['model'])
        super(SimpleSerializer, self).__init__(instance=instance)



class BaseModelSerializer(serializers.ModelSerializer):

    def __init__(self, *args, **kwargs):
        if kwargs:
            partial = kwargs.pop('partial', False)
        else:
            partial = False
        if 'fields' in kwargs:
            self.Meta.fields = kwargs['fields']
        else:
            self.Meta.fields = self.Meta.model.getSerializationFields()

        if len(args) > 0 and 'data' in kwargs:
            super(BaseModelSerializer, self).__init__(instance=args[0], data=kwargs['data'], partial=partial)
        elif len(args) > 0:
            super(BaseModelSerializer, self).__init__(instance=args[0], partial=partial)
        elif 'data' in kwargs:
            super(BaseModelSerializer, self).__init__(data=kwargs['data'], partial=partial)
