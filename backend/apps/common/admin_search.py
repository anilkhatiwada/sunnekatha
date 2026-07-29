from django.db.models import Q

from apps.search.service import matching_aliases


class RomanizedAliasAdminSearchMixin:
    """Supplement normal admin search with the public search alias index."""

    search_alias_mappings = ()

    def get_search_results(self, request, queryset, search_term):
        results, may_have_duplicates = super().get_search_results(
            request, queryset, search_term
        )
        term = search_term.strip()
        if not term or not self.search_alias_mappings:
            return results, may_have_duplicates
        aliases = matching_aliases(term)
        alias_filter = Q()
        has_aliases = False
        for entity_type, lookup in self.search_alias_mappings:
            object_ids = aliases.get(entity_type, set())
            if object_ids:
                alias_filter |= Q(**{f"{lookup}__in": object_ids})
                has_aliases = True
        if not has_aliases:
            return results, may_have_duplicates
        alias_results = queryset.filter(alias_filter)
        return results | alias_results, True
