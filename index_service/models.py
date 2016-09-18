import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone

from django_prometheus.models import ExportModelOperationsMixin

from .utils import short_id


class CreationTimestampModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Identity(ExportModelOperationsMixin('Identity'), CreationTimestampModel):
    """
    An identity, composed of the public key, drop URL and alias.

    This is the only kind of data the register server is allowed to return to clients.
    """

    public_key = models.CharField(max_length=64)
    alias = models.CharField(max_length=255)
    drop_url = models.URLField()

    class Meta:
        # Index over the whole triplet; we'll access this way when processing update requests.
        index_together = ('public_key', 'alias', 'drop_url')
        unique_together = index_together
        verbose_name_plural = 'Identities'

    def delete_if_garbage(self):
        """Clean up this identity if there are no entries referring to it."""
        if not self.entry_set.count():
            self.delete()

    def __repr__(self):
        return 'alias: {} public_key: {}'.format(self.alias, repr(self.public_key))

    __str__ = __repr__


class Entry(ExportModelOperationsMixin('Entry'), CreationTimestampModel):
    """
    An Entry connects a piece of private data (email, phone, ...) to an identity.

    Clients query the register server with privata data to find associated public identities.
    """

    FIELDS_CHOICES = (
        ('email', 'E-Mail address'),
        ('phone', 'phone number'),
    )

    # These are the fields a client can search for
    FIELDS = {'email', 'phone'}

    field = models.CharField(max_length=30, db_index=True, choices=FIELDS_CHOICES)
    value = models.CharField(max_length=200)
    identity = models.ForeignKey(Identity)

    def __str__(self):
        return '{}: {}'.format(self.field, self.value)

    class Meta:
        # Note that there is no uniqueness of anything
        index_together = ('field', 'value')
        verbose_name_plural = 'Entries'


class PendingUpdateRequest(ExportModelOperationsMixin('PendingUpdateRequest'), CreationTimestampModel):
    """
    Pending update request: When additional user-asynchronous authorization is required a request has
    to be stored in the database (and all verifications have to complete) before it can be executed.

    If a request is received for which a verification is needed, it is saved as a PendingUpdateRequest and for each
    verification required a corresponding PendingVerification object is created.

    Verification handlers remove a PendingVerification if it succeeded, if no other verifications are pending for
    the request it is then executed.

    When a verification fails, the handler deletes the PendingRequest and all other PendingVerifications;
    the request has failed. There must be no notification mechanism to the requester, since the requester is
    not authenticated.

    Pending requests expire automatically after settings.PENDING_REQUEST_MAX_AGE.
    """

    # JSON-serialized request
    _json_request = models.TextField()

    @property
    def request(self):
        return json.loads(self._json_request)

    @request.setter
    def request(self, value):
        self._json_request = json.dumps(value)

    submit_date = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        if timezone.now() - self.submit_date >= settings.PENDING_REQUEST_MAX_AGE:
            return True
        return False


class PendingVerification(ExportModelOperationsMixin('PendingVerification'), models.Model):
    """
    A pending verification, e.g. a confirmation mail or SMS that has not been acted upon yet.
    """

    @classmethod
    def get_factory(cls, pending_request):
        def factory(id=None):
            while True:
                id = id or short_id(10)
                if cls.objects.filter(id=id).count():
                    id = None
                    continue
                break
            instance = cls(id=id, request=pending_request)
            instance.save()
            return instance
        return factory

    id = models.CharField(max_length=36, primary_key=True)
    request = models.ForeignKey(PendingUpdateRequest, on_delete=models.CASCADE)

    def _url(self, action):
        return reverse('verify', kwargs={
            'id': self.id,
            'action': action,
        })

    @property
    def confirm_url(self):
        return self._url('confirm')

    @property
    def deny_url(self):
        return self._url('deny')

    @property
    def review_url(self):
        return reverse('review', kwargs={
            'id': self.id
        })
