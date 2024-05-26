# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#

import re
import debugGUI.constants as con

import pdb

def _minRE(regex):
	# remove comments, reduce leading runs of whitespace to single space
	return re.sub(r'\s*[#].*?[\n]\s*|^\s+|[\t\n]+', ' ', regex).replace('  ', ' ')
	# return re.sub(r'\s*[#].*?\n\s*|^\s+|(?!<[^]]\[)()[\t\n]+', ' ', regex).replace('  ', ' ')

def _prtRE(name, regexList):
	print(name)
	for regex in regexList:
		print(_minRE(regex))


## comments, JS style #########################################################

# _STRIP_JS_ADDED = r'''
# 	(?P<leader> 						# group 'leader'
# 		[''' + con.JS_ADDED_CHARS \
# 		+ ''']*		  					#   any char in con.JS_ADDED_CHARS
# 	)									# end group 'leader'
# 	(?P<token>							# group 'token'
# 		[^''' + con.JS_ADDED_CHARS \
# 		+ ''']+		  					#   any char not in con.JS_ADDED_CHARS
# 	)									# end group 'token'
# '''
# do NOT use _minRE as it will remove NL and TAB char from JS_ADDED_CHARS
# STRIP_JS_ADDED = r'(?P<leader> [\t\n {};()]* ) (?P<token> [^\t\n {};()]+ )'
STRIP_JS_ADDED = r'(?P<leader>  [' + con.JS_ADDED_CHARS \
				+ ']*) (?P<token> [^' + con.JS_ADDED_CHARS + ']+)'
STRIP_JS_ADDED_RE = re.compile(STRIP_JS_ADDED, flags=re.VERBOSE)
# '''
# (?P<leader>  []})[{(;\t\n ]*) (?P<token> [^]})[{(;\t\n ]+)
# '''

# ?not used
FIND_JS_ADDED = r'(?P<JSChars> [' + con.JS_ADDED_CHARS + ']*)'
FIND_JS_ADDED_RE = re.compile(FIND_JS_ADDED, flags=re.VERBOSE)


# _FIND_PARENTHESES = r'''
# 	# (?:								# non-capturing group
# 	# 	^ 								#   start of the string
# 	# 	|								#   OR
# 	# 	(?P<newLine>					#   group 'newLine'
# 	# 		[\r]? [\n]					#     new line character(s)
# 	# 	)								#   end group 'newLine'
# 	# )									# end non-capturing group
# 	[^]})[{(]*							# non-enclosing characters
# 	(?:									# non-capturing group
# 		(?P<opener>						#   group 'opener'
# 			[\\''' + con.JS_OPENERS + ''']#     opening characters (escaping 1st opener '[' to avoid nested set ambiguity)
# 		) 								#   end group 'opener'
# 		| 								#   OR
# 		(?P<closer>						#   group 'closer'
# 			[''' + con.JS_CLOSERS + ''']#     closing characters
# 		)								#   end group 'closer'
# 	)									# end non-capturing group
# '''
# 	# '''
# 	#  (?: ^ | (?P<newLine> [\\r]? [\\n] ) ) [^]})[{(]* (?: (?P<opener> [\\\\[{(] ) | (?P<closer> []})] ) )
# 	#  [^]})[{(]* (?: (?P<opener> [\\\\[{(] ) | (?P<closer> []})] ) )
# 	# '''
_FIND_PARENTHESES = r'''
	(?: 								# non-capturing group
		[^''' + con.JS_ENCLOSERS + ''']* 
	) 									# end non-capturing group
	(?P<paren> 							#   group 'paren'
		[''' + con.JS_ENCLOSERS + '''] 
	)									#   end group 'paren'
'''
FIND_PARENTHESES = _minRE(_FIND_PARENTHESES)
FIND_PARENTHESES_RE = re.compile(FIND_PARENTHESES, flags=re.VERBOSE)
# '''
# (?: [^]})[{(]* ) (?P<paren> []})[{(] )
# '''


_TOKENS_WS = r'''
	(?P<leader> 						# group 'leader'
		\s*								#   whitespace
	)									# end group 'leader'
	(?P<token> 							# group 'token'
		[^\t\n ]+						#   any char not whitespace
	)									# end group 'token'
	\s*									# discard whitespace
'''

TOKENS_WS_RE = re.compile(_TOKENS_WS, flags=re.VERBOSE)


_INLINE = r'''
	[/][*]								# open inline comment
	[^*]* [*]+							# non '*'s, ending with '*'s
	(?: [^/] [^*]* [*]+ )*				# non '/', non '*'s, ending with '*'s, maybe
	[*]?[/]								# close inline comment
'''
INLINE = _minRE(_INLINE)

_INLINE_SIMPLE = r'''
	\s* 								# capture leading whitespace
	''' + INLINE + ''' 					#   bounded style comment
	\s*									# capture trailing whitespace
'''
INLINE_SIMPLE = _minRE(_INLINE_SIMPLE)

# re.compile(
INLINE_CMT = r'''						# inline comment
	(?P<inlineCmt>						# group 'inlineCmt'
		\s* 							#   capture leading whitespace
	''' + INLINE + ''' 					#   bounded style comment
		\s*								#   capture trailing whitespace
	)									# end group 'inlineCmt'
'''
# , flags=re.VERBOSE)
#	(?: [\r]? [\n] | \Z )? 				#   capture NL (maybe), allow match of eof
# _prtRE('INLINE_CMT_RE', [INLINE_CMT])
# '''
# (?P<inlineCmt> (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )
# '''

_INLINE_WS = r'''
	(?P<leadInWS>						# group 'leadInWS'
		\s* 							#   capture leading whitespace
	)									# end group 'leadInWS'
	(?P<inlineBody>						# group 'inlineBody'
	''' + INLINE + ''' 					#   bounded style comment
	)									# end group 'inlineBody'
	(?P<trailInWS>						# group 'trailInWS'
		\s*								#   capture trailing whitespace
	)									# end group 'trailInWS'
'''
INLINE_WS = _minRE(_INLINE_WS)
# need multiple re's as Python's doesn't allow repeated group names
INLINE_SIMPLE_RE = re.compile(_minRE(INLINE_SIMPLE), flags=re.VERBOSE)
INLINE_CMT_RE = re.compile(_minRE(INLINE_CMT), flags=re.VERBOSE)
INLINE_WS_RE = re.compile(_minRE(INLINE_WS), flags=re.VERBOSE)


_ENDLINE = r''' 						# end-line comment
	[/][/]								# start eol comment
	[^\r\n]*							# any non-eol characters
'''
ENDLINE = _minRE(_ENDLINE)

_ENDLINE_SIMPLE  = r''' 				# end-line comment
	\s* 								# capture leading whitespace
		''' + ENDLINE + ''' 			#   eol style comment
	(?: \s* | (?<=[\w\W])$)				# capture trailing whitespace (no empty matches!)
'''
ENDLINE_SIMPLE = _minRE(_ENDLINE_SIMPLE)

# re.compile(
_ENDLINE_CMT = r''' 					# end-line comment
	(?P<eolCmt>							# group 'eolCmt'
		\s* 							#   capture leading whitespace
	''' + ENDLINE + ''' 				#   eol style comment
		\s* 							#   capture trailing whitespace
	)									# end group 'eolCmt'
'''
# , flags=re.VERBOSE)
#		(?:[\r]? [\n]|(?<=[\w\W])$		#   capture NL or end of string (no empty matches!)
ENDLINE_CMT = _minRE(_ENDLINE_CMT)
# _prtRE('ENDLINE_CMT_RE', [ENDLINE_CMT])
# '''
#  (?P<eolCmt> (?: \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) ) )
# '''

_ENDLINE_WS = r''' 						# end-line comment
	(?P<leadEolWS>						# group 'leadEolWS'
		\s* 							#   capture leading whitespace
	)									# end group 'leadEolWS'
	(?P<eolBody>						# group 'eolBody'
		''' + ENDLINE + ''' 			#   eol style comment
	)									# end group 'eolBody'
	(?P<trailEolWS>						# group 'trailEolWS'
		(?: \s* | (?<=[\w\W])$)			#   capture trailing whitespace (no empty matches!)
	)									# end group 'trailEolWS'
'''
ENDLINE_WS = _minRE(_ENDLINE_WS)
# need multiple re's as Python's doesn't allow repeated group names
ENDLINE_SIMPLE_RE = re.compile(ENDLINE_SIMPLE, flags=re.VERBOSE)
ENDLINE_CMT_RE = re.compile(ENDLINE_CMT, flags=re.VERBOSE)
ENDLINE_WS_RE = re.compile(ENDLINE_WS, flags=re.VERBOSE)

# lookahead for fn/iife validation
# - less strict as ONLY used for lookaheads
_POSSIBLE_COMMENTS = r'''
	(?:									# non-capturing group
	''' + ENDLINE + ''' 				#   eol style comment
		 	|							#     OR
	''' + INLINE + ''' 					#   bounded style comment
		 	|							#     OR
		\s*								#   whitespace (esp. after fnBody)
	)*									# end non-capturing group
'''
POSSIBLE_COMMENTS = _minRE(_POSSIBLE_COMMENTS)
# print('POSSIBLE_COMMENTS',POSSIBLE_COMMENTS)
# (?: \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* )*

_ANY_COMMENT_OR_WS = r'''
	(?:									# non-capturing group
		(?=\s*[/][/])					#   lookahead ensures whitespace stays with comment
		''' + ENDLINE + ''' 			#   eol style comment
		| 								#   or
		(?=\s*[/][*])					#   lookahead ensures whitespace stays with comment
		''' + INLINE + '''		  		#   bounded style comment
		| 								#   or
		(?![/][/]) (?![/][*]) 			#   if there is no comment
		\s 			  			 		#   capture whitespace
	)+									# end non-capturing group
'''
# capture groups not named as re doesn't allow repeated named matches (regex does!)
# - each use has it's own named capture group
ANY_COMMENT_OR_WS = _minRE(_ANY_COMMENT_OR_WS)
# _prtRE('ANY_COMMENT_OR_WS', [ANY_COMMENT_OR_WS])
# '''
# (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?: \s* |
# (?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* |
# (?![/][/]) (?![/][*]) \s )+
# '''

ANY_COMMENT_OR_WS_RE = re.compile(ANY_COMMENT_OR_WS, flags=re.MULTILINE | re.VERBOSE)


# name validation

# """ Atomic Groups for Engines that Don't Support It
#   r'(?=(A+))\1'
# The lookahead asserts that the expression we want to make atomic—i.e. A+—can be found at the current position, and
# the parentheses capture it. The back-reference \1 then matches it. So far, this is just a long-winded way of matching A+.
# The magic happens if a token fails to match further down in the pattern. The engine will not backtrack into a lookaround,
# and for good reason: if its assertion is true at a given position, it's true! Therefore, Group 1 keeps the same value,
# and the engine has to give up what was matched by A+ in one block.
# """
# namedAtomic=re.compile(r'(?=(?P<atomic>A+))(?P=atomic)')
# - tried on comments; in iife, added about 8% to one w/ 6 comments outside of fnBody
# ?does it provide benefit, eg. forestall catastrophic backtracking

# tmp=re.compile(r'''
# (?=(?P<postArgs> (?: \s* [/][/] [^\r\n]* [\r]? [\n]|$ ) | (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) | (?: \s* ) ) )(?P=postArgs)
# ''', flags=re.VERBOSE)


## config file ################################################################

# [section]
# - convention: comments immediately following are associated w/ secion heading
#   - any preceding belong to last option

_SECTION_HEAD = r'''					# section header, single word
	(?P<section>						# group 'section'
			^\s*\[\s* 					#     opening bracket, trim any whitespace
		(?P<name>						#   group 'name'
			Settings
			|Font|Colors
			|History|Aliases
		)								#   end group 'name'
		\]								#   closing bracket
		# \s*]							#   closing bracket, whitespace (maybe, not trailing)
	)									# end group 'section'
'''
SECTION_HEAD = _minRE(_SECTION_HEAD)
SECTION_TAIL = r'''
	(?P<sectionTail>					# group 'sectionTail'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'sectionTail'
'''
SECTION = [SECTION_HEAD, SECTION_TAIL]
# _prtRE('SECTION_RE', SECTION)
# '''
# (?P<section> ^\s*\[\s* (?P<name> Settings
#   |Font|Colors
#   |History|Aliases
#  ) \s*] )
#  (?P<sectionTail> (?: (?=\s*[/][/]) (?: \s* [/][/] [^\r\n]* [\r]? [\n]|$ ) | (?=\s*[/][*]) (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )* (?: \s*(?!\s*[/]]) )? )
# '''

SECTION_RE = re.compile(''.join(SECTION), flags=re.MULTILINE | re.VERBOSE)


_OPTION_HEAD = r'''  					# option declaration
	^(?P<option>						# group 'option'
		(?P<name>						#   group 'name'
			[a-zA-Z$_] [\w$_-]*			#     name cannot start with a digit (JS property)
		)								#   end group 'name'
		\s*=\s*							#   '=' and surrounding whitespace
		(?P<value>						#   group 'value'
			(?: 						#     non-capture group
				\[	 					#       open bracket (begins a list)
				(?: (?=.*\])			#       while there's still a close bracket ahead 
										#         (on this line, ie. the . vs a contrasting set)
					[\w\W] )*			#       grab any character
			)							#     end non-capture group
			|							#     OR
			(?:  						#     non-capture group
				[\w\W] 					#       any characters
				(?![ \t]*(?:[/][/*]|$))	#       until we see a comment or end of string
			)*							#     end non-capture group
			[\w\W]						#     grab the last character
 		)								#   end group 'value'
	)									# end group 'option'
'''
OPTION_HEAD = _minRE(_OPTION_HEAD)
# OPTION_HEAD2 = re.compile(r'''
# ''', flags=re.MULTILINE | re.VERBOSE)
OPTION_TAIL = r'''
	(?P<optionTail>						# group 'optionTail'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'optionTail'
'''
OPTION = [OPTION_HEAD, OPTION_TAIL]
# _prtRE('OPTION_RE', OPTION)
# '''
#   ^(?P<option> (?P<name> [a-zA-Z$_] [\w$_-]* ) \s*=\s* (?P<value> (?: \[ (?: (?=.*\]) [\w\W] )* )
#   			| (?: [\w\W] (?![ \t]*(?:[/][/*]|$)) )* [\w\W] ) )
#  (?P<optionTail> (?: (?=\s*[/][/]) (?: \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) )
#  | (?=\s*[/][*]) (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )+ | (?: (?![/]) \s )+ )?
# '''

OPTION_RE = re.compile(''.join(OPTION), flags=re.MULTILINE | re.VERBOSE)


## aliases ####################################################################

_ALIAS_FIRST_CHAR = 'a-zA-Z_$'
_ALAIS_REST_CHARS = '\w_$'

_A_NAME = r'''
	[''' + _ALIAS_FIRST_CHAR + ''']		# first character is a letter, underscore or dollar sign
	[''' + _ALAIS_REST_CHARS + ''']*	# subsequent characters may also be numerals
'''

# SilentMsg parsing (see mkCmdIIFE, processMessages)
_MSGLABEL = r''' 						# parse label and echo directive
	(?P<msglabel>						# group 'msglabel'
		<label:							#   '<label:' tag for assignment of result
		(?P<label> 						#   group 'label'
			[''' + _ALAIS_REST_CHARS \
				+ ''' -]+ 				#     1 or more valid label characters
			(?=[^>]*[>])				#     up to closing '>'
		)								#   end group 'label'
		>								#   closing '>'
		<discard:						#   '<discard:' tag to direct console printing
			(?P<discard>				#     group 'discard'
				yes | no				#       'yes' or 'no'
			)							#     end group 'discard'
		>								#   closing '>'
	)									# end group 'msglabel'
'''
MSGLABEL = _minRE(_MSGLABEL)
# '''
# (?P<msglabel> <label: (?P<label> [\w -]+ (?=[^>]*[>]) ) > <discard: (?P<discard> yes | no ) > )
# '''

MSGLABEL_RE = re.compile(MSGLABEL, flags=re.VERBOSE)


_VALID_ALIAS_NAME = r'''
	(?P<nolen>							# group 'nolen'
		^$								#   no characters
	) | 								# end group 'nolen'
	(?:									# non-capturing group
		(?P<first>						#   group 'first'
			[''' + _ALIAS_FIRST_CHAR \
				+ ''']					#     first character is a letter, underscore or dollar sign
		) |								#   end group 'first'
		(?P<bad1st>						#   group 'bad1st'
			[^''' + _ALIAS_FIRST_CHAR \
				+ ''']					#     first character is invalid
		) 								#   end group 'bad1st'
	)									#   end non-capturing
	(?:									#   non-capturing group
		(?P<good>						#     group 'good'
			[''' + _ALAIS_REST_CHARS \
				+ ''']					#       subsequent characters may also be numerals
		) |								#     end group 'good'
		(?P<bad>						#     group 'bad'
			[^''' + _ALAIS_REST_CHARS \
				+ ''']					#       invalid characters
		)								#     end group 'bad'
	)*									#   end non-capturing
'''
VALID_ALIAS_NAME = _minRE(_VALID_ALIAS_NAME)
#'''
# (?P<nolen> ^$ ) | (?: (?P<first> [a-zA-Z_$] ) | (?P<bad1st> [^a-zA-Z_$] ) ) (?: (?P<good> [\w_$] ) | (?P<bad> [^\w_$] ) )*
#'''

VALID_ALIAS_NAME_RE = re.compile(VALID_ALIAS_NAME, flags=re.VERBOSE)


# default polling
_DEFAULT_POLLING = r'''
	^\s*  								# leading comments, etc. already stored
	(?P<no>								# group 'no'
		(?: worldScripts | system ) 	#   only those starting with these
				[.] [^.]*$				#   and at most one dot
		| \s* [(]? \s* function			#   OR fn/iife
				\s* \w* [(].+$ 			#
	) |									# end group 'no'
	(?P<yes>							# group 'yes'
		.+$								#   leave everything else for user to disable
	)									# end group 'yes'
'''
DEFAULT_POLLING = _minRE(_DEFAULT_POLLING)
#'''
# ^\s* (?P<no> (?: worldScripts | system ) [.] [^.]*$ | \s* [(]? \s* function \s* \w* [(].+$ ) | (?P<yes> .+$ )
#'''

DEFAULT_POLLING_RE = re.compile(DEFAULT_POLLING, flags=re.DOTALL | re.VERBOSE)


_ALIAS_NAME = r'''
	\s*(?P<name>						# group 'name'
		''' + _A_NAME + '''				#   alais name
	)									# end group 'name'
	\s*:=								# ':=' with leading whitespace (trailing in pollLead)
'''
ALIAS_NAME = _minRE(_ALIAS_NAME)
# _prtRE('ALIAS_NAME_RE', [ALIAS_NAME])
# '''
# \s*(?P<name> [a-zA-Z_$] [\w_$]* ) \s*:=\s*
#  '''

ALIAS_NAME_RE = re.compile(ALIAS_NAME, flags=re.VERBOSE)


_POLLFLAG = r'''
	(?P<pollFlag>						# group 'pollFlag'
		(?P<pollLead>					#   group 'pollLead'
			\s*							#     leading space
		) 								#   end group 'pollLead'
		(?P<polled> 					#   group 'polled'
			[pPnN]?						#     'p' or 'n', case insensitive
		)	 \s*						#   end group 'polled' (toss any whitespace)
		(?P<inMenu>						#   group 'inMenu'
			[mM]?						#     'm', case insensitive
		)	 \s*						#   end group 'inMenu' (toss any whitespace)
		[:]								#   ':'
	)?									# end group 'pollFlag' (entire poll flag may be absent)
'''
POLLFLAG = _minRE(_POLLFLAG)
#'''
# (?P<pollFlag> (?P<pollLead> \s* ) (?P<polled> [pPnN]? ) \s* (?P<inMenu> [mM]? ) \s*[:] )?
#'''

_ALIAS_DEFN = r'''
	(?P<aliasDefn>						# group 'aliasDefn'
		(?:								#   non-capturing group
			(?! (?:[ \t]*[/][/*] \s*)?	#     while not facing a possibly commented
			''' + _A_NAME + '''			#       alais name
				\s*:=\s*)				#       assignment
			[\w\W]						#     grab any character
		)*								#   end non-capturing group
		\s*								#   capture trailing whitespace so 'aliasTail' re won't
	)									# end group 'aliasDefn'
'''
ALIAS_DEFN = _minRE(_ALIAS_DEFN)
#'''
# (?P<aliasDefn> (?:  (?! (?:[ \t]*[/][/*] \s*)? [a-zA-Z_$] [\w_$]* \s*:=\s*) [\w\W] )* \s* )
#'''
ALIAS_TAIL = r'''
	(?P<aliasTail>						# group 'aliasTail'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'aliasTail'
'''

# parse polling after alias & ':=' removed
POLLING = [POLLFLAG, ALIAS_DEFN, ALIAS_TAIL]
# _prtRE('POLLING',POLLING)
#'''
# (?P<pollFlag> (?P<pollLead> \s* ) (?P<polled> [pPnN]? ) \s* (?P<inMenu> [mM]? ) \s*[:] )?
# (?P<aliasDefn> (?: (?! [a-zA-Z_$] [\w_$]* \s*:=\s*) (?![ \t]*[/][/*] \s* [a-zA-Z_$] [\w_$]* \s*:=\s*) [\w\W] )* \s* )
# (?P<aliasTail> (?: (?=\s*[/][/]) (?: \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) ) | (?=\s*[/][*]) (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )+ | (?: (?![/]) \s )+   )?
#'''

POLLING_RE = re.compile(''.join(POLLING), flags=re.VERBOSE)


PRE_DEFN = r'''
	(?P<preDefn>						# group 'preDefn'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'preDefn'
'''
_NO_COMMENT = r'''
	(?P<simpleAlias>					# group 'simpleAlias'
		(?:								#   non-capture group
			(?!\s* [/][/*])				#     while not facing the start of a comment
			(?!\s*$)					#     while not facing trailing whitespace
			[\w\W]						#     capture all character (Tempered Greedy Token)
		)*								#   end non-capture group
	)									# end group 'simpleAlias'
'''
NO_COMMENT = _minRE(_NO_COMMENT)
#'''
# (?P<simpleAlias> (?: (?!\s* [/][/*]) (?!\s*$) [\w\W] )* )
#'''
POST_DEFN = r'''
	(?P<postDefn>						# group 'postDefn'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'postDefn'
'''
# for simple aliases (not func or iife), this is applied on contents of aliasDefn
# after POLLING_RE, after poll flags parsed and removed
ALIAS = [PRE_DEFN, NO_COMMENT, POST_DEFN]
ALIAS_CMTS = ['preDefn', 'postDefn']
# _prtRE('ALIAS_RE', ALIAS)
# '''
# (?P<preDefn> (?: (?=\s*[/][/]) (?: \s* [/][/] [^\r\n]* [\r]? [\n]|$ ) | (?=\s*[/][*]) (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )* (?: \s*(?!\s*[/]]) )? )
#  (?: (?!\s* [/][/*]) [\w\W] )*
#  (?P<postDefn> (?: (?=\s*[/][/]) (?: \s* [/][/] [^\r\n]* [\r]? [\n]|$ ) | (?=\s*[/][*]) (?: \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? ) )* (?: \s*(?!\s*[/]]) )? )
# '''

ALIAS_RE = re.compile(''.join(ALIAS), flags=re.VERBOSE)


_IS_VALID_FN = r'''						# check first to avoid catastrophic backtracking (stupid Python re)
    (?= 								# look ahead for validity
		\A								#   start of string
	''' + POSSIBLE_COMMENTS + ''' 
        function 						#   'function' 
		(?: [^{}()]* [(] ){1}			#   its '('
		(?: [^{}()]* [)] ){1} 			#   its ')' (no parentheses in args unless requested!)
		(?: [^{}()]* [{] ){1}			#   fn body's '{', the first one
		(?: [^}]*[}] )+					#   up to the last '}'
		(?: [^\s/]*	)					#   possible junk before comment (like ; after fnBody!)
	''' + POSSIBLE_COMMENTS + ''' 
		\Z								#   end of string
	)									# end look ahead
'''
IS_VALID_FN = _minRE(_IS_VALID_FN)
# print('IS_VALID_FN',IS_VALID_FN)
# '''
# (?= \A (?: \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* )*
# function (?: [^{}()]* [(] ){1} (?: [^{}()]* [)] ){1} (?: [^{}()]* [{] ){1} (?: [^}]*[}] )+
# (?: \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* )*  \Z )
# '''


_FN_LEAD = r'''
	(?P<fnLead>							# group 'fnLead'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'fnLead'
'''
FN_LEAD = _minRE(_FN_LEAD)
_FN_CALL = r'''
	(?P<fnCall> 						# group 'fnCall'
		function \s*					#   'function' with whitespace, maybe
		(?P<fnName>						#   group 'fnName'
			(?: [a-zA-Z_$] [\w_$]*)?	#     function name, optional (1st char not a number)
		) 								#   end group 'fnName'
		\s* [(] 						#   whitespace maybe, open parenthesis '('
		(?P<fnArgs> 					#   group 'fnArgs'
			[^)]* 						#     all characters up to ')'
		)								#   end group 'fnArgs'
		[)]								#   closing parenthesis ')'
	)									# end group 'fnCall'
'''
FN_CALL = _minRE(_FN_CALL)
_FN_HEAD = r'''
	(?P<fnHead>							# group 'fnHead'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'fnHead'
'''
FN_HEAD = _minRE(_FN_HEAD)


# Tempered Greedy Token: {START}(?:(?!{END}).)*{END}
#   (match {START}...{END}  skipping any { inbetween)
# for next closing brace: (?:(?![}])[\w\W])*[}]
# + stopping on last }:   (?:(?![}][^}]*\Z)[\w\W])*[}]
# vs
# Explicit Greedy Alternation: {START}(?:[^{]|{(?!END}))*{END}
#   (match {START}...{END}  skipping any { inbetween)
# for last closing brace:  (?:[^}]|[}](?![^}]*\Z))*[}]
#  - 40% faster

_FN_BODY = r'''
	(?P<fnBody>							# fnBody group (entire function statement)
		(?:								#   non-capture group
			(?=[^}]*[}])				#     while there's still a close brace
			[^}]*[}]					#     capture all upto and including
		)+								#   end non-capture group
	)									# end group 'fnBody' 
	(?: [^\s/]*	)						# possible junk before comment (like ; after fnBody!)
'''
FN_BODY = _minRE(_FN_BODY)

_FN_TAIL = r'''
	(?P<fnTail>							# group 'fnLead'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'fnLead'
'''
FN_TAIL = _minRE(_FN_TAIL)

FUNCTION = [IS_VALID_FN, FN_LEAD, FN_CALL, FN_HEAD, FN_BODY, FN_TAIL]
FUNCTION_CMTS = ['fnLead', 'fnHead', 'fnTail']
# _prtRE('FUNCTION_RE', FUNCTION)
# '''
# (?= \A (?: \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* )*   function (?: [^{}()]* [(] ){1} (?: [^{}()]* [)] ){1} (?: [^{}()]* [{] ){1} (?: [^}]*[}] )+ (?: \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* )* \Z )
#  (?P<fnLead> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* | (?![/][/]) (?![/][*]) \s )+   )?
#  (?P<fnCall> function \s* (?P<fnName> (?: [a-zA-Z_$] [\w_$]*)? ) \s* [(] (?P<fnArgs> [^)]* ) [)] )
#  (?P<fnHead> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* | (?![/][/]) (?![/][*]) \s )+   )?
#  (?P<fnBody> (?: (?=[^}]*[}]) [^}]*[}] )+ )
#  (?P<fnTail> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?: \s* | (?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] \s* | (?![/][/]) (?![/][*]) \s )+   )?
# '''

# function parser
# - used when CFGFILE is read, user adds an alias and prior to registration

FUNCTION_RE = re.compile(''.join(FUNCTION), flags=re.VERBOSE)


# look ahead to prevent catastrophic backtracking, eg. if missing parenthesis on
# expresion/invocation, 1st/last brace, etc.
# - match is followed by pair matching to avoid those syntax errors
# tmp = re.compile(r'''
_IS_VALID_IIFE = r'''					# check first to avoid catastrophic backtracking (stupid Python re)
    (?= 								# look ahead for validity
		\A								#   start of string
	''' + POSSIBLE_COMMENTS + ''' 
        [(] \s* function 				#   '(' followed by 'function' 
		[^{}()]* [(]					#   its parameter '('
		(?: [^{})]* [)] )+	 			#   its   "  ')'
		[^{}()]* [{]					#   fn body's '{', the first one
		(?: [^}]*[}] )+					#   up to the last '}'
		[^{}()]* [)]					#   ')' to close expression
		[^{}()]* [(]					#   '(' and 
		(?: [^{})]* [)] )+	 			#   ')' to invoke expression
	''' + POSSIBLE_COMMENTS + ''' 
		\Z								#   end of string
	)									# end look ahead
'''
# ''', flags=re.VERBOSE)
IS_VALID_IIFE = _minRE(_IS_VALID_IIFE)

_OPEN_IIFE = r'''
	[(] \s*								# open parenthesis and whitespace
'''
OPEN_IIFE = _minRE(_OPEN_IIFE)

_PRE_ARGS = r'''
	[)]									# closing parenthesis
	(?P<preArgs>						# group 'preArgs'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'preArgs'
'''
PRE_ARGS = _minRE(_PRE_ARGS)

_IIFE_ARGS = r'''
	[(]									# open parenthesis
	(?P<iifeArgs>						# group 'iifeArgs'
		[\w\W]*(?=[)])					#   all characters up to closing parenthesis
	) 									# end group 'iifeArgs'
	[)]									# closing parenthesis
'''
IIFE_ARGS = _minRE(_IIFE_ARGS)

_POST_ARGS = r'''
	(?P<postArgs>						# group 'postArgs'
	''' + ANY_COMMENT_OR_WS + '''
   	)?									# end group 'postArgs'
'''
POST_ARGS = _minRE(_POST_ARGS)

IIFE = [IS_VALID_IIFE, FN_LEAD, OPEN_IIFE, FN_CALL, FN_HEAD, FN_BODY, FN_TAIL,
		PRE_ARGS, IIFE_ARGS, POST_ARGS]
IIFE_CMTS = ['fnLead', 'fnHead', 'fnTail', 'preArgs', 'iifeArgs', 'postArgs']
# _prtRE('IIFE_RE', IIFE)
# '''
#  (?= \A [^{}()]* [(] \s* function [^{}()]* [(] (?: [^{})]* [)] )+ [^{}()]* [{] (?: [^}]*[}] )+ [^{}()]* [)] [^{}()]* [(] (?: [^{})]* [)] )+ [^{}()]* \Z )
#  (?P<fnLead> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? | (?![/]) \s* )+   )?
#  [(] \s*
#  (?P<fnCall> function \s* (?P<fnName> (?: [a-zA-Z_$] [\w_$]*)? ) \s* [(] (?P<fnArgs> [^)]* ) [)] )
#  (?P<fnHead> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? | (?![/]) \s* )+   )?
#  (?P<fnBody> (?: (?=[^}]*[}]) [^}]*[}] )+ )
#  (?P<fnTail> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? | (?![/]) \s* )+   )?
#  [)] (?P<preArgs> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? | (?![/]) \s* )+   )?
#  [(] (?P<iifeArgs> [\w\W]*(?=[)]) ) [)]
#  (?P<postArgs> (?: (?=\s*[/][/]) \s* [/][/] [^\r\n]* (?:[\r]? [\n]|(?<=[\w\W])$) | (?=\s*[/][*]) \s* [/][*] [^*]* [*]+ (?: [^/] [^*]* [*]+ )* [*]?[/] (?: [\r]? [\n]|\Z )? | (?![/]) \s* )+   )?
# '''

# iife parser
# - used when CFGFILE is read, user adds an alias and prior to registration

IIFE_RE = re.compile(''.join(IIFE), flags=re.VERBOSE)


# quote conversion for aliases
# - any unescaped single quotes are converted to double quotes to match
#   the output style of javascript's .toString()
UNESCAPED_QUOTES_RE = re.compile(r"(?<![\\])[']")


## for minifying functions & IIFEs ############################################

# quoted string segments, including line spanning (JS line ends with '\')
# - used to find quoted strings, disregard comments inside quotes
# - not captured, as only indices are used
_QUOTED = r'''							# quoted strings, multi-line
	(?P<quoted>							# group 'quoted'
		(?<![\\]) 				 		#   no preceding backslash
		(?P<open>						#   group 'open'
			["'] 						#     an unescaped quote
		)								#   end group 'open'
		(?: 							#   non-capturing group
			[\\]? [^\\\r\n] |			#     quoted string
			[\\]  [\r]?[\n]				#     that may wrap if ending in backslash
		)*?								#   end group (may be empty)
		(?<![\\]) 				 		#   no preceding backslash
		(?P=open)  						#   a matching unescaped 'open' quote
	)									# end group 'quoted'
'''
QUOTED = _minRE(_QUOTED)
#'''
# (?P<quoted> (?<![\\]) (?P<open> ["'] ) (?: [\\]? [^\\\r\n] | [\\] [\r]?[\n] )*? (?<![\\]) (?P=open) )
#'''

QUOTED_RE = re.compile(QUOTED, flags=re.VERBOSE)

# whitespace > 1 character width (including tabs)
# - used with .sub to reduce multiple spaces outside quotes
#   (Entry widgets react badly with these)
MULTI_WS = r'''							# tab and/or 2 or more unquoted spaces
	(?P<ws>								# group 'ws'
		(?:								#   non-capture prefix group
			[\r\n\t\v\f] \s*			#     lone escaped (maybe more)
			|							#     or
			\s{2,}						#     2 or more of escaped/space
		)+								#   end non-capture group
	)									# end group 'ws'
'''
MULTI_WS_RE = re.compile(MULTI_WS, flags=re.VERBOSE)


# whitespace characters (including tabs) between NLs
# - are superfluous and make formatting more complicated, so are removed
# - just a per line .rstrip() on a string w/ multiple lines
ENDLINE_STRIP_WS = r'''					# tab and/or spaces before newline
	(?P<ws>								# group 'ws'
		(?:								#   non-capture prefix group
			[\r\t\v\f ]+				#     whitespace not NL
			[\n]						#     new line (NL)
		)+								#   end non-capture group
	)									# end group 'ws'
'''
ENDLINE_STRIP_WS_RE = re.compile(ENDLINE_STRIP_WS, flags=re.VERBOSE)


## file finder ################################################################

# 'Word' treatment: match possibly quoted Search text that qualifies as
# a word, namely, preceded by whitespace or quote, succeeded by whitespace,
# matching quote, punctuation or start of a comment
# quoted string segments, including line spanning (JS line ends with '\')
_FIND_QUOTED = r'''
	(?:									# non-capture prefix group
		^ | \s+	| 						#   start of string or whitespace or
		(?P<quote>						#   group 'quote'
			(?<![\\]) ["'] 				#     an unescaped quote
		) 								#   end group 'quote'
	)									# end non-capture group
	(?P<target> 						# capturing group 'target'
		{}								#   search string inserted by .format
	)									# end group
	(?:									# non-capture suffix group
		(?(quote)						#   conditional group
			(?<![\\]) (?P=quote)		#     yes-pattern
			|							#       or
			(?: $ | [,;:\s.!?] | 		#     no-pattern
				[/][/] | [/][*] 		#       including comment starts
			)							#     end no-pattern
		)								#   end conditional group
	)									# end non-capture group
'''
FIND_QUOTED = _minRE(_FIND_QUOTED)
#'''
#  (?:^|\s+|(?P<quote>(?<![\\])["']))(?P<target>{})(?:(?(quote)(?<![\\])(?P=quote)|(?:$|[,;:\s.!?]|[/][/]|[/][*])))
#'''
# - is compiled after .format inserts Search text in ff._FindParameters.mkSeekers


## from Oolite ################################################################

# JS errors

# Exception: TypeError: c is undefined\n    oolite-debug-console.js, line 1749:\n    <line out of range!>
# Exception: uncaught exception: evalExpression, cannot decode expression "false)"\n    Active script: station_options 1.0
_OOLITE_ERROR = r'''
	\s* [^:]+ : \s+  					# string 'Exception: '
	(?P<type>   						# group 'type'
		[^:]+   						#   all characters but colon
	)  									# end group 'type'
	: \s*  								# colon (delimiter)
	(?P<error>  						# group 'error'
		.*   							#   all characters
	)   								# end group 'error'
	$  									# end of line
	(?:\s* [^:]+ : .*$)?				# entire line 'Active script: ...' (maybe!)
	(?:									# traceback (maybe!) -not present for user defined 'throw str'
		\s* [^.]* \.js, \s+ line \s+ 	#   string 'oolite-debug-console.js, line '
		(?P<line>  						#   group 'line'
			\d+   						#     run of digits
		)  								#   end group 'line'
		: \s* $  						#   ':' to end of line
		(?P<context>  					#   group 'context'
			[\s\S]*   					#     rest of the message
		)  								#   end group 'context'
	)?									# end traceback
	\Z  								# end of string
'''
OOLITE_ERROR = _minRE(_OOLITE_ERROR)
#'''
# \s* [^:]+ : \s+ (?P<type> [^:]+ ) : \s* (?P<error> .* ) $ (?:\s* [^:]+ : .*$)? (?: \s* [^.]* \.js, \s+ line \s+ (?P<line> \d+ ) : \s* $ (?P<context> [\s\S]* ) )? \Z
#'''

OOLITE_ERROR_RE = re.compile(OOLITE_ERROR, flags=re.MULTILINE | re.VERBOSE)


# plist colors

_OOLITE_COLOR = r'''
	(?=[cegwmu])  						# look ahead for valid 1st character (for speed)
	(?P<key> 							# group 'key'
		(?=\w+-\w+-color) 				#   if 2 '-' present (debug console color)
			(?P<isa_dcColor>			#   group 'isa_dcColor'
				command | error |		#     capture keyword
				exception | general | 
				warning
			)							#   end group 'isa_dcColor'
		| 								#   OR
		(?=\w+-\w+-\w+-color) 			#   if 2 '-' present (an Oolite message color)
			(?P<isa_ooColor>			#   group 'isa_ooColor'
				(?:						#     capture hyphenated keyword
					command | macro |	
					unknown
				)-						#     capture hyphen
				(?:						#     capture hyphenated keyword
					error | exception |
					expansion | info |
					macro| result |
					warning
				)
			)							#   end group 'isa_ooColor'
	)									# end group 'key'
	-(?P<plane>							# group 'plane'
		foreground | background			#   capture keyword
	)									# end group 'plane'
	-color								# match rest of color's name
'''
OOLITE_COLOR = _minRE(_OOLITE_COLOR)
#'''
# (?=[cegwmu]) (?P<key> (?=\w+-\w+-color) (?P<isa_dcColor> command | error | exception | general | warning ) | (?=\w+-\w+-\w+-color) (?P<isa_ooColor> (?: command | macro | unknown )- (?: error | exception | expansion | info | macro| result | warning ) ) ) -(?P<plane> foreground | background ) -color
#'''

OOLITE_COLOR_RE = re.compile(OOLITE_COLOR, flags=re.VERBOSE)


## output filtering ###########################################################

# MEM_STATS_START_RE = re.compile('^Entities:\s*$')
# MEM_STATS_END_RE = re.compile('^Total:\s+\d+\.\d+.*?B\s*$')
# - not needed, as setting filterMemStatsVar turns off filter
# - may be necessary if we start filtering more
