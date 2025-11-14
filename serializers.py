from django.apps import apps
from rest_framework import serializers


class SimpleSerializer(serializers.ModelSerializer):
    """A generic serializer for a model.

    Used as a backup by the api if no other serializer is specified. it is unlikely to be suitable for anything but
    very simple models.
    """

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
                self.Meta.fields = self.Meta.model.get_serialization_fields()

        elif 'app' in context and 'model' in context:
            self.Meta.model = apps.get_model(context['app'], context['model'])
        super(SimpleSerializer, self).__init__(instance=instance)


class BaseModelSerializer(serializers.ModelSerializer):
    """The serializer for the base model.

    This model should be inherited by all other serializers.

    This takes the Model serializer from Django Rest Framework and makes it more flexible by allowing the
    specification of data in the `__init__` function. This was done to allow the required fields to be specified. This
    can be important when requesting large numbers of records to control the size of the data returned.
    """

    def __init__(self, *args, **kwargs):
        if kwargs:
            partial = kwargs.pop('partial', False)
        else:
            partial = False
        if 'fields' in kwargs:
            self.Meta.fields = kwargs['fields']
        else:
            self.Meta.fields = self.Meta.model.get_serialization_fields()

        if len(args) > 0 and 'data' in kwargs:
            super(BaseModelSerializer, self).__init__(instance=args[0], data=kwargs['data'], partial=partial)
        elif len(args) > 0:
            super(BaseModelSerializer, self).__init__(instance=args[0], partial=partial)
        elif 'data' in kwargs:
            super(BaseModelSerializer, self).__init__(data=kwargs['data'], partial=partial)
