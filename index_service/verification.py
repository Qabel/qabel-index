
"""

.. note::

    Validation => to check whether data matches the data model

    Verification => an action the user needs to complete to confirm a request


Hidden assumption for verification: some way or another we receive a HTTP request when the outcome is established.
E.g. link in a verification e-mail is clicked, SMS verification service POSTs to a specified URL, ...
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.template.response import TemplateResponse as render
from django.utils.translation import ugettext_lazy as _

from sendsms.message import SmsMessage

from index_service.serializers import UpdateRequestSerializer
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
        context = self.mail_context()
        subject = _('Qabel Index confirmation')
        body = render_to_string('verification/email.txt', context)
        from_email = settings.DEFAULT_FROM_EMAIL
        email_message = EmailMultiAlternatives(subject, body, from_email, [self.email])
        html_email = render_to_string('verification/email.html', context)
        email_message.attach_alternative(html_email, 'text/html')
        email_message.context = context

        return email_message

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
        if settings.FACET_SHALLOW_VERIFICATION:
            return
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


def execute_if_complete(pending_request):
    if pending_request.pendingverification_set.count():
        return False
    serializer = UpdateRequestSerializer(data=pending_request.request)
    serializer.is_valid(True)
    request = serializer.save()
    request.execute()
    pending_request.delete()
    return True


def expired(request):
    return render(request, 'request_expired.html')


def confirmed(request):
    return render(request, 'request_status.html', {
        'status': 'confirmed',
    })


def denied(request):
    return render(request, 'request_status.html', {
        'status': 'denied',
    })


def verify(request, id, action):
    """Verify request directly with one request."""
    pending_verification = get_object_or_404(PendingVerification, id=id)
    pending_request = pending_verification.request
    if pending_request.is_expired():
        pending_request.delete()
        return expired(request)
    if action == 'confirm':
        pending_verification.delete()
        assert execute_if_complete(pending_request)
        return confirmed(request)
    elif action == 'deny':
        pending_request.delete()
        return denied(request)


def review(request, id):
    """Request review page."""
    action = request.POST.get('action')
    if action in ('confirm', 'deny'):
        return redirect(verify, id=id, action=action)
    pending_verification = get_object_or_404(PendingVerification, id=id)
    pending_request = pending_verification.request
    if pending_request.is_expired():
        pending_request.delete()
        return expired(request)
    req = pending_request.request
    return render(request, 'review.html', {
        'items': req['items'],
        'identity': req['identity'],
    })
