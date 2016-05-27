import collections

from rest_framework.parsers import BaseParser

_NoiseBox = collections.namedtuple('_NoiseBox', 'sender_pubkey contents')


class NoiseBox(_NoiseBox):
    sender_pubkey = None
    contents = None


class NoiseBoxParser(BaseParser):
    # by the way, MIME type registration is free: http://www.iana.org/form/media-types
    media_type = 'application/vnd.qabel.noisebox+json'

    def parse(self, stream, media_type=None, parser_context=None):
        return NoiseBox()
