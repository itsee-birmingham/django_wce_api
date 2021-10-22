from django.conf.urls import re_path
from api import views

urlpatterns = [
    re_path(r'whoami', views.getUser),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/create/?$', views.ItemCreate.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/update/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemUpdate.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/delete/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemDelete.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/(?P<fieldname>[a-z_]+)/delete/(?P<itemmodel>[0-9_a-zA-Z]+)/(?P<itempk>[0-9_a-zA-Z]+)/?$',
            views.M2MItemDelete.as_view()),
    # private get models MUST COME FIRST
    # these are now only used in citations they have been combined for transcription app
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>private[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/?$', views.PrivateItemDetail.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>private[a-z_]+)/?$', views.PrivateItemList.as_view()),
    # non-private models
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/(?P<pk>[0-9_a-zA-Z]+)/?$', views.ItemDetail.as_view()),
    re_path(r'^(?P<app>[a-z_]+)/(?P<model>[a-z_]+)/?$', views.ItemList.as_view())

]
