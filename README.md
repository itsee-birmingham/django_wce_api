# The api app

The api app underlies everything else in the Workspace for Collaborative Editing Django implementation.

The api is used internally in the Django application and can also be used externally. It uses Django Rest Framework to
handle serialisation. The views in other apps which handle the retrieval and display of data as well as data changes
also call the api app either through the api or directly by using the functions in views.py

## Base model inheritance

The api has an abstract model called BaseModel which inherits from the diango.db.models Model class. It adds the
fields which the api application expects to be present in all models it tries to save. These are the following meta data
fields:

-   created_time
-   created_by
-   last_modified_time
-   last_modified_by
-   version_number

All models in apps which intend to use the api model for creating and saving models **must** be based on this abstract
model rather than the one provided by Django, unless the model itself includes all of the fields specified above.

To work with all of the functions of the api app each model must include the following variables or functions (not all
are required for all functions):

- AVAILABILITY - a string which determines the availability of the model through the api (see below on decorators for
  supported values)

- SERIALIZER - a string containing the class name of the serializer for this model. The serializer itself should be
  added to the serializers.py file for the app (see section on api serializers)

- REQUIRED_FIELDS - a list of the fields required when creating an object using the api. This should be the list of
  minimum fields required for the object to be created.

- get_serialization_fields() - a function that returns the fields that will be included in the serialization by default
  (unless specific fields are given in the request).

- get_fields() - a function that returns a dictionary with field names as keys and fields type as the data. This is
  used in serialization and display to determine what the field type is and therefore how to go about interacting with it.


Other things which can be useful to specify are the standard Django things such as:

- \_\_str\_\_() - the string representation of the object, useful for display purposes but note that there can only be
  one

- ordering - a variable in the Meta class in the model which specifies the default order for returning objects.

To make the SQL calls more efficient the following variables should be provided on any models that require them:

- RELATED_KEYS - A list of all fields that are foreign keys in this model.

- PREFETCH_KEYS - A list of all of the many-to-many or one-to-many keys in this model ﻿(these might be declared with a
  foreign key in the related model only).

The citations app has many functions which we may end up extracting and sharing with other apps such as the display of
a list of objects in a table and the display of the details of a single object. These views also use model level
variables and functions including (but perhaps not limited to):

- LIST_FIELDS - ﻿A list of fields to display in the 'list view' of the model. A dictionary can be used if the database field name is different from the column label for display and/or the search string required (for example when searching related models or array fields) keys for dictionary are 'id', 'label' and 'search' respectively. Both 'label' and 'search' will default to 'id' if not provided. If all three values are the same a string can be provided instead of a dictionary.

- ITEM_FIELDS - A list of the fields to display when displaying a single item from the database in the order the fields should be shown.

- get_search_fields() - A list of dictionaries containing metadata about the fields appropriate for searches of the data in the model (see citations app for structure and code example). Used in an ajax call on the search page to get the fields relevant for searching each model. This will sometimes include relations from other models (again there are examples in the citations app).

## The api base serializer

The api app currently specified two serializers both inheriting from the rest_framework.serializers.ModelSerializer.

There is a SimpleSerializer which I had hoped would be somewhat generic and remove the need to specify a serializer for each model but this did not really work out and once I have investigated any remaining references (as per the TODO in the code) this serializer should be deleted.

The BaseModelSerializer is the one we use, it takes the rest\_framework.serializers.ModelSerializer and makes it more flexible by allowing the specification of data in the \_\_init\_\_ function. This was done specifically to allow the desired fields to be specified to restrict the size of the data being returned on serialization when necessary.

Each model still needs to specify a serializer in a serializers.py file in the app directory, the location is important so that the serializer can be found. The serializer must inherit BaseModelSerializer and can be as a minimum the following:

```python
class AuthorSerializer(api_serializers.BaseModelSerializer):
  class Meta:
    model = models.Author
```

If there are many to many fields involved (as with the citation model in the citations app) then a full serializer must be specified. See the code and drf documentation for details. An example in the ITSEE code would be the CitationSerializer

## Post_save signals on BaseModel

The BaseModel contains the ‘version_number’ field which I plan to use in the ETag in the http header in order to achieve ‘optimistic concurrency control’/’optimistic locking’. The version number is set to 1 after being created and then incremented on each save. It is worth implementing as a post_save signal as it will basically apply to all models. Because it applies to all models that inherit BaseModel (which should end up being all of them) I am putting the code in the api app. It is in the signals.py file in the api app. In order to add the post_save signal to any models inheriting BaseModel **each app** that needs the post save hooks must add the following in the apps.py file in the [appname]Config class after the name variable is set and this function:

```python
﻿def ready(self):
  import api.signals
```

Everything should then just take care of itself.

**TODO:** it might also be worth moving the created and last_modified data into this post save hook rather than handling them in the ItemUpdate/ItemCreate views in the api app.


## The api views

As explained above the api app provides views for getting, creating updating and searching items in the database both through the drf serialisation and for other views in python that are dealing directly with Django objects (should they choose to use it - the citations app does for example). The views are based on the views for listing items, retrieving a single item and updating and creating items provided by rest_framework.generics which each of the classes in the views.py file inherits. However, I have made them more flexible so that a single view can be used with any model and with a range of additional arguments which are typically stored in the models themselves. The models must contain certain information in order to work with the api views. This is detailed in the section on the api Base Model.

The views can be used directly or through ajax using the functions in api.js int he static folder for the api app.

## api.js

The api.js has both callback based functions and promise based functions. This is largely because I did not know about promises/they were not standardised when some of this code was written. Any new code should ideally be written using the promise based functions which all have function names which end in 'promise'. I have not been able to use them all of the time (probably due to a still incomplete understanding) and have not yet gone back through older code such as the citations app to refactor the js to use promises only.

## api decorators

The decorators use the AVAILABILITY setting on the models to determine how availbale they are through the api. It only concerns GET requests at present (although we may want to extend it later) as write permissions are controlled using Django mechanisms and always require the user to be logged in. Supported values for AVAILABILITY and their definitions are as follows:

- public - all instances of the model are available to anyone
- private - only the owner of a superuser can see it
- logged_in - all instances of the model are available to anyone who is logged in
- project - only logged in people who are members of the project specified in the data request can see it. A project id must be supplied in the request for this to work (note the project must be in the same app - an extension will be required for the project to be in a different app at some point)
- public_or_project - if the public field in the instance is set to True the instance is available to anyone, if not it behaves as project above.
- public_or_user - if the public field in the instance is set to True the instance is available to anyone, otherwise it behaves as private above.

Any field which is public_or_... must include a public field in the model.
If a model does not specify its availability it will be assumed that it is private.

This feature is still very much under development and there are probably lots of improvements to be made. It may even be that we can find a django plugin that would do this but when I looked I could not find one that did what I wanted and was still maintained.

## searches through api

Write the documentation for this.
