
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils.decorators import method_decorator
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .crypto import NoiseBoxParser, KeyPair, encode_key
from .models import Identity, Entry, PendingUpdateRequest, PendingVerification
from .serializers import SearchSerializer, UpdateRequestSerializer, SearchResultSerializer, IdentitySerializer, scrub_field, \
    ApiRequestSerializer
from .verification import execute_if_complete
from .utils import authorized_api


"""
Public API
==========

API endpoints are documented at the corresponding endpoint view.

Public keys are represented by their hexadecimal string encoding, since JSON cannot transport binary data.
"""


class RaisableResponse(Response, RuntimeError):
    pass


def error(description):
    return RaisableResponse({'error': description}, 400)


@api_view(('GET',))
@authorized_api
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
@authorized_api
def key(request, format=None):
    """
    Return the ephemeral server public key.
    """
    return Response({
        'public_key': encode_key(KeyPair(settings.SERVER_PRIVATE_KEY).public_key)
    })


@method_decorator(authorized_api, 'dispatch')
class SearchView(APIView):
    """
    Search for identities registered for private data.
    """

    parser_classes = (JSONParser,)

    def parse_value(self, field, value):
        try:
            return scrub_field(field, value)
        except ValueError as exc:
            raise error('Failed to parse field %r: %s' % (field, exc)) from exc

    def parse_query_params(self, query_params):
        """Return {field-name -> set-of-values}."""
        query_fields = query_params.keys()
        if not query_params or not set(query_fields) <= Entry.FIELDS:  # Note: (not <=) != (>=) for sets!
            raise error('No or unknown fields specified: ' + ', '.join(query_fields))
        fields = {}
        for field in query_fields:
            for value in query_params.getlist(field):
                value = self.parse_value(field, value)
                fields.setdefault(field, set()).add(value)
        return fields

    def parse_json(self, json):
        serializer = SearchSerializer(data=json)
        serializer.is_valid(True)
        query = serializer.save()['query']
        if not query:
            raise error('No fields specified.')
        fields = {}
        for field_value in query:
            field, value = field_value['field'], field_value['value']
            if field not in Entry.FIELDS:
                raise error('Unknown field %r specified.' % field)
            value = self.parse_value(field, value)
            fields.setdefault(field, set()).add(value)
        return fields

    def get_identities(self, fields):
        query = Q()
        for field, values in fields.items():
            for value in values:
                query |= Q(entry__field=field, entry__value=value)
        identities = Identity.objects.filter(query).distinct()
        return identities

    def mark_matching_fields(self, identity, fields):
        """identity.matches = list(fields that matched this identity)."""
        matches = []
        for field, search_values in fields.items():
            entries = identity.entry_set.filter(field=field)
            for entry in entries:
                identity_value = entry.value
                if identity_value in search_values:
                    matches.append({
                        'field': field,
                        'value': identity_value,
                    })
        # Makes query result reproducible, easier for tests and caching
        matches.sort(key=lambda match: (match['field'], match['value']))
        identity.matches = matches

    def process_search(self, fields):
        identities = self.get_identities(fields)
        for identity in identities:
            self.mark_matching_fields(identity, fields)
        return Response({
            'identities': SearchResultSerializer(identities, many=True).data
        })

    def get(self, request, format=None):
        try:
            fields = self.parse_query_params(request.query_params)
            return self.process_search(fields)
        except RaisableResponse as rr:
            return rr

    def post(self, request, format=None):
        try:
            fields = self.parse_json(request.data)
            return self.process_search(fields)
        except RaisableResponse as rr:
            return rr

search = SearchView.as_view()


@method_decorator(authorized_api, 'dispatch')
class UpdateView(APIView):
    """
    Atomically create or delete entries in the user directory.
    """

    parser_classes = (JSONParser, NoiseBoxParser)

    def put(self, request, format=None):
        if request.content_type == NoiseBoxParser.media_type:
            pubkey, update_request_json = request.data
            update_request = self.deserialize_update_request(update_request_json)
            if not pubkey or not self.is_key_authorized(pubkey, update_request):
                return Response(status=403)
            update_request.public_key_verified = True
        else:
            update_request = self.deserialize_update_request(request.data)
            update_request.public_key_verified = False
            if not update_request.items:
                return error('Need to encrypt identity update')
        with transaction.atomic():
            serialized_request = UpdateRequestSerializer(update_request).data
            pur = PendingUpdateRequest(request=serialized_request)
            pur.save()
            update_request.start_verification(PendingVerification.get_factory(pur), request.build_absolute_uri)
            if execute_if_complete(pur):
                # All done!
                return Response(status=204)
            else:
                return Response(status=202)

    def deserialize_update_request(self, json):
        serializer = UpdateRequestSerializer(data=json)
        serializer.is_valid(True)
        return serializer.save()

    def is_key_authorized(self, pubkey, update_request):
        """Return whether all items of the request are covered by the given pubkey."""
        try:
            return pubkey == bytes.fromhex(update_request.identity.public_key)
        except ValueError:
            return False

update = UpdateView.as_view()


def check_api_request(api_request, api_name):
    serializer = ApiRequestSerializer(data=api_request)
    serializer.is_valid(True)
    api_request = serializer.save()
    if api_request['api'] != api_name:
        return error('Request not meant for this API.')


@method_decorator(authorized_api, 'dispatch')
class StatusView(APIView):
    """
    Atomically create or delete entries in the user directory.
    """

    parser_classes = (NoiseBoxParser,)

    def post(self, request, format=None):
        public_key, api_request = request.data
        public_key = public_key.hex()
        error = check_api_request(api_request, 'status')
        if error:
            return error
        confirmed_entries = Entry.objects.filter(identity__public_key=public_key)
        pending_requests = PendingUpdateRequest.objects.filter(public_key=public_key)
        entries = []
        entries.extend(map(self.confirmed_entry, confirmed_entries))
        for request_entries in map(self.pending_request, pending_requests):
            entries.extend(request_entries)

        response = {
            'entries': entries,
            'identity': self.find_identity(public_key),
        }

        return Response(response)

    @staticmethod
    def find_identity(identity_pk):
        """Given the public key of an identity, return serialized identity."""
        try:
            identity = Identity.objects.get(public_key=identity_pk)
            return IdentitySerializer(identity).data
        except Identity.DoesNotExist:
            pur = PendingUpdateRequest.objects.filter(public_key=identity_pk)[:1].get()
            return pur.request['identity']

    @staticmethod
    def confirmed_entry(entry):
        return {
            'status': 'confirmed',
            'field': entry.field,
            'value': entry.value,
        }

    @staticmethod
    def pending_request(pur):
        serializer = UpdateRequestSerializer(data=pur.request)
        serializer.is_valid(raise_exception=True)
        request = serializer.save()
        for item in request.items:
            if item.action == 'create':
                status = 'unconfirmed'
            else:
                status = 'deletion-pending'
            yield {
                'status': status,
                'field': item.field,
                'value': item.value
            }

status = StatusView.as_view()


@method_decorator(authorized_api, 'dispatch')
class DeleteIdentityView(APIView):
    """
    Delete entire identity and all entries through encrypted request.
    """

    parser_classes = (NoiseBoxParser,)

    def post(self, request, format=None):
        public_key, api_request = request.data
        public_key = public_key.hex()
        error = check_api_request(api_request, 'delete-identity')
        if error:
            return error
        with transaction.atomic():
            try:
                Identity.objects.get(public_key=public_key).delete()
            except Identity.DoesNotExist:
                return Response(status=404)
        return Response(status=204)

delete_identity = DeleteIdentityView.as_view()
