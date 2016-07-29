import io

from django.conf import settings
from django.core.checks import Error, register

from rest_framework.parsers import BaseParser, JSONParser

from ._crypto import decrypt_box, KeyPair, NoiseError, encode_key, decode_key


class NoiseBoxParser(BaseParser):
    # by the way, MIME type registration is free: http://www.iana.org/form/media-types
    media_type = 'application/vnd.qabel.noisebox+json'
    upper_media_type = 'application/json'

    def __init__(self):
        super().__init__()
        self.upper_parser = JSONParser()

    def parse(self, stream, media_type=None, parser_context=None):
        box = stream.read()
        public_key, contents = decrypt_box(KeyPair(settings.SERVER_PRIVATE_KEY), box)
        return public_key, self.upper_parser.parse(io.BytesIO(contents.encode()), self.upper_media_type)


@register(deploy=True)
def check_server_private_key(app_configs, **kwargs):
    try:
        KeyPair(settings.SERVER_PRIVATE_KEY)
    except (ValueError, AssertionError):
        return [
            Error('SERVER_PRIVATE_KEY must be 32 bytes or 64 hexadecimal characters.')
        ]
    return []
