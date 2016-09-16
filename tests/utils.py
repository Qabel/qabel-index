
from django.utils import translation

import pytest

from index_service.utils import short_id, normalize_phone_number, get_current_cc


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
