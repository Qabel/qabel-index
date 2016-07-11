
"""

.. note::

    Validation => to check whether data matches the data model

    Verification => an action the user needs to complete to confirm a request


Hidden assumption for verification: some way or another we receive a HTTP request when the outcome is established.
E.g. link in a verification e-mail is clicked, SMS verification service POSTs to a specified URL, ...
"""

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from sendsms.message import SmsMessage

import mail_templated

from register_service.serializers import UpdateRequestSerializer
from .models import PendingVerification


class Verifier:
    FIELD = None

    def __init__(self, identity, action_to_confirm, field_to_verify_value, pending_verification_factory, url_filter):
        """
        Prepare verification process for *action_to_confirm* on *field_to_verify_value*.

        Note: allocate a PendingVerification here.
        """
        self.identity = identity
        self.action = action_to_confirm
        setattr(self, self.FIELD, field_to_verify_value)
        self.pending_verification_factory = pending_verification_factory
        self.url_filter = url_filter

    def start_verification(self):
        """Start the verification process."""

    def _context(self, pending_verification):
        return {
            'identity': self.identity,
            'action': self.action,
            'confirm_url': self.url_filter(pending_verification.confirm_url),
            'deny_url': self.url_filter(pending_verification.deny_url),
            'review_url': self.url_filter(pending_verification.review_url)
        }


class PendingMixin:
    def __init__(self, identity, action_to_confirm, field_to_verify_value, pending_verification_factory, url_filter):
        super().__init__(identity, action_to_confirm, field_to_verify_value, pending_verification_factory, url_filter)
        self.pending_verification = pending_verification_factory()


class EmailVerifier(PendingMixin, Verifier):
    FIELD = 'email'

    def start_verification(self):
        self.mail().send()

    def mail(self):
        return mail_templated.EmailMessage(
            template_name='verification/email.tpl',
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[self.email],
            context=self.mail_context()
        )

    def mail_context(self):
        context = self._context(self.pending_verification)
        context.update({
            'email': self.email,
        })
        return context


class PhoneVerifier(PendingMixin, Verifier):
    FIELD = 'phone'

    def start_verification(self):
        self.sms().send(fail_silently=False)

    def sms(self):
        return SmsMessage(
            to=[self.phone],
            body=self.body(),
        )

    def body(self):
        return render_to_string('verification/sms.tpl', context=self.body_context()).strip()

    def body_context(self):
        context = self._context(self.pending_verification)
        context.update({
            'phone': self.phone,
        })
        return context

VERIFIER_CLASSES = {
    'email': EmailVerifier,
    'phone': PhoneVerifier,
}


class VerificationManager:
    def __init__(self, identity, public_key_verified, pending_verification_factory, url_filter=None):
        self.identity = identity
        self.public_key_verified = public_key_verified
        self.pending_verification_factory = pending_verification_factory
        self.url_filter = url_filter or (lambda url: url)

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
        return verifier(self.identity, item.action, item.value,
                        self.pending_verification_factory, self.url_filter)


def verify(request, id, action):
    """Verify request directly with one request."""
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


def review(request, id):
    """Request review page."""
    ...
