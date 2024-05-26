#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
# cag: 30-6-22, added LET & CONST support
import os.path
import unittest

from jsengine.parser import kind as tok
from jsengine.parser import op

from . import conf
from . import fs
from . import htmlparse
from . import jsparse
from . import lintwarnings
from . import util

_globals = frozenset([
    'Array', 'Boolean', 'Math', 'Number', 'String', 'RegExp', 'Script', 'Date',
    'isNaN', 'isFinite', 'parseFloat', 'parseInt',
    'eval', 'NaN', 'Infinity',
    'escape', 'unescape', 'uneval',
    'decodeURI', 'encodeURI', 'decodeURIComponent', 'encodeURIComponent',
    'Function', 'Object',
    'Error', 'InternalError', 'EvalError', 'RangeError', 'ReferenceError',
    'SyntaxError', 'TypeError', 'URIError',
    'arguments', 'undefined'
])

def _parse_control_comment(comment):
    """ Returns None or (keyword, parms) """
    comment_atom = comment.atom.strip()
    if comment_atom.lower().startswith('jsl:'):
        control_comment = comment_atom[4:]
    elif comment_atom.startswith('@') and comment_atom.endswith('@'):
        control_comment = comment_atom[1:-1]
    else:
        return None

    keywords = (
        'ignoreall',
        'ignore',
        'end',
        'option explicit',
        'import',
        'fallthru',
        'pass',
        'declare',
        'unused',
        'content-type',
    )
    for keyword in keywords:
        # The keyword must either match or be separated by a space.
        if control_comment.lower() == keyword or \
            (control_comment.lower().startswith(keyword) and \
             control_comment[len(keyword)].isspace()):
            parms = control_comment[len(keyword):].strip()
            return (comment, keyword, parms.strip())

    return None

class ScopeObject:
    """ Outer-level scopes will never be associated with a node.
        Inner-level scopes will always be associated with a node.
    """
    def __init__(self, parent, node, type_):
        assert type_ in ('scope', 'arg', 'function', 'var'), \
            'Unrecognized identifier type: %s' % type_
        self._parent = parent
        self._node = node
        self._type = type_
        self._kids = []
        self._identifiers = {}
        self._references = []
        self._unused = []

    @property
    def parent_scope(self):
        return self._parent

    @property
    def node(self):
        return self._node

    def add_scope(self, node):
        assert not node is None
        self._kids.append(ScopeObject(self, node, 'scope'))
        self._kids[-1]._parent = self
        self._kids[-1]._node = node
        return self._kids[-1]

    def add_declaration(self, name, node, type_):
        assert isinstance(name, str)
        self._identifiers[name] = ScopeObject(self, node, type_)

    def add_reference(self, name, node):
        self._references.append((name, node))

    def set_unused(self, name, node):
        self._unused.append((name, node))

    def has_property(self, name):
        return name in self._identifiers

    def get_property_type(self, name):
        if name in self._identifiers:
            return self._identifiers[name]._type
        return None

    def resolve_property(self, name):
        if name in self._identifiers:
            return self._identifiers[name]
        if self._parent:
            return self._parent.resolve_property(name)
        return None

    def get_identifier_warnings(self):
        """ Returns a tuple of unreferenced and undeclared, where each is a list
            of (scope, name, node) tuples.
        """
        unreferenced = {}
        undeclared = []
        obstructive = []
        self._find_warnings(unreferenced, undeclared, obstructive, False)

        # Convert "unreferenced" from a dictionary of:
        #   { (scope, name): node }
        # to a list of:
        #   [ (scope, name, node) ]
        # sorted by node position.
        unreferenced = [(key[0], key[1], node) for key, node
                        in list(unreferenced.items())]
        unreferenced.sort(key=lambda x: x[2].start_offset)

        return {
            'unreferenced': unreferenced,
            'undeclared': undeclared,
            'obstructive': obstructive,
        }

    def _find_warnings(self, unreferenced, undeclared, obstructive,
                       is_in_with_scope):
        """ unreferenced is a dictionary, such that:
                (scope, name): node
            }
            undeclared is a list, such that: [
                (scope, name, node)
            ]
            obstructive is a list, such that: [
                (scope, name, node)
            ]
        """
        if self._node and self._node.kind == tok.WITH:
            is_in_with_scope = True

        # Add all identifiers as unreferenced. Children scopes will remove
        # them if they are referenced.  Variables need to be keyed by name
        # instead of node, because function parameters share the same node.
        for name, info in list(self._identifiers.items()):
            unreferenced[(self, name)] = info.node

        # Check for variables that hide an identifier in a parent scope.
        if self._parent:
            for name, info in list(self._identifiers.items()):
                if self._parent.resolve_property(name):
                    obstructive.append((self, name, info.node))

        # Remove all declared variables from the "unreferenced" set; add all
        # undeclared variables to the "undeclared" list.
        for name, node in self._references:
            resolved = self.resolve_property(name)
            if resolved:
                # Make sure this isn't an assignment.
                if node.parent.kind in (tok.ASSIGN, tok.INC, tok.DEC) and \
                   node.node_index == 0 and \
                   node.parent.parent.kind == tok.SEMI:
                    continue
                unreferenced.pop((resolved.parent_scope, name), None)
            else:
                # with statements cannot have undeclared identifiers.
                if not is_in_with_scope:
                    undeclared.append((self, name, node))

        # Remove all variables that have been set as "unused".
        for name, node in self._unused:
            resolved = self.resolve_property(name)
            if resolved:
                unreferenced.pop((resolved.parent_scope, name), None)
            else:
                undeclared.append((self, name, node))

        for child in self._kids:
            child._find_warnings(unreferenced, undeclared, obstructive,
                                 is_in_with_scope)
    def find_scope(self, node):
        for kid in self._kids:
            scope = kid.find_scope(node)
            if scope:
                return scope

        # Always add it to the outer scope.
        if not self._parent:
            assert not self._node
            return self

        # Conditionally add it to an inner scope.
        assert self._node
        if (node.start_offset >= self._node.start_offset and \
            node.end_offset <= self._node.end_offset):
            return self

        return None

class _Script:
    def __init__(self):
        self._imports = set()
        self.scope = ScopeObject(None, None, 'scope')
        self._ignores = []
    def add_ignore(self, start, end):
        self._ignores.append((start, end))
    def should_ignore(self, offset):
        for start, end in self._ignores:
            if start <= offset <= end:
                return True
        return False
    def importscript(self, script):
        self._imports.add(script)
    def hasglobal(self, name):
        return not self._findglobal(name, set()) is None
    def _findglobal(self, name, searched):
        """ searched is a set of all searched scripts """
        # Avoid recursion.
        if self in searched:
            return None

        # Check this scope.
        if self.scope.has_property(name):
            return self
        searched.add(self)

        # Search imported scopes.
        for script in self._imports:
            global_ = script._findglobal(name, searched)
            if global_:
                return global_

        return None

def _findhtmlscripts(contents, default_version):
    # Disable the warning about starttag being unsubscriptable
    # pylint: disable=E1136

    starttag = None
    for tag in htmlparse.findscripttags(contents):
        if tag['type'] == 'start':
            # Ignore nested start tags.
            if not starttag:
                jsversion =  util.JSVersion.fromattr(tag['attr'], default_version)
                starttag = dict(tag, jsversion=jsversion)
                src = tag['attr'].get('src')
                if src:
                    yield {
                        'type': 'external',
                        'jsversion': jsversion,
                        'offset': tag['offset'],
                        'src': src,
                    }
        elif tag['type'] == 'end':
            if not starttag:
                continue

            # htmlparse returns 1-based line numbers. Calculate the
            # position of the script's contents.
            start_offset = starttag['offset'] + starttag['len']
            end_offset = tag['offset']
            script = contents[start_offset:end_offset]

            if not jsparse.isvalidversion(starttag['jsversion']) or \
               jsparse.is_compilable_unit(script, starttag['jsversion']):
                if script.strip():
                    yield {
                        'type': 'inline',
                        'jsversion': starttag['jsversion'],
                        'offset': start_offset,
                        'contents': script,
                    }
                starttag = None
        else:
            assert False, 'Invalid internal tag type %s' % tag['type']

def lint_files(paths, lint_error, encoding, conf=conf.Conf(), printpaths=True):
    def lint_file(path, kind, jsversion, encoding):
        def import_script(offset, import_path, jsversion):
            # The user can specify paths using backslashes (such as when
            # linting Windows scripts on a posix environment.
            import_path = import_path.replace('\\', os.sep)
            include_dirs = [os.path.dirname(path)] + conf['include-dir']
            for include_dir in include_dirs:
                abs_path = os.path.join(include_dir, import_path)
                if os.path.isfile(abs_path):
                    return lint_file(abs_path, 'js', jsversion, encoding)

            _report(offset, 'error', 'io_error', {
                'error': 'The file could not be found in any include paths: %s' % import_path
            })
            return _Script()

        def report_lint(node, errname, offset=0, **errargs):
            assert errname in lintwarnings.warnings, errname
            if conf[errname]:
                _report(offset or node.start_offset, 'warning', errname, errargs)

        def report_parse_error(offset, errname, errargs):
            assert errname in lintwarnings.errors, errname
            _report(offset, 'error', errname, errargs)

        def _report(offset, msg_type, errname, errargs):
            errdesc = lintwarnings.format_error(errname, **errargs)
            if lint_cache[normpath].should_ignore(offset):
                return None
            pos = node_positions.from_offset(offset)
            return lint_error(normpath, pos.line, pos.col, msg_type, errname, errdesc)

        normpath = fs.normpath(path)
        if normpath in lint_cache:
            return lint_cache[normpath]
        if printpaths:
            print(normpath)

        lint_cache[normpath] = _Script()
        try:
            contents = fs.readfile(path, encoding)
        except IOError as error:
            lint_error(normpath, 0, 0, 'error', 'io_error', str(error))
            return lint_cache[normpath]
        node_positions = jsparse.NodePositions(contents)

        script_parts = []
        if kind == 'js':
            script_parts.append((0, jsversion or conf['default-version'], contents))
        elif kind == 'html':
            assert jsversion is None
            for script in _findhtmlscripts(contents, conf['default-version']):
                # TODO: Warn about foreign languages.
                if not script['jsversion']:
                    continue

                if script['type'] == 'external':
                    other = import_script(script['offset'], script['src'], script['jsversion'])
                    lint_cache[normpath].importscript(other)
                elif script['type'] == 'inline':
                    script_parts.append((script['offset'], script['jsversion'],
                                         script['contents']))
                else:
                    assert False, 'Invalid internal script type %s' % \
                                  script['type']
        else:
            assert False, 'Unsupported file kind: %s' % kind

        _lint_script_parts(script_parts, lint_cache[normpath], report_lint, report_parse_error,
                           conf, import_script)
        return lint_cache[normpath]

    lint_cache = {}
    for path in paths:
        ext = os.path.splitext(path)[1]
        if ext.lower() in ['.htm', '.html']:
            lint_file(path, 'html', None, encoding)
        else:
            lint_file(path, 'js', None, encoding)

def _lint_script_part(script_offset, jsversion, script, script_cache, conf,
                      report_parse_error, report_lint, import_callback):
    def report(node, errname, offset=0, **errargs):
        if errname == 'empty_statement' and node.kind == tok.LC:
            for pass_ in passes:
                if pass_.start_offset > node.start_offset and \
                   pass_.end_offset < node.end_offset:
                    passes.remove(pass_)
                    return

        if errname == 'missing_break':
            # Find the end of the previous case/default and the beginning of
            # the next case/default.
            assert node.kind in (tok.CASE, tok.DEFAULT)
            prevnode = node.parent.kids[node.node_index-1]
            expectedfallthru = prevnode.end_offset, node.start_offset
        elif errname == 'missing_break_for_last_case':
            # Find the end of the current case/default and the end of the
            # switch.
            assert node.parent.kind == tok.LC
            expectedfallthru = node.end_offset, node.parent.end_offset
        else:
            expectedfallthru = None

        if expectedfallthru:
            start, end = expectedfallthru
            for fallthru in fallthrus:
                # Look for a fallthru between the end of the current case or
                # default statement and the beginning of the next token.
                if fallthru.start_offset > start and fallthru.end_offset < end:
                    fallthrus.remove(fallthru)
                    return

        report_lint(node, errname, offset, **errargs)

    declares = []
    unused_identifiers = []
    import_paths = []
    fallthrus = []
    passes = []

    possible_comments = jsparse.findpossiblecomments(script, script_offset)

    # Check control comments for the correct version. It may be this comment
    # isn't a valid comment (for example, it might be inside a string literal)
    # After parsing, validate that it's legitimate.
    jsversionnode = None
    for comment in possible_comments:
        cc = _parse_control_comment(comment)
        if cc:
            node, keyword, parms = cc
            if keyword == 'content-type':
                ccversion = util.JSVersion.fromtype(parms)
                if ccversion:
                    jsversion = ccversion
                    jsversionnode = node
                else:
                    report(node, 'unsupported_version', version=parms)

    if not jsparse.isvalidversion(jsversion):
        report_lint(jsversionnode, 'unsupported_version', script_offset,
                    version=jsversion.version)
        return

    if jsversion.e4x:
        report_lint(None, 'e4x_deprecated',
                    jsversionnode.start_offset if jsversionnode else script_offset)

    try:
        root = jsparse.parse(script, jsversion, script_offset)
    except jsparse.JSSyntaxError as error:
        # Report errors and quit.
        report_parse_error(error.offset, error.msg, error.msg_args)
        return

    comments = jsparse.filtercomments(possible_comments, root)

    if jsversionnode is not None and jsversionnode not in comments:
        # TODO
        report(jsversionnode, 'incorrect_version')

    start_ignore = None
    for comment in comments:
        cc = _parse_control_comment(comment)
        if cc:
            node, keyword, parms = cc
            if keyword == 'declare':
                if not util.isidentifier(parms):
                    report(node, 'jsl_cc_not_understood')
                else:
                    declares.append((parms, node))
            elif keyword == 'unused':
                if not util.isidentifier(parms):
                    report(node, 'jsl_cc_not_understood')
                else:
                    unused_identifiers.append((parms, node))
            elif keyword == 'ignore':
                if start_ignore:
                    report(node, 'mismatch_ctrl_comments')
                else:
                    start_ignore = node
            elif keyword == 'end':
                if start_ignore:
                    script_cache.add_ignore(start_ignore.start_offset, node.end_offset)
                    start_ignore = None
                else:
                    report(node, 'mismatch_ctrl_comments')
            elif keyword == 'import':
                if not parms:
                    report(node, 'jsl_cc_not_understood')
                else:
                    import_paths.append((node.start_offset, parms))
            elif keyword == 'fallthru':
                fallthrus.append(node)
            elif keyword == 'pass':
                passes.append(node)
        else:
            if comment.opcode == op.C_COMMENT:
                # Look for nested C-style comments.
                nested_comment = comment.atom.find('/*')
                if nested_comment < 0 and comment.atom.endswith('/'):
                    nested_comment = len(comment.atom) - 1
                # Report at the actual error of the location. Add two
                # characters for the opening two characters.
                if nested_comment >= 0:
                    offset = comment.start_offset + 2 + nested_comment
                    report(comment, 'nested_comment', offset=offset)
            if comment.atom.lower().startswith('jsl:'):
                report(comment, 'jsl_cc_not_understood')
            elif comment.atom.startswith('@'):
                report(comment, 'legacy_cc_not_understood')
    if start_ignore:
        report(start_ignore, 'mismatch_ctrl_comments')

    # Find all visitors and convert them into "onpush" callbacks that call "report"
    visitors = {
        'push': lintwarnings.make_visitors(conf)
    }
    for event in visitors:
        for kind, callbacks in list(visitors[event].items()):
            visitors[event][kind] = [_getreporter(callback, report) for callback in callbacks]

    # Push the scope/variable checks.
    _get_scope_checks(visitors, script_cache.scope, report)

    # kickoff!
    _lint_node(root, visitors)

    for fallthru in fallthrus:
        report(fallthru, 'invalid_fallthru')
    for fallthru in passes:
        report(fallthru, 'invalid_pass')

    # Process imports by copying global declarations into the universal scope.
    for offset, path in import_paths:
        script_cache.importscript(import_callback(offset, path, jsversion))

    for name, node in declares:
        declare_scope = script_cache.scope.find_scope(node)
        _warn_or_declare(declare_scope, name, 'var', node, report)

    for name, node in unused_identifiers:
        unused_scope = script_cache.scope.find_scope(node)
        unused_scope.set_unused(name, node)

    for node in jsparse.find_trailing_whitespace(script, script_offset):
        report(node, 'trailing_whitespace')

def _lint_script_parts(script_parts, script_cache, report_lint, report_parse_error, conf,
                       import_callback):

    for script_offset, jsversion, script in script_parts:
        _lint_script_part(script_offset, jsversion, script, script_cache, conf,
                          report_parse_error, report_lint, import_callback)

    scope = script_cache.scope
    identifier_warnings = scope.get_identifier_warnings()
    for decl_scope, name, node in identifier_warnings['undeclared']:
        if name in conf['declarations']:
            continue
        if name in _globals:
            continue
        if not script_cache.hasglobal(name):
            report_lint(node, 'undeclared_identifier', name=name)
    for ref_scope, name, node in identifier_warnings['unreferenced']:
        # Ignore the outer scope.
        if ref_scope != scope:
            type_ = ref_scope.get_property_type(name)
            if type_ == 'arg':
                report_lint(node, 'unreferenced_argument', name=name)
            elif type_ == 'function':
                report_lint(node, 'unreferenced_function', name=name)
            elif type_ == 'var':
                report_lint(node, 'unreferenced_variable', name=name)
            else:
                assert False, 'Unrecognized identifier type: %s' % type_
    for ref_scope, name, node in identifier_warnings['obstructive']:
        report_lint(node, 'identifier_hides_another', name=name)

def _getreporter(visitor, report):
    def onpush(node):
        try:
            ret = visitor(node)
            assert ret is None, 'visitor should raise an exception, not return a value'
        except lintwarnings.LintWarning as warning:
            # TODO: This is ugly hardcoding to improve the error positioning of
            # "missing_semicolon" errors.
            if visitor.warning in ('missing_semicolon', 'missing_semicolon_for_lambda',
                                   'trailing_comma', 'trailing_comma_in_array'):
                offset = warning.node.end_offset
            else:
                offset = None
            report(warning.node, visitor.warning, offset=offset, **warning.errargs)
    return onpush

def _warn_or_declare(scope, name, type_, node, report):
    property = scope.resolve_property(name)
    if property and property.parent_scope == scope:
        # Only warn about duplications in this scope.
        # Other scopes will be checked later.
        if property.node.kind == tok.NAME and property.node.opcode == op.ARGNAME:
            report(node, 'var_hides_arg', name=name)
        else:
            report(node, 'redeclared_var', name=name)
    else:
        scope.add_declaration(name, node, type_)

def _get_scope_checks(visitors, scope, report):
    scopes = [scope]

    def _visit(event, *args):
        def _decorate(fn):
            for arg in args:
                visitors.setdefault(event, {}).setdefault(arg, []).append(fn)
            return fn
        return _decorate

    @_visit('push', tok.NAME)
    def _push_name(node):
        if node.node_index == 0 and node.parent.kind == tok.COLON and node.parent.parent.kind == tok.RC:
            return # left side of object literal
        if node.parent.kind in [tok.VAR, tok.LET, tok.CONST]:
            _warn_or_declare(scopes[-1], node.atom, 'var', node, report)
            return
        if node.parent.kind == tok.CATCH:
            scopes[-1].add_declaration(node.atom, node, 'var')
        scopes[-1].add_reference(node.atom, node)

    @_visit('push', tok.FUNCTION)
    def _push_func(node):
        if node.opcode in (None, op.CLOSURE) and node.fn_name:
            _warn_or_declare(scopes[-1], node.fn_name, 'function', node, report)
        _push_scope(node)
        for var_name in node.fn_args:
            if scopes[-1].has_property(var_name.atom):
                report(var_name, 'duplicate_formal', name=var_name.atom)
            scopes[-1].add_declaration(var_name.atom, var_name, 'arg')

    @_visit('push', tok.LEXICALSCOPE, tok.WITH)
    def _push_scope(node):
        scopes.append(scopes[-1].add_scope(node))

    @_visit('pop', tok.FUNCTION, tok.LEXICALSCOPE, tok.WITH)
    def _pop_scope(node):
        scopes.pop()


def _lint_node(node, visitors):

    for kind in (node.kind, (node.kind, node.opcode)):
        if kind in visitors['push']:
            for visitor in visitors['push'][kind]:
                visitor(node)

    for child in node.kids:
        if child:
            _lint_node(child, visitors)

    for kind in (node.kind, (node.kind, node.opcode)):
        if kind in visitors['pop']:
            for visitor in visitors['pop'][kind]:
                visitor(node)


class TestLint(unittest.TestCase):
    def testFindScript(self):
        html = """
<html><body>
<script src=test.js></script>
hi&amp;b
a<script><!--
var s = '<script></script>';
--></script>
ok&amp;
..</script>
ok&amp;
</body>
</html>
"""
        scripts = [(x.get('src'), x.get('contents'))
                   for x in _findhtmlscripts(html, util.JSVersion.default())]
        self.assertEqual(scripts, [
            ('test.js', None),
            (None, "<!--\nvar s = '<script></script>';\n-->")
        ])
    def testJSVersion(self):
        def parsetag(starttag, default_version=None):
            script, = _findhtmlscripts(starttag + '/**/</script>', \
                                       default_version)
            return script

        script = parsetag('<script>')
        self.assertEqual(script['jsversion'], None)

        script = parsetag('<script language="vbscript">')
        self.assertEqual(script['jsversion'], None)

        script = parsetag('<script type="text/javascript">')
        self.assertEqual(script['jsversion'], util.JSVersion.default())

        script = parsetag('<SCRIPT TYPE="TEXT/JAVASCRIPT">')
        self.assertEqual(script['jsversion'], util.JSVersion.default())

        script = parsetag('<script type="text/javascript; version = 1.6 ">')
        self.assertEqual(script['jsversion'], util.JSVersion('1.6', False))

        script = parsetag('<script type="text/javascript; version = 1.6 ">')
        self.assertEqual(script['jsversion'], util.JSVersion('1.6', False))

        script = parsetag('<SCRIPT TYPE="TEXT/JAVASCRIPT; e4x = 1 ">')
        self.assertEqual(script['jsversion'], util.JSVersion('default', True))

        script = parsetag('<script type="" language="livescript">')
        self.assertEqual(script['jsversion'], util.JSVersion.default())

        script = parsetag('<script type="" language="MOCHA">')
        self.assertEqual(script['jsversion'], util.JSVersion.default())

        script = parsetag('<script type="" language="JavaScript1.2">')
        self.assertEqual(script['jsversion'], util.JSVersion('1.2', False))

        script = parsetag('<script type="text/javascript;version=1.2" language="javascript1.4">')
        self.assertEqual(script['jsversion'], util.JSVersion('1.2', False))

        # Test setting the default version.
        script = parsetag('<script>', util.JSVersion('1.2', False))
        self.assertEqual(script['jsversion'], util.JSVersion('1.2', False))

        script = parsetag('<script type="" language="mocha">',
                              util.JSVersion('1.2', False))
        self.assertEqual(script['jsversion'], util.JSVersion.default())

