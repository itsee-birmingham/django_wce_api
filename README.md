# The API App

The API app underlies everything else in the Workspace for Collaborative Editing Django implementation.

The API is used internally in the Django application and can also be used externally. It uses Django REST Framework to
handle serialisation. The views in other apps which handle the retrieval and display of data as well as data changes
also call the API app either through the api or directly by using the functions in views.py

## Configuration/Dependencies

This app is tested with Django 3.2.

The API requires Django REST Framework and is tested on version 3.12.4.

The following configuration is required in the Django settings:

```python
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.DjangoModelPermissionsOrAnonReadOnly'
    ],
    'DEFAULT_PARSER_CLASSES': ('rest_framework.parsers.JSONParser',)
}
```


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

If there are many to many fields involved then a full serializer must be specified. See the Django REST Framework
documentation for details. An example in the ITSEE code is the `CitationSerializer`.

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

## The API Views

The API app provides views for getting, creating, updating, deleting and searching items in the database both through
the Django REST Framework serialisations and directly with the Django objects. The views are based on those provided by
`rest_framework.generics` which each of the classes in the `views.py` file inherits. However, they have been made them
more flexible so that a single view can be used with any model and with a range of additional arguments which are
typically stored in the models themselves. The models must contain certain information in order to work with the API
views. This is detailed in the section on the API BaseModel.


## Using the API

The API can be accessed directly via the URL or using AJAX via the JavaScript functions. The views provided in the API app can also be used directly in other views as described below.

### URL Access

URL access works for all methods but login is required for everything except GET. Only the GET features are explained
here because for the majority of applications the JavaScript functions should be used for everything else.

#### Base API

The API follow the app and model structure. To return a list of items use the app name and the model name as follows:

[host]/api/[appname]/[modelname]

This will return 100 items by default and provide links to get the next/previous 100 items.

To access an single item use the app name, the model name and the id of the item as follows:

[host]/api/[appname]/[modelname]/[itemid]

As well as the API itself the API app provides view functions that can be used in the views of other apps and returns
the Django objects so they can be more easily integrated with Django templates. These functions are: `get_objects()` in
the `ItemList` class view; and `get_item()` in the `ItemDetail` class view.

#### Options

There are several options that can be used to control the data returned by the API when returning a list of items.

- **_fields** - A list of comma separated fields to return in the data.
- **_sort** - A list of comma separated fields to use for sorting. A - can be added before a field name to reverse the
  direction.
- **limit** - The number of items to return (when returning large number of items the \_fields item should be used to
  control the size to improve performance). Note there is no underscore in this option as it uses the options already
  provided by Django REST Framework.

There is an extra option available when using `get_objects()` from the `ItemList` view directly.

- **_show** - The id of an item in the model. The slice of the items returned will be the slice that includes the
  item with this id. It is useful when returning users to the list after viewing a single item to ensure they are
  returned to the same place they left.

#### Searching

The API can be used for many searches but those which include any complex logic will need to be constructed using Q
objects in Django.

The basic format for searches follow the standard key value pair structure in a URL where they key is the field name in
the model and the value is the value being searched for.

Relations can be searched using  \_\_ (double underscore) in between the different model field names as explained in
the Django documentation.

The value can also be modified to allow several different types of searches. Not all search options are relevant to all
data types.

- value - equals (exact match)
- !value - does not equal
- value|i - makes any text search case insensitive
- \*value\* - contains
- value\* - starts with
- \*value - ends with
- \>value - greater than
- \>=value - greater than or equal to
- \<value - less than
- \<=value - less than or equal to

To perform an AND search on a field add the field to the URL twice with a different value each time. For example to
look for an item with a title that contains the letters 'r' and 't':

```
[host]/api/[appname]/[modelname]?title=*r*&title=*t*
```

To perform an OR search on a field add the field once and use separate the values with commas. For example to look for
an item with a publication year of 1999 or 2004:

```
[host]/api/[appname]/[modelname]?publication_year=1999,2004
```

Queries involving AND/OR logic in a combination of fields are not supported by the API but can be built with Django Q
objects.


### AJAX/JavaScript Access

The JavaScript file, `api.js`, has both callback based functions and promise based functions to access the API. Any new
code should ideally be written using the promise based functions which all have function names which end in 'promise'.
The other functions remain to support for apps that existed before JavaScript promises were standardised and added to
the API code.

The main functions available are described below. Create, update and delete functions require the correct model
permissions to be set in the Django admin interface.

- #### setupAjax()

A useful setup function that can be run if the JavaScript functions are to be used. It ensures that the csrf token is
added to any AJAX calls which require it.

- #### getCurrentUserPromise()

Returns the details of the logged in user.

- #### getItemFromDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model containing the item. |
| model | <code>string</code> | The name of the model containing the item. |
| id | <code>int</code> | The id of the item. |
| project | <code>int</code> | [optional] The id of the current project (required to retrieve an item from a model with project based permissions). |

Retrieves an item from the database.

- #### getItemsFromDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model containing the items. |
| model | <code>string</code> | The name of the model containing the items. |
| criteria | <code>JSON</code> | The criteria to use for retrieval (can include search criteria or other api options, must contain project__id if the model has project based permissions). |

Retrieves any items that match the criteria from the database.

This function also contains an optional argument, method, in case GET requests ever get too large and require POST to
send. This has not yet been required and therefore it is not implemented in the server side code and the default uses
GET.

- #### createItemInDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model. |
| model | <code>string</code> | The name of the model. |
| data | <code>JSON</code> | The data required to create the item (not including the id field which is automatically assigned). |

Creates an item in the specified model.

- #### updateItemInDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model. |
| model | <code>string</code> | The name of the model. |
| data | <code>JSON</code> | The full data of the item to be saved including the current id. |

Replaces an existing item with a new one specified model.

- #### updateFieldsInDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model. |
| model | <code>string</code> | The name of the model. |
| id | <code>int</code> | The id of the item. |
| data | <code>JSON</code> | The fields and associated data which need to be updated. |

Update only the specified fields of the item identified by the id.

- #### deleteItemFromDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model. |
| model | <code>string</code> | The name of the model. |
| id | <code>int</code> | The id of the item to be deleted. |

Delete the specified item.

- #### deleteM2MItemFromDatabasePromise()

| Param  | Type                | Description  |
| ------ | ------------------- | ------------ |
| app | <code>string</code> | The name of the app containing the model. |
| model | <code>string</code> | The name of the model. |
| model_id | <code>int</code> | The id of the item containing the M2M field. |
| field_name | <code>string</code> | name of the M2M field in the model. |
| item_model | <code>string</code> | The name of the related field model. |
| item_id | <code>int</code> | The id of the item in the related model. |

Remove a Many-to-Many (M2M) reference from a model. It does not delete the related model just the reference to it in
the main model.


## Tests

The tests for the API are in a separate Django app called `api_tests` as there are no models that can be used for
testing in the API itself. Testing documentation is available in the `api_tests` app.


## License

This app is licensed under the GNU General Public License v3.0.

## Acknowledgments

This application was released as part of the Multimedia Yasna Project funded by the European Union Horizon 2020
Research and Innovation Programme (grant agreement 694612).

The software was created by Catherine Smith at the Institute for Textual Scholarship and Electronic Editing (ITSEE) in
the University of Birmingham. It is based on a suite of tools developed for and supported by the following research
projects:

- The Workspace for Collaborative Editing (AHRC/DFG collaborative project 2010-2013)
- COMPAUL (funded by the European Union 7th Framework Programme under grant agreement 283302, 2011-2016)
- CATENA (funded by the European Union Horizon 2020 Research and Innovation Programme under grant agreement 770816, 2018-2023)
