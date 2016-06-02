import collections
import codecs

from rest_framework.parsers import BaseParser

DecryptedNoiseBox = collections.namedtuple('DecryptedNoiseBox', 'sender_pubkey contents')


class NoiseBoxParser(BaseParser):
    # by the way, MIME type registration is free: http://www.iana.org/form/media-types
    media_type = 'application/vnd.qabel.noisebox+json'

    def parse(self, stream, media_type=None, parser_context=None):
        return DecryptedNoiseBox('0' * 64, b'')


def encode_public_key(public_key):
    """Return hex-string representation of binary *public_key*."""
    if len(public_key) != 32:
        raise ValueError('binary public keys must be 32 bytes')
    return codecs.encode(public_key, 'hex').decode()


def decode_public_key(public_key):
    """Return binary represntation of hex-string *public_key*."""
    if len(public_key) != 64:
        raise ValueError('hex public keys must be 64 characters long')
    return codecs.decode(public_key, 'hex')
