from django.contrib import admin
from django.utils.translation import ugettext_lazy as _

from . import models

admin.site.site_title = _('Index')
admin.site.site_header = _('Qabel Index Admin')
admin.site.index_title = _('Qabel Index Admin')


@admin.register(models.Entry)
class EntryAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)


class EntryInlineAdmin(admin.TabularInline):
    model = models.Entry
    extra = 0


@admin.register(models.Identity)
class IdentityAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)
    inlines = [EntryInlineAdmin]


class PendingVerificationInline(admin.TabularInline):
    model = models.PendingVerification


@admin.register(models.PendingUpdateRequest)
class PendingUpdateRequestAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)
    inlines = (PendingVerificationInline,)


@admin.register(models.DoneVerification)
class DoneVerificationAdmin(admin.ModelAdmin):
    fields = ('id', 'state',)
    readonly_fields = ('created',)
    list_display = ('id', 'state', 'created',)
