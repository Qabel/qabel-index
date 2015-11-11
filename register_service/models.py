from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class Identity(models.Model):
    alias = models.CharField(max_length=255, db_index=True, null=False, blank=False)
    public_key = models.TextField(null=False, blank=False, primary_key=True, db_index=True)
    drop_url = models.URLField(null=False, blank=False)
    email = models.EmailField(blank=True, db_index=True)
    mobile = PhoneNumberField(blank=True, db_index=True)
    created_at = models.DateTimeField(editable=False)
    updated_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        ''' On save, update timestamps '''
        if not self.created_at:
            self.created_at = timezone.now()
        self.updated_at = timezone.now()
        return super(Identity, self).save(*args, **kwargs)
