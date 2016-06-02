
import pytest

from django.core import mail

from register_service.verification import EmailVerifier


@pytest.mark.parametrize('action', ['create', 'delete'])
def test_email_templating(identity, mocker, action):
    fake_pending_verification = mocker.MagicMock()
    fake_pending_verification.confirm_url = 'https://example.com/confirm'
    fake_pending_verification.deny_url = 'https://example.com/deny'
    ev = EmailVerifier(identity, action, 'foo@example.com', lambda: fake_pending_verification)
    ev.start_verification()

    assert len(mail.outbox) == 1
    message = mail.outbox.pop()
    assert message.to == ['foo@example.com']
    body = message.body
    assert identity.public_key in body
    assert fake_pending_verification.confirm_url in body
    assert fake_pending_verification.deny_url in body
