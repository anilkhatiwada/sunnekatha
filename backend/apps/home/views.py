from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.home.serializers import HomeResponseSerializer
from apps.home.service import home_service


class HomeView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = HomeResponseSerializer

    def get(self, request):
        return Response(home_service.compose(user=request.user))
