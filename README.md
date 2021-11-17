# The API App

The API app underlies everything else in the Workspace for Collaborative Editing Django implementation.

The API is used internally in the Django application and can also be used externally. It uses Django Rest Framework to
handle serialisation. The views in other apps which handle the retrieval and display of data as well as data changes
also call the API app either through the api or directly by using the functions in views.py

## BaseModel Inheritance

The API has an abstract model called `BaseModel` which inherits from the `diango.db.models.Model` class. It adds the
fields which the API application expects to be present in all models it tries to save. These are the following meta data
fields:

-   created_time
-   created_by
-   last_modified_time
-   last_modified_by
-   version_number

All models in apps which intend to use the API model for creating and saving models **must** be based on this abstract
model rather than the one provided by Django, unless the model itself includes all of the fields specified above.

To work with all of the functions of the API app each model must include the following variables or functions (not all
are required for all functions):

- AVAILABILITY - a string which determines the availability of the model through the API (see below on decorators for
  supported values)

- SERIALIZER - a string containing the class name of the serializer for this model. The serializer itself should be
  added to the serializers.py file for the app (see section on API serializers)

- REQUIRED_FIELDS - a list of the fields required when creating an object using the API. This should be the list of
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

REMOVE FOR MUYA
If the data in the models are going to be displayed in tables or are going to be used for searching then the following
model variables and function might be useful. This is mostly used in the citations app and some in the catena_catalogue:

- LIST_FIELDS - ﻿A list of fields to display in the 'list view' of the model. A dictionary can be used if the database field name is different from the column label for display and/or the search string required (for example when searching related models or array fields) keys for dictionary are 'id', 'label' and 'search' respectively. Both 'label' and 'search' will default to 'id' if not provided. If all three values are the same a string can be provided instead of a dictionary.

- ITEM_FIELDS - A list of the fields to display when displaying a single item from the database in the order the fields should be shown.

- get_search_fields() - A list of dictionaries containing metadata about the fields appropriate for searches of the data in the model (see citations app for structure and code example). Used in an ajax call on the search page to get the fields relevant for searching each model. This will sometimes include relations from other models (again there are examples in the citations app).

## The API BaseModelSerializer

The api app includes two serializers both inheriting from the `rest_framework.serializers.ModelSerializer` class.

`SimpleSerializer` is only used as a backup if no other serializer is specified. This serializer might be good enough
for retrieving data in a few scenarios but in the vast majority of cases a specific serializer will need to be provided
for the model.

`BaseModelSerializer` takes the `rest\_framework.serializers.ModelSerializer` and makes it more flexible by allowing the
specification of data in the `\_\_init\_\_` function. This was done to allow the required fields to be specified. This
can be important when requesting large numbers of records to control the size of the data returned.

Each model needs to specify a serializer in a `serializers.py` file in the app directory; the location is important
so that the serializer can be found. The serializer must inherit `BaseModelSerializer` and can be very minimal in most
cases. A simple version is as follows:

```python
class AuthorSerializer(api_serializers.BaseModelSerializer):
  class Meta:
    model = models.Author
```

If there are many to many fields involved then a full serializer must be specified. See the django rest framework
documentation for details. An example in the ITSEE code is the `CitationSerializer`.

## The API Views

The API app provides views for getting, creating, updating, deleting and searching items in the database both through
the Django rest framework serialisations and directly with the Django objects. The views are based on those provided by
`rest_framework.generics` which each of the classes in the `views.py` file inherits. However, they have been made them
more flexible so that a single view can be used with any model and with a range of additional arguments which are
typically stored in the models themselves. The models must contain certain information in order to work with the API
views. This is detailed in the section on the API BaseModel.

The views can be used directly or through AJAX using the functions in `api.js`.

## JavaScript

The JavaScript file, `api.js`, has both callback based functions and promise based functions to access the API. Any new
code should ideally be written using the promise based functions which all have function names which end in 'promise'.
The other functions remain for legacy support for apps that existed before JavaScript promises were standardised.

## API Decorators

The decorators use the AVAILABILITY setting on the models to control access to the data through the API. It only
concerns GET requests because write permissions are controlled using other Django mechanisms and always require the
user to be logged in. In all cases a member of the group [appname]\_superusers, if implemented, can see all data from
that app.  Supported values for AVAILABILITY and their definitions are as follows:

- **public** - All instances of the model are available to anyone.
- **private** - Only the owner can see it. Models with this availability setting must have a user field.
- **logged_in** - All instances of the model are available to anyone who is logged in.
- **project** - Only logged in people who are members of the project specified in the data request can see it. A project id must be supplied in the request for this to work (note the project must be in the same app - an extension will be required for the project to be in a different app at some point).
- **public_or_project** - If the public field in the instance is set to True the instance is available to anyone, if not it behaves as project above. Models with this availability setting must have a public field.
- **public_or_user** - If the public field in the instance is set to True the instance is available to anyone, otherwise it behaves as private above. Models with this availability setting must have a public field and a user field.

If a model does not specify its availability it will be assumed to be private.


## Using the API

### Data List

### Single Item


### Searching

Write the documentation for this.


## Tests

The tests for the API are in a separate Django app called `api_tests` as there are no models that can be used for
testing in the API itself. Testing documentation is available in the `api_tests` app.
