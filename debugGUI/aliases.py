# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, re
from collections import namedtuple
import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import ttk
else:
	import tkinter.ttk as ttk

import debugGUI.appUtils as au
import debugGUI.config as cfg
import debugGUI.comments as cmt
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.regularExpn as rx
import debugGUI.stringUtils as su
import debugGUI.widgets as wg

# life cycle of an alias

# read CFGFILE:
#     rx.ALIAS_NAME_RE (match not retained)
#     rx.POLLING_RE: Alias instantiated, poll attrs init'd (match not retained)
#
# before start listening:
#     checkJSsyntax is called in runConsole
#
# upon connection:
#     once script props received, checkLoadedAliases called
#         calls _checkAliasName, then .defn is assigned if it checks out
#			- sets .commentSpans, calls .parseDefn (sets .match, .type, etc),
#			  _makeCmtsBySpan (only if formatting) - instantiates AliasComment
# registration:
#     prepAliasForRegistration
#         creates alias string, checks it w/ checkJSsyntax
#         returns string if no error (string sent to Oolite)
#     restoreAliasDefn (return message from Oolite)
#         _rebuildComments (some may have moved due to .toString formatting)
#         checkJSsyntax (in case _rebuildComments screws up)
#         sets obj.defn
#			- sets .commentSpans, calls parseDefn (sets .match, .type, etc),
#			  _makeCmtsBySpan (only if formatting) - instantiates AliasComment
#         if NOT formatting, return from Oolite is ignored if it's not an error message
#
# after Add Btn (ie. editing):
#     newAliasAdd: _checkAliasName, _initNewAlias (if new), _checkAliasText
#     aliasAdd: _checkAliasName, _initNewAlias (if new), _checkAliasText
#         after all checks out ok, calls
#             checkJSsyntax
#         _aliasDBinsert calls
#			- sets .commentSpans, calls parseDefn (.match, .type, etc),
#			   _makeCmtsBySpan (only if formatting) - instantiates AliasComment


_AliasButton = namedtuple('AliasButton', 'alias button width')

# list of _reserved JS words for alias name validation
_reserved = [
	'abstract', 'arguments', 'await', 'boolean', 'break', 'byte', 'case',
	'catch', 'char', 'class', 'const', 'constructor', 'continue', 'debugger',
	'default', 'delete', 'do', 'double', 'else', 'enum', 'eval', 'export', 
	'extends', 'false', 'final', 'finally', 'float', 'for', 'function',  
	'goto', 'if', 'implements', 'import', 'in', 'instanceof', 'int', 
	'interface', 'let', 'long', 'native', 'new', 'null', 'package', 'private',
	'protected', 'prototype', 'public', 'return', 'short', 'static', 'super', 
	'switch', 'synchronized', 'this', 'throw', 'throws', 'transient', 'true', 
	'try', 'typeof', 'var', 'void', 'volatile', 'while', 'with', 'yield'
]

## alias variables ############################################################

class StackElement(object):
	# noinspection PyArgumentList
	def __init__(self, op, alias):
		self.op = op
		self.alias = alias
		self.clear = False
		self.obj = None
		self.defn = None
		self.prev = None		# for 'edit' only: text before edit; need both
								# to keep undo/redo traversal simple
		self.edited = False
		self.polled = None
		self.button = None
		self.inMenu = False
		self.__class__.__dict__.get(op, self._missing_method)(self)

	def _missing_method(self, repeat=None):
		raise ValueError('StackElement has no such method: {!r}'.format(self.op))

	def edit(self):
		self.obj = gv.aliases.get(self.alias)
		self._saveLiveData()
		if self.op == 'edit':
			self.prev = self.defn
			self.defn = self.obj.defn[:]
	delete = edit
	add = edit

	def nameClear(self):
		self._saveLiveData()

	def textClear(self):
		self._saveLiveData()

	def _saveLiveData(self):
		self.obj = gv.aliases.get(self.alias)
		self.defn = gv.fetchAliasText()
		self.edited = gv.aliasDefn.edit_modified()
		self.polled = _getAliasPollState(self.alias)
		self.button = gv.aliasMenuButtons.get(self.alias)

	def polled(self):
		self.obj = gv.aliases.get(self.alias)
		self.polled = self.obj.polled if self.obj else None

	def inMenu(self):
		self.obj = gv.aliases.get(self.alias)
		self.button = self.obj.button if self.obj else None
		self.inMenu = self.obj.inMenu

	def clone(self):
		# clone instance for undo as the one on the stack is converted into a redo
		clone = self.__class__(self.op, self.alias)
		for attr in self.__dict__:
			setattr(clone, attr, getattr(self, attr))
		return clone

	def __repr__(self):
		try:
			rpt = 'StackElement({!r}, {!r}): '.format(self.op, self.alias)
			if self.op == 'nameClear':
				rpt += 'clear: {}, edited: {}'.format(self.clear, self.edited)
			else:
				rpt += 'clear: {}, edited: {}, poll: {}, inMenu: {}, button: {}'.format(
						self.clear, self.edited, self.polled, self.inMenu, self.button)
			for attr in ['defn', 'prev']:
				value = getattr(self, attr)
				if value:
					rpt += f'\n        {attr} ({len(value)}): ' + su.shortText(value)
			return rpt
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

class UndoStack(object):

	def __init__(self):
		self.stack = []
		self._index = -1

	def reset(self):
		del self.stack[:]
		self._index = -1

	@property
	def pointer(self):
		"""undo stack pointer, an 'undo' decrements, a 'redo' increments"""
		if self._index >= len(self.stack):
			self._index = len(self.stack) - 1
		return self._index

	@pointer.setter
	def pointer(self, value):
		self._index = max(-1, min(value, len(self.stack) - 1))

	@property
	def stackMembers(self):
		return [item.alias for item in self.stack]

	def buttonInStack(self, alias):
		return any(item.button for item in self.stack if alias == item.alias)

	def addUndo(self, op, alias):
		# prune remaining redo's so we don't fork the undo chain
		if len(self.stack) > 0:
			self.deleteItems(self.pointer + 1, len(self.stack))
		# trim bottom of stack if stack is too large
		if len(self.stack) > con.MAX_UNDOS:
			bottomMember = self.stack[0].alias
			for idx in range(0, len(self.stack)):
				if self.stack[idx].alias != bottomMember:
					self.deleteItems(0, idx)
					break
		# check if top of stack is inverse of undo we're about to add
		# - if it is, pop off the top instead
		if len(self.stack) > 0 and self.stack[-1].alias == alias:
			if self.stack[-1].op == op and op in ['polled', 'inMenu',]:
				_ = self.stack.pop()
				return
		self.stack.append(StackElement(op, alias))
		self.pointer = len(self.stack) - 1

	def deleteItems(self, start, end):
		# remove subsection[start:end] of the stack, destroying any buttons
		# that appear nowhere else
		liveButtons = {item.button for idx, item in enumerate(self.stack)
						if (idx < start or idx >= end)
				   			and item.button is not None}
		deleting = [item for idx, item in enumerate(self.stack)
					if idx < start or idx >= end]
		# destroy any orphaned buttons, ie. not in use and not in remaining stack
		# (using a set as there may be multiple references)
		orphans = {item.button for item in deleting
				   if item.button and item.obj.button is None
				   		and item.button not in liveButtons}# and item.button not in gv.aliasMenuButtons}
		for button in orphans:
			button.destroy()
		del self.stack[start:end]

	flipOps = {'add': 'delete', 'edit': 'edit', 'delete': 'add'}
	def invertOp(self):
		# when an undo occurs, .pointer will move down one on the stack
		# the item passed now must be altered to become a redo
		try:
			item = self.stack[self.pointer]
			if item.op in self.flipOps:
				item.op = self.flipOps[item.op]
				if item.op == 'edit': # swap defn/prev
					item.defn, item.prev = item.prev, item.defn
					item.obj.edited, item.edited = item.edited, item.obj.edited
			elif item.op == 'nameClear':
				item.clear = not item.clear
			elif item.op == 'textClear':
				item.clear = not item.clear
				print(f'invertOp, .button is {item.button!r}')
			elif item.op == 'polled':
				item.obj.polled, item.polled = item.polled, item.obj.polled
			elif item.op == 'inMenu':
				item.obj.button, item.button = item.button, item.obj.button
				item.inMenu = not item.inMenu
			else:
				if con.CAGSPC:
					print('invertOp, undo has invalid op: {!r}'.format(item.op))
					pdb.set_trace()
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	def canUndo(self):
		# .pointer points at last op; when we undo all op's, .pointer == -1
		# index.setter ensures .pointer refers to a list item
		return -1 < self.pointer

	def undo(self):
		if self.canUndo():
			item = self.stack[self.pointer].clone()
			self.invertOp()
			self.pointer -= 1
			return item

	def canRedo(self):
		# .pointer points at last op; when we undo all op's, .pointer == -1
		# so a redo is available if there are any stack items above .pointer
		maxIdx = len(self.stack) - 1
		return self.pointer < maxIdx and maxIdx >= 0

	def redo(self):
		if self.canRedo():
			self.pointer += 1
			item = self.stack[self.pointer].clone()
			self.invertOp()
			return item

	def __repr__(self):
		try:
			if len(self.stack) == 0:
				return 'UndoStack is empty'
			rpt = 'UndoStack: len: {}, pointer: {}\n'.format(
					len(self.stack), self.pointer)
			for idx, item in enumerate(self.stack):
				rpt += ' => ' if idx == self.pointer else '    '
				rpt += '{!r}\n'.format(item)
			return rpt
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

_aliasSelected = None					# last alias selected
_undoStack = UndoStack()				# undo/redo stack, singleton
_pollQueue = []							# FIFO queue for polling aliases
_execQueue = []							# FIFO queue for polling of fn/iife 
										# (fast, once upon connection, new system)
_textIndex = None						# index in Text widget upon event

_aliasWindowOpened = False
def showAliasWindow():					# display alias frame (via Options menu)
	global _aliasWindowOpened

	alias = _aliasSelected
	if gv.aliasWindow.winfo_ismapped():
		_updateAliasButtonState(alias)
		gv.aliasWindow.lift()
		return

	gv.aliasMsgStr.set('')
	gv.aliasRegStr.set('')
	_loadAliasListBox(alias)
	if alias and alias in gv.aliases:
		_setAliasText(alias)
	_updateAliasButtonState(alias)
	gridMenuButtons()
	gv.aliasListBox.focus_set()
	if gv.aliasWindow.mouseXY:
		gv.aliasWindow.restoreTop()
	else:								# initial opening of window
		aliasPosn = None
		try:
			aliasPosn = gv.CurrentOptions['History'].get('AliasWindow', None)
			if aliasPosn is None:	# posn wrt appWindow
				width, height = mu.getWidgetReqWH(gv.aliasWindow)
				posX, posY = mu.getWidgetRoot(gv.bodyText)
				geom = '{}x{}+{}+{}'.format(width, height, posX, posY)
				gv.aliasWindow.mouseXY = [posX, posY]
			elif ',' in aliasPosn:		# old style setting
				width, height = mu.getWidgetReqWH(gv.aliasWindow)
				position = aliasPosn.strip('[]')
				posX, posY = map(int, position.split(','))
				geom = '{}x{}+{}+{}'.format(width, height, posX, posY)
				gv.aliasWindow.mouseXY = [posX, posY]
			else:
				geom = aliasPosn
				_, posX, posY = aliasPosn.split('+')
				gv.aliasWindow.mouseXY = [int(posX), int(posY)]
			gv.aliasWindow.geometry(geom)
			gv.CurrentOptions['History']['AliasWindow'] = geom
			gv.aliasWindow.restoreTop()		# uses .mouseXY if not None
			gv.aliasWindow.savePosition()	# sets .mouseXY
		except Exception as exc:
			errmsg = 'Exception: {}, aliasPosn: {}'.format(
								exc, aliasPosn)
			if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
			else:
				gv.debugLogger.exception(errmsg)
			gv.aliasWindow.center()
	# initial opening of window, set sash & init scriptProps
	if not _aliasWindowOpened:
		# initialize scriptProps if editing before ever connecting
		if not gv.connectedToOolite and len(gv.scriptProps) == 0:
			gv.scriptProps.extend(gv.aliases.keys())
		gv.root.update_idletasks()
		_aliasWindowOpened = True
		# building complete, initialize sash horizontal position
		# - had to wait until first time opened for .winfo... fns to work
		sashOffset = gv.CurrentOptions['History'].get('AliasSashOffset')
		if sashOffset is None:	# option not in CFGFILE
			gv.root.after_idle(au.initAliasSash)
		else:
			gv.root.after_idle(au.positionAliasSash, sashOffset)

def clearPollQueues():					# called in sessionCleanup
	del _pollQueue[:]
	del _execQueue[:]

## event handlers #############################################################

# (^\s+def \w+\(.*?\n)
# $1		_callStack\(\)	## callStack\n
_depthChart = []
def _callStack(forced=False):
	if not forced: return
	import inspect
	stack = inspect.stack()
	try:
		fns = [st[3] for st in stack if 'DebugConsole.py' in st[1] \
					and st[3] not in ['callStack', 'main', '<module>',]]
		if not forced and any(fn in ['setupApp', 'checkLoadedAliases', 'pollAliases',
					  # 'showAliasWindow',
					  'processSilentCmd', ] for fn in fns):
			return

		def returned():
			return prev != callers and prev.endswith(callers)

		callers = ', '.join(fns[1:])
		if len(_depthChart):
			prev, count = _depthChart[-1]
			while returned():
				_depthChart.pop()
				if len(_depthChart) == 0: break
				prev, count = _depthChart[-1]
			if not forced and prev == callers:	# another call
				repeated = '"'
				_depthChart[-1][1] += 1
				if count > 2:
					comma = callers.find(', ')
					comma = comma if -1 < comma else len(callers)
					repeated += ' (' + callers[:comma] + ', same call)'
					_depthChart[-1][1] = 0
				callers = repeated
			elif prev in callers:				# calling sub-routine
				_depthChart.append([callers, 0])
				idx = callers.index(prev)
				comma = callers.rfind(',', 0, idx)
				idx = comma if -1 < comma else idx
				callers = callers[:idx]
			else:
				_depthChart.append([callers, 0])
		else:
			_depthChart.append([callers, 0])
		msg = '{!r:>25} : {}{}'.format(fns[0],
				' . '*(len(_depthChart) - 1), callers)
		print('{}{} modified: {}'.format(msg, ' '*(80 - len(msg)),
				'True' if gv.aliasDefn.edit_modified() else 'False'))
	except Exception as exc: ## temp!!
		print(exc)
		traceback.print_exc()
		pdb.set_trace()
	finally:
		del stack

def editAlias(event=None):				# <Return> in listbox handler
										# also called by newAliasAdd & _initNewAlias
	_callStack()	## callStack
	if event and _editsPending(event.widget):
		return 'break'					# only check on event, as fn also used as utility
	txt = gv.aliasDefn
	txt.tag_remove('sel', '1.0', 'end')
	txt.mark_set('insert', 'end -2c')
	txt.xview_moveto(0)
	txt.yview_moveto(0)
	txt.focus_set()
	return 'break' 						# so default event handlers don't fire

def _aliasListVertical(direction, event):
	_callStack()	## callStack
	boxes = gv.aliasListBoxes
	box = boxes.index(event.widget) if event.widget in boxes else -1
	
	if box < 0:
		return 'break'
	index, alias = _getListboxSelection(event.widget)
	column = boxes[box]
	count = column.size()
	index = (index + direction) % count
	column.selection_clear(0, 'end')
	column.selection_set(index)
	_highlightAliasRow(alias, index)
	column.focus_set()
	column.activate(index)
	lookupAlias(event, 'Up' if direction < 0 else 'Down')

def aliasListUpArrow(event=None):		# <KeyPress-Up> handler
	_aliasListVertical(-1, event)
	return 'break'

def aliasListDownArrow(event=None): 	# <KeyPress-Down> handler
	_aliasListVertical(1, event)
	return 'break'

def _aliasListHorizontal(direction, event):
	try:
		_callStack()	## callStack
		boxes = gv.aliasListBoxes
		box = boxes.index(event.widget) if event.widget in boxes else -1
		if box < 0:
			return
		index, alias = _getListboxSelection(event.widget)
		if index is None:
		
			if event:
				print('aliasListHorizontal, event:')
				widget = None; broken = False; line = ''
				pLen = sum(len(k) + len(str(v)) + 5
						   for k, v in event.__dict__.items()
						   if k != 'widget' and v != '??')
				for _key, _value in sorted(event.__dict__.items(),
										   key=lambda x: x[0]):
					if _key == 'widget':
						# noinspection PyProtectedMember
						widget = '{} = {}'.format(_key, _value._w)
						continue
					if _value != '??':
						pair = '{} = {}'.format(_key, repr(_value)
								if su.is_str(_value) else _value)
						if not broken and len(line) + len(pair) > pLen/2: 
							broken = True
							line += '\n\t'
						line += pair + ', '
				print('\t{}\n\t{}'.format(line[:line.rfind(',')], widget))
			print('USE NEXT LINE TO STEP THRU ERROR')
			pdb.set_trace()
			_getListboxSelection(event.widget)
			
		boxes[box].selection_clear(0, 'end')
		row = boxes[(box + direction) % len(boxes)]
		row.selection_set(index)
		_highlightAliasRow(alias, index)
		row.focus_set()
		row.activate(index)
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()
##?will selection_set fire event

def aliasListLeftArrow(event=None):		# <KeyPress-Left> handler
	_aliasListHorizontal(-1, event)
	return 'break'

def aliasListRightArrow(event=None):	# <KeyPress-Right> handler
	_aliasListHorizontal(1, event)
	return 'break'

def _switchToAlias(alias):
	global _aliasSelected

	_aliasSelected = alias
	clearAliasEntry()
	_clearAliasTextBox()
	_setAliasListBoxTo(alias)
	_setAliasText(alias)

def lookupAlias(event=None, key=None):	# <<ListboxSelect>> handler
	_callStack()	## callStack
	gv.aliasMsgStr.set('')
	gv.aliasRegStr.set('')
	index, alias = _getListboxSelection(event.widget)
	if alias != _aliasSelected and _editsPending():
		_setAliasListBoxTo(_aliasSelected)
		return
	if index is not None and key in ['Up', 'Down', None]:
		if alias != _aliasSelected:
			_switchToAlias(alias)
		if key is not None:
			return 'break'
			
		# perform action only on clicks, not arrow keys
		if event.widget == gv.polledListBox:
			toggleAliasPoll()
			return 'break'
		elif event.widget == gv.inMenuListBox:
			toggleAliasInMenu()
			return 'break'
			
		if gv.connectedToOolite:
			obj = gv.aliases.get(alias)
			if obj is None:
				if con.CAGSPC:
					print(f'lookupAlias, {alias!r} is missing from gv.aliases')
					pdb.set_trace()
				return 'break'
			# noinspection PySimplifyBooleanCheck
			if obj.polled and obj.register != con.ALIAS_INVALID:
				# verify alias if it has a dynamic value
				_sendAliasRegistration(alias)
			elif obj.polled == False:
				_reportAliasStatus(alias)
		else:
			gv.aliasRegStr.set('not connected')
	return 'break'
###

def newAliasAdd(event=None):			# <Return> handler in aliasNameEntry
	_callStack()	## callStack
	if _editsPending(event.widget):	
		return 'break'
	gv.aliasRegStr.set('')
	alias = _checkAliasName()
	# noinspection PySimplifyBooleanCheck
	if alias is None:
		return 'break'
	isNew = alias not in gv.aliases
	if isNew:
		_initNewAlias(alias) # sets obj.defn from alaisDefn
	else:
		_setAliasListBoxTo(alias)
	inText = _checkAliasText(alias, isNew)
	if inText is None:
		return 'break'
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'newAliasAdd, {alias!r} is missing from gv.aliases')
			pdb.set_trace()
		return 'break'
	if len(inText) == 0:
		gv.aliasMsgStr.set('define new alias "{}"'.format(alias))
		editAlias()
	elif obj.defn != inText:
		gv.aliasMsgStr.set('editing alias "{}"'.format(alias))
		editAlias()
	return 'break'

def clearAliasEntry(event=None):		# <Escape> handler for Entry field clear
	_callStack()	## callStack
	if event:							# fn also called with no args, as utility
		alias = _fetchAliasName()
		if len(alias):
			if _haveEditsPending():
				return 'break'
			_undoStack.addUndo('nameClear', alias)
	gv.aliasNameVar.set('')
	gv.aliasNameEntry.selection_clear()
	gv.aliasNameEntry.icursor(0)
	if event:
		# noinspection PyUnboundLocalVariable
		_updateAliasButtonState(alias)
	return 'break'

_emphasizedError = False

# noinspection PyUnusedLocal
def _emphasizeLine(lineNum, offset, obj):
	global _emphasizedError
	try:
		txt = gv.aliasDefn
		error = txt.index('{}.{}'.format(lineNum, offset))
		start = txt.index('{}.0'.format(lineNum))
		end = txt.index(start + ' lineend')
		# find the start/end of text so not emphasizing whitespace
		emphStart = txt.search(r'\S', start, regexp=1, stopindex=end)
		emphStart = start if emphStart == '' else emphStart
		emphEnd = txt.search(r'\S', end, regexp=1, backwards=1, stopindex=start)
		emphEnd = end if emphEnd == '' else emphEnd
		if txt.compare(error, '<', emphStart):
			emphStart = error
		elif txt.compare(error, '>', emphEnd):
			emphEnd = error
		# exclude comment from emphasis
		hasEol =  txt.search(r'//', error, stopindex=emphEnd)
		hasInline = txt.search(r'/*', error, stopindex=emphEnd)
		if hasEol != '' and hasInline != '' and txt.compare(error, '<', hasEol) \
				and txt.compare(error, '<', hasInline):
			emphEnd = hasEol if txt.compare(hasEol, '<', hasInline) else hasInline
		elif hasEol != '' and txt.compare(error, '<', hasEol):
			emphEnd = hasEol
		elif hasInline != '' and txt.compare(error, '<', hasInline):
			emphEnd = hasInline
		hasInlineEnd = txt.search(r'*/', error, backwards=1, stopindex=emphStart)
		if hasInlineEnd != '' and txt.compare(error, '>', hasInlineEnd):
			emphStart = txt.index( hasInlineEnd + ' + 2 char')
		txt.tag_add('searchMark', emphStart, emphEnd)
		_emphasizedError = True
		# ensure line is visible
		txt.see(start)
	except Exception as exc:
		if con.CAGSPC:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

def _clearAliasTextBox():
	_callStack()	## callStack
	txt = gv.aliasDefn
	txt.tag_remove('sel', '1.0', 'end')
	txt.tag_remove('searchMark', '1.0', 'end')
	txt.delete('1.0', 'end')
	txt.edit_modified(False)
	txt.mark_set('insert', '1.0')
	gv.aliasValueVar.set('')
	setAliasPollButton()
	_setAliasToMenuButton()

def _doClearAliasText(alias): # , menuButton):
	obj = gv.aliases.get(alias)
	menuButton = obj.button if obj else None

	print(f'_doClearAliasText, {alias!r} has {"no" if menuButton is None else "a"} menu button')
	if menuButton:
		print(f'  button has state {menuButton.state() if menuButton else "nada"}')

	if obj:
		obj.defn = ''
		obj.edited = False
		obj.polled = None
		obj.button = None # is preserved in undo element
		obj.inMenu = False
		print('  alias reset, polled: {}, button: {}, inMenu: {}, '.format(
				obj.polled, obj.button, obj.inMenu))
	if menuButton is not None:
		gridMenuButtons()
		print('_doClearAliasText, calling gridMenuButtons()')
##?should we also be clearing .defn & setting .edited (text now stored in undo)

def _undoClearAliasText(undo):
	print(f'_undoClearAliasText, {undo.alias!r} has '
		  f'{"no" if undo.button is None else "a"} menu button, '
		  f'undo.inMenu: {undo.inMenu}')
	if undo.button:
		print(f'  button has state {undo.button.state()}')

	obj = gv.aliases.get(undo.alias)
	if obj:
		obj.polled = undo.polled
		obj.button = undo.button
		obj.inMenu = undo.button is not None
		if obj.inMenu:
			gv.aliasMenuButtons[undo.alias] = undo.button
		print('  alias reset, polled: {}, button: {}, inMenu: {}'.format(
				obj.polled, obj.button, obj.inMenu))
	if undo.button is not None:
		gridMenuButtons()
		print('_undoClearAliasText, calling gridMenuButtons()')
	
def clearAliasText(event=None):			# <Escape> handler for Text field clear
	_callStack()	## callStack
	if event:
		alias = _fetchAliasName()
		if len(alias):
			if _haveEditsPending():
				return 'break'
			_undoStack.addUndo('textClear', alias)
			_doClearAliasText(alias)
			_updateAliasRow(alias)
		_clearAliasTextBox()
		_updateAliasButtonState(alias, '')
	return 'break'

## widget handlers ############################################################

def toggleAliasPoll(): 					# handler for 'polled' Checkbutton,
										# <Return> in polledListBox
	_callStack()	## callStack
	alias = _fetchAliasName()
	if len(alias) == 0:
		setAliasPollButton()
		return
	if alias not in gv.aliases:
		_initNewAlias(alias) # sets obj.defn from alaisDefn
	_undoStack.addUndo('polled', alias)
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'toggleAliasPoll, {alias!r} is missing from gv.aliases')
			pdb.set_trace()
		return 'break'
	if obj.register in [con.ALIAS_INVALID, con.ALIAS_SUSPENDED]:
		# re-try registering
		toggled = _getAliasPollState(alias)
		obj.failures = con.ALIAS_POLL_RETRYS - 1
	else:
		toggled = not _getAliasPollState(alias)
	obj.polled = toggled
	setAliasPollButton(alias, toggled)
	_setAliasListValue(_aliasPolledStr(alias), gv.polledListBox, alias)
	_highlightAliasRow(alias)
	# reset registry (allow back into queue to re-examine validity)
	obj.register = con.ALIAS_UNREGISTERED
	obj.edited = True
	_updateAliasButtonState(alias)
	return 'break'

# noinspection PyUnusedLocal
def toggleAliasInMenu(event=None):		# handler for aliasAsButton Checkbutton,
										# <Return> in inMenuListBox
	_callStack()	## callStack
	alias = _fetchAliasName()
	if len(alias) == 0:
		return
	if alias not in gv.aliases:
		gv.aliasMsgStr.set('alias not registered')
		return
	_undoStack.addUndo('inMenu', alias)
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'toggleAliasInMenu, {alias!r} is missing from gv.aliases')
			pdb.set_trace()
		return 'break'
	obj.edited = True
	try:
		# buttons are stored in obj until destroyed.  They remain in obj if
		# they are on the undo/redo stack.  Are destroyed when removed from stack,
		# if they're no longer in obj
		if obj.button:
			if obj.inMenu:				# remove button if present
				gv.aliasMenuButtons.pop(alias, None)
				# don't destroy button if alias appears in undo stack
				obj.deleteBtn(keep=_undoStack.buttonInStack(alias))
			else:						# restore button
				gv.aliasMenuButtons[alias] = obj.button
				obj.inMenu = True
		else:							# create button
			if obj.register == con.ALIAS_UNREGISTERED:
				gv.aliasMsgStr.set('alias not registered')
			elif obj.register == con.ALIAS_INVALID:
				gv.aliasMsgStr.set('alias is invalid')
			_makeAliasMenuButton(alias)
		_setAliasListValue(_aliasInMenuStr(alias), gv.inMenuListBox, alias)
		_highlightAliasRow(alias)
		_setAliasToMenuButton(alias)
		gridMenuButtons()
		_updateAliasButtonState(alias)
		return 'break'
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def aliasAdd():							# handler for 'Add' button
	global _textIndex

	_callStack()	## callStack
	gv.aliasRegStr.set('')
	alias = _checkAliasName()
	# noinspection PySimplifyBooleanCheck
	if alias is None:
		return 'break'
	isNew = alias not in gv.aliases
	if isNew:
		_initNewAlias(alias) # sets obj.defn from alaisDefn
	inText = _checkAliasText(alias, isNew)
	if inText is None:
		return 'break'
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'aliasAdd, {alias!r} is missing from gv.aliases')
			pdb.set_trace()
		return 'break'
	# checkJSsyntax returns tuple/errmsg, not False
	check = cmt.checkJSsyntax(obj, inText)
	if check is not True:
		if isinstance(check, (list,tuple)):
			_, line, offset = check
			_emphasizeLine(line, offset, obj)
		return 'break'
	isNew = isNew or obj.readOffset < 0
	_textIndex = gv.aliasDefn.index('insert')
	_undoStack.addUndo('delete' if isNew else 'edit', alias)
	# make Undo button available if stack empty & get systax error
	_setAliasButtonState(alias, obj.defn)
	if inText != obj.defn:
		obj.edited = True
		obj.register = con.ALIAS_SUSPENDED
		if alias in _pollQueue:	# remove from queue
			_pollQueue.remove(alias)
	if len(inText) > 0:
		_aliasDBinsert(alias, inText, isNew)
	else: # executing a blank definition may be an attempt to delete
		msg = "{} '{}'".format('use Delete to remove' \
								if alias in gv.aliases \
								else 'define alias', alias)
		gv.aliasMsgStr.set(msg)
	_updateAliasButtonState(alias, inText)
	return 'break'

def aliasDelete(): 						# handler for 'Delete' button
	_callStack()	## callStack
	gv.aliasRegStr.set('')
	alias = _fetchAliasName()
	if len(alias) == 0:				# deleting listbox entry?
		_, alias = _getListboxSelection(gv.aliasListBox)
		# - returns None, None if nothing selected
	if alias:
		_deleteAlias(alias)

def aliasRedo():						# handler for 'Redo' button
	# safety valve for accidental Undo clicks
	# - only applies for alias edit session,
	#   ie. gets cleared when change to different alias

	print('.\nRedo Button clicked')
	print('aliasRedo, aliasDefn', _dbgInText())
	print(_undoStack)

	if not _undoStack.canRedo():
		print(f'aliasRedo, no stack, bailing')
		return
	if _haveEditsPending():
		return
	gv.aliasRegStr.set('')
	redo = _undoStack.redo()

	print('  {}-{!r}, {!r}'.format(redo.op, redo.alias,
					_dbgObjText(redo.alias) if redo.defn else 'n/a'))
	if redo.prev:
		print(f'      .prev: {su.shortText(redo.prev)}')

	aliasUndo(redo) # using this as common processing function

def _haveEditsPending():
	inEntry = _fetchAliasName()
	inText = gv.fetchAliasText()
	defnSaved = inEntry in gv.aliases and len(inText) \
				and inText == gv.aliases[inEntry].defn
	if gv.aliasDefn.edit_modified() and not defnSaved:
		msg = 'The existing alias "{}" is not saved.'.format(inEntry)
		msg += '\nRecent edits will be lost.'
		msg += '\nDo you wish to continue?'
		reply = wg.OoInfoBox(gv.root, msg, font=gv.OoFonts['default'],
							label='Overwrite?').askYesNo()
		if not reply:
			return True
		# reset modified flag to suppress usual message in _editsPending()
		gv.aliasDefn.edit_modified(False)
	return False

def _dbgInText():
	return su.shortText(gv.aliasDefn.get('1.0', 'end'))

def _dbgObjText(alias):
	obj = gv.aliases.get(alias)
	if obj is None:
		return 'alias not in db: ' + alias
	return su.shortText(obj.defn)

def aliasUndo(undo=None): 				# handler for 'Undo' button
	_callStack()	## callStack
	if undo is None:
		print('.\nUndo Button clicked')
	print('aliasUndo, aliasDefn', _dbgInText())
	print(_undoStack)

	if undo is None and not _undoStack.canUndo():
		return
	if _haveEditsPending():
		return
	gv.aliasMsgStr.set('')
	gv.aliasRegStr.set('')
	if undo is None: # normal undo vs call by aliasRedo
		undo = _undoStack.undo()
	print('  {}-{!r}, {!r}'.format(undo.op, undo.alias,
					undo.defn[:22] if undo.defn else 'n/a'))
	defn = None
	if undo.op == 'delete':
		_deleteAlias(undo.alias, isUndo=True)
	elif undo.op in ['add', 'edit']:
		_aliasUndoDelete(undo)
		defn = undo.defn
	elif undo.op == 'polled':
		if undo.alias != _aliasSelected:
			_switchToAlias(undo.alias)
		obj = gv.aliases.get(undo.alias)
		if obj:
			obj.polled = undo.polled
			_setAliasListValue(_aliasPolledStr(undo.alias),
							   gv.polledListBox, undo.alias)
			_highlightAliasRow(undo.alias)
			setAliasPollButton(undo.alias)
	elif undo.op == 'inMenu':
		if undo.alias != _aliasSelected:
			_switchToAlias(undo.alias)
		obj = gv.aliases.get(undo.alias)
		if obj:
			if not undo.inMenu:		# remove button if present
				gv.aliasMenuButtons.pop(undo.alias, None)
			elif undo.button:		# restore button if missing
				assert undo.alias not in gv.aliasMenuButtons
				gv.aliasMenuButtons[undo.alias] = undo.button
			obj.button = undo.button
			obj.inMenu = undo.inMenu
			_setAliasListValue(_aliasInMenuStr(undo.alias),
							   gv.inMenuListBox, undo.alias)
			_highlightAliasRow(undo.alias)
			_setAliasToMenuButton(undo.alias)
			gridMenuButtons()
		elif undo.alias in gv.aliasMenuButtons:
			orphan = gv.aliasMenuButtons.pop(undo.alias, None)
			if orphan:
				print('aliasUndo, found orphaned button {!r}'.format(orphan))
				pdb.set_trace()
				# orphan.destroy()
	elif undo.op == 'nameClear':
		gv.aliasNameVar.set('' if undo.clear else undo.alias)
		# if not undo.clear and undo.alias in gv.aliases:
		if undo.alias != _aliasSelected and undo.alias in gv.aliases:
			_switchToAlias(undo.alias)
	elif undo.op == 'textClear':
		if undo.clear: # redo an undone clearText -> clearText
			_doClearAliasText(undo.alias)
			_clearAliasTextBox()
		else: # undo a clearText -> re-instate what was cleared
			_undoClearAliasText(undo)
			_insertAliasText(undo.defn)
			gv.aliasMsgStr.set('"{}" restored'.format(undo.alias))
		setAliasPollButton(undo.alias)
		_setAliasToMenuButton(undo.alias)
		_updateAliasRow(undo.alias)
	gv.aliasValueVar.set('')
	_updateAliasButtonState(undo.alias, defn)

	print('aliasUndo, EXIT, aliasDefn', _dbgInText())
	print(_undoStack)

## widget validators ##########################################################

def setAliasButtonsByEntry(*args): 		# name Entry validation for button state
	_callStack()	## callStack
	action, where, what, before, after, trigger, reason, name = args
	# print('action: {}, where: {}, what: {}, before: {}, after: {}, trigger: {}, reason: {}, name: {}'.format(
		# action, where, what, before, after, trigger, reason, name))

	# this fires before Entry's are loaded (ie. when setting textvariable)
	#  so button state must be handled by the enforcer, eg. lookupAlias
	if reason == 'forced':
		return True
	gv.aliasMsgStr.set('')
	gv.aliasRegStr.set('')
	_setAliasButtonState(after, gv.fetchAliasText())
	return True		# allow all changes (validation fns must return a boolean)

_selectedText = None
def aliasTextValidate(event=None): 		# definition Text validation; capture
										# selection, set polling & button state
	global _selectedText
	_callStack()	## callStack

	# try to replicate Tkinter exception
	if event and False:	#
		print('aliasTextValidate, event:')
		widget = None; broken = False; line = ''
		pLen = sum(len(k) + len(str(v)) + 5
				   for k, v in event.__dict__.items()
				   if k != 'widget' and v != '??')
		for key, value in sorted(event.__dict__.items(),
								 key=lambda x: x[0]):
			if key == 'widget':
				# noinspection PyProtectedMember
				widget = '{} = {}'.format(key, value._w)
				continue
			if value != '??':
				pair = '{} = {}'\
					.format(key, repr(value) if su.is_str(value) else value)
				if not broken and len(line) + len(pair) > pLen/2:
					broken = True
					line += '\n\t'
				line += pair + ', '
		print('\t{}\n\t{}'.format(line[:line.rfind(',')], widget))

	if not event:
		return
	if event.type == '2':			# KeyPress; save selection as it'll be cleared before KeyRelease
		txt = gv.aliasDefn
		selection = txt.tag_ranges('sel')
		if len(selection) == 2:
			selIdx = txt.index('sel.first')
			selEndIdx = txt.index('sel.last')
			_selectedText = txt.get(selIdx, selEndIdx)
##?why is this done; it's never used
	elif event.type == '3':			# KeyRelease
		alias = _fetchAliasName()
		defn = gv.fetchAliasText()
		if alias not in gv.aliases or gv.aliases[alias].polled is None:
			# only apply default rule to alias with undefined poll state
			default = gv.defaultPolling(alias, defn) if len(defn) else None
			if alias in gv.aliases:
				gv.aliases[alias].polled = default
			setAliasPollButton(alias, default)
		_setAliasButtonState(alias, defn)
##

def _checkAliasName(alias=None):
	_callStack()	## callStack
	gv.aliasMsgStr.set('')
	if alias is None:
		alias = _fetchAliasName()
	while True:
		results = rx.VALID_ALIAS_NAME_RE.match(alias).groupdict()
		if results.get('nolen') is not None:
			gv.aliasMsgStr.set('enter an alias name')
			break
		bad1st = results.get('bad1st')
		if bad1st is not None:
			gv.aliasMsgStr.set('must start w/ $, _, or a letter, not {!r}'.format(
					','.join(bad1st)))
			break
		bad = results.get('bad')
		if bad is not None:
			gv.aliasMsgStr.set('invalid character{} {!r}'.format(
					'' if len(bad) == 1 else 's', ','.join(bad)))
			break
		if alias in _reserved:
			gv.aliasMsgStr.set('_reserved word')
			break
		if alias not in gv.aliases and alias in gv.scriptProps:
			gv.aliasMsgStr.set('{!r} already in use'.format(alias))
			gv.aliasNameVar.set('')
			break
		return alias
	gv.root.after_idle(gv.aliasNameEntry.focus_set)
	return None

def _checkAliasText(alias, isNew):
	_callStack()	## callStack
	#
	# *assuming* this is preceded by a checkAliasName call
	#
	inText = gv.fetchAliasText()
	if len(inText) == 0:
		if isNew:
			gv.aliasMsgStr.set('enter definition for {!r}'.format(alias))
			return None
		else:							# only when len==0 so don't clobber edits
			gv.aliasMsgStr.set("alias {!r} already exists".format(alias))
			gv.aliasDefn.edit_modified(False) # don't trigger warning
			_setAliasText(alias)		# restore existing alias' defn
		return None
	orig, fixed = _checkDefnQuotes(inText)
	if fixed is None:
		return orig
	if orig != fixed:
		gv.aliasMsgStr.set('all \' replaced with "')
	return fixed

def _checkDefnQuotes(defn):				# checks for unbalanced quotes, replaces
										# doubles for singles for func/IIFE
										# - if different, issue msg
	_callStack()	## callStack
	BACK_QUOTE = "`"
	SINGLE = "'"
	DOUBLE ='"'
	ESCAPED_DOUBLE = '\\"'
	stripped = su.stripComments(defn)
	if stripped.count(BACK_QUOTE) > 0:
		gv.aliasMsgStr.set('illegal `s')
		return defn, None
	double = stripped.count(DOUBLE) - stripped.count(ESCAPED_DOUBLE)
	if double % 2 != 0:
		gv.aliasMsgStr.set('unbalanced "s')
		return defn, None
	if stripped.count(SINGLE) == 0:
		return defn, defn
	return defn, _chgOuterQuotes(defn)

def _chgOuterQuotes(string):
	# need to free single quotes to submit alias (else syntax error)
	SINGLE = "'"
	DOUBLE ='"'
	ESCAPED_SINGLE = r"\'"
	# quoted = [match.span() for match in rx.QUOTED_RE.finditer(string)]
	quoted, cmtSpans = su.generateCommentSpans(string)
	# don't alter quotes in comments as never sent to Oolite
	quotes = [(qStart, qEnd) for qStart, qEnd in quoted
			  if not any(start < qStart < qEnd <= end
						 for start, end, _, _, _, _ in cmtSpans)]
	fixed = []
	lastEnd = 0
	for start, end in quotes:
		fixed.append(string[lastEnd:start])
		if string[start] == string[end- 1] == DOUBLE:
			if -1 < string.find(SINGLE, start, end):
				fixed.append(string[start:end].replace(SINGLE, ESCAPED_SINGLE))
			else:
				fixed.append(string[start:end])
		else:	#  string[start] == string[end- 1] == SINGLE:
			if -1 < string.find(DOUBLE, start, end):
				fixed.append(DOUBLE)
				fixed.append(string[start + 1:end - 1].replace(SINGLE, ESCAPED_SINGLE))
				fixed.append(DOUBLE)
			else:
				fixed.append(string[start:end].replace(SINGLE, DOUBLE))
		lastEnd = end
	fixed.append(string[lastEnd:])
	return ''.join(fixed)

def checkLoadedAliases():				# validate aliases loaded from CFGFILE
	_callStack()	## callStack OrderedDict
	msgCount = 0
	for alias, obj in list(gv.aliases.items()):
		# - using list() as _aliasDBremove alters dict
		alias = _checkAliasName(alias)
		# noinspection PySimplifyBooleanCheck
		if alias is None:
			if msgCount > 0: gv.app.colorPrint('')
			msg = 'invalid alias {!r} in {}, discarding'.format(alias, con.CFGFILE)
			gv.app.colorPrint(msg, emphasisRanges=[15, len(alias)])
			reason = gv.aliasMsgStr.get()
			gv.app.colorPrint('  reason: {}'.format(reason),
								emphasisRanges=[10,len(reason)])
			msgCount += 1
		defn = obj.defn
		if len(defn) == 0:
			if msgCount > 0: gv.app.colorPrint('')
			msg = 'missing definition for {!r} in {}'.format(alias, con.CFGFILE)
			gv.app.colorPrint(msg, emphasisRanges=[24, len(alias)])
			msgCount += 1
			continue
		orig, fixed = _checkDefnQuotes(defn)
		# noinspection PySimplifyBooleanCheck
		if fixed == False:
			if msgCount > 0: gv.app.colorPrint('')
			defn = defn if len(defn) < 60 else '{} ... {}'.format(
								defn[:25], defn[-25:])
			msg = 'invalid definition {!r} in {}, discarding\n{}'.format(
								alias, con.CFGFILE, defn)
			gv.app.colorPrint(msg, emphasisRanges=[20, len(alias)])
			reason = gv.aliasMsgStr.get()
			msg = '  reason: {}'.format(reason)
			gv.app.colorPrint(msg, emphasisRanges=[10,len(reason)])
			msgCount += 1
		elif orig != fixed:
			if msgCount > 0: gv.app.colorPrint('')
			msg = '\ndefinition of {!r} in {}, adjusted to: (quotes changed)'.format(
								alias, con.CFGFILE)
			gv.app.colorPrint(msg, emphasisRanges=[15, len(alias)])
			nls = [nl.start() for nl in re.finditer(con.NL, fixed)]
			if len(nls) > 20:
				gv.app.colorPrint('  {}'.format(fixed[:nls[10]]))
				gv.app.colorPrint(' ... (report abridged as > 20 lines)')
				gv.app.colorPrint('  {}'.format(fixed[nls[-10]:]))
			else:
				gv.app.colorPrint('  {}'.format(fixed))
			msgCount += 1
			if alias:
				obj.defn = fixed

		if alias is None or fixed is None:
			print(f'checkLoadedAliases, "{alias}", fixed: {fixed}')
			pdb.set_trace()
			_aliasDBremove(alias)

def _setAliasButtonState(alias, defn):
	global _emphasizedError
	_callStack()	## callStack
	noName = len(alias) == 0 if alias else True
	noEntry = len(defn) == 0 if defn else True
	state = ['disabled'] if noName or noEntry \
							or (alias in gv.aliases
								and gv.aliases[alias].defn == defn) \
						 else ['!disabled']
	if state == ['disabled']:
		if _emphasizedError:
			gv.aliasDefn.tag_remove('searchMark', '1.0', 'end')
			_emphasizedError = False
		gv.aliasDefn.edit_modified(False)
	gv.aliasAddBtn.state(state)

	state = ['!disabled'] if _undoStack.canRedo() else ['disabled']
	gv.aliasRedoBtn.state(state)

	state = ['!disabled'] if _undoStack.canUndo() else ['disabled']
	gv.aliasUndoBtn.state(state)

	state = ['disabled'] if noName or alias not in gv.aliases else ['!disabled']
	gv.aliasDelBtn.state(state)

	state = ['disabled'] if noName or noEntry else ['!disabled']
	gv.aliasPollCheck.state(state)

	state = ['disabled'] if noName or alias not in gv.aliases else ['!disabled']
	gv.aliasAsButton.state(state)

	if not noName:
		_setAliasToMenuButton(alias)

def _updateAliasButtonState(alias=None, defn=None):
	# sets buttons' state using listbox selection
	global _aliasSelected, _emphasizedError

	_callStack()	## callStack
	if alias != _aliasSelected:
		_aliasSelected = alias
	_setAliasButtonState(alias, gv.fetchAliasText() if defn is None else defn)
	if _emphasizedError:
		gv.aliasDefn.tag_remove('searchMark', '1.0', 'end')
		_emphasizedError = False

## listbox functions ##########################################################

def _aliasPolledStr(alias):
	obj = gv.aliases.get(alias)
	if obj is None:
		pdb.set_trace()
	return 'p' if obj.polled == True and obj.register != con.ALIAS_INVALID \
			else ''

def _aliasInMenuStr(alias):
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			pdb.set_trace()
		return ''
	return 'm' if obj.inMenu else ''

def _getListboxSelection(widget):
	_callStack()	## callStack
	currSelection = ''
	for box in gv.aliasListBoxes:
		currSelection = box.curselection()
		# - returns tuple w/ indices of the selected element(s)
		if box is widget and len(currSelection) > 0:
			break
	if len(currSelection) == 0:
		return None, None
	index = currSelection[0]
	return index, gv.aliasListBox.get(index)

def _setAliasListBoxTo(alias):
	# listbox maintenance (selection, see, activate)
	_callStack()	## callStack
	aliasList = gv.aliasListBox
	inBox = aliasList.get(0, 'end')
	index = inBox.index(alias) if alias in inBox else -1
	if -1 < index < aliasList.size():
		gv.aliasNameVar.set(alias)
		aliasList.see(index)
		aliasList.xview_moveto(0.0)
		_updateAliasRow(alias, index)

def _loadAliasListBox(alias=None):		# reloads listbox, sets/clear selection
	_callStack()	## callStack
	aliasList = gv.aliasListBox
	inMenuList, polledList = gv.inMenuListBox, gv.polledListBox
	if len(gv.aliases) == 0:
		aliasList.delete(0, 'end')
		polledList.delete(0, 'end')
		inMenuList.delete(0, 'end')
		return

	aliasData = sorted([(name, _aliasPolledStr(name), _aliasInMenuStr(name)) \
						for name in gv.aliases.keys()], key=lambda x: x[0].lower())
	# aliasData = sorted([(alias, obj.polled, obj.button is not None) \
						# for alias, obj in aliases.items()], key=lambda x: x[0].lower())
	## - WOW, this will assign values to 'alias' in Python2 but not Python3
	aliasList.setContents([name for name, _, _ in aliasData])
	polledList.delete(0, 'end')
	polledList.insert('end', *[polled for _, polled, _ in aliasData])
	inMenuList.delete(0, 'end')
	inMenuList.insert('end', *[inMenu for _, _, inMenu in aliasData])
	if alias:						# set box to current alias
		_setAliasListBoxTo(alias)
	else:
		aliasList.selection_clear(0, 'end')
		polledList.selection_clear(0, 'end')
		inMenuList.selection_clear(0, 'end')
##

def _highlightAliasRow(alias, index=-1):
	_callStack()	## callStack
	aliasList = gv.aliasListBox
	if index < 0:
		inBox = aliasList.get(0, 'end')
		index = inBox.index(alias) if alias in inBox else -1
	if -1 < index < aliasList.size():
		for box in gv.aliasListBoxes:
			box.selection_clear(0, 'end')
			box.selection_set(index)
		gv.aliasListBox.activate(index)

def _updateAliasRow(alias, index=-1):
	_callStack()	## callStack
	if index < 0:
		inBox = gv.aliasListBox.get(0, 'end')
		index = inBox.index(alias) if alias in inBox else -1
	if index < 0:	# not in list, nothing to do
		return
	obj = gv.aliases.get(alias)
	if obj:
		inMenuList, polledList = gv.inMenuListBox, gv.polledListBox
		if (polledList.get(index) == 'p') != obj.polled:
			_setAliasListValue(_aliasPolledStr(alias),
								polledList, alias, index)
		if (inMenuList.get(index) == 'm') != obj.inMenu:
			_setAliasListValue(_aliasInMenuStr(alias),
								inMenuList, alias, index)
		_highlightAliasRow(alias, index)

def _insertAliasListRow(alias):
	_callStack()	## callStack
	listRows = list(gv.aliasListBox.get(0, 'end'))
	if alias in listRows:				# performing an edit Undo
		return
	listRows.append(alias)
	listRows.sort(key=str.lower)
	index = listRows.index(alias)
	gv.aliasListBox.insert(index, alias)
	gv.polledListBox.insert(index, _aliasPolledStr(alias))
	gv.inMenuListBox.insert(index, _aliasInMenuStr(alias))
##

def _deleteAliasListRow(index):
	_callStack()	## callStack
	if -1 < index < gv.aliasListBox.size():
		gv.aliasListBox.delete(index)
		gv.polledListBox.delete(index)
		gv.inMenuListBox.delete(index)
## not restoring to menubar

def _setAliasListValue(value, alList, alias=None, index=-1):
	# change alList[index] to value
	_callStack()	## callStack
	aliasList = gv.aliasListBox
	try:
		if index < 0:
			inBox = aliasList.get(0, 'end')
			index = inBox.index(alias) if alias in inBox else -1
		if index < 0: ##
			print('setAliasListValue, value: {}, alList: {}, alias: {}, index: {}'.format(
					value, alList, alias, index))
			pdb.set_trace()
			return
		if -1 < index < aliasList.size():
			curr = alList.get(index)
			if value != curr:
				alList.delete(index)
				alList.insert(index, value)
			alList.activate(index)
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()
##

## widget functions ###########################################################

def _fetchAliasName():					# retrieve alias name from Entry
	_callStack()	## callStack
	alias = gv.aliasNameVar.get().strip()
	return unicode(alias) if con.Python2 else alias

def _editsPending(widget=None):			# display warning if edits will be lost
										# if user adds/switches alias, inserts text
	_callStack()	## callStack
	if widget is None:
		widget = gv.aliasWindow.focus_get()
	txt = gv.aliasDefn
	edited = txt.edit_modified()
	if not edited:
		return False
	inEntry = _fetchAliasName()
	inText = gv.fetchAliasText()
	_, inList = _getListboxSelection(widget)
	# - returns index, name of the currently selected list item
	#   or None, None if nothing selected
	if inList and inList != inEntry and gv.aliases[inList].defn == inText:
		return False				# inList not modified, safe to proceed
	msg = 'Your edits to {!r} have not been saved.\n'.format(inEntry)
	msg += 'Do you want to discard them?'
	discard = wg.OoInfoBox(gv.root, msg, label='Cancel changes?').askYesNo()
	if discard:
		txt.edit_modified(False)
		gv.root.after_idle(widget.focus_set)
		return False
	else:
		gv.root.after_idle(txt.focus_set)
		return True

def _insertAliasText(value):
	_callStack()	## callStack
	txt = gv.aliasDefn
	if _editsPending():
		return
	txt.delete('1.0', 'end')
	txt.insert('end', value)
	if _textIndex is not None:
		txt.mark_set('insert', _textIndex)
	txt.edit_reset()
	txt.edit_modified(False)
	au.updateAliasValueWidth()

def _setAliasText(alias):
	# sets definition Text, value Label, polling Checkbutton
	_callStack()	## callStack
	if _editsPending():
		return
	obj = gv.aliases.get(alias)
	if obj and len(obj.defn):
		_insertAliasText(obj.defn)
		_setAliasValue(alias)
		setAliasPollButton(alias)
		_setAliasToMenuButton(alias)
		_updateAliasButtonState(alias, obj.defn)
	else:
		_clearAliasTextBox()
		gv.aliasDefn.focus_set()
		_updateAliasButtonState(alias, '')

def _setAliasValue(alias):
	# formatter for display of alias value; shares measurement cache w/
	# console printer, see addWords
	_callStack()	## callStack
	if alias in gv.aliases:
		obj = gv.aliases.get(alias)
		if obj is None:
			gv.aliasValueVar.set('')
			if con.CAGSPC:
				print(f'_setAliasValue, {alias!r} is missing from gv.aliases')
				pdb.set_trace()
			return
		font = gv.OoFonts['default']
		spaceLen = gv.spaceLen
		if obj.type is None:
			value = obj.value
		else: # fn/iife have no meaningful return from registration
			value = su.stripComments(obj.defn, obj)
		value = _aliasMinify(value)
		maxWidth = gv.aliasValueWidth
		vLen = au.measurePhrase(value)
		if vLen > maxWidth:				# won't fit in value Label
			cache = gv.measuredWords
			words, trunc, width = value.split(), '', gv.ellipsisLen
			for word in words:
				if word not in cache:
					cache[word] = font.measure(word)
				wordLen = cache[word]
				if width + wordLen > maxWidth: break
				trunc += word
				width += wordLen
				if width + spaceLen > maxWidth: break
				trunc += ' '
				width += spaceLen
			gv.aliasValueVar.set(trunc.strip() + con.ELLIPSIS)
		else:
			gv.aliasValueVar.set(value)

def _initNewAlias(alias):
	_callStack()	## callStack
	obj = gv.aliases[alias] = gv.Alias(alias)
	obj.edited = True
	# default .register is ALIAS_UNREGISTERED which allows deletion w/o connection
	# ie. user edits offline and we know it's never been registered
	_insertAliasListRow(alias)
	_highlightAliasRow(alias)
	gv.aliasValueVar.set('')
	editAlias()				# move to definition box
	inText = gv.fetchAliasText()
	_updateAliasButtonState(alias, inText)
	if len(inText):
		obj.defn = inText
		gv.aliasDefn.edit_modified(True)
		obj.polled = gv.defaultPolling(alias, inText)
		setAliasPollButton(alias, obj.polled)
	else:
		setAliasPollButton()

def _aliasDBinsert(alias, defn, isNew):	# finish new alias insert or edit
	_callStack()	## callStack
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'_aliasDBinsert, {alias!r} missing from gv.aliases')
			pdb.set_trace()
		return
	obj.defn = defn
	if obj.button:						# edit may change how button acts
		_setAliasButtonCmd(alias)
	gv.aliasDefn.edit_modified(False)
	gv.aliasMsgStr.set('"{}" {}'.format(alias, 'added' if isNew else 'changed'))
	_updateAliasRow(alias)
	obj.register = con.ALIAS_UNREGISTERED
	_sendAliasRegistration(alias)

def _aliasUndoDelete(undo):		# insert previously deleted/edited alias
	_callStack()	## callStack
	try:
		alias = undo.alias
		obj = gv.aliases[alias] = undo.obj
		# these may be changed, the obj may not be up to date
		# eg. user toggles poll, alters text then deletes
		# - undoing delete restores to previous state, not previous registration
		wasEdited = obj.defn != undo.defn
		obj.defn = undo.defn
		print(f'_aliasUndoDelete, set obj.defn = {_dbgObjText(alias)}')
		obj.polled = undo.polled
		obj.button = undo.button
		obj.inMenu = undo.button is not None
		gv.aliasNameVar.set(alias)
		gv.aliasMsgStr.set('"{}" restored'.format(alias))
		_insertAliasListRow(alias)			# no op if already present
		if undo.button:
			if wasEdited:
				_setAliasButtonCmd(alias)	# undo may change how button acts
			if obj.inMenu and alias not in gv.aliasMenuButtons:
				gv.aliasMenuButtons[alias] = undo.button
			_setAliasToMenuButton(alias)
			gridMenuButtons()
		_setAliasText(alias)
		_highlightAliasRow(alias)
		obj.edited = True
		_sendAliasRegistration(alias)
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()
###

def _deleteAlias(alias, isUndo=False):
	# unregister prior to deletion / delete if never registered
	_callStack()	## callStack
	if alias and alias in gv.aliases:
		if not isUndo:
			# preserve post-registration edits in separate undo
			if gv.aliasDefn.edit_modified():
				_undoStack.addUndo('edit', alias)
				gv.aliases[alias].edited = True
			_undoStack.addUndo('add', alias)
		if gv.connectedToOolite:
			_unregisterAlias(alias)
		elif gv.aliases[alias].register == con.ALIAS_UNREGISTERED:
			_aliasDBremove(alias)# never registered during session
		else: # don't delete until can determine it's not in console.script
			gv.aliasMsgStr.set('connection required')

def _aliasDBremove(alias):				# remove alias from data base
	_callStack()	## callStack
	if _fetchAliasName() == alias:# user still has it selected
		clearAliasEntry()
		_clearAliasTextBox()
	gv.aliasMsgStr.set('"{}" deleted'.format(alias))
	obj = gv.aliases.pop(alias, None)
	if obj and obj.inMenu:
		if alias in gv.aliasMenuButtons:
			toggleAliasInMenu()
			gv.aliasMenuButtons.pop(alias, None)
		# don't destroy button if alias appears in undo stack
		obj.deleteBtn(keep=_undoStack.buttonInStack(alias))
	boxList = list(gv.aliasListBox.get(0, 'end'))
	if alias in boxList:
		index = boxList.index(alias) # one just deleted
		_deleteAliasListRow(index)
		boxList.remove(alias)
		if len(boxList) > 0:
			index = index - 1 if index > 0 else 0
			alias = boxList[index]
			_setAliasListBoxTo(alias)
			_highlightAliasRow(alias, index)
			_setAliasText(alias) # calls _updateAliasButtonState
		else:
			_updateAliasButtonState(alias, '') # '' prevents a fetchAliasText call
	else:
		_updateAliasButtonState()

## formatting #################################################################

def _aliasMinify(value):				# reduce whitespace except within quotes
	_callStack()	## callStack
	value = su.stripComments(value)
	end = 0;  reduced = []
	while True:
		quoted = rx.QUOTED_RE.search(value, end)
		if not quoted:
			break
		start = quoted.start('quoted')
		reduced.append(rx.MULTI_WS_RE.sub(' ', value[end:start]))
		end = quoted.end('quoted')
		reduced.append(value[start:end])
	reduced.append(rx.MULTI_WS_RE.sub(' ', value[end:]))
	return ''.join(reduced)

def _reformatDefn(alias, value):
	_callStack()	## callStack
	# called following registration & only when gv.formattingAliases
	# - see saveValue inside reportAliasRegistration
	# - when not formattingAliases, we strip to send and just keep .defn as is
	obj = gv.aliases.get(alias)
	if obj:
		obj.resetPoll()
		cmt.restoreAliasDefn(obj, value)

## functions/IIFEs ############################################################

# iife's are created as 2 properties:
# - <alias> has its getter set to a function that calls the iife function which
#    is stored in a second property named IIFE_PROPERTY_TAG + <alias>
def _mkIIFEObjectCmd(alias, defn):						# mk silent cmd for an iife
	_callStack()	## callStack
	obj = gv.aliases.get(alias)
	if obj is None:
		if con.CAGSPC:
			print(f'_mkIIFEObjectCmd, {alias!r} missing from gv.aliases')
			pdb.set_trace()
		return ''
	args = obj.iifeArgs
	iifeProp = con.IIFE_PROPERTY_TAG + alias
	# save the function as a hidden property and invoke using getter
	cmd = 'Object.defineProperties( console.script, { ' + alias
	cmd += ': { get: function () { return '
	cmd += 'this.{}({});'.format(iifeProp, args)
	# cmd += 'set: function (x) { '
	# cmd += 'this.{} = x;'.format(iifeProp) + ' }, '
	cmd += ' }, enumerable: false, configurable: true }, '
	# by setting enumerable to false prevents iife's fn from executing
	cmd += iifeProp + ': { value: ' + defn
	cmd += ', enumerable: true, configurable: true, writable: true } } ) '
	if gv.formattingAliases:
		cmd += '? console.script.{}.toString() : null; '.format(iifeProp)
	# else:							# don't return function's code
	# 	cmd += '? true : null; '
	return cmd

def _mkFnObjectCmd(alias, defn):		# mk silent commands for a function
	_callStack()	## callStack
	# obj = gv.aliases.get(alias)
	# if obj is None:
	# 	if con.CAGSPC:
	# 		print(f'_mkFnObjectCmd, {alias!r} missing from gv.aliases')
	# 		pdb.set_trace()
	# 	return ''
	# defn = obj.match['fnCall'] + obj.match['fnBody']
	cmd = 'Object.defineProperty( console.script, "{}", '.format(alias)
	cmd += '{{ value: {}, '.format(defn)
	cmd += 'enumerable: true, configurable: true, writable: true } ) '
	if gv.formattingAliases:
		cmd += '? console.script.{}.toString(): null; '.format(alias)
	# else:							# don't return function's code
	# 	cmd += '? true : null; '
	return cmd

## sending silent commands ####################################################

# before an alias is registered, comments are removed
# if formattingAliases and the alias is a fn/iife, successful registration
# returns the functions using .toString and any comments are restored
# @mu.showCall
def _sendAliasRegistration(alias, poll=False):
	# sends silent cmd for user & polling ('send' & 'poll')
	_callStack()	## callStack
	if not gv.connectedToOolite:
		if not poll:
			gv.aliasRegStr.set('Not connected')
		return False
	if poll: # don't poll while editing else possible SyntaxError
		if alias == _fetchAliasName() and gv.aliasDefn.edit_modified():
			return False
	else:
		gv.aliasRegStr.set('')
		gv.aliasValueVar.set('')
		if alias in _pollQueue:	# remove from queue
			_pollQueue.remove(alias)
		if alias in _execQueue:	# remove from queue
			_execQueue.remove(alias)
	if alias in gv.aliases:
		obj = gv.aliases[alias]
		defn = cmt.prepAliasForRegistration(obj, silent=poll)
		if len(defn.strip()) == 0:
			return False
		if obj.match and obj.type == 'func':
			cmd = _mkFnObjectCmd(alias, defn)
		elif obj.match and obj.type == 'iife':
			cmd = _mkIIFEObjectCmd(alias, defn)
		else:
			cmd = 'Object.defineProperty(console.script, "{}", '.format(alias)
			cmd += '{ enumerable: true, configurable: true, writable: true, '
			cmd += '  value: typeof( {0} ) == "function" ? '.format(defn)
			cmd += '{0}.bind(console) : {0}'.format(defn)
			cmd += ' }) ? console.script.'
			cmd += '{alias} : null; '.format(alias=alias)
		if len(cmd) == 0:
			return False
		gv.app.queueSilentCmd(cmd, 'alias-{}-{}'.format(
								alias, 'poll' if poll else 'send'))
		obj.register = con.ALIAS_POLLING
		obj.pollTime = mu.timeCount()
		return True
	return False

def _unregisterAlias(alias):
	# sends silent cmd to delete prop from console.script
	_callStack()	## callStack
	if alias in gv.aliases:
		if gv.connectedToOolite:
			gv.aliases[alias].register = con.ALIAS_POLLING
			if alias in _pollQueue:
				_pollQueue.remove(alias)
			if alias in _execQueue:
				_execQueue.remove(alias)
			cmd = 'delete console.script["{}"]'.format(alias)
			gv.app.queueSilentCmd(cmd, 'alias-{}-remove'.format(alias))
			if gv.aliases[alias].type == 'iife':
				gv.removeIIFEprop(alias)
		else:
			_reportOnDeletion(alias)

## reporting on silent commands ###############################################

def reportAliasRegistration(label, value):
	# processes returns from silent commands
	def saveValue(val):
		if obj.type is None:
			obj.value = val		# used in _setAliasValue to display alias' value
		elif gv.formattingAliases:
			_reformatDefn(alias, val)			# update using .toString output
		# else do nothing.  when not formattingAliases, we strip comments before
		# sending for registration but do not alter obj.defn
		obj.register = con.ALIAS_REGISTERED
		obj.configMenuBtn()

	def setInvalid():
		if gv.sessionInitialized and obj.register != con.ALIAS_INVALID:
			if obj.failures < con.ALIAS_POLL_RETRYS:
				obj.register = con.ALIAS_UNREGISTERED
			else:						# .polled == True never excluded
				obj.register = con.ALIAS_SUSPENDED if obj.polled == True \
											else con.ALIAS_INVALID
		# else: do not alter when offline
		obj.configMenuBtn()

	_callStack()	## callStack
	_, alias, op = label.split('-')
	obj = gv.aliases[alias]
	editing = _fetchAliasName()
	if op == 'send':
		# 'no result' => prop not set
		# 'undefined' => JS prop value is 'undefined'
		if value == 'undefined' or value.startswith('no result'):
			# do not delete as may be for diff oxp, still want it saved in cfg
			setInvalid()
			if alias == editing:
				if value.startswith('no result'):
					# got exception setting property (see mkCmdIIFE)
					gv.aliasMsgStr.set('invalid definition')
					gv.aliasValueVar.set('<no such property>')
				else:
					gv.aliasValueVar.set(value)
				setAliasPollButton(alias)
		else:
			saveValue(value)
			if alias == editing:
				_setAliasText(alias)
				_setAliasValue(alias)
		_reportAliasStatus(alias)
	elif op == 'poll':
		if value == 'undefined' or value.startswith('no result'):
			obj.failures += 1
			setInvalid()
		else:
			saveValue(value)
		if alias == editing:
			setAliasPollButton(alias)
	elif op == 'remove':
		if su.is_str(value) and value in ['true', 'false']:
			# value == 'false' => delete failed, so still registered
			obj.register = con.ALIAS_REGISTERED if value == 'false' \
											else con.ALIAS_UNREGISTERED
			_reportOnDeletion(alias)
	obj.pollTime = -1

def _reportAliasStatus(alias):			# report on alias insertion attempt
	_callStack()	## callStack
	if alias and alias in gv.aliases:
		status = gv.aliases[alias].register
		if status == con.ALIAS_REGISTERED:
			gv.aliasRegStr.set('registered ok')
		elif status == con.ALIAS_SUSPENDED:
			gv.aliasRegStr.set('not registered')
		elif status == con.ALIAS_INVALID:
			gv.aliasRegStr.set('cannot register')
		else:
			gv.aliasRegStr.set('unable to register')

def _reportOnDeletion(alias):			# reports on outcome of deletion attempt
	_callStack()	## callStack
	if alias in gv.aliases:				# in case it gets deleted while polling
		if gv.aliases[alias].register == con.ALIAS_UNREGISTERED:
			# delete returned false or was never registered
			if gv.connectedToOolite:
				gv.aliasRegStr.set('unregistered ok')
			_aliasDBremove(alias)
		else:
			gv.aliasRegStr.set('not unregistered')

# Object.getOwnPropertyDescriptor(console.script, 'sreset')
# Object.getOwnPropertyDescriptor(console.script, '_$_sreset')

## polling functions ##########################################################

def _getAliasPollState(alias):			# return current polling state
	_callStack()	## callStack
	pollState = None
	if alias in gv.aliases:
		pollState = gv.aliases[alias].polled
	return gv.defaultPolling(alias) if pollState is None else pollState

def _isAliasPolled(alias):				# returns current polling state (bool)
	_callStack()	## callStack
	if alias in gv.aliases:
		return gv.aliases[alias].register not in [con.ALIAS_INVALID,
												  con.ALIAS_SUSPENDED] \
				and _getAliasPollState(alias)
	else:
		return gv.defaultPolling(alias)

def setAliasPollButton(alias=None, state='empty'):
	# sets polling checkbutton and bitmap
	# default state='empty' because state can be True, False or None
	_callStack()	## callStack
	if alias and alias in gv.aliases:
		obj = gv.aliases[alias]
		if obj.register == con.ALIAS_INVALID:
			polled = False
		elif obj.register == con.ALIAS_SUSPENDED:
			if obj.failures < con.ALIAS_POLL_RETRYS:# re-trying registering
				polled = True
			else:
				polled = 'halted'
		else: # state may be None if alias not Added or no poll flag in CFGFILE
			polled = state if state != 'empty' else _isAliasPolled(alias)
		_setPollCheckBitmap(polled)
	elif state != 'empty':
		_setPollCheckBitmap(state)
	else:								# reset
		_setPollCheckBitmap(None)

def _setPollCheckBitmap(state='empty'):
	# default state='empty' because state can be True, 'halted', False or None
	_callStack()	## callStack
	key = None if state == 'empty' else state
	text = con.ALIASPOLLINGTEXT[key]['text']
	gv.aliasPollCheck.config(text=text)
	image = gv.OoBitmaps[con.ALIASPOLLINGTEXT[key]['image']]
	gv.aliasPollCheck.config(text=text, image=image)

def resetPolling():						# reset polling status of all aliases
	global _pollingReset
	_callStack()	## callStack
	for obj in gv.aliases.values():
		obj.resetPoll()
	del _pollQueue[:]
	del _execQueue[:]
	# polled first as are a one-time registration
	_pollExecutables()
	_pollingReset = True

def _pollExecutables():
	# registration of fn/iife aliases, one-time per session/system
	_callStack()	## callStack
	if gv.connectedToOolite:
		queue = _execQueue
		queue.extend(k for k, v in gv.aliases.items() \
				if v.register != con.ALIAS_INVALID \
					and v.match and v.type in ['func', 'iife'])
		while len(queue) > 0:
			_sendAliasRegistration(queue.pop(0), poll=True)

def _appWidthChanged():
	width, _ = mu.getAppDimns(gv.root)
	changed = gv.appWidth != width
	gv.appWidth = width
	return changed

_pollingReset = None
# poll of all aliases only occurs at session start or when entering a new system
# - 3 states:
#	*	'None' until session startup then 'True',
#			which triggers initial polling
# 	*	'False' when said polling is complete;
#	*	finally gridMenuButtons is called and state reset to 'None'

def pollAliases(count):
	# controls polling in batches, records time sent
	global _pollingReset
	_callStack()	## callStack
	if gv.connectedToOolite:
		queue = _pollQueue
		# noinspection PySimplifyBooleanCheck
		if _pollingReset == True: # poll ALL aliases except invalid
			queue.extend(k for k, v in gv.aliases.items() \
						if v.register != con.ALIAS_INVALID and v.type is None)
			_pollingReset = False
		elif len(queue) < count:
			# limit polling to those so flagged, excluding esp. executables
			# as polling them can interfere, esp. when changing fn <-> iife
			# noinspection PySimplifyBooleanCheck
			if _pollingReset == False:
				if _appWidthChanged():
					au.afterLoop(gv.tkTiming['slow'], 'gridMenuButtons',
								gridMenuButtons)
				_pollingReset = None
			# do not poll while editing, except when trying to clear 'halted'
			editing = None
			if gv.aliasWindow.winfo_ismapped():
				alias = _fetchAliasName()
				if alias and alias in gv.aliases:
					# alias is being viewed, don't poll
					editing = alias

			# polling limit to aliases which are
			# - not already queued
			# - not invalid
			# - not being edited
			# - not a function/iife
			# - is polled (not currently suspended & has less than max failures)
			#   or is not registered
			queue.extend(k for k, v in gv.aliases.items() \
						if k not in queue \
						and v.register != con.ALIAS_INVALID \
						and k != editing \
						and v.type is None \
						and ((v.polled == True
							  and v.register != con.ALIAS_SUSPENDED
							  and v.failures < con.ALIAS_POLL_RETRYS)
							 or v.register == con.ALIAS_UNREGISTERED))

			# when .polled == True, polling is suspended after
			# ALIAS_POLL_RETRYS failures but
			# when .polled == False, .register = ALIAS_INVALID after
			# ALIAS_POLL_RETRYS failures
			# - done to distinguish between properties which do not
			#   evaluate & can not evaluate
			#   eg. oxp not present (worldScripts.oxp is undefined)
			#       & property of said oxp

		while count > 0 and len(queue) > 0:
			alias = queue.pop(0) # FIFO
			if _sendAliasRegistration(alias, poll=True):
				count -= 1

## menubar alias buttons ######################################################

def _setAliasToMenuButton(alias=None):
	_callStack()	## callStack
	# update alias-to-menu button
	inMenu = alias is not None and alias in gv.aliasMenuButtons
	if inMenu and alias in gv.aliases:
		gv.aliases[alias].configMenuBtn()
	state = con.ALIASINMENUTEXT[inMenu]
	image = gv.OoBitmaps[state['image']]
	gv.aliasAsButton.config(text=state['text'], image=image)

def _makeAliasMenuButton(alias):		# build alias menu button
	_callStack()	## callStack
	obj = gv.aliases.get(alias)
	if obj:
		# aliasButtonFrames is also in_ gv.menubar
		gv.aliasMenuButtons[alias] = obj.createBtn(gv.menubar)
		if len(obj.comments) > 0:
			for cmt in obj.comments:
				lowText = cmt.text.lower()
				slash = lowText.find('/')
				tag = lowText.find(con.ALIAS_TOOLTIP, slash + 2)
				if -1 < tag:
					isInline = lowText.find('*', slash) == slash + 1
					tipEnd = lowText.find('*', slash + 2) if isInline else None
					msg = cmt.text[tag + len(con.ALIAS_TOOLTIP):tipEnd].strip()
					wg.ToolTip(obj.button, msg,
						gv.CurrentOptions['Settings'].get('FindToolTipDelayMS', 0),
							   allowHide=False)
					break
	_setAliasButtonCmd(alias)

def _setAliasButtonCmd(alias):			# set cmd invoked when menubar button pressed
	_callStack()	## callStack
	button = gv.aliasMenuButtons.get(alias)
	if button is None:
		return
	obj = gv.aliases.get(alias)
	if obj is None:
		return
	if obj.type and obj.match:
		label = 'btn-{}-cmd'.format(alias)
		args = obj.match['fnArgs']
		if len(args) > 0 and len(obj.iifeArgs) == 0:
			# user needs to pass args (iife may provide its own)
			# NB: must use iife's property when user has to enter args
			#     to avoid "TypeError: <alias> is not a function"
			propToCall = (con.IIFE_PROPERTY_TAG + alias) \
						  if obj.type == 'iife' else alias
			cStr = propToCall + '(  ) // <-- insert {}'.format(args)
			cmd = lambda: gv.cmdLine.insert('insert', cStr)
		else:						# execute fn/iife
			call = alias + ('()' if obj.type == 'func' else '')
			cStr = 'console.script.{}'.format(call)
			cmd = lambda: gv.app.queueImmediateCmd(cStr, label, discard=False)
			# - not discarded to trap for Exceptions
	else:
		cmd = lambda: gv.cmdLine.insert('insert', obj.defn)
	button.config(command=cmd)
	obj.configMenuBtn()

def _clearButtonFrames():
	frames = gv.aliasButtonFrames
	count, total = 0, len(frames)
	while count < total:
		for slave in frames[count].grid_slaves():
			slave.grid_forget()
		frames[count].grid_forget()
		count += 1

def _makeButtonFrame(num):
	frames = gv.aliasButtonFrames
	while len(frames) < num:				# create a new frame (will be reused))
		frames.append(ttk.Frame(gv.menubar,
								name=mu.TkName('aliasButtonFrames')))

def _gridButtonFrame(row, num):
	_callStack()	## callStack
	frame = gv.aliasButtonFrames[num]
	frame.grid_forget()
	col, span = (0, 2) if num > 0 else (1, 1)
	frame.grid(row=row, column=col, sticky='e', columnspan=span)
	# need .lower() so buttons are not hidden under frame
	# (alt: .lift() on each button gridded)
	frame.lower()
	return frame						# convenience return

_gridMenuStats = [0, 0, 0]
def gridMenuButtons():					# arrange alias buttons in menubar
	global _gridMenuStats

	def spanWidth(num):
		# noinspection PyUnresolvedReferences
		return sum(sp.width for sp in rowButtons[num]) # list of _AliasButton

	def moveToRow(src, dst):			# move from src to dst if favourable
		srcWidth, dstWidth = rowWidths[src], rowWidths[dst]
		# move 1st button if src follows dst or last button if src precedes dst
		btnW = rowButtons[src][0 if src > dst else -1].width
		# first row of buttons is shorter due to menu buttons
		maxWidth = freeWidth if dst == 0 else appWidth
		diff = srcWidth - dstWidth		# is negative if prev is bigger
		newDiff = (dstWidth + btnW) - (srcWidth - btnW)
		# - rows reversed so obvious shift is < 0
		# - only shift if difference reduced

		# if larger enough and button will fit and won't thrash
		# (ie. be undone next time)
		if (dstWidth + btnW) <= maxWidth \
					and diff > btnW and newDiff < diff:
			if src > dst:
				# can shift current row's first button backward
				rowButtons[dst].append(rowButtons[src].pop(0))
			else:
				# can shift current row's last button forward
				rowButtons[dst].insert(0, rowButtons[src].pop())
			return True
		return False

	def rowsUnbalanced():
		for idx in range(rowLen):		# check if row can shift a button
			if idx > 0:					# check previous row
				if moveToRow(idx, idx - 1):
					return True
			if idx < rowLen - 1:		# check next row
				if moveToRow(idx, idx + 1):
					return True
		return False

	_callStack()	## callStack
	au.removeAfter('gridMenuButtons')
	if len(gv.aliasMenuButtons) == 0:
		if any(bf.winfo_ismapped() for bf in gv.aliasButtonFrames):
			# wipe clean all frames from last placement
			_clearButtonFrames()
		return

	gv.root.update_idletasks()
	# not winfo_reqwidth which is way off for frames!
	appWidth = gv.app.winfo_width()
	# add up menu buttons width
	menuWidth = sum(btn.menuButton.winfo_reqwidth() \
								for btn in wg.OoBarMenu.menus)
	# calculate alias buttons width
	orderedBtns = sorted([(alias, btn, btn.winfo_reqwidth()) \
							for alias, btn in gv.aliasMenuButtons.items()],
						key=lambda x: x[0].lower())
	# add up alias buttons width
	btnWidth = sum(width for _, _, width in orderedBtns)
	freeWidth = appWidth - menuWidth
	if len(orderedBtns) == sum(len(fr.grid_slaves()) \
							for fr in gv.aliasButtonFrames):
		# same number of buttons currently gridded, check widths
		altered = any(saved != curr for saved, curr \
					  in zip(_gridMenuStats,
							[appWidth, menuWidth, btnWidth]))
		if not altered:
			# prevent flashing loop from non-sizing events (see appConfig)
			return
	_gridMenuStats = [appWidth, menuWidth, btnWidth]

	rowButtons, slack = [[]], freeWidth
	row = 0
	# fill rows not exceeding each row's free space
	for alias, button, width in orderedBtns:
		if width > slack: 			# add a row
			rowButtons.append([])
			_, slack, row = 0, appWidth, row + 1
		rowButtons[row].append(_AliasButton(alias, button, width))
		slack -= width
	if row > 0:						# balance row lengths
		rowLen = len(rowButtons)
		while True:
			rowWidths = [spanWidth(rw) for rw in range(rowLen)]
			if rowsUnbalanced():
				continue
			break

	# wipe clean all frames from last placement
	_clearButtonFrames()
	# initialize first frame
	_makeButtonFrame(1)
	inFrame = _gridButtonFrame(0, 0)
	currRow = column = 0
	# place buttons & create frames if needed
	for row, span in enumerate(rowButtons):
		if row != currRow:
			_makeButtonFrame(row + 1)
			inFrame = _gridButtonFrame(row, row)
			currRow = row
			column = 0
		for alias, button, width in span:
			button.grid_forget()
			button.grid(row=row, column=column, in_=inFrame)	# , sticky='e'
			column += 1
# gridMenuButtons is called in fontMenu & plistMenu
gv.gridMenuButtons = gridMenuButtons

def setAllMenuButtons():				# initialize all saved menubar buttons when setupApp
	_callStack()	## callStack
	inMenu = [alias for alias, obj in gv.aliases.items() if obj.inMenu]
	for alias in inMenu:
		_makeAliasMenuButton(alias)
	gridMenuButtons()
	alias = _fetchAliasName()
	_setAliasToMenuButton(alias if len(alias) > 0 else None)
	gv.root.update()

## alias error handling #######################################################

def _reportAll(message, caller):
	print('_reportAll, {}, lastCommand:'.format(caller))
	lines = gv.lastCommand.split(con.NL)
	for line in lines:
		print(line)
	print('_reportAll, {}, message:'.format(caller))
	lines = message.split(con.NL)
	for line in lines:
		print(line)

_pollErrorStarted = False
def rptAliasError(msgTag, message, appPrint=None):
	global _pollErrorStarted

	msgLabel = msgTag['label']
	_, alias, op = msgLabel.split('-')
	obj = gv.aliases.get(alias)
	if obj is None:  ###
		errmsg = 'alias {!r} not found '.format(alias)
		errmsg += 'in aliases (len: {})'.format(len(gv.alias) if gv.aliases
												else 'gv.aliases is None!')
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.error(errmsg)
	# prevent further registrations until edited
	obj.register = con.ALIAS_INVALID
	# prevent it from delaying other alias polling
	obj.pollTime = -1

	parsedErr = rx.OOLITE_ERROR_RE.match(message)

	if not parsedErr:  ###
		errmsg = 'OOLITE_ERROR_RE failed to match {!r}'.format(message)
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.error(errmsg)
	errmsg = parsedErr['type'] + ': '
	if parsedErr['line'] and len(parsedErr['line']):
		lineNum = int(parsedErr['line']) - con.DEBUG_TRY_EVAL_LINE
		for comment in obj.comments:
			endCmt = comment.offset + len(comment.text)
			if lineNum < obj.defn.count(con.NL, 0, endCmt):
				break
			if -1 < su.endsLine(obj.defn, 0, comment.offset) \
					and -1 < su.endsLine(obj.defn, comment.offset, endCmt):
				# prefix ends a line and ctext ends a line
				# startsLine/endsLine(string, start, stop)
				# return index of NL or -1 if not found
				lineNum += 1
		errmsg += 'line {}, '.format(lineNum)
	errmsg += parsedErr['error']
	# errmsg += '{}: {}\n'.format(parsedErr['error'], parsedErr['context'])
	# - useless as cites code in oolite-debug-console.js
	## ?so why is Latest.log entries correct => check source
	if op == 'poll':
		msg = ''
		if gv.sessionInitialized == 0 and not _pollErrorStarted:
			# only needed once as there's not option to reload CFGFILE (yet?)
			_pollErrorStarted = True
			msg += 'Oolite reports error(s) in {} \n'.format(con.CFGFILE)
		msg += 'for alias {!r}, \t{}'.format(alias, errmsg)
		start = msg.find(parsedErr['type'])
		if appPrint and callable(appPrint):
			appPrint(msg, emphasisRanges=[start, len(parsedErr['type'])])
		else:
			wg.OoInfoBox(gv.root, msg, font=gv.OoFonts['default'],
						 label='Alias Polling Error')
		# if con.CAGSPC:
		# 	_reportAll(message, 'rptAliasError, "poll"')
		# 	pdb.set_trace()
	elif op == 'send':
		msg = 'Oolite reports an exception for alias {!r} \n\n{}'.format(
				alias, errmsg)
		wg.OoInfoBox(gv.root, msg, font=gv.OoFonts['default'],
					 label='Alias Error')
		# if con.CAGSPC:
		# 	_reportAll(message,'rptAliasError, "send"')
		# 	pdb.set_trace()
	elif con.CAGSPC:  ##
		# print('rptAliasError, unhandled SyntaxError for op == {!r}, alias {}'.format(op, alias))
		# print('rptAliasError, internal cmd \n  {!r}'.format(gv.lastCommand))
		# print('\nrptAliasError, message: ({}), len {}'.format(msgLabel, len(gv.pendingMessages)))
		# print('rptAliasError, lastCommand:')
		_reportAll(message,'rptAliasError, not "poll" or "send"')
		# pdb.set_trace()

	# allow sendSilentCmd to resume
	gv.replyPending = gv.replyPendingTimer = None
	gv.lastCommand = None
##

