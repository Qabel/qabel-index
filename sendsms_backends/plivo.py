"""
http://pypi.python.org/pypi/plivo/
"""
import logging

from plivo import RestAPI

from django.conf import settings

from sendsms.backends.base import BaseSmsBackend

PLIVO_AUTH_ID = getattr(settings, 'PLIVO_AUTH_ID', '')
PLIVO_AUTH_TOKEN = getattr(settings, 'PLIVO_AUTH_TOKEN', '')

PLIVO_REPORT_URL = getattr(settings, 'PLIVO_REPORT_URL', '')
PLIVO_REPORT_METHOD = getattr(settings, 'PLIVO_REPORT_METHOD', 'GET')

logger = logging.getLogger(__name__)

report_params = {}
if PLIVO_REPORT_URL:
    report_params.update({
        'url': PLIVO_REPORT_URL,
        'method': PLIVO_REPORT_METHOD,
    })
    logger.info('Picked up report URL: %s, HTTP verb: %s', PLIVO_REPORT_URL, PLIVO_REPORT_METHOD)


class SmsBackend(BaseSmsBackend):
    def send_messages(self, messages):
        api = RestAPI(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN)
        for message in messages:
            params = {
                'src': message.from_phone,
                'text': message.body,
            }
            params.update(report_params)

            for to in message.to:
                try:
                    params.update({
                        'dst': to,
                    })
                    logger.debug('Sending message from %s to %s (%d bytes body)',
                                 message.from_phone, to,
                                 len(message.body.encode()))
                    status_code, response = api.send_message(params)
                    ok = status_code in (200, 202, 204)
                    log = logger.info if ok else logger.error
                    log('Message status: %d\nResponse is: %s', status_code, response)
                except Exception:
                    logger.exception('Exception while sending message (fail_silently=%s)', self.fail_silently)
                    if not self.fail_silently:
                        raise
