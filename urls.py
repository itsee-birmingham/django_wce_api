from django.apps import apps
from django.urls import re_path, path
from api import views
from api.models import BaseModel

urlpatterns = [
    re_path(r'whoami', views.get_user),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/create/?$', views.ItemCreate.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/update/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemUpdate.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/delete/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemDelete.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/(?P<fieldname>[a-z_]+)/delete/(?P<itemmodel>[0-9_a-zA-Z]+)/(?P<itempk>[0-9_a-zA-Z]+)/?$',  # NoQA
            views.M2MItemDelete.as_view()),
    # private get models MUST COME FIRST
    # these are now only used in citations they have been combined for transcription app
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>private[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/?$', views.PrivateItemDetail.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>private[a-z_]+)/?$', views.PrivateItemList.as_view()),
    # non-private models
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemDetail.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/?$', views.ItemList.as_view())
]


urlpatterns_docs = []


# add extras just for the api docs!
def generate_dynamic_endpoints():
    endpoints = []
    for app in apps.get_app_configs():
        if app.label in ['citations']:
            for model in app.get_models():
                if issubclass(model, BaseModel):
                    if hasattr(model, 'AVAILABILITY') and model.AVAILABILITY == 'public':
                        list_endpoint = path(f'{app.label}/{model.__name__.lower()}/', views.ItemList.as_view(), name=f'{app.label}-{model.__name__.lower()}')  # NoQA
                        endpoints.append(list_endpoint)
    return endpoints


urlpatterns += generate_dynamic_endpoints()
