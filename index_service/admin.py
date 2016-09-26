from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models

admin.site.site_title = _('Index')
admin.site.site_header = _('Qabel Index Admin')
admin.site.index_title = _('Qabel Index Admin')


@admin.register(models.Entry)
class EntryAdmin(admin.ModelAdmin):
    pass


class EntryInlineAdmin(admin.TabularInline):
    model = models.Entry
    extra = 0


@admin.register(models.Identity)
class IdentityAdmin(admin.ModelAdmin):
    inlines = [EntryInlineAdmin]


class PendingVerificationInline(admin.TabularInline):
    model = models.PendingVerification


@admin.register(models.PendingUpdateRequest)
class PendingUpdateRequestAdmin(admin.ModelAdmin):
    inlines = (PendingVerificationInline,)
