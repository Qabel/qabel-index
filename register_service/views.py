import operator
from functools import reduce

from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from register_service.models import Identity
from register_service.serializers import IdentitySerializer


class IdentityList(APIView):
    def post(self, request, format=None):
        # Build a Q object with all the user's request parameters
        f = [Q(**{k + "__icontains": v}) for k,v in request.POST.dict().items()]
        identities = Identity.objects.filter(reduce(operator.or_, f))
        if not identities:
            return Response(status=204)
        else:
            serializer = IdentitySerializer(identities, many=True)
            return Response(serializer.data)

class IdentityCreate(APIView):
    def post(self, request, format=None):
        serializer = IdentitySerializer(data=request.POST)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        else:
            return Response(serializer.errors, status=400)


class IdentityUpdate(APIView):
    def post(self, request, format=None):
        public_key = request.POST.get('public_key')
        if not public_key:
            return Response("The public key is required.", status=404)
        try:
            identity = Identity.objects.get(public_key=public_key.rstrip())
        except Identity.DoesNotExist:
            return Response("", status=404)
        serializer = IdentitySerializer(identity, data=request.POST, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=200)
        else:
            return Response(serializer.errors, status=400)