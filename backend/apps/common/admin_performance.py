def is_admin_changelist_request(request):
    match = getattr(request, "resolver_match", None)
    return bool(match and match.url_name and match.url_name.endswith("_changelist"))


def is_admin_autocomplete_request(request):
    match = getattr(request, "resolver_match", None)
    return bool(match and match.url_name == "autocomplete")
