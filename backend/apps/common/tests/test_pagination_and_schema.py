from apps.common.pagination import (
    StandardCursorPagination,
    StandardPageNumberPagination,
)
from apps.common.schema import STANDARD_ERROR_RESPONSES, with_standard_errors


def test_page_number_pagination_matches_frontend_query_names():
    assert StandardPageNumberPagination.page_size_query_param == "pageSize"
    assert StandardPageNumberPagination.max_page_size == 100


def test_cursor_pagination_has_stable_tie_breaker():
    assert StandardCursorPagination.cursor_query_param == "cursor"
    assert StandardCursorPagination.ordering == ("-updated_at", "-id")


def test_standard_error_responses_can_be_extended():
    responses = with_standard_errors({200: "success"})

    assert set(STANDARD_ERROR_RESPONSES).issubset(responses)
    assert responses[200] == "success"
