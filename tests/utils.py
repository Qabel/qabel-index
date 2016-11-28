
from unittest.mock import MagicMock

from django.utils import translation

import pytest

from index_service.utils import short_id, normalize_phone_number, get_current_cc, AccountingAuthorization, check_drop_url


def test_short_id():
    id = short_id(5)
    assert len(id) == 5
    other_id = short_id(5)
    assert other_id != id  # failure probability: 18**-5 ~ 529 ppb


class NormalizePhoneNumberTest:
    def test_no_fallback_failing(self):
        with pytest.raises(ValueError):
            normalize_phone_number('1234 / 5678', None)  # No CC, no fallback

    def test_no_fallback(self):
        number = normalize_phone_number('+49 1234-5678', None)
        assert number == '+4912345678'

    @pytest.mark.parametrize('input, fallback_cc, output', (
            ('0010 1234', 'DE', '+101234'),
            ('0010 1234', 'AZ', '+101234'),
            ('001110 1234', 'AU', '+101234'),
    ))
    def test_outgoing_international(self, input, fallback_cc, output):
        assert normalize_phone_number(input, fallback_cc) == output

    def test_outgoing_international_no_fallback(self):
        with pytest.raises(ValueError):
            normalize_phone_number('0010 1234', None)

    def test_fallback_differs(self):
        assert normalize_phone_number('+10 1234', 'DE') == '+101234'  # DE = +49

    def test_fallback(self):
        assert normalize_phone_number('1234', 'DE') == '+491234'

    def test_fallback_capitalization(self):
        with pytest.raises(ValueError):
            assert normalize_phone_number('1234', 'de') == '+491234'


class GetCurrentCcTest:
    def test_from_default(self):
        assert get_current_cc() == 'DE'

    def test_explicit(self):
        assert get_current_cc('en-us') == 'US'

    def test_activated(self):
        with translation.override('en-au'):
            assert get_current_cc() == 'AU'


class AccountingAuthorizationTest:
    def test_headers(self, settings):
        aa = AccountingAuthorization()
        settings.ACCOUNTING_APISECRET = 'foo und bar'
        headers = aa.headers()
        assert len(headers) == 1
        assert headers['APISECRET'] == 'foo und bar'

    def test_endpoint_url(self, settings):
        aa = AccountingAuthorization()
        settings.ACCOUNTING_URL = 'gopher://accounting.plan9/foo'
        assert aa.endpoint_url() == 'gopher://accounting.plan9/foo/api/v0/internal/user/'

    def test_check(self):
        aa = AccountingAuthorization()
        session = MagicMock()
        token = 'Token 1234'
        ok, reason = aa.check(token, session)
        assert not ok
        json = {
            'auth': token,
        }
        session.post.assert_called_once_with(aa.endpoint_url(), headers=aa.headers(), json=json)

    @pytest.mark.parametrize('status_code, json, ok, reason', (
        (200, {'user_id': 5, 'active': True}, True, None),
        (200, {'user_id': 5, 'active': False}, False, 'Account is disabled.'),
        (200, {'active': False}, False, 'Invalid response.'),
        (200, {'user_id': 5}, False, 'Invalid response.'),
        (200, {}, False, 'Invalid response.'),
        (404, {}, False, 'User not found.'),
        (400, {'user_id': 5, 'active': True}, False, 'Unknown.'),  # wrong status code but proper JSON shall fail
        (400, {'error': 'the foo did not bar'}, False, 'the foo did not bar'),
    ))
    def test_check_response(self, status_code, json, ok, reason):
        aa = AccountingAuthorization()
        response = MagicMock()
        response.status_code = status_code
        response.json.return_value = json
        result, result_reason = aa.check_response(response)
        assert result is ok
        if reason:
            assert result_reason == reason


class CheckDropUrlTest:
    @pytest.mark.parametrize('input', (
        '',
        'wss://foo.bar/1234567890123456789012345678901234567890123',
        'http://horst/1234567890123456789012345678901234567890123',
        'http://foo.bar/1234567890123456789012345678901234567890',
        'http://foo.bar/bcdefghijklmnopqrstuvwxyzabcdefghijklmnopo',
        'http://foo.bar/xabcdefghijklmnopqrstuvwxyzabcdefghijklmnopo',
        'http://foo.bar/.bcdefghijklmnopqrstuvwxyzabcdefghijklmnopo',
        'http://foo.bar/abcdefghijklmnopqrstuvwxyzabcdefghijklmnopq/',
    ))
    def test_invalid(self, input):
        assert not check_drop_url(input)

    @pytest.mark.parametrize('input', (
        'http://foo.bar/abcdefghijklmnopqrstuvwxyzabcdefghijklmnopq',
        'https://foo.bar/abcdefghijklmnopqrstuvwxyzabcdefghijklmnopq',
        'http://localhost/1234567890123456789012345678901234567890123',
        'http://foo.bar./abcdefghijklmnopqrstuvwxyzabcdefghijklmnopq',
    ))
    def test_valid(self, input):
        assert check_drop_url(input)
