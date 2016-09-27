
import pytest

from django.core import mail

import sendsms

from index_service.verification import EmailVerifier, PhoneVerifier


@pytest.mark.parametrize('action', ['create', 'delete'])
def test_email_templating(identity, mocker, action, write_mail):
    fake_pending_verification = mocker.MagicMock()
    fake_pending_verification.review_url = 'https://example.com/124'
    ev = EmailVerifier(identity, action, 'foo@example.com', lambda: fake_pending_verification, lambda url: url)
    ev.start_verification()

    assert len(mail.outbox) == 1
    write_mail(action)
    message = mail.outbox.pop()
    assert message.to == ['foo@example.com']
    body = message.body
    assert identity.public_key in body
    assert fake_pending_verification.review_url in body


def test_phone_sms_sent(identity, mocker):
    fake_pending_verification = mocker.MagicMock()
    fake_pending_verification.review_url = 'https://example.com/123/review'
    pv = PhoneVerifier(identity, 'create', '+49123456789', lambda: fake_pending_verification, lambda url: url)
    pv.start_verification()

    assert len(sendsms.outbox) == 1
    sms = sendsms.outbox.pop()
    assert sms.to == ['+49123456789']
    assert fake_pending_verification.review_url in sms.body
    assert len(sms.body) < 160, 'SMS too long (160 character limit)'
    assert sms.body == sms.body.strip(), 'No trailing/leading whitespace in SMS messages'
