from django.conf.urls import include, url
from django.contrib import admin
from register_service import views


rest_urls = [
    url(r'^search/', views.IdentityList.as_view(), name='api-search'),
    url(r'^create/', views.IdentityCreate.as_view(), name='api-create'),
    url(r'^update/', views.IdentityUpdate.as_view(), name='api-update')
]
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v0/', include(rest_urls))
]

