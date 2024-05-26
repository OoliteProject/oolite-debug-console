# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, logging
from collections import namedtuple, OrderedDict
import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import ttk
else:
	import tkinter as tk
	import tkinter.ttk as ttk

import debugGUI.constants as con
import debugGUI.miscUtils as mu
import debugGUI.regularExpn as rx
import debugGUI.stringUtils as su

##======================================================================
## global variables
##======================================================================

root = None					# app's Tk root (return from tk.Tk())
app = None					# AppWindow instance (app's ttk Frame)
menubar = None				# ttk Frame for menubar
menuFrame = None			# ttk frame to hold all the menus (for dynamic toolbar)
setupComplete = False
appWidth = None				# app's width, to trigger gridMenuButtons if changes
appHeight = None			# app's height, because it was there
appearance = None			# single Appearance instance for changing color

startUpInfo = {
	'setup': [], 			# contains any exceptions raised during setupApp
	'error': []}			# contains any other exceptions
debugLogger = None			# class Logger for output to log file

# contents of con.CFGFILE as dict of Section instances
# - this represents what was read from CFGFILE, use it to detect changes
ConfigFile = {key: None for key in  con.defaultConfig.keys()}
CurrentOptions = None		# current working options dict

gameStarted = None			# Tk variable for player's ship status 
connectedToOolite = False	# flag for live connection
OoSettings = {}				# converted settings from Oolite's
							#   noteConfiguration packet, excluding macros
	
geometries = {				# option widget mapping for window geometries
	'Geometry': None, 
	'AliasWindow': None, 
	'FinderWindow': None
}
	
sashPosns = {				# current sash offsets in PanedWindow's
	'SashOffset': None, 
	'AliasSashOffset': None, 
	'FindSashOffset': None
}

##======================================================================
## tkinter stuff
##======================================================================

OoBitmaps = {}				# custom bitmaps for Tk widgets
CASCADE_KWS = {				# cascade menu kwargs, updated after Tk initialized
	'image': None, 'compound': 'left'}
appWindow = None			# ttk PanedWindow, main application
bodyText = None				# Tk Text widget, main output displaying
cmdLine = None				# Tk Text widget, command line input
btnRun = None				# ttk Button in cmdLine to run command  
btnCmdClr = None			# ttk Button in cmdLine to clear window 
textWidgets = []			# list of Tk Text widget, for setting colors
afterLoopIDs = {}			# dict of ID # from Tk's after cmd, saved for termination
popupWindows = None			# dict of top level windows, to save position in cfg
							# - dict created in buildGUI
appStyleFns = {}			# dict of appearance fns from various modules
monitorsWidth = 0			# max width available across multiple monitors
monitorsHeight = 0			# max height ...

##======================================================================
## aliases
##======================================================================

aliases = None				# OrderedDict, key: alias name, value: class Alias
							# - set in initConfig
aliasWindow = None			# class TopWindow containing ttk PanedWindow, 
							#   which has ScrollingListBox, ScrollingText
aliasDefn = None			# Tk Text widget, alias editor
aliasPaned = None			# ttk PanedWindow, aliases
aliasMsgStr = None			# Tk variable for alias editor msgs
aliasRegStr = None			# Tk variable for alias registration msgs
aliasListBox = None			# Tk Listbox for selecting alias
polledListBox = None		# Tk Listbox for toggling polling
inMenuListBox = None		# Tk Listbox for toggling membership in menubar
aliasListBoxes = []			# list of Tk Listbox for events, maintenance
aliasNameVar = None			# Tk variable for alias name
aliasNameEntry = None		# ttk Entry for typing alias name 
aliasPollCheck =  None		# Tk Checkbox for setting alias poll status
aliasAsButton =  None		# ttk Checkbox for toggling membership in menubar
aliasMenuButtons = {}		# dict (key: alias) of Tk Buttons (may be present in menubar)
aliasButtonFrames = []		# list of Tk Frames for Tk Buttons present in menubar
aliasValueVar =  None		# Tk variable for value of an alias
aliasValueLabel =  None		# ttk Label for displaying alias value
aliasAddBtn =  None			# ttk Button for adding/editing an alias
aliasDelBtn =  None			# ttk Button for deleting an alias
aliasUndoBtn =  None		# ttk Button for undoing add or delete
aliasRedoBtn =  None		# ttk Button for undoing accidental undo
aliasValueWidth = None		# width of alias 'value' Label
gridMenuButtons = None		# function to redraw menu, exposed here for appUtils
formattingAliases = False

##======================================================================
## file search
##======================================================================

grepWindow = None			# Tk TopWindow for file search
grepCanvas = None			# Tk Canvas for search parameters
grepPaned = None			# ttk PanedWindow for output, filesList & contextText
filesList =  None			# ScrollingListBox for displaying/selecting files found
contextText = None			# ScrollingText for displaying result context
pathEntry =  None			# OoCombobox for search paths
inclEntry =  None			# OoSelector for file types
exclEntry =  None			# OoSelector for excluded file types
textEntry =  None			# OoSelector for search string(s)
ignoreCase = None			# Tk IntVar for Checkbutton ' Ignore case'
matchAll = None				# Tk IntVar for Checkbutton ' Match all (vs any)'
subDirs = None				# Tk IntVar for Checkbutton ' Include sub-folders'
oxzFiles = None				# Tk IntVar for Checkbutton ' Include oxz files'
contextNum = None			# Tk IntVar for Spinbox '# of context lines'
contextNumBtn = None		# Tk Spinbox for context lines
treatText = None			# Tk StringVar for Radiobutton 'Treat search text as:'
findComboboxes = None		# dict of OoCombobox's
searchRunning = 'finished'	# state of File Finder

##======================================================================
## menus
##======================================================================

debugMenu = None			# class OoBarMenu instance
debugOptions = {			# Tk variables 
							# NB: most debugOptions are off until connection
	'showLog': None,		# tk.IntVar for showing 'log' messages in console
							# - a *local* option (in Debug menu to match Mac version)
	'logMsgCls': {},		# a dict of class string and tk.IntVar's
	'debugFlags': {},		# a dict of flag name and tk.IntVar's
	'wireframe': None,		# tk.IntVar for toggling wireframe graphics -> is read-only
	'showFPS': None,		#  "			"	displaying fps stats (Shift-F)
	'timeAccel': None, 		# StringVar used to query current state
	'timeAccelSlow': None, 	# StringVar for slow menu
	'timeAccelFast': None, 	# IntVar for fast menu
}
optionsMenu = None			# class OoBarMenu instance 
localOptnVars = {}			# dict of Tk variables for options menu
plistTkvars = {}			# dict of Tk variables for client settings
detailLevelVar = None		# Tk variable for detail level setting
entityDumpVar = None		# Tk variable: flag to restore Show Log if necessary
currStarSystem = None		# Tk variable w/ system name
							# - aliases re-register for each system
playerHasTarget = None		# Tk variable for result of query
ooliteMenu = None			# class OoBarMenu instance
ooliteColors = {}			# dict of colors from connection settings
fontMenu = None				# class OoBarMenu instance
fontSelect = None			# class TopWindow for selecting font face
fontSelectListBox= None		# Tk Listbox containing font names
debugConsoleMenus = []		# list of menus currently showing
	
##======================================================================
## oolite connection
##======================================================================

scriptProps = []			# list of console.script properties to avoid collision
pollingSuspended = False	# polling suspended for user commands
initStartTime = None		# timestamp for measuring startup sequence
sessionInitialized = 0		# counts stages of initialization

# these 2 are Tk variable for connection timestamp
# - both use Tk's trace for event callbacks
sessionStartTime = None		# timestamp set as property in console.script
currentSessionTime = None	# value read from console.script property

# timing delays (ms) for use with Tk's 'after' callbacks
# - user configurable via CFGFILE (for slower machines)
tkTiming = {
	'fast': 5,				# timing limit for processMessages; keep below 8 ms,
							#   Oolite's retry wait interval for lost packets
	'lazy': 40,				# timing between silent commands/failed polling
	'slow': 120,			# timing between retries of failed polling
							#   or tasks known to be time consuming
}
timedOutCmds = {}			# dict of SilentMsg namedtuple
requests = []				# list of SilentMsg's waiting to be sent to Oolite
replyPending = None			# SilentMsg sent to Oolite that has yet to respond
replyPendingTimer = None	# time when replyPending was sent
pendingMessages = []		# output buffer for colorPrint
lastCommand = None			# last command string sent to Oolite (see handleMessage)

##======================================================================
## fonts and measures
##======================================================================

OoFonts = {}				# dict of fonts used in gui
measuredWords = {}			# cached font.measure results
measuredEWords = {}			#  "       "            "    for 'emphasis' font
screenLines = None			# number of lines available in output window (bodyText)
lineSpace = None
whiteSpaceChrs = None		# dict of whitespace characters in current font

# cached font.measured char used in width calculations
spaceLen = None
eSpaceLen = None
ellipsisLen = None			# font specific length of an ellipsis (ie. '...')
zeroLen = None

# output filtering, not complete
filterMemStatsVar = None			 
colorPrintFilterREs = None	# regex's for filtering output; see dumpMemStatsLogOnly

##======================================================================
## update functions
##======================================================================

def initVars():
	global debugLogger
	debugLogger = logging.getLogger('DebugConsole')
	# noinspection PyUnresolvedReferences
	base = CurrentOptions['Settings'].get('BaseTimingMS')
	if base is not None:
		tkTiming.update({'fast': base, 
						 'lazy': base * 8,
						 'slow': base * 24})

def defaultSelectorList(widget, listTag):
	empty, parts, selections = defaultSelector(widget, listTag)
	if parts is None:
		return empty, None
	# need list of list, not list of tuple for equality test in _getAppsCfg
	return empty, [list(items) for items in zip(parts, selections)]

def defaultSelector(widget, listTag):
	parts = con.defaultConfig['History'].get(listTag)
	# some Entry's are initially empty by default (see con.defaultConfig)
	empty = listTag in ['FindExcls', 'FindSearches']
	if parts is None:
		return empty, None, None
	selections = widget.defaultSelections(len(parts))
	return empty, parts, selections

def genCharMeasures():			# compute length of special characters
	global spaceLen, ellipsisLen, zeroLen, eSpaceLen, lineSpace, whiteSpaceChrs
	font = OoFonts['default']
	spaceLen = font.measure(' ')
	ellipsisLen = font.measure(con.ELLIPSIS)
	# Tk uses zeros while the rest of the world uses em's
	zeroLen = font.measure('0')
	eSpaceLen = OoFonts['emphasis'].measure(' ')
	lineSpace = OoFonts['default'].metrics('linespace')
	whiteSpaceChrs = OrderedDict({uchr:font.measure(uchr) \
						for uchr in con.UNI_WHITESPACE.values()})

def save20History(option, combo):
	if hasattr(combo, 'selectors') and combo.selectors > 0:
		items = combo.getList()
		if len(items) == 0:
			CurrentOptions['History'][option] = None
			return
		selections = combo.getAllSelections()
		if len(items) > 20:
			del items[20:]
			if selections is not None:
				del selections[20:]
			combo.setList(items, selections)
		# history = list(zip(items, selections))
		# need list of list, not list of tuple for equality test in _getAppsCfg
		history = [list(hist) for hist in zip(items, selections)]
	else:
		history = combo.getList()
		if len(history) > 20:
			del history[20:]
			combo.setList(history)
	# noinspection PyUnresolvedReferences
	CurrentOptions['History'][option] = history

##======================================================================
## debug functions
##======================================================================

# noinspection PyUnresolvedReferences,PyUnusedLocal
def setTrace():
	if con.CAGSPC:
		import debugGUI.aliases as al
		import debugGUI.appUtils as au
		import debugGUI.bitmaps as bm
		import debugGUI.buildApp as ba
		import debugGUI.cmdHistory as ch
		import debugGUI.colors as cl
		import debugGUI.config as cfg
		##import debugGUI.constants as con
		import debugGUI.debugMenu as dm
		import debugGUI.findFile as ff
		import debugGUI.fontMenu as fm
		##import debugGUI.miscUtils as mu
		import debugGUI.optionsMenu as om
		import debugGUI.plistMenu as pm
		# import debugGUI.regularExpn as rx
		##import debugGUI.stringUtils as su
		import debugGUI.style as st
		import debugGUI.widgets as wg

		self = app
		gv = sys.modules[__name__]
		settings = CurrentOptions['Settings']
		font = CurrentOptions['Font']
		colors = CurrentOptions['Colors']
		history = CurrentOptions['History']
		pdb.set_trace()

# noinspection PyUnresolvedReferences
def toggleDebugMsgs():
	current = debugLogger.getEffectiveLevel()
	if current == logging.DEBUG:
		debugLogger.setLevel(logging.WARNING)
	else:
		debugLogger.setLevel(logging.DEBUG)

##======================================================================
## application classes
##======================================================================

# format of internal messages, used for those sent to Oolite
SilentMsg = namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')

minDefaultComments = {}
def _isDefComment(sectionName, text):
	if sectionName not in minDefaultComments:
		minDefaultComments[sectionName] = ''.join(su.removeWS(cmt)
					for comments in con.defaultComments[sectionName].values()
							for cmt in comments)
	defComments = minDefaultComments[sectionName]
	if len(defComments):
		if su.removeWS(text) in defComments:
			return True
	return False

class Section(object):
	def __init__(self, name, location):
		self.name = name
		self.location = location
		self.options = {}
		self.comments =[]

	# noinspection PyUnusedLocal
	def addComment(self, text, offset=None): # offset here to match Alias method
		if not _isDefComment(self.name, text):
			self.comments.append(text)

	def addOption(self, name, value):
		# value is an Option instance for all settings except aliases
		# which are Alias instances
		self.options[name] = value

	# emulate dictionary

	def get(self, key, default=None):
		if key not in self.options:
			return default
		return self.__getitem__(key)

	def set(self, key, value):
		self.__setitem__(key, value)

	def __getitem__(self, key):
		if key not in self.options:
			raise KeyError('key {!r} not in options'.format(key))
		return self.options[key].value

	def __setitem__(self, key, value):
		if key not in self.options:
			self.options[key] = Option(self.name, key, value, None)
		else:
			self.options[key].value = value

	def __delitem__(self, key):
		if key not in self.options:
			raise KeyError('key {!r} not in options'.format(key))
		del self.options[key]

	def __iter__(self):
		for key in self.options.keys():
			yield key

	def __reversed__(self):
		for key in reversed(self.options.keys()):
			yield key

	def clear(self):
		self.options.clear()

	def keys(self):
		return self.options.keys()

	def values(self):
		return [val.value for val in self.options.values()]

	def items(self):
		return [(key, val) for key, val in self.options.items()]

	def iterkeys(self):
		for key in self.options.keys():
			yield key

	def itervalues(self):
		for val in self.options.values():
			yield val

	def iteritems(self):
		for key, val in self.options.items():
			yield key, val

	__marker = object()

	def pop(self, key, default=__marker):
		if key in self.options:
			result = self.options[key]
			del self.options[key]
			return result
		if default is self.__marker:
			raise KeyError(key)
		return default

	def setdefault(self, key, default=None):
		if key in self.options:
			return self.options[key]
		self.options[key] = default
		return default

	def popitem(self, last=True):
		if len(self.options) == 0:
			raise KeyError('options is empty')
		key = next(reversed(self.options) if last else iter(self.options))
		value = self.options.pop(key)
		return key, value

	def copy(self):
		return self.options.copy()

	def __repr__(self):
		rpt = 'Section({!r}) starts at {}, has {} options and {} comments\n'.format(
					self.name, self.location, len(self.options), len(self.comments))
		for text in self.comments:
			rpt += '  comment: {}\n'.format(text)
		for value in self.options.values():
			rpt += repr(value) + con.NL
		return rpt

# ConfigFile{section} -> Section	<----------------\
#							.options{} -> Option	  \
#							.comments[]		.section--/
#											.comments[]

class Option(object):
	def __init__(self, section, name, value, location): ### ?need to add section name
		self.section = section
		self.name = name
		self.value = value
		self.location = location
		self.comments = []

	# noinspection PyUnusedLocal
	def addComment(self, text, offset=None): # offset here to match Alias method
		if not _isDefComment(self.section.name, text):
			self.comments.append(text)

	def __repr__(self):
		rpt = '  Option({!r}) starts at {} and {} comments\n'.format(
					self.name, self.location, len(self.comments))
		rpt += '    value: {!r}\n'.format(self.value)
		for text in self.comments:
			rpt += '  comment: {!r}\n'.format(text)
		return rpt

# noinspection PyAttributeOutsideInit
class Alias(object):			# OrderedDict members
	defaultFont = None
	disabledFont = None

	def __init__(self, name, location=-1):
		self.name = name		# short string as designator
		self.location = location# position in CFGFILE when read
		self.edited = False		# flag for whether contents changed (preserve loaded version)
		self.match = None		# regex match
		self.type = None		# 'func' for functions, 'iife' for iife's otherwise remains None
		self.inMenu = False		# flag for whether alias is a menu button (cannot rely on .button being None,
								#   as it may not be created yet or is on undo stack)
		self.button = None		# Button widget if assigned to menubar push buttons
		self.comments = []		# comments preserved when CFGFILE is read
		self.polled = None		# boolean for inclusion into polling queue (NB: None => user yet to assign)
		self.pollRead = False	# polled when read (if it's only .edited, preserve original formatting)
		self.pollLead = ' '		# comment/whitespace before polling, after ':=' (fnLead is caught in .match)
								# - we insist on a minimum 1 space separation on output
		self.commentSpans = []	# list of tuple of spans (start, end, hasNL, kind, # of tokens, # of code tokens)
								#   for ENDLINE_CMT_RE, INLINE_CMT_RE
								#   where hasNl is a bool, kind is in ['inline', 'eol']
		self._defn = ''			# definition, gets assigned to a property of console.script
		self.tokenSpans = []	# (start, end) for tokens in .defn, split using JS_ADDED_CHARS, not whitespace
								# - created after stripping out all comments
								# - used for comment positioning after JS's .toString, which
								#   may insert/delete characters in JS_ADDED_CHARS
		self.resetDefn()
		self.resetPoll()
		self.resetFunc()
		self.resetIIFE()

	def getDefn(self):
		return self._defn

	def setDefn(self, value):
		self.delDefn()
		self._defn = value
		_, spans = su.generateCommentSpans(self._defn)
		self.commentSpans.extend(spans)
		self.parseDefn()
		if formattingAliases:
			self.makeCmtsBySpan()
		self.tokenSpans.extend(su.createTokenSpans(value, strip_JS=True))

	def delDefn(self):
		self._defn = ''
		del self.commentSpans[:]
		del self.tokenSpans[:]

	defn = property(getDefn, setDefn, delDefn,
				'alias definition, is assigned to a property of console.script')

	def resetDefn(self):		# after an edit or formatting .toString, reset attributes that need updating
		del self.defn
		self.value = ''			# last polled result from evaluating defn
		self.readOffset = -1	# when reading CFGFILE, # char.s to skip over polling and/or iife's '('
								# - needed for correct comment .offset values (see cfgAddAliasComment)
								# - also used to tell if alias is new (ie. not read)

	def resetPoll(self):		# reset for initial polling (eg. enter new system)
		self.register = con.ALIAS_UNREGISTERED	# last polling result
		self.pollTime = -1		# timestamp to detect time-outs
		self.failures = 0		# counter used set .register to ALIAS_INVALID (3 strike rule)
		self.updateBtnState()

	def resetFunc(self):		# reset attributes when no longer a function
		self.match = None		# regex match object from FUNCTION_RE
		self.value = ''

	def resetIIFE(self):		# reset attributes when no longer an iife
		self.match = None		# regex match object from IIFE_RE
		self.iifeArgs = ''		# 'iifeArgs' from regex match object from IIFE_RE
								# - when formatting, Oolite returns .toString of the function, so
								#   must be stored separately to reconstruct
		self.iifeArgsSpan = None# position when read (match.span())
		self.value = ''

	def addComment(self, text, offset=None, tag=None):
		comment = AliasComment(self, offset, text, tag)
		self.comments.append(comment)
		if tag == 'iifeArgs' and formattingAliases:
			# remove comment from .iifeArgs to avoid duplication when rebuilding
			found = self.iifeArgs.find(text)
			if -1 < found:
				self.iifeArgs = self.iifeArgs[:found] \
							  + self.iifeArgs[found + len(text):]
		# spans for each token to ensure identification
		comment.tokenSpans = su.createTokenSpans(text, offset, strip_JS=True)

	def makeCmtsBySpan(self):
		"""create AliasComment instances using 'self's .commentSpans"""
	
		try:
			del self.comments[:]
			# setup for assigning tags to comments
			if self.type == 'func':
				tags = rx.FUNCTION_CMTS
			elif self.type == 'iife':
				tags = rx.IIFE_CMTS
			else:
				tags = rx.ALIAS_CMTS
			tagged = [(self.match.start(tag), self.match.end(tag), tag) for tag in tags
						if self.match[tag] and len(self.match[tag]) > 0]
			# use self.commentSpans to instantiate AliasComment's
			for start, end, hasNL, kind, allTokens, codeTokens in self.commentSpans:
				tag = [tag for tagStart, tagEnd, tag in tagged
					   if tagStart <= start < tagEnd]
				hasTag = tag[0] if len(tag) else None
				text = self.defn[start:end]
	
				if self.type == 'func' and hasTag == 'fnTail' \
						and text == con.NL:
					continue		# no need to carry final NL char
				if self.type == 'iife' and hasTag == 'postArgs' \
						and text == con.NL:
					continue		# no need to carry final NL char
				self.addComment(text, start, hasTag)
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	def parseDefn(self):
		try:
			# need to differentiate between an iife that .toString returns as a
			# function and a user changing an iife to a function
			#  - .type remembers what it was and resetFunc/resetIIFE are
			#     called if it should change
			while True:
				match = rx.IIFE_RE.match(self.defn)
				if match:
					if self.type == 'func':
						# user switched from function -> iife; property gets reused
						self.resetFunc()
					self.type = 'iife'
					self.match = match
					self.iifeArgs = match['iifeArgs']
					self.iifeArgsSpan = match.span('iifeArgs')
					break
				match = rx.FUNCTION_RE.match(self.defn)
				if match:
					if self.type == 'iife':
						# user switched from iife -> function,
						# remove IIFE_PROPERTY_TAG property
						removeIIFEprop(self.name)
						self.resetIIFE()
					self.type = 'func'
					self.match = match
					break
				match = rx.ALIAS_RE.match(self.defn)
				if match:
					if self.type == 'iife':
						removeIIFEprop(self.name)
						self.resetIIFE()
					elif self.type == 'func':
						self.resetFunc()
					self.type = None
					self.match = match
					if self.polled is None:	# only set default for new defn
						self.polled = defaultPolling(self.name, self.defn)
					break
				msg = 'failed to parse alias {!r}: \n  {!r}'.format(
						self.name, self.defn)
				debugLogger.error(msg)
				if con.CAGSPC:
					print(msg)
					pdb.set_trace()
				break

		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	# def clone(self):			# clone instance exclusively for undo stack
	# 	clone = self.__class__(self.name)
	# 	for attr in self.__dict__:
	# 		if attr == 'value':
	# 			# don't save this, as undo stack can grow large as it is
	# 			setattr(clone, attr, '')
	# 			continue
	# 		value = getattr(self, attr)
	# 		if isinstance(value, (list, tuple)) or su.is_str(value):
	# 			setattr(clone, attr, value[:])
	# 		else:
	# 			setattr(clone, attr, value)
	# 	return clone

	@classmethod
	def registerFonts(cls, normal, disabled):
		cls.defaultFont = normal
		cls.disabledFont = disabled
		
	def createBtn(self, master):
		if self.button is None:
			# tooltip has to be added in aliases.py (python hierarchical imports)
			self.button = ttk.Button(master, style='alias.TButton',
									name=mu.TkName(self.name, 'aliasMenuButton'))
		return self.button # convenience return

	def configMenuBtn(self):
		if self.button is None:	
			return
		text = self.name
		# non executing buttons just insert text into cmdLine
		state = 'normal' if connectedToOolite else 'disabled'
		if self.type in ['func', 'iife']:
			if self.match['fnName'] and len(self.match['fnName']):
				text = self.match['fnName']
			state = 'normal' if self.register == con.ALIAS_REGISTERED \
							else 'disabled'
		if hasattr(self.__class__, 'defaultFont'):
			normal = self.__class__.defaultFont
			disabled = self.__class__.disabledFont
			font = disabled if state == 'disabled' else normal
			width = font.measure(text + '00') // font.measure('0')
		else:					# forgot to set fonts??
			width = max(3, len(text))
		self.button.configure(text=text, state=state, width=width)
		self.inMenu = True

	def updateBtnState(self):
		if self.button is None:
			return
		# non executing buttons just insert text into cmdLine
		state = 'normal'
		if self.type in ['func', 'iife']:
			state = 'normal' if self.register == con.ALIAS_REGISTERED \
							else 'disabled'
		self.button.configure(state=state)

	def deleteBtn(self, keep=False):
		if self.button is not None:
			# keep == True means buttom is on the undo stack
			if keep:
				print(f'*** deleteBtn, keep: {keep}, calling grid_forget on {self.button}')
				self.button.grid_forget()
				print(f'    afterwards, self.button: {self.button}')
			else:
				print(f'*** deleteBtn, keep: {keep}, calling destroy on {self.button}')
				self.button.destroy()
				self.button = None
				aliasMenuButtons.pop(self.name, None)
		self.inMenu = False

	def __repr__(self):
		try:
			rep = 'Alias({!r})'.format(self.name)
			if -1 < self.location:
				rep += '  (read at {} in {})'.format(self.location, con.CFGFILE)
			if self.defn is None or len(self.defn):
				rep += '\n    defn: {!r}'.format(self.defn)
			if len(self.value):
				rep += '\n   value: {!r}'.format(self.value)
			if self.match:
				rep += '\n    type {!r}: {!r}'.format(self.type, self.match)
			if self.iifeArgs:
				rep += '\niifeArgs: {!r}, iifeArgsSpan: {}'.format(
						self.iifeArgs, self.iifeArgsSpan)
			if len(self.comments):
				rep += '\ncomments: {!r}'.format(self.comments)
			rep += '\n  polled: {}, register: {}'.format(
					'None' if self.polled is None else self.polled,
					con.DEBUG_ALIAS[self.register])
			rep += ', pollTime: {}, pollRead: {}, failures: {}'.format(
					self.pollTime, self.pollRead, self.failures)
			rep += '\n  edited: {}, readOffset: {}, inMenu: {}'.format(
					self.edited, self.readOffset, self.inMenu)
			if self.button:
				# noinspection PyProtectedMember
				rep += ' button: {}'.format(self.button._name)
			rep += ', pollLead: {!r}'.format(self.pollLead)
			return rep
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

class AliasComment(object):
	def __init__(self, parent, offset, text, tag=None):
		self.parent = parent
		self.alias = parent.name
		self.text = text
		self.length = len(text)
		self.offset = offset
		self.tokenCount = -1		# number of JS_ADDED_CHARS tokens that precede comment
		self.tag = tag				# re group name for comments outside fn body
		self.tokenSpans = None

	def __repr__(self):
		try:
			rep = '\n   AliasComment({!r})'.format(self.alias)
			if self.tag is not None:
				rep += ', tag: {!r}'.format(self.tag)
			if self.offset is not None:
				rep += ' at offset: {!r}'.format(self.offset)
			if len(self.text):
				rep += '\n    text ({}): {!r}'.format(self.length, self.text)
			if self.tokenSpans:
				rep += '\n    tokenSpans: {}'.format(self.tokenSpans)
			return rep
		except Exception as exc:
			msg = '<<{}>>'.format(exc)
			print(exc)
			traceback.print_exc()
			pdb.set_trace()
			return msg

class Appearance(object):
	defaults = {
		'ColorMenus': (con.DEFAULT_MENU_COLOR, 
						con.DEFAULT_MENU_BACKGND ), 
		'ColorPopups': (con.DEFAULT_MENU_COLOR, 
						con.DEFAULT_MENU_BACKGND ), 
		'ColorButtons': (con.DEFAULT_WIDGET_COLOR, 
						con.DEFAULT_WIDGET_BACKGND ), 
	}
	def __init__(self, style,
				 updateStyle, updateAppColors,
				 setMenuColors, setPopupColors):
		# NB. tk, fonts, options & cascadeBitmap are locals to this
		#     module, so be wary if move class to different file
		self.tk = root
		self.style = style
		self.cascadeBitmap = OoBitmaps['triangleBitMap']
		# app functions
		self.updateStyle = updateStyle
		self.updateAppColors = updateAppColors
		self.setMenuColors = setMenuColors
		self.setPopupColors = setPopupColors

	def updateApp(self):
		self.updateBitmapColors()
		self.updateStyle()
		# update colors/bitmaps for custom Checkbutton
		self.updateCheckButtons()
		# optional colored items
		self.updateMenu()
		self.updatePopup()
		self.updateButton()
		# rest of the app
		self.updateAppColors()
		
	def usingOoColors(self):
		# return bool for app using Oolite colors vs local scheme
		if not OoSettings or len(OoSettings) == 0:
			return False		# have never connected
		if 'general-foreground-color' not in OoSettings:
			return False
		return CurrentOptions['Settings'].get('PlistOverrides', False)

	def OoliteColors(self):					
		# return a subset dict of OoSettings containing colors
		return {label: color for label, color in OoSettings.items() \
								if label.endswith('-color')}

	@staticmethod
	def cnvListColor(value):				
		# convert a list of color values (float) to list of int
		if isinstance(value[0], float):
			if any(v > 1 for v in value):
				# askcolor returns floats from 0 to 255.99609375
				return map(int, value[:3])
			elif all(v <= 1 for v in value):
				# oolite returns normalized floats
				return map(lambda x: int(x*255), value[:3])
		else:							# don't use alpha channel [3]
			return value[:3]

	@staticmethod
	def codifyColor(value): 				
		# arg can be a Tk|OO str, '#xxxxxx', list|tuple of float|int
		# return '#xxxxxx'
		if value is None: 
			return None
		if isinstance(value, (list, tuple)):
			red, green, blue = Appearance.cnvListColor(value)
			color = '#{:02x}{:02x}{:02x}'.format(red, green, blue)
			return color
		elif su.is_str(value) and len(value) > 0:
			if value[0] == '#': 		# a Tk color str
				if len(value) == 4:		# #rgb => #rrggbb as per TkLib/GetColor
					color = '#{}{}{}'.format(
							value[1] * 2, value[2] * 2, value[3] * 2)
				else:					# #rrggbb
					color = value
			else:					 	# a named color
				color = value
				ookey = value if value.endswith('Color') \
							else value + 'Color'
				if ookey in con.OOCOLORS.keys():
					color = con.OOCOLORS[ookey] 
				elif value in con.TKCOLORS.keys():
					color = con.TKCOLORS[value]
			return color
		return value

	@staticmethod
	def contrastColor(color, named):
		_PRIMARYCOLORS = {
			'black': '#000000', 'blackColor': '#000000',
			'red': '#ff0000', 'redColor': '#ff0000',
			'green': '#00ff00', 'greenColor': '#00ff00',
			'blue': '#0000ff', 'blueColor': '#0000ff',
			'cyan': '#00ffff', 'cyanColor': '#00ffff',
			'yellow': '#ffff00', 'yellowColor': '#ffff00',
			'magenta': '#ff00ff', 'magentaColor': '#ff00ff',
			'white': '#ffffff', 'whiteColor': '#ffffff',
		}

		# return a contrasting color of the given one (for menu commands)
		if named in _PRIMARYCOLORS.keys():
			return 'white' if named in ['blue', 'black'] else 'black'
		if named in _PRIMARYCOLORS.values():
			return 'white' if named in ['#0000ff', '#000000'] else 'black'
		if isinstance(color, (list, tuple)):  # [3] may be present (alpha)
			rgb = Appearance.cnvListColor(color)
		# rgb = _cnvListColor(color)
		else:
			rgb = [int(color[1:3], base=16),
				   int(color[3:5], base=16),
				   int(color[5:7], base=16)]
		average = sum(rgb) / 3
		skewed = any(a + b < c // 2 for a in rgb for b in rgb for c in rgb)
		if skewed and average > 64:
			contrast = 'black'
		else:
			# black works better in midrange, so limit white to 3/8 of range
			contrast = 'white' if average < 96 else 'black'
		return contrast
## being called twice upon connection

	def disabledColors(self, fg, bg):
		# calculate colors for 'disabled' state

		def extractChannels(color):
			channels = {'red': (1, 3), 'green': (3, 5), 'blue': (5, 7)}
			return [int(color[start:end], base=16)
					for start, end in channels.values()]

		def adjustChannels(color, adjustment):
			limiter, limit = (max, 0) if adjustment < 0 else (min, 255)
			return [limiter(channel + adjustment, limit)
					for channel in extractChannels(color)]

		def intToRGB(num):
			return '{:02x}'.format(num)

		ADJUST = 64
		fgsNum, bgsNum = self.codifyColor(fg), self.codifyColor(bg)
		fgIsBigger = int(fgsNum[1:], base=16) > int(bgsNum[1:], base=16)
		fgRGB = adjustChannels(fgsNum, -ADJUST if fgIsBigger else ADJUST)
		bgRGB = adjustChannels(bgsNum, ADJUST if fgIsBigger else -ADJUST)
		return '#{}{}{}'.format(*map(intToRGB, fgRGB)), \
			   '#{}{}{}'.format(*map(intToRGB, bgRGB))

	def updateTkOptionDb(self):					
		# update colors in Tk's option database (called in updateStyle)
		fg, bg = self.getCurrentFgBg()
		sFg, sBg = self.getSelectFgBg()
		# for widgets not in ttk (mainly for OoInfoBox)
		self.tk.option_add('*font', OoFonts['default'])
		self.tk.option_add('*background', bg)
		self.tk.option_add('*foreground', fg)
		self.tk.option_add('*selectbackground', sBg)
		self.tk.option_add('*selectforeground', sFg)
		return fg, bg, sFg, sBg

	def _lookupColors(self, tag):					
		# return foreground/background for 'tag'
		local = CurrentOptions['Colors']
		defColor = con.defaultConfig['Colors']
		fg = bg = None
		if self.usingOoColors():
			fg = OoSettings.get(tag + '-foreground-color')
			bg = OoSettings.get(tag + '-background-color')
			if fg:
				fg = Appearance.codifyColor(fg)
			if bg:
				bg = Appearance.codifyColor(bg)
		if not fg:
			fg = local.get(tag + '-foreground',
					defColor.get(tag + '-foreground', 'black'))
		if not bg:
			bg = local.get(tag + '-background',
					defColor.get(tag + '-background', 'white'))
		return fg, bg

	def getCurrentFgBg(self):						
		# return the 'general' foreground/background
		return self._lookupColors('general')

	def getSelectFgBg(self):						
		# return the 'select' foreground/background
		return self._lookupColors('select')
		
	def getOptionalColors(self, toggle):
		colored = CurrentOptions['Settings'].get(toggle, False)
		if colored:
			fg, bg = self.getCurrentFgBg()
		else:
			fg, bg = self.defaults[toggle]
		return fg, bg, colored
		
	def updateMenu(self):
		fg, bg, colored = self.getOptionalColors('ColorMenus')
		self.style.configure('OoBarMenu.TMenubutton',
								background=bg, foreground=fg)
		# menus have bitmap for cascade 
		if colored:
			self.cascadeBitmap.configure(foreground=fg, background=bg)
		else:
			dFg, dBg = self.defaults['ColorMenus'] ### switch to using system defaults
			self.cascadeBitmap.configure(foreground=dFg, background=dBg)
		self.setMenuColors()	# only Menubutton in ttk, not Menu

	def updatePopup(self):
		fg, bg, colored = self.getOptionalColors('ColorPopups')
		# scrollbars follow coloring of popup menus
		self.style.configure('Vertical.TScrollbar', background=fg, 
								arrowcolor=bg, troughcolor=bg)
		self.style.configure('Horizontal.TScrollbar', background=fg, 
								arrowcolor=bg, troughcolor=bg)
		self.setPopupColors()	# no Menu in ttk

	def updateBitmapColors(self, fg=None, bg=None):
		if fg is None:
			fg, bg = self.getCurrentFgBg()

		for name, bitmap in OoBitmaps.items():
			bitmap.configure(foreground=fg, background=bg)

	def updateCheckButtons(self):
		# turn off default gray for disabled
		fg, bg = self.getCurrentFgBg()
		fgDis, bgDis = self.disabledColors(fg, bg)
		# already done in updateBitmapColors()
		# for bitmap in ['checkedBoxBitMap', 'unCheckedBoxBitMap']:
		# 	OoBitmaps[bitmap].configure(foreground=fg, background=bg)

		default, disabled = OoFonts['default'], OoFonts['disabled']
		self.style.configure('TCheckbutton',
							 font=default, background=bg, foreground=fg)
		self.style.map('TCheckbutton',
							font=[('disabled', disabled)],
							foreground=[('disabled', fgDis)],
							background=[('disabled', bgDis)])

	def updateButton(self):
		fg, bg, colored = self.getOptionalColors('ColorButtons')
		fgDis, bgDis = self.disabledColors(fg, bg)

		# bitmaps for aliasInMenu
		for btnDict in con.ALIASINMENUTEXT.values():
			OoBitmaps[btnDict['image']].configure(foreground=fg, background=bg)
		for btnDict in con.ALIASPOLLINGTEXT.values():
			OoBitmaps[btnDict['image']].configure(foreground=fg, background=bg)

		default, disabled = OoFonts['default'], OoFonts['disabled']
		# foreground, background and disabled colors
		for style in ['TButton', 'aliasInMenu.TCheckbutton']:
			self.style.configure(style, font=default,
								background=bg, foreground=fg)
			self.style.map(style, font=[('disabled', disabled)],
						   foreground=[('disabled',
										fgDis if colored
											else con.DEFAULT_WIDGET_DISABLED)],
						   background=[('disabled', bgDis if colored else bg)])

##======================================================================
## functions common to aliaes.py and comments.py
##======================================================================

@mu.showCall
def removeIIFEprop(alias):
	if connectedToOolite:
		cmd = 'delete console.script.{}'.format(con.IIFE_PROPERTY_TAG + alias)
		app.queueSilentCmd(cmd, 'del-{}-IProp'.format(alias))

def fetchAliasText():					# retrieve definition from Text
	defn = aliasDefn.get('1.0', 'end -1c')	# Text widget always contains a con.NL, even after del!
	# convert all tabs now as .toString will
	defn = defn.expandtabs(con.CFG_TAB_LENGTH)
	return unicode(defn) if con.Python2 else defn

def defaultPolling(alias, defn=None):
	# set default based on 'system...' or 'worldScript...'
	try:
		if defn is None:
			if alias in aliases:
				defn = aliases[alias].defn
			if defn and len(defn) == 0:
				defn = fetchAliasText()
		if defn is None or len(defn) == 0:
			return False
		stripped = su.stripComments(defn)
		poll = rx.DEFAULT_POLLING_RE.match(stripped)
		if poll:
			return poll['yes'] is not None

		errmsg = 'DEFAULT_POLLING_RE for {!r} failed to match '.format(alias)
		errmsg += repr(stripped)
		if con.CAGSPC:
			print(errmsg)
			pdb.set_trace()
		else:
			debugLogger.error(errmsg)

		return False
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()
## remove dbg block
