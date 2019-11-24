from django.db import models


class BaseModel (models.Model):

    created_time = models.DateTimeField(null=True)
    created_by = models.TextField('created_by', blank=True)
    last_modified_time = models.DateTimeField(null=True)
    last_modified_by = models.TextField('Last_modified_by', blank=True)
    version_number = models.IntegerField(null=True)  # has to be null because set in post_save on create

    class Meta:
        abstract = True
