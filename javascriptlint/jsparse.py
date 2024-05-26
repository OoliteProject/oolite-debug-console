#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
""" Parses a script into nodes. """
import re
import unittest

from jsengine import JSSyntaxError
import jsengine.parser
from jsengine.parser import kind as tok
from jsengine.parser import op
from jsengine.structs import *

from .util import JSVersion

def isvalidversion(jsversion):
    if jsversion is None:
        return True
    return jsengine.parser.is_valid_version(jsversion.version)

def findpossiblecomments(script, script_offset):
    assert not script_offset is None
    pos = 0
    single_line_re = r"//[^\r\n]*"
    multi_line_re = r"/\*(.*?)\*/"
    full_re = "(%s)|(%s)" % (single_line_re, multi_line_re)
    comment_re = re.compile(full_re, re.DOTALL)

    comments = []
    while True:
        match = comment_re.search(script, pos)
        if not match:
            return comments

        # Get the comment text
        comment_text = script[match.start():match.end()]
        if comment_text.startswith('/*'):
            comment_text = comment_text[2:-2]
            opcode = op.C_COMMENT
        else:
            comment_text = comment_text[2:]
            opcode = op.CPP_COMMENT

        start_offset = match.start()
        end_offset = match.end()-1

        comment_node = ParseNode(tok.COMMENT, opcode,
                                 script_offset + start_offset,
                                 script_offset + end_offset, comment_text, [])
        comments.append(comment_node)

        # Start searching immediately after the start of the comment in case
        # this one was within a string or a regexp.
        pos = match.start()+1

def parse(script, jsversion, start_offset=0):
    """ All node positions will be relative to start_offset. This allows
        scripts to be embedded in a file (for example, HTML).
    """
    assert not start_offset is None
    jsversion = jsversion or JSVersion.default()
    assert isvalidversion(jsversion), jsversion
    return jsengine.parser.parse(script, jsversion.version, start_offset)

def filtercomments(possible_comments, root_node):
    comment_ignore_ranges = NodeRanges()

    def process(node):
        if node.kind == tok.STRING or \
                (node.kind == tok.OBJECT and node.opcode == op.REGEXP):
            comment_ignore_ranges.add(node.start_offset, node.end_offset)
        for kid in node.kids:
            if kid:
                process(kid)
    process(root_node)

    comments = []
    for comment in possible_comments:
        if comment_ignore_ranges.has(comment.start_offset):
            continue
        comment_ignore_ranges.add(comment.start_offset, comment.end_offset)
        comments.append(comment)
    return comments

def findcomments(script, root_node, start_offset=0):
    possible_comments = findpossiblecomments(script, start_offset)
    return filtercomments(possible_comments, root_node)

def find_trailing_whitespace(script, script_offset):
    nodes = []

    trailing_whitespace = re.compile(r'\S(?P<whitespace>[^\S\r\n]+)([\r\n]|$)')

    for match in trailing_whitespace.finditer(script):
        start = match.start('whitespace')
        end = match.end('whitespace')
        nodes.append(ParseNode(tok.WHITESPACE, None,
                               script_offset + start,
                               script_offset + end-1,
                               script[start:end], []))
    return nodes

def is_compilable_unit(script, jsversion):
    jsversion = jsversion or JSVersion.default()
    assert isvalidversion(jsversion)
    return jsengine.parser.is_compilable_unit(script, jsversion.version)

def _dump_node(node, node_positions, depth=0):
    if node is None:
        print('     '*depth, end=' ')
        print('(None)')
        print()
    else:
        print('     '*depth, end=' ')
        print('%s, %s' % (repr(node.kind), repr(node.opcode)))
        print('     '*depth, end=' ')
        if node.kind != tok.RESERVED:
            print('%s - %s' % (node_positions.from_offset(node.start_offset),
                               node_positions.from_offset(node.end_offset)))
        if hasattr(node, 'atom'):
            print('     '*depth, end=' ')
            print('atom: %s' % node.atom)
        if node.no_semi:
            print('     '*depth, end=' ')
            print('(no semicolon)')
        print()
        for child_node in node.kids:
            _dump_node(child_node, node_positions, depth+1)

def dump_tree(script):
    node_positions = NodePositions(script)
    try:
        node = parse(script, None)
    except JSSyntaxError as error:
        pos = node_positions.from_offset(error.offset)
        print('Line %i, Column %i: %s' % (pos.line+1, pos.col+1, error.msg))
        return
    _dump_node(node, node_positions)

class TestComments(unittest.TestCase):
    def _test(self, script, expected_comments):
        root = parse(script, None)
        comments = findcomments(script, root)
        encountered_comments = [node.atom for node in comments]
        self.assertEqual(encountered_comments, list(expected_comments))
    def testSimpleComments(self):
        self._test('re = /\//g', ())
        self._test('re = /\///g', ())
        self._test('re = /\////g', ('g',))
    def testCComments(self):
        self._test('/*a*//*b*/', ('a', 'b'))
        self._test('/*a\r\na*//*b\r\nb*/', ('a\r\na', 'b\r\nb'))
        self._test('a//*b*/c', ('*b*/c',))
        self._test('a///*b*/c', ('/*b*/c',))
        self._test('a/*//*/;', ('//',))
        self._test('a/*b*/+/*c*/d', ('b', 'c'))

class TestNodePositions(unittest.TestCase):
    def _test(self, text, expected_lines, expected_cols):
        # Get a NodePos list
        positions = NodePositions(text)
        positions = [positions.from_offset(i) for i in range(0, len(text))]
        encountered_lines = ''.join([str(x.line) for x in positions])
        encountered_cols = ''.join([str(x.col) for x in positions])
        self.assertEqual(encountered_lines, expected_lines.replace(' ', ''))
        self.assertEqual(encountered_cols, expected_cols.replace(' ', ''))
    def testSimple(self):
        self._test(
            'abc\r\ndef\nghi\n\nj',
            '0000 0 1111 2222 3 4',
            '0123 4 0123 0123 0 0'
        )
        self._test(
            '\rabc',
            '0 111',
            '0 012'
        )
    def testText(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEqual(pos.text(NodePos(0, 0), NodePos(0, 0)), 'a')
        self.assertEqual(pos.text(NodePos(0, 0), NodePos(0, 2)), 'abc')
        self.assertEqual(pos.text(NodePos(0, 2), NodePos(1, 2)), 'c\r\ndef')
    def testOffset(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEqual(pos.to_offset(NodePos(0, 2)), 2)
        self.assertEqual(pos.to_offset(NodePos(1, 0)), 5)
        self.assertEqual(pos.to_offset(NodePos(3, 1)), 11)
    def testStartPos(self):
        pos = NodePositions('abc\r\ndef\n\nghi', NodePos(3, 4))
        self.assertEqual(pos.to_offset(NodePos(3, 4)), 0)
        self.assertEqual(pos.to_offset(NodePos(3, 5)), 1)
        self.assertEqual(pos.from_offset(0), NodePos(3, 4))
        self.assertEqual(pos.text(NodePos(3, 4), NodePos(3, 4)), 'a')
        self.assertEqual(pos.text(NodePos(3, 4), NodePos(3, 6)), 'abc')
        self.assertEqual(pos.text(NodePos(3, 6), NodePos(4, 2)), 'c\r\ndef')

class TestNodeRanges(unittest.TestCase):
    def testAdd(self):
        r = NodeRanges()
        r.add(5, 10)
        self.assertEqual(r._offsets, [5, 11])
        r.add(15, 20)
        self.assertEqual(r._offsets, [5, 11, 15, 21])
        r.add(21, 22)
        self.assertEqual(r._offsets, [5, 11, 15, 23])
        r.add(4, 5)
        self.assertEqual(r._offsets, [4, 11, 15, 23])
        r.add(9, 11)
        self.assertEqual(r._offsets, [4, 12, 15, 23])
        r.add(10, 20)
        self.assertEqual(r._offsets, [4, 23])
        r.add(4, 22)
        self.assertEqual(r._offsets, [4, 23])
        r.add(30, 30)
        self.assertEqual(r._offsets, [4, 23, 30, 31])
    def testHas(self):
        r = NodeRanges()
        r.add(5, 10)
        r.add(15, 15)
        assert not r.has(4)
        assert r.has(5)
        assert r.has(6)
        assert r.has(9)
        assert r.has(10)
        assert not r.has(14)
        assert r.has(15)
        assert not r.has(16)

class TestCompilableUnit(unittest.TestCase):
    def test(self):
        tests = (
            ('var s = "', False),
            ('bogon()', True),
            ('int syntax_error;', True),
            ('a /* b', False),
            ('re = /.*', False),
            ('{ // missing curly', False)
        )
        for text, expected in tests:
            encountered = is_compilable_unit(text, JSVersion.default())
            self.assertEqual(encountered, expected)
        self.assertTrue(not is_compilable_unit("/* test", JSVersion.default()))

class TestLineOffset(unittest.TestCase):
    def testErrorPos(self):
        def geterror(script, start_offset):
            try:
                parse(script, None, start_offset)
            except JSSyntaxError as error:
                return (error.offset, error.msg, error.msg_args)
            assert False
        self.assertEqual(geterror(' ?', 0), (1, 'syntax_error', {}))
        self.assertEqual(geterror('\n ?', 0), (2, 'syntax_error', {}))
        self.assertEqual(geterror(' ?', 2), (3, 'syntax_error', {}))
        self.assertEqual(geterror('\n ?', 2), (4, 'syntax_error', {}))
    def testNodePos(self):
        def getnodepos(script, start_offset):
            root = parse(script, None, start_offset)
            self.assertEqual(root.kind, tok.LC)
            var, = root.kids
            self.assertEqual(var.kind, tok.VAR)
            return var.start_offset
        self.assertEqual(getnodepos('var x;', 0), 0)
        self.assertEqual(getnodepos(' var x;', 0), 1)
        self.assertEqual(getnodepos('\n\n var x;', 0), 3)
        self.assertEqual(getnodepos('var x;', 7), 7)
        self.assertEqual(getnodepos(' var x;', 7), 8)
        self.assertEqual(getnodepos('\n\n var x;', 7), 10)
    def testComments(self):
        def testcomment(comment, startpos, expected_offset):
            root = parse(comment, None, startpos)
            comment, = findcomments(comment, root, startpos)
            self.assertEqual(comment.start_offset, expected_offset)
        for comment in ('/*comment*/', '//comment'):
            testcomment(comment, 0, 0)
            testcomment(' %s' % comment, 0, 1)
            testcomment('\n\n %s' % comment, 0, 3)
            testcomment('%s' % comment, 7, 7)
            testcomment(' %s' % comment, 7, 8)
            testcomment('\n\n %s' % comment, 7, 10)
    def testTrailingWhitespace(self):
        def testwhitespace(text, expected_whitespace):
            nodes = find_trailing_whitespace(text, 0)
            if expected_whitespace:
                node, = nodes
                self.assertEqual(node.atom, expected_whitespace)
            else:
                self.assertEqual(nodes, [])

        testwhitespace('  ', '')
        testwhitespace('  \n', '')
        testwhitespace('a  \n', '  ')
        testwhitespace('a\n   ', '')
        testwhitespace('a\n {}   ', '   ')
        testwhitespace('a\n {}   \n', '   ')

if __name__ == '__main__':
    unittest.main()

