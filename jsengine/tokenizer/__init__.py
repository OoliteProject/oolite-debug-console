# vim: sw=4 ts=4 et
from jsengine import JSSyntaxError
from . import tok
from . import _char_handlers

_CHARS = _char_handlers.CharHandler

_WHITESPACE = _CHARS.to_charset('\u0020\t\u000B\u000C\u00A0\uFFFF')
_LINETERMINATOR = _CHARS.to_charset('\u000A\u000D\u2028\u2029')
_DIGITS = _CHARS.to_charset('0123456789')
_HEX_LETTERS = _CHARS.to_charset('abcdefABCDEF')
_HEX_DIGITS = _CHARS.join_charsets(_DIGITS, _HEX_LETTERS)
_IDENT = _CHARS.to_charset('abcdefghijklmnopqrstuvwxyz' + \
                           'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
                           '$_')
_IDENT_WITH_DIGITS = _CHARS.join_charsets(_IDENT, _DIGITS)
_NUMBER_XS = _CHARS.to_charset('xX')
_NUMBER_ES = _CHARS.to_charset('eE')
_NUMBER_PLUS_MINUS = _CHARS.to_charset('+-')


def enable_debug_checks(enable=True):
    global _CHARS # pylint: disable=W0603
    if enable:
        _CHARS = _char_handlers.DebugCharHandler
    else:
        _CHARS = _char_handlers.CharHandler


class Token:
    def __init__(self, tok, atom=None):
        self.tok = tok
        self.atom = atom
        self.start_offset = None
        self.end_offset = None
    def set_offset(self, start_offset, end_offset):
        self.start_offset = start_offset
        self.end_offset = end_offset
    def __repr__(self):
        return 'Token(%r, %r)' % \
            (self.tok, self.atom)

class TokenStream:
    def __init__(self, content, start_offset=0):
        assert isinstance(start_offset, int)
        self._content = content
        self._start_offset = start_offset
        self._offset = 0
        self._watched_offset = None

    def get_offset(self):
        return self._start_offset + self._offset

    def watch_reads(self):
        self._watched_offset = self._offset

    def get_watched_reads(self):
        assert self._watched_offset is not None
        s = self._content[self._watched_offset:self._offset]
        self._watched_offset = None
        return s

    def eof(self):
        return self._offset >= len(self._content)

    def readchr(self):
        c = self.peekchr()
        if not c:
            raise JSSyntaxError(self.get_offset(), 'unexpected_eof')
        self._offset += 1
        return c

    def readchrif(self, expect):
        if self.peekchr() == expect:
            self._offset += 1
            return expect
        return _CHARS.none()

    def readchrin(self, seq):
        s = self.peekchrin(seq)
        if s:
            self._offset += 1
        return s

    def peekchr(self):
        if self._offset < len(self._content):
            return _CHARS.to_ord(self._content[self._offset])
        return _CHARS.none()

    def peekchrin(self, seq):
        c = self.peekchr()
        if c and _CHARS.in_charset(c, seq):
            return c
        return _CHARS.none()

    def readtextif(self, text):
        """ Returns the string if found. Otherwise returns None.
        """
        len_ = len(text)
        if self._offset + len_ <= len(self._content):
            peeked = self._content[self._offset:self._offset+len_]
            if peeked == text:
                self._offset += len_
                return text

        return None

class Tokenizer:
    def __init__(self, stream):
        self._stream = stream
        self._peeked = []
        self._error = False

    def peek(self):
        self._readahead()
        return self._peeked[-1]

    def peek_sameline(self):
        self._readahead()
        for peek in self._peeked:
            if peek.tok == tok.EOL:
                return peek
        else:
            return peek

    def advance(self):
        assert not self._error

        self._readahead()
        peek = self._peeked[-1]
        self._peeked = []
        if peek.tok == tok.ERROR:
            self._error = True
            raise JSSyntaxError(peek.start_offset, peek.atom or 'syntax_error')
        return peek

    def next_withregexp(self):
        assert not self._error
        self._readahead()
        if self._peeked[-1].tok == tok.DIV:
            token = self._parse_rest_of_regexp()
            token.set_offset(self._peeked[-1].start_offset, self._stream.get_offset()-1)
            self._peeked = []
            if token.tok == tok.ERROR:
                self._error = True
                raise JSSyntaxError(token.start_offset, token.atom or 'syntax_error')
            return token
        return self.advance()

    def expect(self, tok):
        encountered = self.advance()
        if encountered.tok != tok:
            raise JSSyntaxError(encountered.start_offset, 'expected_tok',
                                { 'token': tok.getliteral() })
        return encountered

    def expect_identifiername(self):
        encountered = self.advance()
        if tok.keywords.has(encountered.tok) != -1:
            encountered.tok = tok.NAME
        if encountered.tok != tok.NAME:
            raise JSSyntaxError(encountered.start_offset, 'syntax_error')
        return encountered

    def _readahead(self):
        """ Always ensure that a valid token is at the end of the queue.
        """
        if self._peeked:
            assert self._peeked[-1].tok not in (tok.EOL, tok.SPACE,
                                                tok.C_COMMENT, tok.CPP_COMMENT,
                                                tok.HTML_COMMENT)
            return
        while True:
            start_offset = self._stream.get_offset()
            peek = self._next()
            end_offset = self._stream.get_offset()-1
            if peek.tok == tok.ERROR:
                peek.set_offset(end_offset, end_offset)
            else:
                peek.set_offset(start_offset, end_offset)

            self._peeked.append(peek)
            assert isinstance(peek.tok, tok.TokenType), repr(peek.tok)
            if peek.tok not in (tok.EOL, tok.SPACE,
                                tok.C_COMMENT, tok.CPP_COMMENT,
                                tok.HTML_COMMENT):
                return

    def _parse_rest_of_regexp(self):
        stream = self._stream
        while True:
            c = stream.readchr()
            if c == _CHARS.to_ord('\\'):
                c = stream.readchr()
                if c == _CHARS.to_ord('\n'):
                    return Token(tok.ERROR)
            elif c == _CHARS.to_ord('['):
                while True:
                    # Handle escaped characters, but don't allow line breaks after the escape.
                    c = stream.readchr()
                    escaped = False
                    if c == _CHARS.to_ord('\\'):
                        c = stream.readchr()
                        escaped = True

                    if c == _CHARS.to_ord('\n'):
                        return Token(tok.ERROR)
                    if c == _CHARS.to_ord(']') and not escaped:
                        break
            elif c == _CHARS.to_ord('\n'):
                return Token(tok.ERROR)
            elif c == _CHARS.to_ord('/'):
                break

        # TODO: Validate and save
        while True:
            c = stream.readchrin(_IDENT)
            if not c:
                break

        return Token(tok.REGEXP)

    def _next(self, parse_regexp=False):
        stream = self._stream

        if stream.eof():
            return Token(tok.EOF)

        stream.watch_reads()

        c = stream.readchr()

        # WHITESPACE
        if _CHARS.in_charset(c, _WHITESPACE) or _CHARS.in_charset(c, _LINETERMINATOR):
            linebreak = _CHARS.in_charset(c, _LINETERMINATOR)
            while True:
                if stream.readchrin(_LINETERMINATOR):
                    linebreak = True
                elif stream.readchrin(_WHITESPACE):
                    pass
                else:
                    break
            if linebreak:
                return Token(tok.EOL)
            return Token(tok.SPACE)

        # COMMENTS
        if c == _CHARS.to_ord('/'):
            if stream.peekchr() == _CHARS.to_ord('/'):
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.CPP_COMMENT)
            if stream.peekchr() == _CHARS.to_ord('*'):
                linebreak = False
                while True:
                    if stream.eof():
                        return Token(tok.ERROR, atom='unterminated_comment')
                    c = stream.readchr()
                    if _CHARS.in_charset(c, _LINETERMINATOR):
                        linebreak = True
                    elif c == _CHARS.to_ord('*') and stream.readchrif(_CHARS.to_ord('/')):
                        return Token(tok.C_COMMENT)
                return Token(tok.EOF)
        elif c == _CHARS.to_ord('<'):
            if stream.readtextif('!--'):
                while not stream.eof() and not stream.peekchrin(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.HTML_COMMENT)

        # STRING LITERALS
        if c == _CHARS.to_ord('"') or c == _CHARS.to_ord("'"):
            # TODO: Decode
            s = ''
            quote = c
            while True:
                c = stream.readchr()
                if c == _CHARS.to_ord('\\'):
                    c = stream.readchr()
                elif c == quote:
                    return Token(tok.STRING, atom=s)
                s += _CHARS.from_ord(c)

        # NUMBERS
        if _CHARS.in_charset(c, _DIGITS) or (c == _CHARS.to_ord('.') and stream.peekchrin(_DIGITS)):
            s = c # TODO
            if c == _CHARS.to_ord('0') and stream.readchrin(_NUMBER_XS):
                # Hex
                while stream.readchrin(_HEX_DIGITS):
                    pass
            elif c == _CHARS.to_ord('0') and stream.readchrin(_DIGITS):
                # Octal
                while stream.readchrin(_DIGITS):
                    pass
            else:
                # Decimal
                if c != _CHARS.to_ord('.'):
                    while stream.readchrin(_DIGITS):
                        pass
                    stream.readchrif(_CHARS.to_ord('.'))

                while stream.readchrin(_DIGITS):
                    pass

                if stream.readchrin(_NUMBER_ES):
                    stream.readchrin(_NUMBER_PLUS_MINUS)
                    if not stream.readchrin(_DIGITS):
                        raise JSSyntaxError(stream.get_offset(), 'syntax_error')
                    while stream.readchrin(_DIGITS):
                        pass

                if stream.peekchrin(_IDENT):
                    return Token(tok.ERROR)

            atom = stream.get_watched_reads()
            return Token(tok.NUMBER, atom=atom)

        if tok.punctuators.hasprefix(_CHARS.from_ord(c)):
            s = _CHARS.from_ord(c)
            while True:
                c = stream.peekchr()
                if c and tok.punctuators.hasprefix(s + _CHARS.from_ord(c)):
                    s += _CHARS.from_ord(c)
                    stream.readchr()
                else:
                    break
            d = tok.punctuators.get(s)
            if not d:
                raise JSSyntaxError(stream.get_offset(), 'syntax_error')
            return Token(d)
        if _CHARS.in_charset(c, _IDENT):
            while stream.readchrin(_IDENT_WITH_DIGITS):
                pass

            atom = stream.get_watched_reads()
            tt = tok.keywords.get(atom, tok.NAME)
            t = Token(tt)
            t.atom = atom
            return t

        raise JSSyntaxError(stream.get_offset(), 'unexpected_char',
                            { 'char': _CHARS.from_ord(c) })
