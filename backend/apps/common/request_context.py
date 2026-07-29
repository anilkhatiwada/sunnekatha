import re
from contextvars import ContextVar
from uuid import uuid4

_request_identifier = ContextVar("request_identifier", default="")


def current_request_identifier():
    return _request_identifier.get()


class RequestIdentifierMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        supplied = request.headers.get("X-Request-ID", "").strip()
        cleaned = re.sub(r"[^A-Za-z0-9._:-]", "-", supplied)[:100]
        identifier = cleaned if cleaned else str(uuid4())
        request.request_identifier = identifier
        token = _request_identifier.set(identifier)
        try:
            response = self.get_response(request)
            response["X-Request-ID"] = identifier
            return response
        finally:
            _request_identifier.reset(token)
