# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4
#
import sys, os, io, zipfile, locale, gc, re
from fnmatch import fnmatch
from operator import itemgetter

import pdb, traceback

import debugGUI.appUtils as au
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.regularExpn as rx
import debugGUI.widgets as wg

# OPENINGS = '([{'
# CLOSINGS = ')]}'
# ALL_BRACKETS = OPENINGS + CLOSINGS
# STOPPERS = '.,;:'
# AUTO_SUBSTR = STOPPERS + ALL_BRACKETS

_preferredEncoding = locale.getpreferredencoding()
_indents = ['    ' * x for x in range(20)]
# offset to 1st char past line number, colon, etc (from 'fmt = ' below)
# - needed to align emphasis
_textStart = 8

_filesFound = {} 	# dict of class _Found for results of search
_reportingProgress = False
_numFolders = 0
_numFiles = 0
_numOxzs = 0
_numOxzsFolders = 0
_numOxzsFiles = 0

_settings = None
_defaults = None


class _FindParameters(object):
	def __init__(self):
		self.dir = None
		self.excl = None
		self.incl = None
		self.tokens = None
		self.noCase = True
		self.matchAll = True
		self.quitEarly = False
		self.subdir = True
		self.oxzToo = True
		self.context = 3
		self.mode = 'Token'

	def addPath(self, path):
		path = path.strip(con.PATH_STRIP_CHARS)
		if len(path) == 0:
			msg = 'You must select a path before search can start.'
			wg.OoInfoBox(gv.root, label='Missing path', destruct=5, msg=msg)
			return False
		if con.IS_WINDOWS_PC:
			path = path.lower()
		self.dir = os.path.normpath(path)
		path = path.replace(os.sep, '/')
		if not _isTargetFolder(path):
			msg = 'Search Path cannot be searched.\n'
			msg += '(check your Excluded option settings?...)'
			wg.OoInfoBox(gv.root, label='Excluded path', destruct=5, msg=msg)
			return False
		if not os.path.exists(self.dir):
			msg = 'Specified Search Path does not exist.\n'
			msg += path + con.NL
			wg.OoInfoBox(gv.root, label='Invalid path', destruct=5, msg=msg)
			return False
		return True

	@staticmethod
	def itemize(exts):
		if ',' in exts:
			exts = exts.replace(',', ';')
		return [ext.strip() for ext in exts.split(';')]

	def _mkFileTypesList(self, items):
		if len(items) > 0:
			allTypes = set()
			for item in items:
				if len(item.strip()):
					allTypes.update(self.itemize(item))
			return list(allTypes)
		return None

	def addIncl(self, incl):
		if self.oxzToo:
			incl.extend(['.oxz', '.OXZ', '.Oxz'])
		if len(incl) == 0:
			self.incl = None
			return
		if con.IS_WINDOWS_PC:
			incl = [it.lower() for it in incl]
		self.incl = self._mkFileTypesList(incl)

	def addExcl(self, excl):
		if len(excl) == 0:
			self.excl = None
			return
		if con.IS_WINDOWS_PC:
			excl = [it.lower() for it in excl]
		self.excl = self._mkFileTypesList(excl)

	@staticmethod
	def _findQuoted(string, start):
		singles = string.count("'", start)
		doubles = string.count('"', start)
		singleQuoted = singles > 0 and singles % 2 == 0
		doubleQuoted = doubles > 0 and doubles % 2 == 0
		if not singleQuoted and not doubleQuoted:
			return -1, -1
		singleAt = string.find("'", start)
		doubleAt = string.find('"', start)
		splitter = opener = -1
		if singleQuoted and  (doubleAt == -1 or singleAt < doubleAt):
			splitter, opener = "'", singleAt
		elif doubleQuoted and (singleAt == -1 or doubleAt < singleAt):
			splitter, opener = '"', doubleAt

		else:
			print('findQuoted, singles {}, doubles {}, singleAt: {}, doubleAt {}'.format(
					singles, doubles, singleAt, doubleAt))
			traceback.print_exc()
			pdb.set_trace()

		closer = string.find(splitter, opener + 1)
		return opener, closer

	def addTokens(self, tokens):
		if len(tokens) == 0 \
				or all(len(token.strip()) == 0 for token in tokens):
			msg = 'Your target is too vague and will always match.\n'
			msg += 'Enter a more specific Search text.'
			wg.OoInfoBox(gv.root, label='Empty target', destruct=5, msg=msg)
			return False
		if self.mode not in ['Token', 'Word',]:
			self.tokens = tokens
			return True
		adding = []
		for token in tokens:
			token = token.strip()
			index, tokenLen = 0, len(token)
			while index < tokenLen:
				openAt, closeAt = self._findQuoted(token, index)
				if openAt == closeAt == -1:	# no (more) pairs of quotes
					break
				# split any preceding tokens
				if index < openAt:
					adding.extend(tok for tok in token[index:openAt].split()
									if len(tok) > 0)
				# save quoted token
				adding.append(token[openAt + 1: closeAt])
				index = closeAt + 1
			# split any succeeding tokens
			if index < tokenLen - 1:
				adding.extend(tok for tok in token[index:].split()
								if len(tok) > 0)
		self.tokens = adding
		return True

	def setCase(self, ignore):
		self.noCase = ignore
		if ignore and (self.mode in ['Token', 'Substring', 'Word',]
						or self.mode == 'File' and con.IS_WINDOWS_PC):
			for x, token in enumerate(self.tokens):
				self.tokens[x] = token.lower()

	def setContext(self, tkVar):
		default = _settings.get('FindContextLines',
								_defaults.get('FindContextLines', 3))
		self.context = mu.getSpinboxValue(tkVar, default)

	seekers = {'tokens': {}, 'substrs': [], 'cache': {}}
	def _addCompiledRE(self, item):
		# noinspection PyBroadException
		try:
			if item in self.seekers['tokens']:
				return
			if item not in self.seekers['cache']:
				self.seekers['cache'][item] = re.compile(item)
			self.seekers['tokens'][item] = self.seekers['cache'][item]
		except re.error as rer:
			msg = 'Regex error: {}'.format(rer)
			wg.OoInfoBox(gv.root, msg, font=gv.OoFonts['default'],
						 label='Regular Expression Error')
			return False
		except Exception as exc:
			print(exc)
			print(type(exc))
			traceback.print_exc()
			pdb.set_trace()
			return False
		return True

	def mkSeekers(self):
		del self.seekers['substrs'][:]
		self.seekers['tokens'].clear()

		if self.mode in ['File', 'Substring']:
			self.seekers['substrs'].extend(self.tokens)
		elif self.mode == 'Regex':
			for tk in self.tokens:
				# ensure there's at least one capture group
				if not(self._addCompiledRE('(?P<target>' + tk + ')')):
					return False
		elif self.mode == 'Word':  # leading whitespace, trailing punctuation
			for tk in self.tokens:
				if not(self._addCompiledRE(rx.FIND_QUOTED.format(tk))):
					return False
		else:  # 'Token'; allow whitespace at brackets
			for tk in self.tokens:
				if not(self._addCompiledRE(r'(?:^|\W)\s*(?P<target>'
										   + re.escape(tk)
										   + r')\s*(?:\W|$)')):
					return False
		return True

class _FileKey(object):
	def __init__(self, path, file, inOxz):
		if con.IS_WINDOWS_PC:
			self.path = path.replace('/', '\\')
		else:
			self.path = path
		self.file = file
		self.inOxz = inOxz

class _Found(object):
	def __init__(self, key, spans, row, lines, prefix):
		self.fileKey = key 		# key in _filesFound of file this was found in
		self.spans = spans
		if lines is None:
			self.line = self.text = self.previous = None
			self.prefix = self.suffix = None
		else:
			self.line = row + 1
			self.text = self.formatLine(row, lines)
			self.prefix = self.formatContext(row, lines, -1, prefix)
			self.suffix = self.formatContext(row, lines, +1)
		self.oxzRpt = False

	@staticmethod
	def formatLine(row, lines):
		fmt = '{:>6}: {}'.format(row + 1, lines[row]) # +1 as row is 0-indexed
		return fmt.strip(con.NL)

	def formatContext(self, row, lines, dirn, spec=None):
		count = findArgs.context
		dest, maxIdx = [], len(lines)
		if dirn > 0: # 'spec' MAY be sent to shorten suffix
			idx = row + 1
			if spec is not None:
				count = spec
		else: # 'spec' specifies prefix start
			idx = spec
		while 0 <= idx < maxIdx:	#  and count > 0
			# prefix may be shortened depending on what was last output
			if dirn < 0 and idx == row:
				break
			if dirn > 0 and count == 0:
				break
			dest.append(self.formatLine(idx, lines))
			count -= 1
			idx += 1
		return con.NL.join(dest) + con.NL if len(dest) else ''

	def foundTarget(self): # generator for matched lines
		lastMatch = len(self.spans) - 1
		column = 0
		for x, span in enumerate(self.spans):
			start = _textStart + span[0]
			end = _textStart + span[1]
			pre = self.text[column:start]
			target = self.text[start:end]
			post = self.text[end:] if x == lastMatch else ''
			yield pre, target, post
			column = end

class _ListResult(object):
	def __init__(self, key, text, isOxz=False,
				 matches=0, lines=0, fileSize=0):
		self.fileKey = key 		# key in _filesFound of file this was found in
		self.text = text
		self.isOxz = isOxz
		self.matches = matches
		self.lines = lines
		self.fileSize = fileSize

findArgs = None
neverOpened = True
def showFileFind():			# display finder frame (called via Options menu)
	global _settings, _defaults, findArgs, neverOpened

	if _settings is None: # first time setup
		_settings = gv.CurrentOptions['History']
		_defaults = con.defaultConfig['History']
		findArgs = _FindParameters()

	for box in [gv.inclEntry, gv.exclEntry, gv.textEntry]:
		box.checkSelectionCount()

	if gv.grepWindow.winfo_ismapped():
		gv.grepWindow.lift()
		return

	if gv.grepWindow.mouseXY:
		gv.grepWindow.restoreTop()
	else:							# initial opening of window
		grepPosn = None
		try:
			grepPosn = _settings.get('FinderWindow')
			if grepPosn is None:	# posn wrt appWindow
				# ensure it's deep enough for all settings
				inputW, inputH = mu.getWidgetReqWH(gv.grepCanvas.cvFrame)
				outputW, outputH = mu.getWidgetReqWH(gv.contextText)
				rootX, rootY = mu.getWidgetRoot(gv.app)
				openAt = (rootX + con.SCROLL_WIDTH,
						  rootY + con.SCROLL_HEIGHT)
				gv.grepWindow.mouseXY = openAt
				geom = '{}x{}+{}+{}'.format(
						inputW + outputW, inputH, *openAt)
				gv.grepWindow.geometry(geom)
			else:
				gv.grepWindow.geometry(grepPosn)
				_, _, rootX, rootY = mu.parseGeometry(grepPosn)
				gv.grepWindow.mouseXY = (rootX, rootY)
			gv.grepWindow.restoreTop()
		except Exception as exc:
			errmsg = 'Exception: {}, grepPosn: {}'.format(exc, grepPosn)
			if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
			else:
				gv.debugLogger.exception(errmsg)
			gv.grepWindow.center()

	width, height = mu.getWidgetReqWH(gv.grepCanvas.cvFrame)
	gv.grepCanvas.canvas.config(width=width, height=height)
	au.positionFindSash()

	for box in [gv.pathEntry, gv.inclEntry, gv.exclEntry, gv.textEntry]:
		if neverOpened:
			# force window manager to initialize dimensions for later mapping
			box.post()
			gv.grepWindow.update()
			box.unpost()
		box.xview_moveto(0.0)
		box.selection_clear()
	neverOpened = False

## event handlers #############################################################

# noinspection PyUnusedLocal
def startFileFind(event=None):	# handler for 'Search' button & '<Return>' event
	if _loadArgs():
		_clearSearch()
		setFindOptions()
		_searchDir()

def _clearSearch():
	global _reportCount, _numFolders, _numFiles,\
			_numOxzs, _numOxzsFolders, _numOxzsFiles
	
	# reset search vars
	_filesFound.clear()
	del _foundListItems[:]
	gv.filesList.delete(0, 'end')
	_clearContext()
	_reportCount = _numFolders = _numFiles = 0
	_numOxzs = _numOxzsFolders = _numOxzsFiles = 0
	gv.searchRunning = 'running'
	gc.collect()

def cancelFileFind():	# handle for 'Cancel' button
	gv.searchRunning = 'halted'

## options processing #########################################################

_finderOptions = {}
def setFindOptions():
	if len(_finderOptions) == 0:	# init after startup
		_finderOptions.update({
			'FindPaths':		(gv.pathEntry,		'OoCombobox'),
			'FindTypes':		(gv.inclEntry,		'OoSelector'),
			'FindIncluding':	(gv.inclEntry,		'Selection'),
			'FindExcls':		(gv.exclEntry,		'OoSelector'),
			'FindExcluding':	(gv.exclEntry,		'Selection'),
			'FindSearches':		(gv.textEntry,		'OoSelector'),
			'FindSearching':	(gv.textEntry,		'Selection'),
			'FindIgnoreCase':	(gv.ignoreCase,		'IntVar'),
			'FindMatchAll':		(gv.matchAll,		'IntVar'),
			'FindQuitOnFirst':	(gv.quitOnFirst,	'IntVar'),
			'FindSubDirs':		(gv.subDirs,		'IntVar'),
			'FindOxzFiles':		(gv.oxzFiles,		'IntVar'),
			'FindContextLines':	(gv.contextNum,		'Spinbox'),
			'FindTreatment':	(gv.treatText,		'StringVar'),
		})

	for option, spec in _finderOptions.items():
		fVar, fType = spec
		# widgets built with default values so don't need setting
		if fType in ['OoCombobox', 'OoSelector']:
			fVar.adjustEntry()
			gv.save20History(option, fVar)
		elif fType == 'Selection':
			_settings[option] \
				= 'all' if fVar.useAll.get() \
						else ('checked' if fVar.useChecked.get()
										else 'current')
		elif fType == 'IntVar':
			_settings[option] = True if fVar.get() else False
		elif fType == 'Spinbox':
			default = _settings.get('FindContextLines',
				  				    _defaults.get('FindContextLines', 3))
			_settings[option] = mu.getSpinboxValue(fVar, default)
		else:
			_settings[option] = fVar.get()

def _loadArgs():
	# treatText must be first as used by setCase, addTokens
	findArgs.mode = gv.treatText.get()
	# tokens loaded early so other options can modify them
	if not findArgs.addTokens(gv.textEntry.getValues()):
		return False
	findArgs.setCase(bool(gv.ignoreCase.get()))
	findArgs.matchAll = bool(gv.matchAll.get())
	findArgs.quitEarly = bool(gv.quitOnFirst.get())
	findArgs.subdir = bool(gv.subDirs.get())
	findArgs.oxzToo = bool(gv.oxzFiles.get())
	findArgs.setContext(gv.contextNum)

	# must preceed .addPath as it checks excl's via _isTargetFolder
	findArgs.addExcl(gv.exclEntry.getValues())
	if not findArgs.addPath(gv.pathEntry.get()):
		return False

	findArgs.addIncl(gv.inclEntry.getValues())
	if findArgs.mode == 'File':
		# add tokens to included
		if findArgs.incl is None:
			findArgs.incl = findArgs.tokens
		else:
			findArgs.incl.extend(tk for tk in findArgs.tokens
								 if tk not in findArgs.incl)
	msg = ''
	## chk only selected or just box
	if findArgs.incl is None or len(findArgs.incl) == 0 \
			or all(len(inc) == 0 for inc in findArgs.incl):
		msg += 'You must specify file type(s) before starting search.\n'
		msg += '(use "*.*" if you really want to search everything)'
	if len(msg):
		wg.OoInfoBox(gv.root, label='Missing file type', destruct=7, msg=msg)
		return False

	if not findArgs.mkSeekers():
		return False

	# print('_loadArgs, findArgs:')
	# for k,v in findArgs.__dict__.items():
	# 	print('  {}: {} ({})'.format(k,v,type(v)))
	# print('  substrs: {} ({})'.format(findArgs.seekers['substrs'], type(findArgs.seekers['substrs'])))
	# print('  tokens: {} ({})'.format(findArgs.seekers['tokens'], type(findArgs.seekers['tokens'])))
	return True

## output functions ###########################################################

def _clearContext():
	txt = gv.contextText
	txt.config(state='normal')
	txt.tag_remove('fileSearch', '1.0', 'end')
	txt.delete('1.0', 'end')
	txt.config(state='disabled')

_reportCount = 0
_dots =  ['', ' .', ' ..', ' ...', ' ....',
		  ' .....', ' ......', ' .......']
_stars = ['', ' *', ' **', ' ***', ' ****',
		  ' *****', ' ******', ' *******']
def _progressReport():
	global _reportCount

	au.removeAfter('_progressReport')

	# the repetitious code that follows is intended to decrease the # of strings
	# created, as this is called every gv.tkTiming['slow'] milliseconds
	if findArgs.mode == 'File':
		fLen = sum(1 for it in _foundListItems if not it.isOxz)
		if _numOxzs: # findArgs.oxzToo
			status = 'searched %d %s, %d zipped %s (%d %s), %d %s' % \
				  ( _numFolders, _some('folder', _numFolders),
					_numOxzs, _some('file', _numOxzs),
					_numOxzsFolders, _some('folder', _numOxzsFolders),
					fLen, _some('match', fLen) )
		else:
			status = 'searched  %d %s, %d %s' % \
				  ( _numFolders, _some(' folder', _numFolders), 
					fLen, _some('match', fLen) )
	else:
		fLen = sum(it.matches for it in _foundListItems)
		if _numOxzs: # findArgs.oxzToo
			status = 'searched %d %s, %d %s, %d zipped %s (%d %s, %d %s), %d %s' % \
				  ( _numFiles,  _some('file', _numFiles),
					_numFolders, _some('folder', _numFolders),
					_numOxzs, _some('file', _numOxzs),
					_numOxzsFiles,  _some('file', _numOxzsFiles),
					_numOxzsFolders, _some('folder', _numOxzsFolders),
					fLen, _some('match', fLen) )
		else:
			status = 'searched %d %s, %d %s, %d %s' % \
				  ( _numFiles,  _some('file', _numFiles),
					_numFolders, _some('folder', _numFolders),
					fLen, _some('match', fLen) )
	if gv.searchRunning == 'running':
		suffix = _stars[_reportCount % 8]
		au.afterLoop(gv.tkTiming['slow'], '_progressReport', _progressReport)
	else:
		if gv.searchRunning == 'halted':
			suffix = ' ... Search halted'
		elif fLen == 0:
			suffix = ' ... No matches found'
		else:
			suffix = ' ... Search complete'
	gv.grepWindow.setTitle(status + suffix)

	txt = gv.contextText
	if _reportingProgress:
		if gv.searchRunning == 'running':
			suffix = _dots[_reportCount % 8]
		txt.config(state='normal')
		if findArgs.quitEarly and _reportCount > 0:
			txt.delete('1.0', '2.0')
			txt.insert('1.0', status + suffix + con.NL)
		else:
			txt.tag_remove('fileSearch', '1.0', 'end')
			txt.delete('1.0', 'end')
			txt.insert('end', status + suffix + con.NL)
		txt.config(state='disabled')
	_reportCount += 1
	txt.update_idletasks()

def _reportFirstMatch(source, header, item):
	try:
		if source not in _filesFound \
				or _filesFound[source] is None \
				or len(_filesFound[source]) == 0:
			return
		match = _filesFound[source][0]
		if _reportCount == 0:
			_progressReport()
		txt = gv.contextText
		txt.config(state='normal')
		txt.insert('end', con.NL)
		if header is not None:
			oxz = 'in "{}":\n'.format(header.fileKey.inOxz)
			txt.insert('end', oxz)
			normPath = header.fileKey.file  # zip folder is included
		else:
			normPath = _joinPath(item.fileKey.path, item.fileKey.file)
		text = '{}"{}"\n'.format(
				_inOxzArrow if source.inOxz else '', normPath)
		txt.insert('end', text)
		# reporting the 1st (& only) match
		#  - for loop used for side-effects (generator init & close)
		for before, target, after in match.foundTarget():
			txt.insert('end', before)
			txt.insert('end', target, 'fileSearch')
			txt.insert('end', after)
			# break
		txt.insert('end', con.NL)
		txt.config(state='disabled')
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def _some(name, amount):
	if amount == 1:
		return name
	return name + ('es' if name.endswith('h') else 's')

def _reportFilesFound():
	_progressReport()
	if con.CAGSPC:
		try:
			print('_reportFilesFound, len(_filesFound)', len(_filesFound))
			for it in findArgs.__dict__:
				print('findArgs.{} = {}'.format(it, getattr(findArgs, it)))
			# pdb.set_trace()
			print('substrs',findArgs.seekers['substrs'])
			print('tokens',findArgs.seekers['tokens'])
			print('_reportFilesFound, types found:')
			print(set(os.path.splitext(f.file)[-1] for f in _filesFound.keys()))
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

# creates _ListResult instances and maintains lists of these
# in _foundListItems in parallel with gv.filesList listbox
# arg 'source' is a key for dict _filesFound (whose values
# are None in 'File' mode, ie. all info in the key)
def _appendFilesList(source, fileSize=None):
	header = None
	if source.inOxz:
		reported = any(True for item in _foundListItems if
						item.isOxz and item.fileKey.inOxz == source.inOxz)
		if not reported:
			oxzSize = os.path.getsize(source.inOxz)
			oxz = 'in "{}":  {}\n'.format(source.inOxz, _fmtSize(oxzSize))
			header = _ListResult(key=source, text=oxz,
								 isOxz=True, fileSize=oxzSize)
		normPath = source.file # zip folder is included
	else:
		normPath = _joinPath(source.path, source.file)
	if findArgs.mode == 'File':
		lines = matches = 0
		text = '{}"{}",  {}\n'.format(
				_inOxzArrow if source.inOxz else '',
				normPath, _fmtSize(fileSize))
	else:
		lines = len(_filesFound[source])
		matches = sum(len(fd.spans) for fd in _filesFound[source])
		text = '{}"{}" ({}), matches: {} in {} {}\n'.format(
				_inOxzArrow if source.inOxz else '',
				normPath, _fmtSize(fileSize),
				matches, lines, _some('line', lines))
	item = _ListResult(key=source, text=text,
					   matches=matches, lines=lines, fileSize=fileSize)

	if header:
		_foundListItems.append(header)
		gv.filesList.insert('end', header.text)
	_foundListItems.append(item)
	gv.filesList.insert('end', item.text)
	if findArgs.quitEarly:
		_reportFirstMatch(source, header, item)
	gv.filesList.update_idletasks()

def _fmtFileTree(result):
	rpt, indent = '', 0
	source = result.fileKey
	drv, path = os.path.splitdrive(source.path)
	path = path.replace('/', os.sep)
	if source.inOxz:
		rpt += 'found in: {}{}'.format(source.inOxz, 2 * con.NL)
		indent = 1
	else:
		rpt += source.path + 2 * con.NL
	folders = path.split(os.sep)
	if len(folders) and len(folders[0]) == 0:
		folders.pop(0)
	if len(drv) and len(folders):
		folders[0] = drv + os.sep + folders[0]
	while len(folders):
		folder = folders.pop(0)
		rpt += '{}{}{}{}'.format(_indents[indent], folder, os.sep, con.NL)
		indent += 1
	rpt += _indents[indent] + source.file + con.NL
	return rpt

_missingLines = (' ' * _textStart) + con.ELLIPSIS + con.NL
_inOxzArrow = '    -> '
# noinspection PyUnusedLocal
def showFindContext(event=None):	# handler for '<<ListboxSelect>>' in results lists
	global _reportingProgress

	_reportingProgress = False
	currSelection = gv.filesList.curselection()
	# - returns tuple w/ indices of the selected element(s)
	if len(currSelection) == 0:
		return 'break'
	found = _foundListItems[currSelection[0]]
	txt = gv.contextText
	txt.config(state='normal')
	txt.tag_remove('fileSearch', '1.0', 'end')
	txt.delete('1.0', 'end')
	if found.isOxz: # clicking on oxz report line resets context window
		_reportingProgress = True
		_progressReport()
	elif findArgs.mode == 'File':
		txt.insert('end', _fmtFileTree(found))
	else:
		if found.fileKey.inOxz:
			txt.insert('end', found.fileKey.inOxz + con.NL)
			txt.insert('end', _inOxzArrow + found.fileKey.file + con.NL)
		else:
			txt.insert('end', found.fileKey.path + os.sep
					   		+ found.fileKey.file + con.NL)
		txt.insert('end', con.NL)
		# each item is a _Found instance
		# we concatenate them for output to contextText, ensuring
		# - context regions are separated by a line with 3 dots
		# - matches are emphasized
		# - when context overlaps, they're merged without duplicates
		#   -> done in _addToFindList
		context = findArgs.context
		items = _filesFound[found.fileKey]
		lastMatch = len(items) - 1
		prevMatchEnd = -1
		for x, item in enumerate(items):
			matchStart = item.line - item.prefix.count(con.NL)
			if x != 0 and prevMatchEnd < matchStart - 1:
			# if x not in [0, lastMatch] and prevMatchEnd < matchStart - 1:
				# not last match and some lines suppressed (- 1 for adjacent lines)
				txt.insert('end', _missingLines)
			txt.insert('end', item.prefix)
			for before, target, after in item.foundTarget():
				txt.insert('end', before)
				txt.insert('end', target, 'fileSearch')
				txt.insert('end', after)
			txt.insert('end', con.NL + item.suffix)
			prevMatchEnd = item.line + item.suffix.count(con.NL)
	txt.xview_moveto(0)
	txt.yview_moveto(0)
	txt.config(state='disabled')
	return 'break'

## utility functions ##########################################################

def _matchFolder(folder, wild):
	# does 'wild' match 'folder' (an absolute path)
	if not folder or len(folder) == 0:
		return False
	# NB: wild always ends with a '/'
	leading = '/' + wild[:-1]
	braced = leading + '/'
	# folders: '.../<folder>' while zip folders: '.../<folder>/
	if folder.endswith(leading) or folder.endswith(braced):
		return True
	if any(ch in wild for ch in '*?[]'):
		if fnmatch(folder, '*' + leading) \
				or  fnmatch(folder, '*' + braced):
			return True
	return False

def _matchWild(folder, file, wild):
	if wild.endswith('/'):
		return _matchFolder(folder, wild)
	if any(ch in wild for ch in '*?[]'):
		if fnmatch(file, wild):
			return True
	return file.endswith(wild) # catches both explicit filenames and '.ext'

def _isTargetFile(folder, file):
	if '/' in file:	# a zip filename may contain folder name(s)
		file = file[file.rfind('/') + 1:]
	if findArgs.mode == 'File':
		if any(fnmatch(file, tk) for tk in findArgs.tokens):
			return True
	if findArgs.excl and len(findArgs.excl):
		for wild in findArgs.excl:
			if _matchWild(folder, file, wild):
				return False
	if findArgs.incl and len(findArgs.incl):
		for wild in findArgs.incl:
			if _matchWild(folder, file, wild):
				return True
	return False

def _isTargetFolder(folder):
	# check excluded to decide if search folder
	if findArgs.excl and len(findArgs.excl):
		for wild in findArgs.excl:
			if wild.endswith('/'):
				if _matchFolder(folder, wild):
					return False
	return True

def _joinPath(path, name):
	return os.path.normpath(os.path.join(path, name))

TERABYTE = 1024 ** 4
GIGABYTE = 1024 ** 3
MEGABYTE = 1024 ** 2
KILOBYTE = 1024
def _fmtSize(fileSize):
	if fileSize > TERABYTE:
		return '{:,.2f} TB'.format(fileSize/TERABYTE)
	elif fileSize > GIGABYTE:
		return '{:,.2f} GB'.format(fileSize/GIGABYTE)
	elif fileSize > MEGABYTE:
		return '{:,.2f} MB'.format(fileSize/MEGABYTE)
	elif fileSize > KILOBYTE:
		return '{:,.2f} KB'.format(fileSize/KILOBYTE)
	return '{} B'.format(fileSize)

# differentiating text vs binary file is non-deterministic
# - don't want to limit text files by ext
# - really don't want to search binaries, as _generateFileLines always works
_ooliteText = ['.js', '.log', '.oolite-save', '.plist', '.txt',
               '.GNUstepDefaults', '.fragment', '.vertex', '.dat']
_ooliteBinary = ['.ogg', '.png', '.ico', '.exe', '.dll', '.pdf']
_textChars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
def _isBinary(path, raw):
	# from https://stackoverflow.com/a/24370596421
	def detect_by_bom(_raw, default):
		# BOM_UTF32_LE's start is equal to BOM_UTF16_LE so need to try the former first
		for enc, boms in ('utf-8-sig', (codecs.BOM_UTF8,)), \
				('utf-32', (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)), \
				('utf-16', (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
			if any(_raw.startswith(bom) for bom in boms):
				return enc
		return default

	# from https://stackoverflow.com/a/7392391
	def is_binary_string(string):
		return bool(string.translate(None, _textChars))

	ext, _ = os.path.splitext(path)
	if ext in _ooliteText:
		if detect_by_bom(raw, False):
			return True
		return not is_binary_string(raw)
	if ext in _ooliteBinary:
		return True
	return is_binary_string(raw)

def _isFileBinary(path, zfp=None):
	if zfp:
		with zfp.open(path, mode='r') as fp:
			raw = fp.read(1024)  # will read less if the file is smaller
	else:
		with io.open(path, mode='rb') as fp:
			raw = fp.read(1024)  # will read less if the file is smaller
	return _isBinary(path, raw)

## search driving functions ###################################################

_folderGenerator = None
def _searchDir():
	global _folderGenerator, _reportingProgress

	_reportingProgress = True
	_folderGenerator = _generateFolders()
	if findArgs.mode == 'File':
		# check if any tokens lack an extension
		for tk in findArgs.tokens:
			_, ext = os.path.splitext(tk)
			if len(ext) == 0:
				_initFileNameOnly()
				break
		_searchForFiles()
	else:
		_searchInsideFiles()
	au.afterLoop(gv.tkTiming['slow'], '_progressReport', _progressReport)

# fetches list of files for _searchDir
def _generateFolders():
	global _numFolders

	for path, dirs, files in os.walk(findArgs.dir):
		if con.IS_WINDOWS_PC:
			path = path.lower()
			files = [file.lower() for file in files]
		path = path.replace(os.sep, '/')
		if _isTargetFolder(path):
			_numFolders += 1
			yield path, files
		else: # exclude children
			dirs[:] = []

# fetches files for _generateFileLines and _locateFile
def _generateOxzFiles(oxzFile):
	global _numOxzs, _numOxzsFolders, _numOxzsFiles

	_numOxzs += 1
	with zipfile.ZipFile(oxzFile) as zfp:
		zippedFiles = zfp.namelist()
		zfolder = skipFolder = ''
		for zfile in zippedFiles:
			if len(skipFolder) and skipFolder in zfile:
				continue
			zInfo = zfp.getinfo(zfile)
			if findArgs.mode != 'File':
				if zInfo.compress_type == 99 \
						or zInfo.flag_bits & 1:  # encrypted
					continue
				if _isFileBinary(zfile, zfp):
					continue
			if zInfo.filename.endswith('/'):  # folder
				zfolder = zfile
				if not _isTargetFolder(zfolder):
					skipFolder = zfile
					continue
				_numOxzsFolders += 1
				skipFolder = ''
				continue
			if not _isTargetFile(zfolder, zfile):
				continue
			_numOxzsFiles += 1
			yield zfp, zfile, zInfo.file_size

# fetches text for _searchInsideFiles
def _generateFileLines(path, files):
	inZipFile = False
	normPath = zfile = 'not set'
	# if all fail, the 'None' codec will be 'utf-8' & errors='replace'
	# ie. will always produce lines
	codecs = [_preferredEncoding, 'utf-8', 'latin-1', None]
	try:
		for file in files:
			inZipFile = False
			if not _isTargetFile(path, file):
				continue
			normPath = _joinPath(path, file)
			if zipfile.is_zipfile(normPath):
				inZipFile = True
				for zfp, zfile, fileSize in _generateOxzFiles(normPath):
					for codec in codecs:
						try:
							with zfp.open(zfile, mode='r') as fp:
								lines = io.TextIOWrapper(fp,
										encoding=codec if codec else 'utf-8',
										errors='strict' if codec else 'replace',
										newline=None).readlines()
						except UnicodeDecodeError:  # try next codec
							continue
						yield lines, zfile, normPath, fileSize
						break
			elif not _isFileBinary(normPath, zfp=None):
				for codec in codecs:
					try:
						with io.open(normPath, mode='rt',
									 encoding=codec if codec else 'utf-8',
									 errors='strict' if codec else 'replace',
									 newline=None) as fp:
							lines = fp.readlines()
					except UnicodeDecodeError:  # try next codec
						continue
					yield lines, file, None, os.path.getsize(normPath)
					break
	except Exception as exc:
		errmsg = 'Exception: {}\n'.format(exc)
		if inZipFile:
			errmsg += '  in {!r}\n    file {!r}'.format(normPath, zfile)
		else:
			errmsg += '  file {!r}'.format(normPath)
		if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
		else:
			gv.debugLogger.exception(errmsg)

# noinspection PyBroadException
def _finishSearch():
	global _folderGenerator, _fileLinesGenerator

	_reportFilesFound()
	if _folderGenerator is not None:
		try:
			_folderGenerator.close()
		except:
			pass
		finally:
			_folderGenerator = None
	if findArgs.mode != 'File' and _fileLinesGenerator is not None:
		try:
			_fileLinesGenerator.close()
		except:
			pass
		finally:
			_fileLinesGenerator = None

## search for target files in folder(s) #######################################

_filenameOnly = []	# tokens that lack an extension
_fileTypes = []		# includes that specify an extension only
def _initFileNameOnly():
	# in 'File' mode, a target may be just the filename, no extension
	# here, we prepare _filenameOnly & _fileTypes from .tokens & .incl
	# respectively, which are used by _fileMatches

	# noinspection PyUnresolvedReferences
	tokens, incl = findArgs.tokens, findArgs.incl
	del _filenameOnly[:]
	_filenameOnly.extend(token for token in tokens \
					  if os.path.splitext(token)[1] == '')
	del _fileTypes[:]
	_fileTypes.extend(ft for ft in incl if ft.startswith('.'))
	_fileTypes.extend(ft[1:] for ft in incl if ft.startswith('*.'))

def _searchForFiles():
	au.removeAfter('_searchForFiles')
	try:
		if gv.searchRunning != 'running':
			_finishSearch()
			return
		path, files = next(_folderGenerator)
		au.afterLoop(gv.tkTiming['fast'], '_locateFile',
								  _locateFile, path, files)
	except StopIteration:  # no more folders
		gv.searchRunning = 'finished'
		_finishSearch()

def _fileMatches(path, name):
	if _isTargetFile(path, name):
		if len(_filenameOnly) and len(_fileTypes):
			if any(name == fn + ft for fn in _filenameOnly
								   for ft in _fileTypes):
				return True
		tokens = findArgs.tokens
		if any(_matchWild(path, name, fn) for fn in tokens):
			return True
	return False

def _locateFile(path, files):
	global _numFiles

	_numFiles += len(files)
	# report on location of found file
	au.removeAfter('_locateFile')
	for file in files:
		normPath = _joinPath(path, file)
		if zipfile.is_zipfile(normPath):
			_, ext = os.path.splitext(normPath)
			if any(fnmatch(normPath, inc) for inc in findArgs.incl):
				for zfp, zfile, fileSize in _generateOxzFiles(normPath):
					zfolder = ''
					if '/' in zfile:
						zfolder, zfilename = zfile.rsplit('/', 1)
					else:
						zfilename = zfile
					if _fileMatches(zfolder, zfilename):
						key =_FileKey(zfolder, zfilename, normPath)
						_filesFound[key] = None
						_appendFilesList(key, fileSize)
		elif _fileMatches(path, file):
			key = _FileKey(path, file, None)
			_filesFound[key] = None
			_appendFilesList(key, os.path.getsize(normPath))

	if findArgs.subdir:
		au.afterLoop(gv.tkTiming['fast'], '_searchForFiles',
				 _searchForFiles)
	else:
		gv.searchRunning = 'finished'
		_finishSearch()

## search for target in files #################################################

_fileLinesGenerator = None
def _searchInsideFiles():
	global _fileLinesGenerator

	au.removeAfter('_searchInsideFiles')
	try:
		if gv.searchRunning != 'running':
			_finishSearch()
			return
		path, files = next(_folderGenerator)
		_fileLinesGenerator = _generateFileLines(path, files)
		au.afterLoop(gv.tkTiming['fast'], '_searchInFiles',
					_searchInFiles, path)
	except StopIteration:  # no more folders
		gv.searchRunning = 'finished'
		_finishSearch()
	except Exception as exc:
		errmsg = 'Exception: {}'.format(exc)
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.exception(errmsg)

def _searchInFiles(path):
	global _numFiles

	au.removeAfter('_searchInFiles')
	try:
		if gv.searchRunning != 'running':
			_finishSearch()
			return
		lines, file, inOxz, fileSize = next(_fileLinesGenerator)
		_numFiles += 1
		au.afterLoop(gv.tkTiming['fast'], '_addToFindList',
					_addToFindList, path, file, inOxz, lines, fileSize)
	except StopIteration:  # no more files
		if findArgs.subdir:
			au.afterLoop(gv.tkTiming['lazy'], '_searchInsideFiles',
						 _searchInsideFiles)
		else:
			gv.searchRunning = 'finished'
			_finishSearch()

_foundListItems = []
def _addToFindList(path, file, inOxz, lines, fileSize):
	au.removeAfter('_addToFindList')
	key = _FileKey(path, file, inOxz)
	context = findArgs.context
	currFile = lastMatch = None
	lastRow = lastSuffix = -1
	for row, spans in _searchFile(path, lines):
		prefix = max(row - context, 0)
		# check for overlap of prefix with previous suffix
		if -1 < lastSuffix and lastSuffix + context >= prefix:
			# set prefix to start where lastSuffix ended
			prefix = lastSuffix + context
			# check if previous suffix overwrites row
			if prefix >= row:
				prefix = -1 # signal no prefix
			# did suffix start at the line before row?
			if lastSuffix == row:
				lastMatch.suffix = ''
			elif lastSuffix + context >= row: # shorten last suffix
				sufLen = row - lastSuffix
				lastMatch.suffix = lastMatch.formatContext(
												lastRow, lines, +1, sufLen)
		elif row > 0:
			# adjust unmodified prefix to expand if any blank lines encountered
			prefix, count = row - 1, context
			while count > 0:
				text = lines[prefix]
				if len(text) > 0 and not text.isspace():
					count -= 1
				if count == 0: break
				if prefix == 0: break
				prefix -= 1
		if currFile is None:
			currFile = _filesFound.setdefault(key, [])
		currFile.append(_Found(key, spans, row, lines, prefix))
		lastMatch = currFile[-1]
		lastRow = row
		lastSuffix = row + 1

	if lastMatch is not None:
		_appendFilesList(key, fileSize)

def _searchFile(path, lines):
	line, spans, straddles, matches = None, [], [], []
	row = -1
	try:
		toLower = findArgs.noCase and findArgs.mode != 'Regex'
		for row, line in enumerate(lines):
			if len(line.strip()) == 0:
				continue
			del spans[:]
			del straddles[:]
			del matches[:]
			if toLower:
				line = line.lower()
			seek = findArgs.seekers['substrs']
			if len(seek):
				for tk in seek:
					start = 0
					# find all substrings in this line
					while True:
						match = line.find(tk, start)
						if match < 0:
							break
						start = match + len(tk)
						spans.append((match, start))
						matches.append(tk)
			seek = findArgs.seekers['tokens']
			if len(seek):
				for tk in seek.values():
					start = 0
					# find all matches of re in this line
					while True:
						match = tk.search(line, start)
						if match:
							# there is a single capture group 'target'
							try:
								span = match.span('target')
								spans.append(span)
								matches.append(match.group('target'))
								start = match.end('target')
							except Exception as exc:
								print(exc)
								traceback.print_exc()
								pdb.set_trace()
						else:
							break
			if len(spans) == 0:
				continue

			if findArgs.matchAll:
				# applies only to Token, Word and Regex
				if findArgs.mode == 'Regex':
					if len(seek) != len(matches):
						continue
				elif not all(tk in matches for tk in findArgs.tokens):
					continue

			spans.sort(key=itemgetter(0))
			# collapse overlapping spans
			if len(spans) > 1:
				finish = 0
				for start, end in spans:
					if start < finish: # spans are tuples
						straddles[-1] = (straddles[-1][0], end)
					else:
						straddles.append((start, end))
					finish = end
				del spans[:]
				for pair in straddles:
					spans.append(pair)

			yield row, spans[:]
			if findArgs.quitEarly:
				break
			continue
		au.afterLoop(gv.tkTiming['fast'], '_searchInFiles',
					 _searchInFiles, path)
	except Exception as exc:
		errmsg = 'Exception: {}'.format(exc)
		errmsg += '  row {}, spans: {}\n'.format(row, spans)
		errmsg += '  >>line: {}\n'.format(line)
		if con.CAGSPC:
			traceback.print_exc()
			print(errmsg)
			pdb.set_trace()
		else:
			gv.debugLogger.exception(errmsg)


