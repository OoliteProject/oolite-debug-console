# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import re
from operator import itemgetter
from collections import namedtuple

import pdb, traceback

import debugGUI.constants as con
import debugGUI.regularExpn as rx

def is_str(value):
	"""Python version agnostic string type checker
	"""
	
	return isinstance(value, (str, unicode) if con.Python2 else str)

def shortText(text):
	if len(text) > 80:
		short = f'{text[:38]} ... {text[-38:]}'
		return repr(short.replace(con.NL, '|'))
	else:
		return repr(text.replace(con.NL, '|'))

def _validateStrParsm(string, start, stop):
	length = len(string)
	if stop is None or not (-1 < stop < length):
		stop = length
	if not( -1 < start <= stop):
		# == stop is edge case for looping, ie. last iteration
		start = 0
	return start, stop

def subInString(sub, string, start=0, stop=None):
	# '' is always found at index 0
	start, stop = _validateStrParsm(string, start, stop)
	return -1 if len(sub) == 0 else string.find(sub, start, stop)

def isSpaceOrEmpty(string, start=0, stop=None):
	# '' is included w/ .isspace()
	start, stop = _validateStrParsm(string, start, stop)
	return start >= stop or string[start:stop].isspace()

def inbounds(index, string, incr=0):
	"""check if 'index' + 'incr' is a valid 'string' offset
	"""
	
	return -1 < (index + incr) < len(string)

def removeWS(string):
	"""return 'string' with all of its whitespace characters [\r\n \t\v\f] removed
	"""
	
	return re.sub(r'\s', '', string)

def leadingWS(string, start=0, stop=None, WS=' '):
	"""number of contiguous characters in 'WS' forward in 'string' 
	   from 'start' to 'stop'
	"""

	start, stop = _validateStrParsm(string, start, stop)
	count = 0
	while -1 < start + count < stop and string[start + count] in WS:
		count += 1
	return count

def trailingWS(string, start=0, stop=None, WS=' '):
	"""number of contiguous characters in 'WS' backward in 'string'
	   from 'start' to 'stop'
	"""

	start, stop = _validateStrParsm(string, start, stop)
	stop -= 1 					# exclude last char like rfind
	count = 0
	while start <= stop - count and string[stop - count] in WS:
		count += 1
	return count

def startsLine(string, start=0, stop=None):
	"""index of first NL in 'string' between 'start' and 'stop', 
	   -1 if not present
	"""

	start, stop = _validateStrParsm(string, start, stop)
	newline = string.find(con.NL, start, stop)
	if -1 < newline:
		if newline == start:
			return newline
		if string[start:newline].isspace():
			return newline
	return -1

def endsLine(string, start=0, stop=None):
	"""index of last NL in 'string' between 'start' and 'stop', 
	   -1 if not present
	"""

	start, stop = _validateStrParsm(string, start, stop)
	# rfind searches [start:end], ie. [end] not included
	newline = string.rfind(con.NL, start, stop)
	if -1 < newline:
		if newline == stop - 1:
			return newline
		if string[newline:stop].isspace():
			return newline
	return -1

def countNLs(string, start=0, stop=None, step=1):
	"""number of NLs (possibly separated by 'WHITESPACE') in 'string'
	   between 'start' and 'stop', in direction 'step'
	"""

	start, stop = _validateStrParsm(string, start, stop)
	if start > stop:
		start, stop = (stop, start)
	count = 0
	# like rfind, last in sequence is not considered
	index = start if step > 0 else stop - 1
	while -1 < start <= index < stop and string[index] in con.WHITESPACE:
		if string[index] == con.NL:
			count += 1
		index += step
	return count

def linesIndent(string, start, WS=' '):
	"""number of spaces at beginning of line that has string[start]
	   - caller must ensure character at start is not a NL (ambiguous)
	"""

	try:
			strLen = len(string)
			if start >= strLen:
				start = strLen - 1
			# 'first' is start of line or of string if no NL (rfind would return -1)
			first = string.rfind(con.NL, 0, start) + 1
			# stop is end of current line or end of string
			stop = string.find(con.NL, first)
			if stop < 0:
				stop = strLen
			count = 0
			while first + count < stop:
				if string[first + count] not in WS:
					break
				count += 1
			return count
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def reduceToJS_ADDED(string):
	"""return list of characters 'string' with all characters not in
	   JS_ADDED_CHARS removed
	"""
	return [ch for ch in string if ch in con.JS_ADDED_CHARS]

def createTokenSpans(string, offset=0, strip_JS=False, exclude=None):
	regex = rx.STRIP_JS_ADDED_RE if strip_JS else rx.TOKENS_WS_RE
	if exclude:
		string = textFromCmtSpans(string, exclude)
	return  [(offset + st.start('token'), offset + st.end('token'))
			 for st in regex.finditer(string)]

##======================================================================
## comment spans
##======================================================================
#
# def generateCommentSpans(string):
# 	"""create a list of comment spans (start, end, hasNL) for string"""
#	# this spanning scheme can have adjacent comments both capture whitespace
#	# - handled in _rebuildComments for fnBody and .makeCmtsBySpan for tagged ones
### ?fixed below, yet to fix makeCmtsBySpan, irrelevant (?) in _rebuildComments
# 	try:
# 		spans = [(match.start(), match.end(), con.NL in match['inlineCmt'], 'inline')
# 					for match in rx.INLINE_CMT_RE.finditer(string)]
# 		spans.extend((match.start(), match.end(), True, 'eol')
# 						for match in rx.ENDLINE_CMT_RE.finditer(string))
# 		# when 2 comments are adjacent but separated by a NL, the first's trailing
# 		# NL will also be captured by the second (trapping for this in the regex
# 		# is not worth it) so remove the second's leading NL
# 		spans = [(start + 1, end, hasNL, kind)
# 				 if any(first < start < last for first, last, _, _ in spans)
# 				 else (start, end, hasNL, kind)
# 				 for start, end, hasNL, kind in spans]
# 		# filter for commented comments
# 		spans = [(start, end, hasNL, kind)
# 					for start, end, hasNL, kind in spans
# 					   if not any(outerStart < start < outerEnd
# 								  for outerStart, outerEnd, _, _ in spans)]
# 		# filter for quoted comments
# 		quoted = [match.span() for match in rx.QUOTED_RE.finditer(string)]
# 		if len(quoted) > 0:
# 			spans = [(start, end, hasNL, kind)
# 						for start, end, hasNL, kind in spans
# 						   if not any(quoteStart < start < end < quoteEnd
# 									  for quoteStart, quoteEnd in quoted)]
# 		return sorted(spans)
# 	except Exception as exc:
# 		print(exc)
# 		traceback.print_exc()
# 		pdb.set_trace()

###

commentSpan = namedtuple('commentSpan',
						 'start, end, hasNL, kind, allTokens, codeTokens')
def generateCommentSpans(string):
	"""create a list of comment spans
	      (start, end, hasNL, kind, allTokens, codeTokens)
	   for string"""
	try:

		def priorTokens(idx, exclInCmt=False): # exclude comment tokens
			cmtStart = yield # 1st yield is reply to .send(None), the initialization
			# for leading comment:
			# - comments capture leading whitespace, so its 'start' will precede
			#   that of the first token if there's whitespace before first comment
			if cmtStart < allSpans[0][1]: # end of first token
				cmtStart = yield 0
			# cmtSpans = [(begin, end) for begin, end, _, _ in comments] \
			cmtSpans = [(leadStart, tailEnd)
						for leadStart, _, _, tailEnd, _, _ in comments] \
						if exclInCmt else []
			count, asLen, cmtSpanIdx = 0, len(allSpans), 0
			lastTokensEnd = allSpans[-1][1]
			# token=string[allSpans[idx][0]:allSpans[idx][1]] ###
			tokensEnd = allSpans[idx][1]
			while True:
				# print(f'priorTokens,              while idx: {idx} < asLen: {asLen} and tokensEnd: {tokensEnd} <= cmtStart: {cmtStart} < lastTokensEnd: {lastTokensEnd}')
				while idx < asLen and tokensEnd <= cmtStart < lastTokensEnd:
					# print(f'priorTokens,              token is {token!r}, tokensEnd: {tokensEnd} not inside any comment span: '
					# 	  f'{not any(begin < tokensEnd <= end for begin, end, _, _ in comments)}')
					if exclInCmt:
						# print(f'  excluding cmt, cmtSpanIdx: {cmtSpanIdx} -> { cmtSpans[cmtSpanIdx]}, tokensEnd: {tokensEnd};   token is {token!r}')
						while cmtSpans[cmtSpanIdx][1] < tokensEnd:
							cmtSpanIdx += 1
							# print(f'    next span {cmtSpans[cmtSpanIdx]}')
						if tokensEnd <= cmtSpans[cmtSpanIdx][0]:
							count += 1
							# print(f'priorTokens,                {token!r} is not part of a comment, count = {count}')
					# print(f'priorTokens,                token {token!r}, idx = {idx}')
					idx += 1
					tokensEnd = allSpans[idx][1]
					# token=string[allSpans[idx][0]:allSpans[idx][1]] ###
					# print(f'priorTokens,              while idx: {idx} < asLen: {asLen} and tokensEnd: {tokensEnd} <= cmtStart: {cmtStart} '
						  # f'< lastTokensEnd: {lastTokensEnd};   token is {token!r}')
				# print(f'priorTokens,                before loop yield, count: {count}, idx: {idx}, cmtStart: {cmtStart}')
				cmtStart = yield count if exclInCmt else idx
				# print(f'\npriorTokens,                 after loop yield, count: {count}, idx: {idx}, cmtStart: {cmtStart}')

		allSpans = createTokenSpans(string, strip_JS=True) # used in generators
		comments = [[match.start('leadInWS'), match.start('inlineBody'),
					 match.end('inlineBody'), match.end('trailInWS'),
					 con.NL in match['inlineBody'], 'inline']
					for match in rx.INLINE_WS_RE.finditer(string)]
		comments.extend([match.start('leadEolWS'), match.start('eolBody'),
						 match.end('eolBody'), match.end('trailEolWS'),
						 True, 'eol']
						for match in rx.ENDLINE_WS_RE.finditer(string))
		comments.sort()

		# filter for commented comments
		comments = [[leadStart, start, end, tailEnd, hasNL, kind]
					for leadStart, start, end, tailEnd, hasNL, kind in comments
					   if not any(outerStart < start < outerEnd
								  for _, outerStart, outerEnd, _, _, _ in comments)]

		# filter for quoted comments
		quoted = [match.span() for match in rx.QUOTED_RE.finditer(string)]
		if len(quoted) > 0:
			comments = [[leadStart, start, end, tailEnd, hasNL, kind]
						for leadStart, start, end, tailEnd, hasNL, kind in comments
						   if not any(quoteStart < start < end < quoteEnd
									  for quoteStart, quoteEnd in quoted)]

		debug = False
		# debug = '//if(c > 45) log(w.name, ship.name+" end i:"+i+" c:"+c);' in string

		# when 2 comments are adjacent, the whitespace between them will be
		# captured by both (trapping for this in the regex is not worth it)
		# so remove the first's trailing whitespace
		for current, follows in zip(comments, comments[1:]):
			currLdStart, currStart, currEnd, currTaEnd, _, _ = current
			nextLdStart, nextStart, nextEnd, nextTaEnd, _, _ = follows

			if debug and 10540 < currStart < 11625:
				print(f'\n{string[currLdStart:currTaEnd]!r}')
				print(f'\n{string[nextLdStart:nextTaEnd]!r}')

			# check if current's tail overlaps with follows' lead
			if nextLdStart <= currEnd <= currTaEnd <= nextStart:
				# set first's end to second's start, ie. shrink current's tail
				current[2] = current[3] = follows[0]

		# for adjacent comments, shift WS in between to front of following
		# so later processing won't output WS prematurely
## problem: what if .toString inserts char between adjacent, eg. }
## ?only applies to inline
		for current, follows in zip(comments, comments[1:]):
			currLdStart, currStart, currEnd, currTaEnd, _, _ = current
			nextLdStart, nextStart, nextEnd, nextTaEnd, _, _ = follows
			if currTaEnd == nextLdStart: # end == start -> adjacent
				if currEnd < currTaEnd:
					if debug:
						print('current',current)
						print('follows',follows)
						print(f'shifting WS from \n    {string[currLdStart:currTaEnd]!r}'
							  f' to \n    {string[nextLdStart:nextTaEnd]!r}')
					current[3] = follows[0] = current[2]
					if debug:
						currLdStart, currStart, currEnd, currTaEnd, _, _ = current
						nextLdStart, nextStart, nextEnd, nextTaEnd, _, _ = follows
						print('current',current)
						print('follows',follows)
						print(f' -> {string[currLdStart:currTaEnd]!r}')
						print(f' -> {string[nextLdStart:nextTaEnd]!r}\n')

		# create generators
		tokenCount, codeCount = priorTokens(0), priorTokens(0, exclInCmt=True)
		# initialize generators
		tokenCount.send(None)
		codeCount.send(None)
		commentSpans = [commentSpan(leadStart, tailEnd, hasNL, kind,
						tokenCount.send(leadStart), codeCount.send(leadStart))
						for leadStart, _, _, tailEnd, hasNL, kind in comments]
		# close generators
		tokenCount.close()
		codeCount.close()
		# print(allSpans[:22])
		# print(commentSpans[:9])
		# print(string[:100].replace('\n','|'))
		# print('0123456789'*8)
		# print(' '+''.join((' '*9)+str(1+x) for x in range(8)))
		# print(f'last of allSpans: {allSpans[-1]}, last of commentSpans: {commentSpans[-1] if len(commentSpans) else "no comments"}')
		# print(f'expect total tokens: {len(createTokenSpans(string, strip_JS=True))}, '
		# 	  f'expect total non-comment tokens: {len(createTokenSpans(string, strip_JS=True, exclude=comments))}, ')
		# print('.')
		# print('|'.join(string[start:end] for start,end,_ in allSpans))
		# print('.')
		# print(', '.join(repr(string[start:end]) for start,end,_,_,_,_ in commentSpans))
		# pdb.set_trace()

		# (start, end, hasNL, kind, allTokens, codeTokens)
		return quoted, commentSpans
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def textFromCmtSpans(string, spans):
	"""given spans (list of tuple(start, end, hasNL[, kind]) for comments, invert
	   the list to get spans for uncommented text, inserting NLs when comments
	   have them.  Return text with comments removed
	"""

	strLen = len(string)
	if not spans or len(spans) == 0:		# no comments
		return [0, strLen, False]
	# flatten and remove 'kind', the 4th of 4 items in tuple
	flat = [idx for span in spans for idx in span[:3]]
	hasEndingNL = flat[-1]
	# strip comments and insert NL for those that have one
	if flat[0] == 0 and flat[-2] == strLen:
		# comments bookend string, remove both ends
		# [0, 15, True, 26, 37, False, ... 657, 671, False, 672, 700, True]
		# -> [15, True, 26, 37, False, ... 657, 671, True, 672]
		flat.pop(0)
		# flat[1] = False		# suppress NL from fnLead comment
		flat.pop()
		flat.pop()
		flat[-2] = flat[-2] or hasEndingNL
	elif flat[0] == 0:
		# string starts with a comment, remove first, add len
		# [0, 15, True, 26, 37, False, ... 657, 671, False, 672, 680, True]
		# -> [15, True, 26, 37, False, ... 657, 671, True, 672, 680, True, 700]
		flat.pop(0)
		# flat[1] = False		# suppress NL from fnLead comment
		flat.append(strLen)
	elif flat[-2] == strLen:
		# string ends with a comment, remove last, add 0
		# [7, 15, True, 26, 37, False, ... 657, 671, False, 672, 700, True]
		# -> [0, False, 7, 15, True, 26, 37, False, ... 657, 671, True, 672]
		flat.insert(0, False)
		flat.insert(0, 0)
		flat.pop()
		flat.pop()
		if len(flat) > 3:	# a single comment has only 3 items
			flat[-2] = flat[-2] or hasEndingNL
	else:
		# neither end has a comment, add 0 and last
		# [7, 15, True, 26, 37, False, ... 657, 671, False, 672, 680, True]
		# -> [0, False, 7, 15, True, 26, 37, False, ... 672, 680, True, 700]
		flat.insert(0, False)
		flat.insert(0, 0)
		flat.append(strLen)

	# flat has repeating triples: start, hasNL, end
	return ''.join((con.NL if flat[x+1] else '') + string[flat[x]:flat[x+2]]
				   for x in range(0, len(flat), 3))

##======================================================================
## removing comments
##======================================================================

# no longer in use
# def _stripByLoops(string):
# 	index = 0
# 	defn = ''
# 	strLen = len(string)
# 	while index < strLen:
# 		blocks = []
# 		quoted = rx.QUOTED_RE.search(string, index)
# 		if quoted:
# 			start, end = quoted.span()
# 			blocks.append((start, end, 'q', None))
# 		endLine = rx.ENDLINE_CMT_RE.search(string, index)
# 		if endLine: # captures leading WS and any trailing NLs
# 			start, end = endLine.span('eolCmt')
# 			blocks.append((start, end, 'e', endLine['eolCmt']))
# 		inLine = rx.INLINE_CMT_RE.search(string, index)
# 		if inLine: # captures leading WS and any trailing NLs
# 			start, end = inLine.span('inlineCmt')
# 			blocks.append((start, end, 'i', inLine['inlineCmt']))
# 		if not len(blocks):
# 			break
# 		blocks.sort(key=itemgetter(0,2))
# 		start, end, kind, comment = blocks.pop(0)
# 		if kind == 'q':				# quoted string, ignore any comments inside
# 			defn += string[index:end]
# 		else:						# excise comment
# 			defn += string[index:start]
# 			# suppress NL from fnLead comment (ie. when start == 0)
# 			if start > 0:
# 				hasNL = su.endsLine(comment)
# 				if -1 < hasNL:
# 					defn += comment[hasNL:]
# 		index = end
#
# 	if index < strLen:
# 		defn += string[index:]
# 	defn = defn.strip()				# suppress any trailing NL
# 	if defn.endswith(con.NL + ')'):
# 		return defn [:-2] + ')'
# 	return defn

def _stripBySpans(string, spans):
	if not spans or len(spans) == 0:# no comments
		return string
	return textFromCmtSpans(string, spans)

def _stripByGenSpans(string):
	_, spans = generateCommentSpans(string)
	return _stripBySpans(string, spans)

def stripComments(string, obj=None):
	"""return a copy of string with comments removed"""

	if obj and obj.commentSpans and not obj.edited:
		_, spans = generateCommentSpans(string)
		if obj.commentSpans != spans:
			print('cmtspans out of date')
			pdb.set_trace()

		return _stripBySpans(string, obj.commentSpans)
	return _stripByGenSpans(string)
##del span check

##======================================================================
## miscellaneous
##======================================================================

def findAll(sub, string, start=0, stop=None, overlap=False):
	"""find all the indices of the substring 'sub' in 'string'
	   (generator for non-regex cases)
	"""

	start, stop = _validateStrParsm(string, start, stop)
	idx = string.find(sub, start, stop)
	while -1 < idx < stop:
		yield idx
		idx = string.find(sub, idx + (1 if overlap else len(sub)), stop)

def flushPending(chars, string, start, stop=None):
	"""adjust 'start' so it is just past the characters in 'chars'
	"""

	start, stop = _validateStrParsm(string, start, stop)
	if len(chars):
		flushIdx = 0
		target = start
		while flushIdx < len(chars):
			closest = findClosest(chars[flushIdx], string, target, stop)
			if -1 < closest:
				target = closest + 1
				flushIdx += 1
				continue
		return target
	return start

def findClosest(char, string, target, start, stop=None):
	"""find the index of 'char' in 'string' closest to 'target'
	   between 'start' and 'stop'
	"""

	start, stop = _validateStrParsm(string, start, stop)
	lSearch = string.rfind(char, start, target + 1) # rfind excludes char at 'end'
	rSearch = string.find(char, target, stop)
	closest = -1
	if -1 < lSearch <= rSearch:
		# both found, pick closest to nextIdx
		closest = lSearch if abs(target - lSearch) \
				   < abs(target - rSearch) else rSearch
	elif lSearch == rSearch < 0:		# neither found! bail
		return -1
	elif lSearch < 0:					# only found > .nextIdx
		closest = rSearch
	elif rSearch < 0:					# only found < .nextIdx
		closest = lSearch
	return closest

def dictWithInts(aDict):
	"""convert to int any numerical strings in 'aDict' (.eg. grid_info)
	"""
	return {k:(int(v) if is_str(v) and v.isdigit() else v) \
				for k, v in aDict.items()}
