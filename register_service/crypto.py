from django.conf import settings
from django.core.checks import Error, register

from rest_framework.parsers import BaseParser

from ._crypto import decrypt_box, KeyPair, NoiseError, encode_key, decode_key


class NoiseBoxParser(BaseParser):
    # by the way, MIME type registration is free: http://www.iana.org/form/media-types
    media_type = 'application/vnd.qabel.noisebox+json'

    def parse(self, stream, media_type=None, parser_context=None):
        box = stream.read()
        return decrypt_box(KeyPair(settings.SERVER_PRIVATE_KEY), box)


@register(deploy=True)
def check_server_private_key(app_configs, **kwargs):
    try:
        KeyPair(settings.SERVER_PRIVATE_KEY)
    except (ValueError, AssertionError):
        return [
            Error('SERVER_PRIVATE_KEY must be 32 bytes or 64 hexadecimal characters.')
        ]
    return []
