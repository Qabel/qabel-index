import datetime

import pytest

from django.conf import settings
from django.utils import timezone

from index_service.models import PendingUpdateRequest, PendingVerification


@pytest.fixture
def dumb_request():
    request = PendingUpdateRequest(request={})
    request.save()
    return request


def test_superuser(admin_user):
    assert admin_user.is_staff


def test_pending_request_expires(db, mocker, dumb_request):
    MAX_AGE = settings.PENDING_REQUEST_MAX_AGE
    assert not dumb_request.is_expired()

    timezone.now = mocker.Mock(spec=timezone.now)

    timezone.now.return_value = dumb_request.submit_date + MAX_AGE - datetime.timedelta(seconds=1)
    assert not dumb_request.is_expired()

    timezone.now.return_value = dumb_request.submit_date + MAX_AGE
    assert dumb_request.is_expired()


def test_pending_verification_duplicate_id(db, dumb_request):
    factory = PendingVerification.get_factory(dumb_request)
    verification1 = factory('1234')
    verification2 = factory('1234')
    assert verification1.id != verification2.id
