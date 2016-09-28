
from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class IndexConfig(AppConfig):
    name = 'index_service'
    verbose_name = _('index service name')
