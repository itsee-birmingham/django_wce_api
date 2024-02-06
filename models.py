from django.db import models


class BaseModel (models.Model):

    created_time = models.DateTimeField(null=True)
    created_by = models.TextField(verbose_name='Created by', blank=True)
    last_modified_time = models.DateTimeField(null=True)
    last_modified_by = models.TextField(verbose_name='Last modified by', blank=True)
    version_number = models.IntegerField(null=True)  # has to be null because set in post_save on create

    def get_serialization_fields():
        fields = '__all__'
        return fields

    class Meta:
        abstract = True
