from django.core.cache import cache
from rest_framework.response import Response

from apps.common.cache import public_cache_keys


class PublicListCacheMixin:
    cache_namespace = None
    cache_timeout = None

    def list(self, request, *args, **kwargs):
        key = public_cache_keys.key(
            self.cache_namespace,
            query=request.query_params,
            host=request.get_host(),
        )
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        response = super().list(request, *args, **kwargs)
        if response.status_code == 200:
            cache.set(key, response.data, timeout=self.cache_timeout)
        return response


class PublicDetailCacheMixin:
    cache_namespace = None
    cache_timeout = None

    def get_public_cache_key(self, request):
        return public_cache_keys.key(
            self.cache_namespace,
            identifier=self.kwargs[self.lookup_url_kwarg],
            host=request.get_host(),
        )

    def retrieve(self, request, *args, **kwargs):
        key = self.get_public_cache_key(request)
        cached = cache.get(key)
        if cached is not None:
            return Response(cached)
        instance = self.get_object()
        response = Response(self.get_serializer(instance).data)
        if self.should_cache_object(instance):
            cache.set(key, response.data, timeout=self.cache_timeout)
        return response

    def should_cache_object(self, obj):
        return True
