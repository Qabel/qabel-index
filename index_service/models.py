import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from django_prometheus.models import ExportModelOperationsMixin

from .utils import short_id


class CreationTimestampModel(models.Model):
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('creation timestamp field'))

    class Meta:
        abstract = True


class Identity(ExportModelOperationsMixin('Identity'), CreationTimestampModel):
    """
    An identity, composed of the public key, drop URL and alias.

    This is the only kind of data the register server is allowed to return to clients.
    """

    public_key = models.CharField(max_length=64, db_index=True, unique=True)
    alias = models.CharField(max_length=255)
    drop_url = models.URLField()

    class Meta:
        verbose_name = _('identity model')
        verbose_name_plural = _('identities model plural')

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

    Clients query the register server with private data to find associated public identities.
    """

    FIELDS_CHOICES = (
        ('email', _('E-Mail address')),
        ('phone', _('Phone number')),
    )

    # These are the fields a client can search for
    FIELDS = {'email', 'phone'}

    field = models.CharField(max_length=30, db_index=True, choices=FIELDS_CHOICES)
    value = models.CharField(max_length=200)
    identity = models.ForeignKey(Identity)

    def __str__(self):
        return '{}: {}'.format(self.field, self.value)

    class Meta:
        index_together = ('field', 'identity')
        unique_together = ('field', 'identity')
        verbose_name = _('entry model')
        verbose_name_plural = _('entries model plural')


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

    def __str__(self):
        return '{}: {}'.format(self.created.replace(microsecond=0).isoformat(' '),
                               ', '.join(pv.id for pv in self.pendingverification_set.all()))

    class Meta:
        verbose_name = _('pending update request model')
        verbose_name_plural = _('pending update request model plural')


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

    def _update_state(self, state):
        id = self.id
        self.delete()
        dv, _ = DoneVerification.objects.get_or_create(id=id, defaults={'state': state})
        dv.state = state
        dv.save()

    def confirmed(self):
        self._update_state('confirmed')

    def denied(self):
        self._update_state('denied')

    def expired(self):
        self._update_state('expired')

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

    class Meta:
        verbose_name = _('pending verification model')
        verbose_name_plural = _('pending verification model plural')


class DoneVerification(ExportModelOperationsMixin('DoneVerification'), CreationTimestampModel):
    STATES = (
        ('confirmed', _('Confirmed')),
        ('denied', _('Denied')),
        ('expired', _('Expired')),
    )
    id = models.CharField(max_length=36, primary_key=True)
    state = models.CharField(max_length=20, choices=STATES)

    class Meta:
        verbose_name = _('done verification model')
        verbose_name_plural = _('done verification model plural')
