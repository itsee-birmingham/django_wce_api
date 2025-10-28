import datetime
import re

from django.db.models import Q


def _get_date_field(operator, value):
    value = value.replace(operator, '')
    try:
        date = datetime.datetime.strptime(value, '%Y').date()
        if operator in ['<', '<=']:
            date = date.replace(month=12, day=31)
    except ValueError:
        date = value
    return date


def get_related_model(model_instance, field_name):
    """Get the model of a relational field.

    Args:
        model_instance (django.db.models.Model): The model containing the relational field.
        field_name (str): The relational field name.

    Returns:
        django.db.models.Model: The model which the relationa field references (of the model_instance if the field is
            not relational).
    """
    if '__' in field_name:
        field_name = field_name.split('__')[0]
    return model_instance._meta.get_field(field_name).related_model


def get_related_field_type(model, field):
    """Return the data type of the related field.

    Args:
        model (django.db.models.Model): The model containing the relational field.
        field (str): The field name to find the type of.

    Returns:
        str: The data type of the related field.
    """
    if len(field.split('__')) < 2:
        return None
    related_model = get_related_model(model, field)
    if related_model.__name__ == 'User':  # It is not safe to rely on duck typing here
        # It doesn't really make sense to search user on anything but id but other fields can be included here if they
        # are needed
        related_fields = {'id': 'AutoField'}
    else:
        related_fields = related_model.get_fields()
    if '__' in field and field.split('__')[1] in related_fields:
        field_type = related_fields[field.split('__')[1]]
        if field_type not in ['ForeignKey', 'ManyToManyField']:
            return field_type
        else:
            return get_related_field_type(related_model, '__'.join(field.split('__')[1:]))
    else:
        return None


def get_query_tuple(field_type, field, value):
    """Return a tuple of field and value for use in a django query based on the api request submitted.

    Args:
        field_type (str): The data type of the field for the query.
        field (str): The field name to use in the query.
        value (str): The value to search for in the query with the shorthand used in the api.

    Returns:
        tuple|None: The tuple containing the field and the value to use in the query or None if one can't be created.
    """
    operator_lookup = {
        'CharField': [
            [r'^([^*|]+)\*$', '__startswith'],
            [r'^([^*|]+)\*\|i$', '__istartswith'],
            [r'^\*([^*|]+)$', '__endswith'],
            [r'^\*([^*|]+)\|i$', '__iendswith'],
            [r'^\*([^*|]+)\*$', '__contains'],
            [r'^\*([^*|]+)\*\|i$', '__icontains'],
            [r'^([^*|]+)\|i$', '__iexact'],
        ],
        'TextField': [
            [r'^([^*|]+)\*$', '__startswith'],
            [r'^([^*|]+)\*\|i$', '__istartswith'],
            [r'^\*([^*|]+)$', '__endswith'],
            [r'^\*([^*|]+)\|i$', '__iendswith'],
            [r'^\*([^*|]+)\*$', '__contains'],
            [r'^\*([^*|]+)\*\|i$', '__icontains'],
            [r'^([^*|]+)\|i$', '__iexact'],
        ],
        'IntegerField': [
            [r'^>([0-9]+)$', '__gt'],
            [r'^>=([0-9]+)$', '__gte'],
            [r'^<([0-9]+)$', '__lt'],
            [r'^<=([0-9]+)$', '__lte'],
        ],
        'DateField': [
            [r'^>([0-9]+)$', '__gt', '', ['_get_date_field', '>', value]],
            [r'^>=([0-9]+)$', '__gte', '', ['_get_date_field', '>=', value]],
            [r'^<([0-9]+)$', '__lt', '', ['_get_date_field', '<', value]],
            [r'^<=([0-9]+)$', '__lte', '', ['_get_date_field', '<=', value]],
        ],
        'ArrayField': [[r'^_eq(\d+)$', '__len'], [r'^_gt(\d+)$', '__len__gt'], [r'^(.+)$', '__contains']],
        'NullBooleanField': [[r'^([tT]rue)$', '', True], [r'^([fF]alse)$', '', None]],
        'BooleanField': [[r'^([tT]rue)$', '', True], [r'^([fF]alse)$', '', False]],
        # this assumes that the search is for the value in the JSON field and that that
        # values is text or char there are more searches specific to JSON fields such as
        # presence of key which we do not support yet
        'JSONField': [
            [r'^([^*|]+)\*$', '__startswith'],
            [r'^([^*|]+)\*\|i$', '__istartswith'],
            [r'^\*([^*|]+)$', '__endswith'],
            [r'^\*([^*|]+)\|i$', '__iendswith'],
            [r'^\*([^*|]+)\*$', '__contains'],
            [r'^\*([^*|]+)\*\|i$', '__icontains'],
            [r'^([^*|]+)\|i$', '__iexact'],
        ],
        'ForeignKey': [],
        'ManyToManyField': [],
    }
    options = []

    if field_type in operator_lookup:
        options = operator_lookup[field_type]
    for option in options:
        if re.search(option[0], value):
            if len(option) > 3:
                value = globals()[option[3][0]](option[3][1], option[3][2])
                return ('%s%s' % (field, option[1]), value)
            elif len(option) > 2:
                return ('%s%s' % (field, option[1]), option[2])
            elif field_type == 'ArrayField' and '__len' not in option[1]:
                return ('%s%s' % (field, option[1]), [value])
            else:
                return ('%s%s' % (field, option[1]), re.sub(option[0], '\\1', value))
    if value != '' and field != '' and field_type:
        return (field, value)
    return None


def get_field_filters(queryDict, model_instance, type):
    """Create the queries to use as filters.

    Args:
        queryDict (dict): The query doctionary from the api call.
        model_instance (django.db.models.Model): The model being filtered.
        type (str): A string describing the type of filter required: either `exclude` or `filter`.

    Returns:
        list: A list of django.db.models.Q objects.
    """
    model_fields = model_instance.get_fields()
    query = Q()
    additional_queries = []
    query_tuple = None
    m2m_list = []
    for field in queryDict:
        if field == 'project':
            # project used to be in the list below and I have removed it because
            # we might need to filter by project for some things
            print('Project used to be filtered out - check why it was needed and adjust query if necessary!')
        if field not in ['offset', 'limit'] and field[0] != '_':
            if field in model_fields:
                field_type = model_fields[field]
            elif '__' in field and field.split('__')[0] in model_fields:
                field_type = model_fields[field.split('__')[0]]
            else:
                field_type = None
            if field_type == 'ForeignKey' or field_type == 'ManyToManyField':
                m2m_list.append(field.split('__')[0])
                field_type = get_related_field_type(model_instance, field)
            value_list = queryDict[field]
            # we do not support negation with OR so these are only done when we are filtering
            # I just don't think or-ing negatives on the same field key makes any sense
            for i, value in enumerate(value_list):
                # these are the OR fields
                if ',' in value:
                    if type == 'filter':
                        subquery = Q()
                        for part in value.split(','):
                            if part != '':
                                query_tuple = get_query_tuple(field_type, field, part)
                                if query_tuple:
                                    subquery |= Q(query_tuple)
                                    query_tuple = None
                        query &= subquery
                else:
                    # these are the AND fields
                    if value != '':
                        if type == 'exclude' and value[0] == '!':
                            query_tuple = get_query_tuple(field_type, field, value[1:])
                        elif type == 'filter' and value[0] != '!':
                            query_tuple = get_query_tuple(field_type, field, value)
                        if query_tuple and (i == 0 or field.split('__')[0] not in m2m_list):
                            query &= Q(query_tuple)
                            query_tuple = None
                        elif query_tuple:
                            additional_queries.append(Q(query_tuple))

    queries = [query]
    queries.extend(additional_queries)
    return queries
