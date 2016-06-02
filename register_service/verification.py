
"""

.. note::

    Validation => to check whether data matches the data model

    Verification => an action the user needs to complete to confirm a request


Hidden assumption for verification: some way or another we receive a HTTP request when the outcome is established.
E.g. link in a verification e-mail is clicked, SMS verification service POSTs to a specified URL, ...

TODO: define top-level interface (factory<update request|item, pending_verification_factory> ?)
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

import mail_templated

from register_service.serializers import UpdateRequestSerializer
from .models import PendingVerification


class Verifier:
    def __init__(self, identity, action_to_confirm, field_to_verify_value, pending_verification_factory):
        """
        Prepare verification process for *action_to_confirm* on *field_to_verify_value*.

        Note: allocate a PendingVerification here.
        """

    def start_verification(self):
        """Start the verification process."""


class EmailVerifier(Verifier):
    # XXX request type
    def __init__(self, identity, action_to_confirm, email, pending_verification_factory):
        self.identity = identity
        self.action = action_to_confirm
        self.email = email
        self.pending_verification = pending_verification_factory()

    def start_verification(self):
        self.send_mail()

    def send_mail(self):
        mail_templated.send_mail(
            template_name='verification/email.tpl',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.email],
            context=self.mail_context()
        )

    def mail_context(self):
        return {
            'identity': self.identity,
            'email': self.email,
            'action': self.action,
            'confirm_url': self.pending_verification.confirm_url,
            'deny_url': self.pending_verification.deny_url,
        }


VERIFIER_CLASSES = {
    'email': EmailVerifier,
}


class VerificationManager:
    def __init__(self, identity, public_key_verified, pending_verification_factory):
        self.identity = identity
        self.public_key_verified = public_key_verified
        self.pending_verification_factory = pending_verification_factory

    def start_verification(self, items):
        verifiers = []
        for item in items:
            if item.verification_required(self.public_key_verified):
                verifier = self.get_verifier(item)
                verifiers.append(verifier)
        for verifier in verifiers:
            verifier.start_verification()

    def get_verifier(self, item):
        verifier = VERIFIER_CLASSES[item.field]
        return verifier(self.identity, item.action, item.value, self.pending_verification_factory)


def verify(request, id, action='view'):
    # TODO HTML templates
    pending_verification = get_object_or_404(PendingVerification, id=id)
    pending_request = pending_verification.request
    if pending_request.is_expired():
        pending_request.delete()
        return HttpResponse('xxx request expired xxx', status=400)
    if action == 'confirm':
        pending_verification.delete()
        if not pending_request.pendingverification_set.count():
            serializer = UpdateRequestSerializer(data=pending_request.request)
            serializer.is_valid(True)
            request = serializer.save()
            request.execute()
            pending_request.delete()
        return HttpResponse('xxx confirmed xxx')
    elif action == 'deny':
        pending_request.delete()
        return HttpResponse('xxx denied xxx')
    elif action == 'view':
        # TODO unused
        raise NotImplementedError
