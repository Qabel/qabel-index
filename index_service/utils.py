import base64
import functools
import logging
import random
import re

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.utils import translation

import requests

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


logger = logging.getLogger('index_service.utils.authorization')


def authorization_cache_key(auth_header):
    return 'Auth-' + auth_header


def check_authorization(request):
    if not settings.REQUIRE_AUTHORIZATION:
        reason = 'No authorization required, none checked.'
        logger.info('Request is authorized: %s', reason)
        return True, reason
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if not auth_header:
        reason = 'No authorization supplied.'
        logger.warning('Request is unauthorized: %s', reason)
        return False, reason
    cache_key = authorization_cache_key(auth_header)
    reason = cache.get(cache_key)
    if reason:
        return True, 'Cached: ' + reason
    acked, reason = AccountingAuthorization().check(auth_header)
    if not acked:
        logger.warning('Request is unauthorized: %s', reason)
        return False, reason
    logger.info('Request is authorized: %s', reason)
    cache.set(cache_key, reason, 60)
    return True, reason


class AccountingAuthorization:
    def endpoint_url(self):
        return settings.ACCOUNTING_URL + '/api/v0/internal/user/'

    def headers(self):
        return {
            'APISECRET': settings.ACCOUNTING_APISECRET,
        }

    def check_response(self, response):
        code = response.status_code
        if code == 404:
            return False, 'User not found.'
        if code != 200:
            logger.warning('Failed accounting request was: status=%d, response=\n%s', code, response.content)
            try:
                reason = response.json()['error']
            except:
                reason = 'Unknown.'
            return False, reason

        try:
            json = response.json()
        except ValueError:
            logger.exception('Invalid JSON in reponse from accounting server: %s', response.content)
            return False, 'Invalid response.'

        try:
            active = json['active']
            user_id = json['user_id']
        except KeyError:
            logger.exception('Unable to parse accounting server response: %s', json)
            return False, 'Invalid response.'

        logger.info('Acknowledged token of user ID %s (active=%s)', user_id, active)
        if not active:
            return False, 'Account is disabled.'
        return True, ''

    def check(self, authorization, session=requests):
        """Check supplied authorization, return (authorized, public-reason)."""
        json = {
            'auth': authorization,
        }
        try:
            response = session.post(self.endpoint_url(), headers=self.headers(), json=json)
        except requests.RequestException:
            logger.exception('Accounting server request failed:')
            return False, 'Accounting server unreachable.'
        return self.check_response(response)


def authorized_api(view):
    """View decorator that enforces authorization, if enabled."""
    @functools.wraps(view)
    def wrapper(request, format=None):
        authorized, reason = check_authorization(request)
        if not authorized:
            return JsonResponse({'error': reason}, status=403)
        return view(request, format)
    return wrapper


def check_drop_id(drop_id):
    """
    Require a string of 43 randomly generated characters according to
    RFC 4648 Base 64 Encoding with URL and Filename Safe Alphabet.
    """
    try:
        return (len(drop_id) == 43
                and not re.search(r'[^-_A-Za-z0-9]', drop_id)
                and len(base64.b64decode(drop_id + '=', '-_')) == 32)
    except TypeError:
        return False


def check_drop_url(drop_url):
    validator = URLValidator(schemes=('http', 'https'))
    try:
        validator(drop_url)
    except ValidationError as ve:
        logger.error('check_drop_url: %r is not a drop URL: %s', drop_url, ve)
        return False
    # This always works, because it's at least http://something
    _, drop_id = drop_url.rsplit('/', maxsplit=1)
    if not check_drop_id(drop_id):
        logger.error('check_drop_url: %r is not a drop URL: invalid drop ID', drop_url)
        return False
    return True
