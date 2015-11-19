from django.conf.urls import include, url
from django.contrib import admin
from register_service import views


rest_urls = [
    url(r'^search/', views.IdentityList.as_view(), name='api-identitylist'),
    url(r'^identity/', views.IdentityCreate.as_view(), name='api-identity'),
    url(r'^update/', views.IdentityUpdate.as_view(), name='api-update')
]
urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/v0/', include(rest_urls))
]

