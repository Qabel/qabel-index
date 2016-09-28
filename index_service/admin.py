from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
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

    list_filter = ('created',)
    list_display = ('public_key_short', 'alias', 'email', 'phone')
    search_fields = ('public_key', 'alias', 'drop_url',)

    def public_key_short(self, identity):
        return identity.public_key[:32] + '...'
    public_key_short.short_description = _('shortened public key column')

    def _get_field(self, identity, field):
        try:
            return identity.entry_set.filter(field=field).get().value
        except ObjectDoesNotExist:
            return None
        except MultipleObjectsReturned:
            return '>1'

    def email(self, identity):
        return self._get_field(identity, 'email')
    email.short_description = _('email address column')

    def phone(self, identity):
        return self._get_field(identity, 'phone')
    phone.short_description = _('phone column')


class PendingVerificationInline(admin.TabularInline):
    model = models.PendingVerification


@admin.register(models.PendingUpdateRequest)
class PendingUpdateRequestAdmin(admin.ModelAdmin):
    readonly_fields = ('created',)
    inlines = (PendingVerificationInline,)

    search_fields = ('_json_request',)


@admin.register(models.DoneVerification)
class DoneVerificationAdmin(admin.ModelAdmin):
    fields = ('id', 'state',)
    readonly_fields = ('created',)
    list_display = ('id', 'state', 'created',)
