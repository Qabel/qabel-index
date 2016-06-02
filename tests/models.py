import datetime

from django.conf import settings
from django.utils import timezone

from register_service.models import PendingUpdateRequest


def test_superuser(admin_user):
    assert admin_user.is_staff


def test_pending_request_expires(db, mocker):
    MAX_AGE = settings.PENDING_REQUEST_MAX_AGE
    request = PendingUpdateRequest(request={})
    request.save()
    assert not request.is_expired()
    timezone.now = mocker.Mock(spec=timezone.now)
    timezone.now.return_value = request.submit_date + MAX_AGE - datetime.timedelta(seconds=1)
    assert not request.is_expired()
    timezone.now.return_value = request.submit_date + MAX_AGE
    assert request.is_expired()
