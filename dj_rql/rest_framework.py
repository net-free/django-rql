from __future__ import unicode_literals

from rest_framework.filters import BaseFilterBackend

from dj_rql.filter_cls import RQLFilterClass


class RQLFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        rql_filter_class = self._get_filter_class(view)
        query = self._get_query(request)
        return rql_filter_class(queryset).apply_filters(query)

    @staticmethod
    def _get_filter_class(view):
        rql_filter_class = getattr(view, 'rql_filter_class', None)

        assert rql_filter_class is not None, 'RQL Filter Class must be set in view.'
        assert issubclass(rql_filter_class, RQLFilterClass), \
            'Filtering class must subclass RQLFilterClass.'

        return rql_filter_class

    @staticmethod
    def _get_query(drf_request):
        return drf_request._request.META['QUERY_STRING']
