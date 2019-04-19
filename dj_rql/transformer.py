from __future__ import unicode_literals


from __future__ import unicode_literals

from django.db.models import Q
from lark import Transformer, Tree

from dj_rql.constants import (
    ComparisonOperators, ListOperators, LogicalOperators,
    RQL_LIMIT_PARAM, RQL_OFFSET_PARAM,
)


class BaseRQLTransformer(Transformer):
    def comp(self, args):
        if len(args) == 2:
            # id=1
            operation = ComparisonOperators.EQ
            prop_index = 0
            value_index = 1
        elif args[0].data == 'comp_term':
            # eq(id,1)
            operation = self._get_value(args[0])
            prop_index = 1
            value_index = 2
        else:
            # id=eq=1
            operation = self._get_value(args[1])
            prop_index = 0
            value_index = 2

        return self._get_value(args[prop_index]), operation, self._get_value(args[value_index])

    @staticmethod
    def _get_value(obj):
        while isinstance(obj, Tree):
            obj = obj.children[0]
        return obj.value


class RQLToDjangoORMTransformer(BaseRQLTransformer):
    """ Parsed RQL AST tree transformer to Django ORM Query.

    Notes:
        Grammar-Function name mapping is made automatically by Lark.
    """
    def __init__(self, filter_cls_instance):
        self._filter_cls_instance = filter_cls_instance

    def start(self, args):
        return self._filter_cls_instance.queryset.filter(args[0]).distinct()

    def comp(self, args):
        return self._filter_cls_instance.build_q_for_filter(
            *super(RQLToDjangoORMTransformer, self).comp(args),
        )

    def logical(self, args):
        operation = args[0].data
        children = args[0].children
        if operation == LogicalOperators.get_grammar_key(LogicalOperators.NOT):
            return ~Q(children[0])
        if operation == LogicalOperators.get_grammar_key(LogicalOperators.AND):
            return Q(*children)

        q = Q()
        for child in children:
            q |= child
        return q

    def listing(self, args):
        # Django __in lookup is not used, because of null() values
        operation, prop = self._get_value(args[0]), self._get_value(args[1])
        f_op = ComparisonOperators.EQ if operation == ListOperators.IN else ComparisonOperators.NE

        q = Q()
        for value_tree in args[2:]:
            field_q = self._filter_cls_instance.build_q_for_filter(
                prop, f_op, self._get_value(value_tree),
            )
            if operation == ListOperators.IN:
                q |= field_q
            else:
                q &= field_q
        return q

    def searching(self, args):
        operation, prop, val = tuple(self._get_value(args[index]) for index in range(3))
        return self._filter_cls_instance.build_q_for_filter(prop, operation, val)

    def term(self, args):
        return args[0]

    def expr_term(self, args):
        return args[0]


class RQLLimitOffsetTransformer(BaseRQLTransformer):
    def __init__(self):
        self.limit = None
        self.offset = None

    def start(self, args):
        return self.limit, self.offset

    def comp(self, args):
        prop, operation, val = super(RQLLimitOffsetTransformer, self).comp(args)
        if prop in (RQL_LIMIT_PARAM, RQL_OFFSET_PARAM):
            if operation != ComparisonOperators.EQ:
                raise ValueError

            if prop == RQL_LIMIT_PARAM:
                if self.limit is not None:
                    raise ValueError
                self.limit = val
            elif prop == RQL_OFFSET_PARAM:
                if self.offset is not None:
                    raise ValueError
                self.offset = val
