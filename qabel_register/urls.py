from django.conf.urls import include, url
from django.contrib import admin
from register_service import views


rest_urls = [
    url(r'^$', views.api_root, name='api-root'),
    url(r'^key/$', views.key, name='api-key'),
    url(r'^search/$', views.search, name='api-search'),
    url(r'^update/$', views.update, name='api-update'),
]

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v0/', include(rest_urls))
]
