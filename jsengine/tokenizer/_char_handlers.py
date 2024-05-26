
class _BaseHandler:

    @staticmethod
    def to_charset(s):
        return _Charset(set(ord(c) for c in s))

    @staticmethod
    def join_charsets(a, b):
        return _Charset(a._u | b._u)


class CharHandler(_BaseHandler):

    @staticmethod
    def to_ord(c):
        return ord(c)

    @staticmethod
    def from_ord(i):
        return chr(i)

    @staticmethod
    def in_charset(c, cs):
        return cs.contains(c)

    @staticmethod
    def none():
        return None


class DebugCharHandler(_BaseHandler):

    @staticmethod
    def to_ord(c):
        return _Char(CharHandler.to_ord(c))

    @staticmethod
    def from_ord(c):
        return CharHandler.from_ord(c._u)

    @staticmethod
    def in_charset(c, cs):
        assert isinstance(c, _Char)
        return cs.contains(c._u)

    @staticmethod
    def none():
        return _Char(CharHandler.none())


class _Char:
    def __init__(self, u):
        assert isinstance(u, int) or u is None, u
        self._u = u

    def __hash__(self):
        return hash(self._u)

    def __eq__(self, other):
        assert isinstance(other, _Char), other
        return self._u == other._u

    def __bool__(self):
        return not self._u is None


class _Charset:
    def __init__(self, u):
        assert isinstance(u, set)
        for i in u:
            assert isinstance(i, int)
        self._u = u

    def contains(self, u):
        return u in self._u

    def __add__(self, other):
        return _Charset(self._u | other._u)

