# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
# misc functions that do NOT need any global accessed (vs appUtils)

import sys, time

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
else:
	import tkinter as tk

import pdb, traceback

import debugGUI.constants as con
import debugGUI.regularExpn as rx
import debugGUI.stringUtils as su

## polling utilities ##########################################################

def removePollFlag(match, string):# return string w/ poll flag excluded
	if match['polled'] is None:
		return string
	if match['pollLead'] is None:
		start = match.start('polled')
	else:
		start, plEnd = match.span('pollLead')
		if not string[:plEnd].isspace():
			# there's a comment before the poll flag
			start = plEnd
	exEnd = match.end('polled') if match['inMenu'] is None \
								else match.end('inMenu')
	exEnd = string.find(':', exEnd) + 1
	return string[:start] + string[exEnd:]

def parsePollFlags(obj, match): ## to be moved to mu as also used by alias editor
	if match and match['pollFlag']:
		if match['pollLead']:
			obj.pollLead = match['pollLead']
		if match['polled']:
			obj.polled = 'p' in match['polled'].lower()
		if match['inMenu']:
			obj.inMenu = len(match['inMenu']) > 0
		obj.readOffset = match.end('pollFlag')
	else:
		obj.readOffset = 0	# initialized to -1 for those not in CFGFILE
	obj.defn = match['aliasDefn']

# def stripPolling(string):
# 	pollFlag = rx.POLLING_RE.match(string)
# 	if pollFlag and pollFlag['afterPoll']:
# 		return pollFlag['afterPoll']
# 	return string.lstrip()

def pollIndices(string, start=None, end=None):
	if start is None:
		start = 0
	if end is None:
		end = len(string)
	pollFlag = rx.POLLING_RE.search(string, start, end)
	if pollFlag and pollFlag['polled']:
		return pollFlag.start('polled'), pollFlag.start('afterPoll')
	return -1, -1

## tkinter utilities ##########################################################
		
def formatMouseIndex(txt, x, y):
	return txt.index('@{},{}'.format(x-txt.winfo_rootx(), 
									y-txt.winfo_rooty()))

def parseGeometry(widget): # accepts widget or geometry string
	width = height = xOffset = yOffset = titleBar = '0'
	if su.is_str(widget):
		# geometry was passed, just parse it
		geom = widget
	else:
		widget.update_idletasks()
		geom = widget.winfo_geometry().lower()	# WxH+X+Y
		y, rooty = widget.winfo_y(), widget.winfo_rooty()
		# titleBar is not included in geometry of a toplevel
		if y < rooty and widget is widget.winfo_toplevel():
			titleBar = rooty - y
	cross, plus = geom.find('x'), geom.find('+')
	if -1 < cross < plus:						# found both
		widgetSize, xOffset, yOffset = geom.split('+')
		width, height = widgetSize.split('x')
	elif cross == -1 < plus:					# only offsets +X+Y
		start = 1 if geom[0] == '+' else 0
		xOffset, yOffset = geom[start:].split('+')
	elif plus == -1 < cross:					# no offsets WxH
		width, height = geom.split('x')
	if titleBar != '0':
		height = titleBar + int(height)
	return int(width), int(height), int(xOffset), int(yOffset)

def getAppDimns(widget):
	width, height, xOffset, yOffset = parseGeometry(widget)
	return width, height
	
def getWidgetRoot(widget):
	widget.update_idletasks()
	xRoot = widget.winfo_rootx()
	yRoot = widget.winfo_rooty()
	return xRoot, yRoot
	
def getWidgetWH(widget):
	widget.update_idletasks()
	width = widget.winfo_width()
	height = widget.winfo_height()
	return width, height
	
def getWidgetReqWH(widget):
	widget.update_idletasks()
	width = widget.winfo_reqwidth()
	height = widget.winfo_reqheight()
	return width, height

def addTraceTkVar(tkVar, func):			
	# func should expect args: vname1, vname2, mode (ie. *args)
	if con.Python2:
		return tkVar.trace_variable('w', func)
	else:
		return tkVar.trace_add('write', func)

def getSpinboxValue(tkVar, default):
	try:
		count = tkVar.get()
	except tk.TclError as terr:
		if 'expected floating-point number but got' in terr.args[0]:
			# user blanked Spinbox, using default
			count = default
		else:
			raise terr
	return count

def sliceBindngs(binding):
	# typical Tcl callback
	# 'if {"[2557347361152_handler %# %b %f %h %k %s %t %w %x %y %A %E %K %N %W %T %X %Y %D]" == "break"} break'
	bindList = []
	for bindStr in binding.split('\n'):
		if bindStr.startswith('if {"['):
			space = bindStr.find(' ', 6) # 6 = len('if {"[')
			if -1 < space:
				bindStr = bindStr[6:space]
		bindList.append(bindStr)
	return bindList

def prtBindng(widget, sequence, prefix=''):
	print(prefix, sequence, sliceBindngs(widget.bind(sequence)))


# noinspection PyUnresolvedReferences,PyProtectedMember
def unbindAdded(sequence, widget, funcID):
	# adapted from https://stackoverflow.com/a/41422642

	# widget.unbind(sequence, funcID)
	# tkinter's unbind function does not use its funcid parameter when
	# altering the binding; it just wipes them all. (funcid is only used
	# to delete the Tcl cmd built from you event handler)
	# .unbind(): self.tk.call('bind', self._w, sequence, '')
	# Tcl doc: "If script is an empty string then the current binding for
	#           sequence is destroyed, leaving sequence unbound"
	# Here, we preserve any other bindings and only remove the
	# one we want removed

	try:
		currFuncs = widget.tk.call('bind', widget._w, sequence, None)
		bindings = sliceBindngs(currFuncs)
		replFuncs = [func for func in bindings if len(func) and func != funcID]
		# len(func) will remove empty strings which will accumulate (Tcl bug)

		# print('\nmu.unbindAdded, sequence: {}, widget: {}, funcID: {}'.format(sequence, widget._name, funcID))
		# prtBindng(widget, sequence, 'currFuncs')

		if len(currFuncs) == len(replFuncs) > 0:
			print('mu.unbindAdded, widget {!r}, {!r}, funcID {!r} not found'.format(
				widget._name, sequence, funcID))
			pdb.set_trace()

		widget.tk.call('bind', widget._w, sequence, '\n'.join(replFuncs))

		# prtBindng(widget, sequence, 'after bind')

		try:
			widget.deletecommand(funcID)
			# prtBindng(widget, sequence, ' after del')
			return
		except AttributeError as att:
			# AttributeError: 'NoneType' object has no attribute 'remove'
			# - if func is not .register() for this widget, as is done for
			#   validation commands, _tclCommands may be None!
			#   ie. tkinter assumes all bound cmds are registered and does not
			#       check/trap the case where _tclCommands is None
			print('unbindAdded, Yikes!!! deletecommand threw an AttributeError\n\t', att)
			if widget._tclCommands is not None:
				# different AttributeError
				raise att
			# widget.tk.deletecommand(funcID) # performed before exception was thrown
			if funcID in widget._tclCommands:
				widget._tclCommands.remove(funcID)

			### for debug
				prtBindng(widget, sequence, 'after del')
			else:
				print('mu.unbindAdded, {!r} is missing from {}._tclCommands:'.format(
					funcID, widget._name), widget._tclCommands)

			print(att)
			traceback.print_exc()
			pdb.set_trace()
			###

	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

_widgetNames = {}
# NB: when supplying widget names, it is essential they are never duplicated
#     otherwise Tk will REPLACE existing widget with same name
def TkName(name, suffix='', suffix2=''):
	def fmtNextName(idStr, idCount):
		# return name with num incremented
		return '{}{}{}'.format(idStr, '' \
				if widget[-1] == USCORE \
				else USCORE, idCount + 1)

	def splitCount(string):				
		# split name from count (# after last USCORE)
		if USCORE in string and string[-1] != USCORE:
			idx = string.rfind(USCORE)
			idStr, idCount = string[:idx], string[idx + 1:]
			if idCount.isdigit():
				return idStr, int(idCount)
		return string, ''

	USCORE = '_'
	name = str(name)
	# names cannot start with underscore
	while name[0] == USCORE:
		name = name[1:]
	# Tk requires widget name to start lowercase
	widget = '{}{}{}'.format(
				name[:1].lower() + name[1:] if len(name) else 'ooDbg',
				USCORE + str(suffix) if suffix else '',
				USCORE + str(suffix2) if suffix2 else '')
	# Tk allows no spaces in widget name, lose punctuation to be safe
	for ch in ''' ~`!@#$%^&*()-+={}[]|\:;"'<>,.?/\t\n''':
		if ch in name:
			name = name.replace(ch, '')
	# widget names must be unique, as that's how there accessed
	# (app gets weird if names are duplicated!)
	count = 1
	while widget in _widgetNames:
		leader, num = splitCount(widget)
		if isinstance(num, int):
			while widget in _widgetNames:
				widget = fmtNextName(leader, num)
				_, _ = splitCount(widget)
				break
		else:
			widget = fmtNextName(widget, count)
			count += 1
	_widgetNames[widget] = True
	return widget

## misc. utilities ############################################################

def runningTotal(items):
	total = 0
	for item in items:
		total += item
		yield total

def tooltipFontSize(font, size):
	font.config(size=max(size - size // 4, con.MIN_FONT_SIZE))

def timeCount():
	return time.clock() if con.Python2 else time.perf_counter()

# wrapper for timing function execution
def execTime(func):
	def wrapper(*args, **kws):
		startTime = timeCount()
		result = func(*args, **kws)
		# timeCount() reports in sec (resolution is 100 ns), cnv to millisecond
		elapsed = (timeCount() - startTime) * 1000
		errmsg = func.__name__
		errmsg += ', execution limit exceeded' if elapsed > 5 else  ', used only'
		errmsg += ': {:3.4f} ms'.format(elapsed)
		if args and len(args):
			errmsg += '    args: {}'.format(args)
		if kws and len(kws):
			errmsg += '    kws: {}'.format(kws)
		print(errmsg)
		return result
	return wrapper

def showCall(func):
	def _debug(*args, **kws):
		result = func(*args, **kws)
		print("{}(args: {}, kws: {}) -> {}".format
			  (func.__name__, args, kws, result))
		return result
	return _debug

