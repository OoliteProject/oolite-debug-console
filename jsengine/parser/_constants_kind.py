# vim: sw=4 ts=4 et
# cag: 30-6-22, added LET & CONST

_KINDS = [
    'AND', 'ASSIGN',
    'BITAND', 'BITOR', 'BITXOR', 'BREAK',
    'CASE', 'CATCH', 'COLON', 'COMMA', 'COMMENT', 'CONST', 'CONTINUE',
    'DEC', 'DEFAULT', 'DELETE', 'DIVOP', 'DO', 'DOT',
    'EQ', 'EQOP',
    'FINALLY', 'FOR', 'FUNCTION',
    'HOOK',
    'IF', 'IN',  'INC', 'INSTANCEOF',
    'LB', 'LC', 'LET', 'LEXICALSCOPE', 'LP',
    'MINUS',
    'NAME', 'NEW', 'NUMBER',
    'OBJECT', 'OR',
    'PLUS', 'PRIMARY',
    'RB', 'RC', 'RELOP', 'RESERVED', 'RETURN', 'RP',
    'SEMI', 'SHOP', 'STAR', 'STRING', 'SWITCH',
    'THROW', 'TRY',
    'UNARYOP',
    'VAR',
    'WITH', 'WHILE', 'WHITESPACE',
    'YIELD', # TODO
]
class _Kind:
    def __init__(self, name):
        self._name = name

    def __eq__(self, other):
        assert isinstance(other, _Kind), repr(other)
        return self is other

    def __hash__(self):
        return hash(self._name)

    def __repr__(self):
        return 'kind.%s' % self._name

class _Kinds:
    def __init__(self):
        for kind in _KINDS:
            setattr(self, kind, _Kind(kind))
    def contains(self, item):
        return isinstance(item, _Kind)

kind = _Kinds()
