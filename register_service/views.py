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
