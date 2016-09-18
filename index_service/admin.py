from django.contrib import admin

from . import models


@admin.register(models.Identity)
class IdentityAdmin(admin.ModelAdmin):
    pass


@admin.register(models.Entry)
class EntryAdmin(admin.ModelAdmin):
    pass


class PendingVerificationInline(admin.TabularInline):
    model = models.PendingVerification


@admin.register(models.PendingUpdateRequest)
class PendingUpdateRequestAdmin(admin.ModelAdmin):
    inlines = (PendingVerificationInline,)
