import io
import logging

from django.conf import settings
from django.core.checks import Error, register

from rest_framework.parsers import BaseParser, JSONParser
from rest_framework.exceptions import ParseError

from ._crypto import decrypt_box, KeyPair, NoiseError, encode_key, decode_key

logger = logging.getLogger('index_service.crypto')


class NoiseBoxParser(BaseParser):
    # by the way, MIME type registration is free: http://www.iana.org/form/media-types
    media_type = 'application/vnd.qabel.noisebox+json'
    upper_media_type = 'application/json'

    def __init__(self):
        super().__init__()
        self.upper_parser = JSONParser()

    def parse(self, stream, media_type=None, parser_context=None):
        box = stream.read()
        key_pair = KeyPair(settings.SERVER_PRIVATE_KEY)
        try:
            public_key, contents = decrypt_box(key_pair, box)
        except NoiseError as noise_error:
            logger.exception('decrypt_box() exception, public_key=' + key_pair.public_key.hex())
            raise ParseError from noise_error
        return public_key, self.upper_parser.parse(io.BytesIO(contents.encode()), self.upper_media_type)


@register()
def check_server_private_key(app_configs, **kwargs):
    try:
        KeyPair(settings.SERVER_PRIVATE_KEY)
    except (ValueError, AssertionError):
        return [
            Error('SERVER_PRIVATE_KEY must be 32 bytes or 64 hexadecimal characters.')
        ]
    return []
