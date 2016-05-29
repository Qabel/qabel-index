import base64
import datetime
import uuid

from django.db import models

from register_service.logic import UpdateRequest


class Identity(models.Model):
    """
    An identity, composed of the public key, drop URL and alias.

    This is the only kind of data the register server is allowed to return to clients.
    """

    public_key = models.CharField(max_length=100)
    alias = models.CharField(max_length=255)
    drop_url = models.URLField()

    class Meta:
        # Index over the whole triplet; we'll access this way when processing update requests.
        index_together = ('public_key', 'alias', 'drop_url')
        unique_together = index_together

    def set_pub_key(self, pub_key):
        self.public_key = base64.encodebytes(pub_key)

    def get_pub_key(self):
        return base64.decodebytes(self.public_key)

    pub_key = property(get_pub_key, set_pub_key)

    def delete_if_garbage(self):
        """Clean up this identity if there are no entries referring to it."""
        if not self.entry_set.count():
            self.delete()

    def __repr__(self):
        return u'alias: {0} public_key: {1}'.format(self.alias, repr(self.public_key))


class Entry(models.Model):
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

    class Meta:
        # Note that there is no uniqueness of anything
        index_together = ('field', 'value')


class PendingUpdateRequest(models.Model):
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

    Pending requests expire automatically after MAXIMUM_AGE.
    """

    MAXIMUM_AGE = datetime.timedelta(days=3)

    # JSON-serialized request
    json_request = models.TextField()

    submit_date = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        if datetime.datetime.now() - self.submit_date > self.MAXIMUM_AGE:
            self.delete()
            return True
        return False


class PendingVerification(models.Model):
    """
    A pending verification, e.g. a confirmation mail or SMS that has not been acted upon yet.
    """

    @classmethod
    def get_factory(cls, pending_request):
        def factory(id=None):
            # TODO: generate shorter IDs (in prospect of SMS verification)
            id = str(uuid.uuid4()) or id
            return cls(id=id, request=pending_request)

    # UUIDv4 for this verification
    id = models.CharField(max_length=36, primary_key=True)
    request = models.ForeignKey(PendingUpdateRequest, on_delete=models.CASCADE)
