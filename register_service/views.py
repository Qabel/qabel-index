
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .crypto import NoiseBoxParser
from .models import Identity, Entry, PendingUpdateRequest, PendingVerification
from .serializers import IdentitySerializer, UpdateRequestSerializer


"""
Public API
==========

API endpoints are documented at the corresponding endpoint view.

Public keys are represented by their hexadecimal string encoding, since JSON cannot transport binary data.
"""


def error(description):
    return Response({'error': description}, 400)


@api_view(('GET',))
def api_root(request, format=None):
    """
    Return mapping of API names to API endpoint paths.

    Methods: GET

    Args: None

    Returns:
        JSON: {API name => API endpoint}
    """
    def root_index(*apis):
        response_data = {}
        for api in apis:
            response_data[api] = reverse('api-' + api, request=request, format=format)
        return Response(response_data)
    return root_index('key', 'search', 'update')


@api_view(('GET',))
def key(request, format=None):
    """
    Return the ephemeral server public key.

    Encrypt noise boxes for the update API with this key as the recipient.

    Methods: GET

    Args: None

    Returns:
        JSON: {'pubkey': 'public key (32 bytes), base64 encoded'}
    """
    raise NotImplementedError


@api_view(('GET',))
def search(request, format=None):
    """
    Search for identities registered for private data.

    Methods:
        GET

    Args (query string):
        field=value[&field=value...]

        with *field* one of 'phone' or 'email' and *value* the value to search for.

        When multiple field-value pairs are specified only identities matching all pairs will be returned.

        At least one pair must be specified.

    Returns:
        JSON: [identity, ...]

        with identity := {
            'public_key': 'hex of public key (32 bytes)',
            'drop_url': 'drop protocol URL',
            'alias': 'user specified alias',
        }

        At least one identity is returned for HTTP 200. HTTP 204 indicates no matches and carries no body.

    TODO: Specify. No special-casing of zero-match branch is less code and requires no client special-case.
    """
    data = request.query_params
    identities = Identity.objects
    if not data or set(data.keys()) > Entry.FIELDS:
        return error('No or unknown fields specified: ' + ', '.join(data.keys()))
    for field, value in data.items():
        identities = identities.filter(entry__field=field, entry__value=value)
    if not identities:
        return Response(status=204)
    return Response(IdentitySerializer(identities, many=True).data)


class UpdateView(APIView):
    """
    Atomically create or delete entries in the user register.

    Methods:
        PUT

    Content types:

        - application/json
        - application/vnd.qabel.noisebox+json

        If the content type is plain text it contains an *update request*. This is only valid for requests purely
        made of *deletes*.

        If the content is a noise box, then that noise box must be encrypted for the servers ephemeral key and it's
        signature must be made by the key pair the update request refers to.

        Any update request containing a *create* cannot be executed immediately, since they require explicit
        confirmation by the user. The HTTP status code is thus 202 (Accepted) and not indicative of the request status.

    Update request:
        JSON: {
            'identity': {
                'public_key': 'hex public key',
                'drop_url': 'drop_url',
                'alias': 'alias'
            },
            'items': [update item, ...]
        }

        A list of one or more *update items* specifying changes to the user register. An update request is either
        executed completely or denied completely.

    Update item:
        {
            'action': 'create' or 'delete',
            'field': field name,
            'value': field value
        }

        field name := one of 'phone' or 'email' (as usual)

    Returns:

         Data: None

         Status codes:

         202: accepted request, will be executed when user confirms it
         204: request executed
         400: malformed request
         401: cryptography failure, signing key does not match update request public_key,

         Notable framework status codes:

         415: incorrect content type

    Bugs:
        - seems complex, but really isn't
    """

    parser_classes = (JSONParser, NoiseBoxParser)

    def put(self, request, format=None):
        if request.content_type == NoiseBoxParser.media_type:
            pubkey, update_request = request.data
            if not pubkey or not self.is_key_authorized(pubkey, update_request):
                return Response(status=403)
            update_request.public_key_verified = True
            if update_request.verification_required():
                update_request.execute()
                return Response(status=204)
        else:
            serializer = UpdateRequestSerializer(data=request.data)
            serializer.is_valid(True)
            update_request = serializer.save()
            update_request.public_key_verified = False
        with transaction.atomic():
            serialized_request = UpdateRequestSerializer(update_request).data
            pur = PendingUpdateRequest(request=serialized_request)
            pur.save()
            update_request.start_verification(PendingVerification.get_factory(pur))
        return Response(status=202)

    def decrypt_request(self, request):
        """Decrypt noise box request. Return (sender's pubkey, deserialized request) or (None, None)."""
        raise NotImplementedError

    def is_key_authorized(self, pubkey, update_request):
        """Return whether all items of the request are covered by the given pubkey."""
        raise NotImplementedError

update = UpdateView.as_view()
