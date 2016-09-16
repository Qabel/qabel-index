
import random

from django.utils import translation

import phonenumbers


def short_id(length):
    CHARSET = 'CDEHKMPRSTUWXY2458'
    get_character = CHARSET.__getitem__
    random_numbers = (random.randrange(len(CHARSET)) for i in range(length))
    return ''.join(map(get_character, random_numbers))


def parse_phone_number(phone_number, fallback_cc):
    try:
        return phonenumbers.parse(phone_number, region=fallback_cc)
    except phonenumbers.NumberParseException as exc:
        raise ValueError('Unable to parse phone number %r: %s' % (phone_number, exc)) from exc


def normalize_phone_number(phone_number, fallback_cc):
    """
    Return (str) *phone_number* (str) normalized to ITU-T E.164.

    Apply fallback_CC (str/None) country code, if necessary.
    """
    phone_number = parse_phone_number(phone_number, fallback_cc)
    return phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)


def get_current_cc(language=None):
    language = language or translation.get_language()
    return language.split('-')[-1].upper()


def normalize_phone_number_localised(phone_number):
    return normalize_phone_number(phone_number, get_current_cc())
