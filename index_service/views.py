
from django.conf import settings
from django.db import transaction
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .crypto import NoiseBoxParser, KeyPair, encode_key
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
    """
    return Response({
        'public_key': encode_key(KeyPair(settings.SERVER_PRIVATE_KEY).public_key)
    })


@api_view(('GET',))
def search(request, format=None):
    """
    Search for identities registered for private data.
    """
    data = request.query_params
    identities = Identity.objects
    if not data or set(data.keys()) > Entry.FIELDS:
        return error('No or unknown fields specified: ' + ', '.join(data.keys()))
    for field, value in data.items():
        identities = identities.filter(entry__field=field, entry__value=value)
    return Response({'identities': IdentitySerializer(identities, many=True).data})


class UpdateView(APIView):
    """
    Atomically create or delete entries in the user directory.
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
            update_request.start_verification(PendingVerification.get_factory(pur), request.build_absolute_uri)
        return Response(status=202)

    def decrypt_request(self, request):
        """Decrypt noise box request. Return (sender's pubkey, deserialized request) or (None, None)."""
        raise NotImplementedError

    def is_key_authorized(self, pubkey, update_request):
        """Return whether all items of the request are covered by the given pubkey."""
        raise NotImplementedError

update = UpdateView.as_view()
