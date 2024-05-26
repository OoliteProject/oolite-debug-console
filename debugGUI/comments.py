# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#

import re, difflib

import debugGUI.appUtils as au
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.stringUtils as su
import debugGUI.regularExpn as rx
import debugGUI.widgets as wg

import jsengine
import javascriptlint.lintwarnings as lintwarnings

import pdb
import traceback

# noinspection PyShadowingNames
def _rebuildComments(obj, defn):
	try:
		def mkShort(string):###
			if len(string) > 60:
				return f'{string[:28]}...{string[-28:]}'
			return string

		def running_sum(a):
			tot = 0
			for item in a:
				tot += item
				yield tot

		def genCharCounts(tokenRunLen):
			# given a count of characters, return index of token in
			# defnTokens that has that many characters leading up to it
			count = target = tokIdx = 0
			while tokIdx < tokenRunLen:
				tokCount = defnTokens[tokIdx][1] - defnTokens[tokIdx][0]
				if count + tokCount > target:
					target = yield tokIdx - 1
				count += tokCount
				tokIdx += 1
			else:
				yield tokIdx - 1

		nextToken = None
		def genTokenRuns():
			nonlocal nextToken
			oldTokenCharCounts = list(running_sum(fin - begin
									  for begin, fin in oldDefnTokens))
			newTokenCharCounter = genCharCounts(defnTLen)
			newTokenCharCounter.send(None)
			# oldIdx is codeTokens - 1, refers to tokens in obj.defn
			# - codeTokens is the number of tokens preceding the comment,
			#   so - 1 gives us the index of the last token before the comment
			# - codeTokens excludes all comment tokens (allTokens has them), so
			#   we stripped obj.defn's comments then made oldTokens
			oldIdx, charsInserted = yield
			while oldIdx < oldTLen:
				# .toString may have expanded a token into many by adding spaces
				# we map to new tokens by using total character count of those
				# not in JS_ADDED_CHAR
				index = newTokenCharCounter.send(oldTokenCharCounts[oldIdx]
												 + charsInserted)
				# - index is the last token in defn before charCount characters
				#   (JS_ADDED_CHARS excluded) have passed
				nextToken = defnTokens[min(defnTLen - 1, index + 1)]
				oldIdx, charsInserted = yield defnTokens[index], index
				# - oldIdx is codeTokens - 1, last token before comment in obj.defn

		def genCharacter(string, maxIndex=None):
			# walk string, return index & character, skipping over
			# ';' and runs of spaces
			if maxIndex is None:
				maxIndex = len(string)
			index, char = 0, ''
			while index < maxIndex:
				char = string[index]
				if char not in [';', ' ',]:
					yield char, index
				index += 1
			else:
				yield '', index

		insertedCodeTokens = []
		def findInsertedTokens():
			# defn has more tokens due to inserted space, eg. i+=1 => i += 1
			dtg = ((dt[0], dt[1]) for dt in defnTokens)		# 1 line generators
			otg = ((ot[0], ot[1]) for ot in oldDefnTokens)	# ...
			olds, news = '', ''
			oldc = newc = -1
			try:
				while True:
					while len(olds) <= len(news):
						oldFrom, oldTo = next(otg)
						olds += oldDefn[oldFrom:oldTo].replace('"', '_').replace("'", '_')
						oldc += 1
					while len(news) <= len(olds):
						newFrom, newTo = next(dtg)
						news += defn[newFrom:newTo].replace('"', '_').replace("'", '_')
						newc += 1
					same = min(len(olds), len(news))
					if same > 0 and olds[:same] == news[:same]:
						olds = olds[same:]
						news = news[same:]
						continue
					# found inserted token!
					same = min([x for x in range(same)
								if olds[x] != news[x]], default=-1)
					if -1 < same:
						olds = olds[same:]
						news = news[same:]
					inserted = defn[defnTokens[newc][0]:defnTokens[newc][1]]
					count = len(su.createTokenSpans(inserted, strip_JS=True))
					insertedAt = news.find(inserted)
					news = news[:insertedAt] + news[insertedAt + len(inserted):]
					if len(insertedCodeTokens) and insertedCodeTokens[-1][0] == oldc:
						insertedCodeTokens[-1][1] += count
					else:
						insertedCodeTokens.append([oldc, newc, count])
			except StopIteration:
				pass

		def blockHasStarted(start):
			if defn[start] == con.PARENTHESES[0]:
				return False
			index = defn.rfind(con.PARENTHESES[0], 0, start)
			if index < 0:
				return False
			return defn[index + 1:start].isspace()

		def blockIsEnding(start):
			if defn[start] == con.PARENTHESES[1]:
				return True
			index = defn.find(con.PARENTHESES[1], start)
			if index < 0:
				return False
			return defn[start:index].isspace()

		def getIndent(start):
			"""decide which line to measure indent by presence of
			   opening/closing characters
			   - if preceding is not an encloser, use current line
			   - if first encounter either parenthesis, use current line
			   - if first encounter a closer, search backward to its
			     corresponding opener and use that line
			"""
			def prevLine(offset):
				while offset > 0 and -1 < su.endsLine(defn, 0, offset):
					offset -= 1
				begin = defn.rfind(con.NL, 0, offset) + 1 # is zero if fails
				if defn[offset] != con.NL:
					offset += 1	# to include last char before NL
				return begin, offset

			# + 1 to include last character (args act like range, 2nd not included)
			wsCount = su.trailingWS(defn, 0, start + 1, WS=con.WHITESPACE)
			index = start - wsCount
			if defn[index] in con.PARENTHESES or defn[index] not in con.JS_ENCLOSERS:
				return  su.linesIndent(defn, index)
			index, stop = prevLine(start - wsCount)
			stack = []
			while True:
				enclosers = [(match.group('paren'), match.start('paren')) for match in
							 rx.FIND_PARENTHESES_RE.finditer(defn, index, stop)]
				while len(enclosers) > 0:
					encloser, idx = enclosers.pop()
					if len(stack) == 0: # check for an opener
						if encloser in con.JS_OPENERS:
							# if first enclosers is an opener, use current line
							return su.linesIndent(defn, idx)
						# save closer for backwards match
						stack.append(encloser)
					elif encloser == con.JS_ENCLOSING.get(stack[-1]):
						# matched encloser on top of stack
						stack.pop()
						if len(stack) == 0:
							return su.linesIndent(defn, idx)
					else: # save encloser for backwards matching
						stack.append(encloser)
				index, stop = prevLine(index)
				if -1 < index < stop:
					continue
				break
			print('getIndent, Yikes! failed to match: {!r}'.format(defn[index:]))
			if con.CAGSPC:
				pdb.set_trace()

		def isAdjacentCmt(index):
			codes = obj.commentSpans[index].codeTokens
			if hasattr(isAdjacentCmt, 'previous') \
					and isAdjacentCmt.previous[0] == codes:
				return isAdjacentCmt.previous[1]
			withCodes = [idx for idx, cmt, span in cmtSpanZip
						 if span.codeTokens == codes]
			result = len(withCodes) > 1
			isAdjacentCmt.previous = (codes, result)
			return result

		# def isFirstAdjacentCmt(index):
		# 	codes = obj.commentSpans[index].codeTokens
		# 	if hasattr(isAdjacentCmt, 'previous') \
		# 			and isAdjacentCmt.previous[0] == codes:
		# 		return isAdjacentCmt.previous[1]
		# 	withCodes = [idx for idx, cmt, span in cmtSpanZip
		# 				 if span.codeTokens == codes]
		# 	# ensure it IS an adjacent, then that it's the first one
		# 	result = isAdjacentCmt(index) and withCodes[0] == index
		# 	isFirstAdjacentCmt.previous = (codes, result)
		# 	return result

		def isLastAdjacentCmt(index):
			codes = obj.commentSpans[index].codeTokens
			if hasattr(isAdjacentCmt, 'previous') \
					and isAdjacentCmt.previous[0] == codes:
				return isAdjacentCmt.previous[1]
			withCodes = [idx for idx, cmt, span in cmtSpanZip
						 if span.codeTokens == codes]
			# ensure it IS an adjacent, then that it's the last one
			result = isAdjacentCmt(index) and withCodes[-1] == index
			isLastAdjacentCmt.previous = (codes, result)
			return result

		def commentPosition():

			def commonWS(ending, starting, eStart=0, sStart=0,):
				check = max(su.trailingWS(ending, eStart, WS=con.WHITESPACE),
							su.leadingWS(starting, sStart, WS=con.WHITESPACE))
				if check == 0 or sStart >= len(starting):
					# no whiteespace characters to check
					return 0
				if check == 1:
					# only last of ending vs first of starting
					return 1 if ending[eStart-1] == starting[sStart] else 0
				eEnd = eStart if eStart > 0 else None
				return max([x for x in range(1, check + 1)
							if ending[eStart-x:eEnd]
								== starting[sStart:sStart+x]], default=0)

			def findInsertionPoint():

				def toStringAdded(char):
					# return bool as to whether char was inserted by .toString by
					# comparing character counts from before (prefix + afterCmt)
					# and after (insertRegion)
					return insertCharCounts.get(char, 0) \
							> prefixCharCounts.get(char, 0) \
							  + afterCharCounts.get(char, 0)

				def toStringRemoved(char):
					# return bool as to whether char was removed by .toString by
					# comparing character counts from before (prefix + afterCmt)
					# and after (insertRegion)
					return insertCharCounts.get(char, 0) \
							< prefixCharCounts.get(char, 0) \
							  + afterCharCounts.get(char, 0)

				def movePastChar(index):
					index += 1
					if debug:
						print(f'    => MOVING comment outside {insertChar!r}, '
							  f'index: {index} <? maxInsert: {maxInsert}, '
							  f'insertRegion[index] is NL: {insertRegion[index] == con.NL if index < len(insertRegion) else "nada"!r} ?== NL, '
							  f'cmt startwith NL? {su.countNLs(cmt.text) == 0}')
					if index < maxInsert <= len(insertRegion) \
							and insertRegion[index] == con.NL\
							and su.countNLs(cmt.text) == 0:
						# suppress NL if comment lacks a starting one
						index += 1
						if debug:
							print(f'      => MOVING comment past NL, insertIdx: {index}')
					return index

				closerCount = {'func': {']':0, '}':1, ')': 0},
							   'iife': {']':0, '}':1, ')': 2},
							   None:   {']':0, '}':0, ')': 0}}

				prefixCharCounts = {ch:prefix.count(ch) for ch in {lt for lt in prefix}}
				afterCharCounts =  {ch:afterCmt.count(ch) for ch in {lt for lt in afterCmt}}
				insertMax = insertRegion[:maxInsert]
				insertCharCounts = {ch:insertMax.count(ch) for ch in {lt for lt in insertMax}}

				getInsert = genCharacter(insertRegion, maxInsert)
				getPrefix = genCharacter(prefix)
				insertIdx = prefixIdx = 0
				insertDone = prefixDone = False
				nextInsert = nextPrefix = True
				insertChar = prefixChar = ''
				while not insertDone or not prefixDone:
					lastInsert = (insertChar, insertIdx)
					if not insertDone and nextInsert:
						try:
							insertChar, insertIdx = next(getInsert)
							nextInsert = False
						except StopIteration:
							insertDone = True
					if not prefixDone and nextPrefix:
						try:
							prefixChar, prefixIdx = next(getPrefix)
							nextPrefix = False
						except StopIteration:
							prefixDone = True
					if insertDone and prefixDone:
						break
					if not nextInsert and not nextPrefix and (insertDone or prefixDone):
# tmp? until better loop mechanics
# avoids infinite loop for
#   prefix: [15876:15882]: '] ) {\n', afterCmt: ';\n                                                '
#   insertRegion [:4 maxInsert]: ') {\n'
#   ')' vs ']', 0 vs 0
#   ')' vs ']', 0 vs 0 ...
						break

					if debug: ###
						print(f'  {insertChar!r} vs {prefixChar!r}, {insertIdx} vs {prefixIdx}')

					if insertChar == prefixChar:
						nextInsert = nextPrefix = True
						continue
					if insertChar == con.NL:
						if -1 < su.subInString(prefixChar, insertRegion, insertIdx, maxInsert):
							# is blocking a match to prefixChar
							nextInsert = True
							continue
						if not su.isSpaceOrEmpty(prefix, prefixIdx):
							# only skip formatting if prefix not finished
							nextInsert = True
						else:
							insertDone = True
					elif insertChar == '{':
						if toStringAdded(insertChar):
							# when .toString adds braces, ensure comment goes inside
							insertIdx += 1
							if debug: ###
								print(f'   MOVING comment inside braces, insertIdx: {insertIdx}')
							break
						elif -1 < su.subInString(insertChar, prefix, prefixIdx):
							# out of synch as not caught by equality test above
							nextInsert = True
						else:
							insertDone = True
					elif insertChar == '}':
						inPrefix = -1 < prefix.find(insertChar, prefixIdx)
						reqClosers = closerCount[obj.type].get(insertChar, 0)
						remaining = defn.count(insertChar, defnInsert + insertIdx)
						wasInserted = remaining > reqClosers and toStringAdded(insertChar)
						if debug: ###
							print(f'    **** found {"inserted " if wasInserted else ""}'
								  f'closer, reqClosers: {reqClosers}, remaining: {remaining}')
						if wasInserted or inPrefix or cmt.tag == 'fnTail':
							# move past it if not the final parenthesis (end of fn)
							insertIdx = movePastChar(insertIdx)
							break
						if not inPrefix and insertChar in afterCmt:
							# comment remains inside parentheses
							insertChar, insertIdx = lastInsert if lastInsert is not None else ('', 0)
							if debug: ###
								print(f'    => backup to preserve formatting, insertIdx: {insertIdx}')
							break
						if su.isSpaceOrEmpty(prefix, prefixIdx) \
								or su.isSpaceOrEmpty(insertRegion, insertIdx):
							break
						# insertDone = True
						break
					else:
						insertDone = su.subInString(insertChar, prefix) < 0
					if insertDone and prefixDone:
						break
					if prefixChar == con.NL:
						if -1 < su.subInString(insertChar, prefix, prefixIdx):
							# is blocking a match to insertChar
							nextPrefix = True
							continue
						prefixDone = True
					elif prefixChar == ')':
						# safe to ignore when .toString removes redundant parentheses
						if toStringRemoved(prefixChar):
							nextPrefix = True
						else:
							prefixDone = True
					else:
						prefixDone = True
				getInsert.close()
				getPrefix.close()
				return insertIdx
###

			if nextToken is None:
				# comment is first token in defn
				return 0, 0
			if debug:
				print(f'commentPosition, lastToken: {lastToken}, defnTLen: {defnTLen}', end=', ')

			if tokenIndex < defnTLen - 1:
				defnInsert = max(tokenEnd, defnIdx)
				insertRegion = defn[defnInsert:nextToken[0]]
				if debug:
					print(f'insertRegion: defn[defnInsert {defnInsert}:{nextToken[0]} '
						  f'nextToken[0]]: {insertRegion!r}')
			else:	# we've processed the last token
				defnInsert = defnIdx
				insertRegion = defn[defnInsert:]
				if debug:
					print(f'insertRegion [defnIdx {defnIdx}:]: {insertRegion!r}')

			# trailing whitespace excluded (always goes to right of comment to
			# preserve formatting
			maxInsert = len(insertRegion) - su.trailingWS(insertRegion)

			endOfLastObj = obj.tokenSpans[span.allTokens - 1][1]	# [1] is end
			startOfNextObj = obj.tokenSpans[span.allTokens][0]		# [0] is start
			trailing = su.trailingWS(obj.defn, endOfLastObj, startOfNextObj)
			prefix = obj.defn[endOfLastObj:startOfNextObj - trailing]
			if cmtIndex < len(obj.comments) - 1: # not the last comment
				# to align with insertRegion, collect all characters
				# (excluding comment's) upto next code token
				afterCmt = ''
				lastCmtToken = span.allTokens + len(cmt.tokenSpans) - 1
				# cmtSpanZip is a list of tuple for each comment
				# (index, cmt, cmtSpan) where cmtSpan is a
				# namedtuple(start, end, hasNL, kind, allTokens, codeTokens)
				ccIdx = cmtIndex
				currSpan = cmtSpanZip[ccIdx][2]
				while lastCmtToken + 1 < len(obj.tokenSpans):
					if ccIdx + 1 >= len(obj.comments):
						break	# this is the last comment
					nextSpan = cmtSpanZip[ccIdx + 1][2]
					# check codeTokens for comments and space between
					if nextSpan.codeTokens != currSpan.codeTokens:
						break	# # of codeTokens differ => there's code between
					token = rx.STRIP_JS_ADDED_RE.match(obj.defn, currSpan.end,
													   nextSpan.start)
					if token: 	# there are characters in the interval between
						break	#   that are not in JS_ADDED_CHARS
					# these are adjacent comments
					afterCmt += obj.defn[currSpan.end:nextSpan.start]
					ccIdx += 1
					currSpan = nextSpan
					# its allTokens + its # of spans less one
					lastCmtToken = nextSpan.allTokens \
								+ len(obj.comments[ccIdx].tokenSpans) - 1

				tkStart = obj.tokenSpans[lastCmtToken][1] 		# end of last
				tkEnd = oLen
				if lastCmtToken + 1 < len(obj.tokenSpans):
					tkEnd = obj.tokenSpans[lastCmtToken + 1][0]	# start of next
				afterCmt += obj.defn[tkStart:tkEnd]
			else:	# we've processed the last token
				afterCmt = obj.defn[cmt.tokenSpans[-1][1]:]

			# .toString modification may be complex, ie. changing many characters
			# - eg. function (o) {return (o.x - o.y)};
			#   =>  function (o) {\n    return o.x - o.y;\n}
			if debug:
				print(f'  insertRegion [0:{maxInsert} maxInsert]: {insertRegion[:maxInsert]!r}')
				print(f'  prefix: [{endOfLastObj}:{startOfNextObj - trailing}]: {prefix!r}, afterCmt: {afterCmt!r}')

			insertIndex = findInsertionPoint()
			# skip any whitespace contained in comment as it captures all
			# leading/trailing whitespace
			head = su.leadingWS(cmt.text, WS=con.WHITESPACE)
			cmtHead = cmt.text[:head] if head > 0 else ''

			if debug:
				_region = '' if len(insertRegion) == 0 else \
					(insertRegion[:insertIndex] if insertIndex > 0 else insertRegion[insertIndex])
				print(f'== ? duplicate whitespace, insertIndex: {insertIndex}: '
					  f'{_region!r} vs cmt {mkShort(cmt.text)!r};  cmtHead: {cmtHead!r}')

			common = commonWS(defn, cmt.text, eStart=defnInsert + insertIndex)
			insertAt = max(0, insertIndex - common)
			index = defnInsert + insertAt
			# it is sometimes the case that cmt's tail is longer than formatted indent ...
			while True:
				if index >= dLen: 				# comment trails last of code
					break
				if su.endsLine(cmt.text) < 0:	# comment has no trailing NL
					break
				# do not adjust comments that are immediately followed by another
				if isAdjacentCmt(cmtIndex) and not isLastAdjacentCmt(cmtIndex):
					break
				# find the whitespace that will immediately follow the comment
				leading = su.leadingWS(defn, index, WS=con.WHITESPACE) \
						  - su.countNLs(defn, index)
				cmtTail = su.trailingWS(cmt.text, WS=' ')
				if debug:
					print(f'  ### leading: {leading}, cmtTail: {cmtTail}, index: {index}, '
						  f'blockHasStarted: {blockHasStarted(index)}, '
						  f'blockIsEnding: {blockIsEnding(index)}')
				if defn[index] == con.PARENTHESES[0]:
					indent = getIndent(index - 1)
				elif defn[index] == con.PARENTHESES[1]:
					indent = getIndent(index + 1)
				elif blockHasStarted(index):
					while defn[index] == con.NL:
						index -= 1
					indent = su.linesIndent(defn, index)
				elif blockIsEnding(index):
					while defn[index] == con.NL:
						index += 1
					indent = su.linesIndent(defn, index)
				else:
					while defn[index] == con.NL:
						index += 1
					indent = su.linesIndent(defn, index)

				if debug:
					nextlines = su.linesIndent(defn, index)
					print(f'  ### indent: {indent}, nextlines: {nextlines}')

				if cmtTail + leading == indent:
					break
				if debug:
					print(f'    defnInsert: {defnInsert}, insertAt: {insertAt}, cmtTail: {cmtTail}, '
						  f'indent: {indent}, cmt.text[:{indent - cmtTail}]')
				if cmtTail > indent:
					if debug:
						print(f'  cmtTail > indent, shrinkng, cmt.text: {cmt.text!r}', end='\n           -> ')
					cmt.text = cmt.text[:indent - cmtTail]
					if debug: print(repr(cmt.text))
				elif cmtTail < indent:
					if debug:
						print(f'  cmtTail < indent, padding, cmt.text: {cmt.text!r}', end='\n           -> ')
					cmt.text = cmt.text + ' '*(indent - cmtTail)
					if debug: print(repr(cmt.text))
				break

			if debug:
				tail = su.trailingWS(cmt.text, WS=con.WHITESPACE)
				cTail = cmt.text[-tail:] if tail > 0 else ''
				print(f'== ? duplicate whitespace, insertIndex: {insertIndex}: '
					  f'cmt {cmt.text[-su.trailingWS(cmt.text, WS=con.WHITESPACE)-5:]!r} '
					  f'vs {insertRegion[insertIndex:]!r};  cTail: {cTail!r}')

			common = commonWS(cmt.text, defn, sStart=defnInsert + insertIndex)
			resumeAt = min(len(insertRegion), insertIndex + common)

			if debug:
				print(f'== returning {defnInsert} + {insertAt} = {defnInsert + insertAt}, {defnInsert} + {resumeAt} = {defnInsert + resumeAt}')
			return defnInsert + insertAt, defnInsert + resumeAt

		# tokenSpans is a list of immutable tuples representing tokens
		# interspersed with JS_ADDED_CHARS and occasionally, comments
		# - the JS_ADDED_CHARS may be added/removed by JavaScript's .toString()
		# to restore comments to defn, we traverse tokens to the point where a
		# comment needs insertion
		# - we output defn upto the insertion token's end (after mapping
		#   obj.tokenSpans to defnTokens, as .toString() may increase the number
		#   of tokens by inserting spaces!)
		# - we position the comment among the JS characters between the
		#   insertion token and the next, using those that surround the
		#   comment in obj.defn as a guide
		# - when there is no 'best' position, the comment is placed to the right
		#   of a NL if it ends with one, otherwise to the left of a NL
		#   - this is to prevent generating syntax errors
		# - we output comment using insert/resume points from positioning
		# rinse & repeat

		defn = defn.expandtabs(con.CFG_TAB_LENGTH)
		if obj.type == 'iife':
			# iife's are stored as funtions in console.script properties
			defn = '({})({})'.format(
					defn, obj.iifeArgs if obj.iifeArgs else '')
		if not obj.comments or len(obj.comments) == 0:
			if not defn.endswith(con.NL):
				# can be lost when formattingAliases (ie. .toString)
				# - we maintain it for comparison, as a formatting change will
				#   be counted as a change when deciding to write to CFGFILE
				defn += con.NL
			return defn

		debug = False # True #
		# debug = obj.name in ['shipSpawned', ]

		defnTokens = su.createTokenSpans(defn, strip_JS=True)
		oldDefn = su.stripComments(obj.defn, obj)
		oldDefnTokens = su.createTokenSpans(oldDefn, strip_JS=True)
		oLen, oldTLen = len(obj.defn), len(oldDefnTokens)
		dLen, defnTLen = len(defn), len(defnTokens)
		findInsertedTokens()
		tokenRun = genTokenRuns()
		tokenRun.send(None)
		lastToken = defnIdx = tokenEnd = tokenIndex = 0
		cmtIndex = -1
		newDefn = ''
		cmtSpanZip = [(idx, cmt, span)
					  for idx, cmt, span in
					  zip(range(len(obj.comments)), obj.comments, obj.commentSpans)]
		insertedChars = 0
		for cmtIndex, cmt, span in cmtSpanZip:

			# if '//reset visualEffect index' in cmt.text:
			# 	debug = True
			# else:
			# 	debug = False
			if debug:
				print('.')
				print(f'cmt.offset: {cmt.offset}, start: {span.start}, end: {span.end}, hasNL: {span.hasNL}, '
					  f'kind: {span.kind}, allTokens: {span.allTokens}, codeTokens: {span.codeTokens}')

			if lastToken < span.codeTokens:
				# output intervening code using last token in run
				# - allTokens & codeTokens are count of tokens before comment
				#   so we subtract 1 for a token's index
				tokenSpan, tokenIndex = tokenRun.send((span.codeTokens - 1,
													   insertedChars))
				_, tokenEnd = tokenSpan

				if len(insertedCodeTokens) and span.codeTokens == insertedCodeTokens[0][0]:
					# .toString inserted a token bigger that those handled by JS_ADDED_CHARS
					#   eg. 'default:;' to a switch statement which has no 'default' case
					# 'insertedChars' keeps 'tokenRun' generator in synch
					# 'count' added to 'nextToken'
					oldCT, newCT, count = insertedCodeTokens.pop(0)
					start, end = defnTokens[newCT]
					insertedChars += end - start
					tokenEnd = defnTokens[newCT][1]
					nextToken = defnTokens[min(defnTLen - 1, tokenIndex + count + 1)]

				if debug:
					print(f'    tokenEnd: {tokenEnd}, tokenIndex: {tokenIndex}')
					print(f'    appending [defnIdx {defnIdx}:tokenEnd {tokenEnd}]: {mkShort(defn[defnIdx:tokenEnd])!r}')
				newDefn += defn[defnIdx:tokenEnd]
				defnIdx = tokenEnd

			insert, resume = commentPosition()
			if debug:
				print(f'    insert: {insert}, resume: {resume}, '
					  f'defn[defnIdx {defnIdx}:{insert} insert]: '
					  f'{defn[defnIdx:insert]!r} .isspace?: {defn[defnIdx:insert].isspace()}')

			if defnIdx < insert and (lastToken < span.codeTokens
									 or not defn[defnIdx:insert].isspace()):
				# suppress remnant on adjacent comments
				if debug:
					print(f'..appending remnamt [{defnIdx}:{insert}]: {defn[defnIdx:insert]!r}')
				newDefn += defn[defnIdx:insert]

			if debug:
				print(f'..appending comment {mkShort(cmt.text)!r}')
			lastToken = span.codeTokens
			newDefn += cmt.text
			defnIdx = resume

		tokenRun.close()
		# output remaining code
		if -1 < defnIdx < dLen and defn[defnIdx] == con.NL \
				and newDefn.endswith(con.NL):
			# trailing comment ends with NL
			defnIdx += 1
		if defnIdx < dLen:
			if debug:
				print(f'**appending finale [{defnIdx}:]: {defn[defnIdx:]!r}')
			newDefn += defn[defnIdx:]
		if not newDefn.endswith(con.NL):
			newDefn += con.NL
		else:
			tailNLs = su.countNLs(newDefn, step=-1)
			if tailNLs > 1:
				newDefn = newDefn[:-(tailNLs - 1)]

		if debug:
			pdb.set_trace()

		return newDefn
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def prepAliasForRegistration(obj, silent=False):
	try:
		# contruct alias and remove comments to avoid possible syntax errors
		if obj.type is None:
			# ALIAS_RE captures an leading/trailing comments
			defn = obj.match['simpleAlias']
		else:
			defn = obj.match['fnCall'] + obj.match['fnBody']
			defn = su.stripComments(defn)
		check = checkJSsyntax(obj, defn, silent)
		if check is not True:
			# returns tuple/error message instead of False
			return ''
		return defn
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def restoreAliasDefn(obj, defn):
	# there's nothing to restore when .type is None
	if obj.type is not None:
		newDefn = _rebuildComments(obj, defn)
		check = checkJSsyntax(obj, newDefn, silent=True)
		if check is not True: # returns tuple/error not False
			# _rebuildComments screwed up!
			msg = 'Comment restoration caused the mismatch (d\'Oh!)  \nPlease '
			msg += 'post the definition and edits made when reporting - thanks'
			msg += '\nMoving the comment around should fix the problem.'
			msg += '\nFYI: the error generated was:\n'
			msg += check[0] if isinstance(check, (list,tuple)) else check
			if con.CAGSPC:
				print(msg)
				print('alias', repr(obj.name))
				pdb.set_trace()
			else:
				wg.OoInfoBox(gv.root, msg, label='You found a bug!')
			return False
		obj.defn = newDefn
	return True

def checkJSsyntax(obj, string=None, silent=False):
	try:
		if string is None:
			string = obj.defn
		jsengine.parser.parsestring(string)
	except jsengine.JSSyntaxError as exc:	# report error and bail
		errdesc = lintwarnings.format_error(exc.msg, **exc.msg_args)
		offset = exc.offset
		lineStart = string.rfind(con.NL, 0, offset)
		lineStart = 0 if lineStart < 0 else lineStart
		if string[lineStart] == con.NL:
			lineStart += 1
		lineEnd = string.find(con.NL, offset)
		lineEnd = len(string) if lineEnd < 0 else lineEnd
		lineString = string[lineStart:lineEnd]
		line = string.count(con.NL, 0, offset) + 1
		char = offset - lineStart
		msg = 'JSSyntaxError, line {}, char {}'.format(line, char)
		msg += con.NL + errdesc
		if silent:
			msg += con.NL + lineString
			msg += con.NL + ' ' * (char - 1) + '^'
		else:
			index = char - su.leadingWS(lineString, WS=' ')
			lineString = lineString.strip()
			msg += con.NL + lineString
			# pad both sides so it's same as lineString (OoInfoBox centers msg)
			marker = au.leftFontPad('^', au.measurePhrase(lineString[:index]))
			marker = au.rightFontPad(marker, au.measurePhrase(lineString))
			msg += con.NL + marker
			wg.OoInfoBox(gv.root, msg,
						 label='JSSyntaxError: {!r}'.format(obj.name))
		return msg, line, char
	except Exception as exc:
		if con.CAGSPC:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()
		return repr(exc)
	return True
