#!/bin/env -S python3 -B
# -*- coding: utf-8 -*-
#
#  DebugConsole.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#
#  GUI I/O stuff (c) 2008-2012 Kaks. CC-by-NC-SA 3
#
#  GUI stuff (c) 2019 cag CC-by-NC-SA 4
#
#  CLI arg and several other fixes (c) 2024 MrFlibble CC-by-NC-SA 4
#

"""
A gui implementation of the Oolite JavaScript debug console interface.
"""

__author__	= "Jens Ayton <jens@ayton.se>, Kaks, cag"

#__version__	= "2.08" #From this version on, will be pulling version from _version file.

from _version import __version__

import os, sys #Flibble moved this up near the top in case debug on windows without con.
FROZEN=hasattr(sys, 'frozen')
if sys.platform == 'win32' and FROZEN:
#	sys.stdout = open(os.devnull, "w");
	#This is the only "dump it where we are" Flibble investigates: Just keep the exe in a dir :-|
	sys.stderr = open(os.path.join(os.getcwd(), os.path.basename(sys.argv[0]))+"-stderr.txt", "w")
	# Send all stdout to stderr needs stderr to exist first.
	# When frozen with noconsole on 'doze, there's no stdout to begin with!
	sys.stdout = sys.stderr
	#... or it may just be that we're not going to win.

import cliArgs as dca #Flibble

##################################### 
if dca.g['debug']:
	import pdb
	from traceback import print_exc
#####################################


try:
	from sys import _MEIPASS
	HAVE_MEIPASS = True
except:
	HAVE_MEIPASS = False

from collections import OrderedDict, namedtuple
from ooliteConsoleServer import *
from twisted.internet.protocol import Factory
from twisted.internet import stdio, reactor, tksupport
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol
from pickle import load as pickle_load
from pickle import dump as pickle_dump

from re import compile
from logging import StreamHandler, basicConfig, Formatter, getLogger, shutdown, DEBUG, WARNING
from traceback import format_tb
from errno import ENOENT, ENOSPC

from platform import system as platform_system
platformIsLinux = platform_system() == 'Linux'
platformIsWindows = platform_system() == 'Windows'

#As we have parsed the command line, and dragged in constants, we know the OS
# and if not frozen, knowing the path will allow us to find our icons.
if not FROZEN:
	#Get script path (dereferenced in case symlink).
	SCRIPTPATH = os.path.dirname(os.path.realpath(__file__))


Python2 = sys.version_info[0] == 2
if Python2:
	import ConfigParser as configparser
	from Tkinter import *
	import tkFont
	import tkColorChooser as tkColor
	from time import clock, asctime
	from string import maketrans
else:
	import configparser
	from tkinter import *
	import tkinter.font as tkFont
	import tkinter.colorchooser as tkColor
	from time import perf_counter, asctime


# constants
MINIMUM_WIDTH = 600
MINIMUM_HEIGHT = 480
SCROLLER_WIDTH = 20
DEFAULT_GEOMETRY = '{}x{}+0+0'.format(MINIMUM_WIDTH, MINIMUM_HEIGHT)
DEFAULT_ALIAS_POSN = '[{}, {}]'.format(int(MINIMUM_WIDTH/8), int(MINIMUM_HEIGHT)/3) # 440 120 @ Arial 10
DEBUGGER_TITLE = 'Oolite - Javascript Debug Console ({})'.format('executable' if FROZEN else 'Python2' if Python2 else 'Python3')
GEOMETRY_RE = compile(r'(\d+)x(\d+)\+(\d+)\+(\d+)')
TRIMSECT_RE = compile(r"\[ *(?P<header>[^]]+?) *\]") # trim section names
CONNECTMSG = "Please (re)start Oolite in order to connect."

#Flibble : Adding cli args stuff with sane default paths.
BASE_FNAME = dca.g['base']
CFG_EXT = '.' + dca.g['cext']
HIST_EXT = '.' + dca.g['hext']
LOG_EXT = '.' + dca.g['lext']
LOG_PATH = dca.g['lpath']
CFG_PATH = dca.g['cpath']

CFG_BASE = os.path.join ( CFG_PATH, BASE_FNAME )
HIST_BASE = os.path.join ( LOG_PATH, BASE_FNAME )
LOG_BASE = os.path.join ( LOG_PATH, BASE_FNAME )

CFGFILE = CFG_BASE + CFG_EXT
HISTFILE = HIST_BASE + HIST_EXT
LOGFILE = LOG_BASE + LOG_EXT


MAX_HIST_CMDS = 200
MAX_HIST_SIZE = MAX_HIST_CMDS * 1000

MAX_HIST_VERSION = 3
MAX_CFG_VERSION = 3
MAX_LOG_VERSION = 5

# in seconds
CMD_TIMEOUT = 2			# elapsed time before sending next in queue (current goes in timedOutCmds)
CMD_TIMEOUT_LONG = 4	#    "  except for a couple long running cmds
CMD_TIMEOUT_ABORT = 15	#    "  when cmd is abandonded (deleted from timedOutCmds) as data considered stale

TKCOLORS = {
	'black':	'#000000',
	'red':		'#ff0000',
	'green':	'#00ff00',
	'blue':		'#0000ff',
	'cyan':		'#00ffff',
	'yellow':	'#ffff00',
	'magenta':	'#ff00ff',
	'white':	'#ffffff',
}

OOCOLORS = {
	'blackColor':		'#000000',
	'darkGrayColor':	'#555555',
	'lightGrayColor':	'#2a2a2a',
	'whiteColor':		'#ffffff',
	'grayColor':		'#808080',
	'redColor':		'#ff0000',
	'greenColor':		'#00ff00',
	'blueColor':		'#0000ff',
	'cyanColor':		'#00ffff',
	'yellowColor':	'#ffff00',
	'magentaColor':	'#ff00ff',
	'orangeColor':	'#ff8000',
	'purpleColor':	'#800080',
	'brownColor':		'#996633',
}

debugFlags = OrderedDict((
	('DEBUG_LINKED_LISTS', 		0x00000001),
	# ('UNUSED', 				0x00000002),
	('DEBUG_COLLISIONS', 		0x00000004),
	('DEBUG_DOCKING', 			0x00000008),
	('DEBUG_OCTREE_LOGGING', 	0x00000010),
	# ('UNUSED', 				0x00000020),
	('DEBUG_BOUNDING_BOXES', 	0x00000040),
	('DEBUG_OCTREE_DRAW', 		0x00000080),
	('DEBUG_DRAW_NORMALS', 		0x00000100),
	('DEBUG_NO_DUST', 			0x00000200),
	('DEBUG_NO_SHADER_FALLBACK',0x00000400),
	('DEBUG_SHADER_VALIDATION', 0x00000800),
	# Flag for temporary use, always last in list.
	# ('DEBUG_MISC', 				0x10000000),
))
allDebugFlags = sum(flag for flag in debugFlags.values())

logMessageClasses = OrderedDict((
	('General Errors', 			'general.error'),
	('Script Errors', 			'$scriptError'),
	('Script Debug', 			'$scriptDebugOn'),
	('Shader Debug', 			'$shaderDebugOn'),
	('Troubleshooting Dumps',	'$troubleShootingDump'),
	('Entity State', 			'$entityState'),
	('Data Cache Debug', 		'$dataCacheDebug'),
	('Texture Debug', 			'$textureDebug'),
	('Sound Debug', 			'$soundDebug'),
))

detailLevels = OrderedDict((
	('Minimum', 	'DETAIL_LEVEL_MINIMUM'),
	('Normal', 		'DETAIL_LEVEL_NORMAL'),
	('Shaders', 	'DETAIL_LEVEL_SHADERS'),
	('Extras', 		'DETAIL_LEVEL_EXTRAS'),
))

showConsoleForDebug = {
	'Show Console for Log Messages': 'show-console-on-log',
	'Show Console for Warnings': 'show-console-on-warning',
	'Show Console for Errors': 'show-console-on-error',
}

# these are console properties, with setter & getter fns; cannot use setConfigurationValue, as (3 of 4) values
# actually stored in private properties (eg. __dumpStackForErrors) and we'll get out of sync otherwise
persistenceMap = {
	'dump-stack-for-errors': 'dumpStackForErrors',
	'dump-stack-for-warnings': 'dumpStackForWarnings',
	'show-error-locations': 'showErrorLocations',
	'show-error-locations-during-console-eval': 'showErrorLocationsDuringConsoleEval',
}

# default configuration
defaultConfig = OrderedDict((
		  ('Settings', OrderedDict((
				('SaveConfigOnExit', 	'Yes'),
				('MsWheelHistory', 		'No'),
				('MaxHistoryCmds', 		str(MAX_HIST_CMDS)),
				('SaveHistoryOnExit', 	'Yes'),
				('Geometry', 			DEFAULT_GEOMETRY),
				('AliasWindow', 		DEFAULT_ALIAS_POSN),
				('ConsolePort', 		8563),
				('EnableShowConsole',	'Yes'),
				('MacroExpansion',		'Yes'),
				('TruncateCmdEcho',		'No'),
				('ResetCmdSizeOnRun',	'Yes'),
				('_PlistOverrides_', 	'if Yes, colors and fonts are replaced with those received from Oolite'),
				('PlistOverrides', 		'No'),
				('MaxBufferSize', 		'200000'),
		   ))
		  ),
		  ('Font', OrderedDict((
				('Family', 		'Arial'),
				('Size', 		10),
				('Weight', 		'normal'),
				('Slant', 		'roman'),
		   ))
		  ),
		  ('Colors', OrderedDict((
				('Foreground',	'yellow'),
				('Background',	'black'),
				('Command',		'cyan'),
				('Selectfg',	'black'),
				('Selectbg',	'white'),
		   ))
		  ),
		  ('Aliases', OrderedDict()
		  ),
		))

# globals
TCP_Port = None
app = None
debugLogger = None
cmdLineHandler = None 
openMessages = []

SilentMsg = namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')

class SimpleConsoleDelegate:
	__active = Active = False

	def __init__(self, protocol):
		self.protocol = protocol
		self.identityString = "DebugConsole"

	def __del__(self):
		if self.__active: self.protocol.factory.activeCount -= 1
		if cmdLineHandler.inputReceiver is self:  cmdLineHandler.inputReceiver = None

	def acceptConnection(self):
		return self.protocol.factory.activeCount < 1

	def connectionOpened(self, ooliteVersionString):
		app.colorPrint("Opened connection with Oolite version {}".format(ooliteVersionString))
		app.colorPrint('')
		app.bodyText.update_idletasks()
		app.bodyText.edit_modified(False)
		self.protocol.factory.activeCount += 1
		self.__active = self.Active = True
		cmdLineHandler.inputReceiver = self
		app.client = self.protocol

	def loadConfig(self, config):		# settings received from client; config is a dict of debugger settings
		if not app.connectedToOolite:
			app.initClientSettings(config)
		else:
			app.noteConfig(config)

	def connectionClosed(self, message):
		if message is None or isinstance(message, str):
			if message is not None and len(message) > 0:
				app.colorPrint('Connection closed: "{}"'.format(message))
			else:
				app.colorPrint("Connection closed with no message at {}.".format(asctime))
		if self.__active:
			self.protocol.factory.activeCount -= 1
			self.__active = self.Active = False
		app.tried=0
		app.client = None
		app.disableClientSettings()

	def writeToConsole(self, message, colorKey, emphasisRanges):
		app.handleMessage(message, colorKey, emphasisRanges)

	def clearConsole(self):
		app.bodyClear()

	def showConsole(self):
		if app.localOptions['EnableShowConsole']:
			if app.top.state() != 'zoomed' and app.top.state() != 'normal':
				app.top.state('normal')
			app.top.wm_attributes("-topmost", 1)
			app.top.wm_attributes("-topmost", 0)
			app.top.lift()
			app.cmdLine.focus_set()

	def send(string):
		receiveUserInput(string)

	def receiveUserInput(self, string):
		self.protocol.sendCommand(string)

	def closeConnection(self, message):
		self.protocol.closeConnection(message)
# end class SimpleConsoleDelegate

class TopWindow(Toplevel):
	def __init__(self, parent, name=True, enduring=False, showNow=True):
		Toplevel.__init__(self, parent)
		self.transient(parent)
		self.parent = parent
		self.setTitle(name)
		self.enduring = enduring
		if enduring: 					# override the 'X' from destroying window
			self.protocol('WM_DELETE_WINDOW', self.closeTop)
		self.twFrame = Frame(self)
		self.resizable(width=False, height=False)
		self.twFrame.grid()
		if showNow:
			self.focus_set()
		else:
			self.withdraw()

	def savePosition(self):
		Xoff, Yoff = self.getGeometry(self, coords=True) 
		if Xoff == 0 and Yoff == 0:	# newly minted widget, ie. never mapped
			return					# don't clobber any existing saved values
		self.mouseXY = [Xoff, Yoff]

	@classmethod
	def getGeometry(cls, widget, coords=False):
		widget.update_idletasks()
		info = widget.winfo_geometry()
		widgetSize, Xoff, Yoff = info.split('+')
		width, depth = widgetSize.split('x')
		if coords:
			return [int(Xoff), int(Yoff)]
		else:
			return [int(width), int(depth), int(Xoff), int(Yoff)]

	def center(self):
		width, depth, Xoff, Yoff = self.getGeometry(self.parent.winfo_toplevel())
		winWidth, winDepth, _, _ = self.getGeometry(self)
		winXoff = Xoff + (width>>1) - (winWidth>>1)
		winYoff = Yoff + (depth>>1) - (winDepth>>1)
		self.geometry('{}x{}+{}+{}'.format(winWidth, winDepth, winXoff, winYoff))
		self.mouseXY = [winXoff, winYoff]
		self.restoreTop()

	def showAtMouse(self, coords=None, offsetX=0, offsetY=0):
		if not hasattr(self, 'mouseXY') and coords is None:
			self.mouseXY = self.winfo_pointerxy()
		x, y = self.mouseXY if coords is None else coords
		self.mouseXY = [x + offsetX, y + offsetY]
		self.restoreTop()

	def setTitle(self, name):
		self.name = name
		if name and len(name) > 0:
			self.title(name)

	def openTop(self):
		if not hasattr(self, 'mouseXY'):
			self.showAtMouse()
		else:
			self.restoreTop()

	def restoreTop(self):
		if hasattr(self, 'mouseXY'):
			self.geometry('+{}+{}'.format(*self.mouseXY))
		self.deiconify()
		self.lift()			# required in pyinstaller version else fontSelectTop won't show (anywhere!)
		self.focus_set()

	def closeTop(self, event=None):
		if self.enduring:
			if hasattr(self, 'mouseXY'):# creation delayed until opened (closeTop may precede; see closeAnyOpenFrames)
				self.savePosition()		# preserve user's positioning of window
			self.withdraw()
		else:
			self.destroy()
		return 'break'
# end class TopWindow

class OoInfoBox(TopWindow):
	_count = 0
	def __init__(self, master, msg, font=None, destruct=None, error=False):
		OoInfoBox._count += 1
		TopWindow.__init__(self, master, name='Error' if error else 'Message', enduring=False, showNow=False)
		self.bind('<Escape>', self.closeMessageBox)
		infoBoxFrame = self.twFrame
		length = len(msg)
		if '\n' not in msg and length < 40:
			padding = ' '*((40 - length)>>1)
			msg = '{}{}{}'.format(padding, msg, padding)
		msg = '\n{}\n'.format(msg)
		self.msgBoxStr = StringVar(value=msg, name='ooInfoBox_'+str(OoInfoBox._count)+'_msgBoxStr')
		self.msgBoxLabel = Label(infoBoxFrame, textvariable=self.msgBoxStr,
								 font=font, anchor=CENTER, justify=CENTER)
		self.msgBoxOK = Button(infoBoxFrame, text='OK', font=font,
							   padx=10, command=self.closeMessageBox)
		self.msgBoxOK.bind('<Return>', self.closeMessageBox)
		self.msgBoxLabel.grid(		row=0, column=0, sticky=N, columnspan=2, padx=8)

		if destruct is not None:
			self.msgBoxSpinFrame = Frame(infoBoxFrame)
			self.msgBoxSpinVar = StringVar(value=str(destruct), name='ooInfoBox_'+str(OoInfoBox._count)+'_msgBoxSpinVar')
			self.msgBoxSpinLabel = Label(self.msgBoxSpinFrame, text='closing in:',
										 padx=10, font=font, anchor=W)
			self.msgBoxSpinbox = Spinbox(self.msgBoxSpinFrame, exportselection=0,
										 from_=0, to=10, increment=1, font=font,
										 state='readonly', width=2, textvariable=self.msgBoxSpinVar)
			self.msgBoxSpinbox.bind('<Enter>', self.haltDestruct)
			self.msgBoxSpinLabel.grid(	row=0, column=0, sticky=E) # in msgBoxSpinFrame
			self.msgBoxSpinbox.grid(	row=0, column=1, sticky=W) #  "
			self.msgBoxSpinFrame.grid(	row=1, column=0, sticky=W)
			self.destructID = self.after(1000, self.destructMessage)
			infoBoxFrame.columnconfigure(0, weight=1) # to center OK button (almost)
			infoBoxFrame.columnconfigure(1, weight=3)
			self.msgBoxOK.grid(		row=1, column=1, sticky=SW, padx=2, pady=2)
		else:
			self.msgBoxOK.grid(		row=1, column=0, sticky=S, columnspan=2, padx=2, pady=2)
		self.center()
		self.msgBoxOK.focus_set()

	destructID = None
	def destructMessage(self):
		self.destructID = None
		self.msgBoxSpinbox.invoke('buttondown')
		count = int(self.msgBoxSpinVar.get())
		if count > 0:
			self.destructID = self.after(1000, self.destructMessage)
		else:
			self.closeMessageBox()

	def haltDestruct(self, event=None):
		if self.destructID is not None:
			self.after_cancel(self.destructID)
			self.destructID = None

	def closeMessageBox(self, event=None):
		if self.destructID is not None:
			self.after_cancel(self.destructID)
			self.destructID = None
		if self in openMessages:
			openMessages.remove(self)
		del self.msgBoxStr
		# self.msgBoxStr.unset()
		if hasattr(self, 'msgBoxSpinVar'):
			del self.msgBoxSpinVar
			# self.msgBoxSpinVar.unset()
		self.closeTop()
		return 'break'
# end class OoInfoBox

class OoBarMenu(Menu):					# for menubar pulldown menus that support fonts!
	menus = []
	def __init__(self, master, label, font, **kwargs):
		self.master = master
		self.label = label
		self.font = font
		self.menuButton = Button(master, text=self.label, font=font, name='{}Menu'.format(label.lower()),
									command=self.toggleMenu)
		if platformIsWindows:
			self.menuButton.bind('<Leave>', self.closeMenu)
			# only the OS can close a menu (?), so this at least keeps their 'open' flags in sync
		Menu.__init__(self, master, tearoff=0, font=font, **kwargs)
		self._index = len(OoBarMenu.menus)
		OoBarMenu.menus.append(self)
		self.menuButton.grid(row=0, column=self._index, sticky=W)
		self.menuItems = {}
		self.statesVary = {}
		self.isOpen = False
			
	def closeMenu(self, event=None):
		if self.isOpen and platformIsLinux:
			self.unpost()
			# This subcommand does not work on Windows and the Macintosh, as 
			# those platforms have their own way of unposting menus. (tcl8.5)
		self.isOpen = False
	
	def toggleMenu(self):		# storing open state in 'underline' (not used) to enable toggling
		if not self.isOpen:
			openXY = [self.master.winfo_rootx() + self.menuButton.winfo_x(), 
					  self.master.winfo_rooty() + self.menuButton.winfo_y() + self.menuButton.winfo_height()]
			for menu in OoBarMenu.menus:
				if menu != self:# prevent flashing on Linux??
					menu.closeMenu()
			self.isOpen = True
			self.post(*openXY)	# we wait for the menu to close
		else:
			self.closeMenu()
		
	def _add(self, kind, **kwargs):
		if 'label' not in kwargs: return
		label = kwargs['label']
		if 'stateChange' in kwargs:
			self.statesVary[label] = kwargs['stateChange']
			del kwargs['stateChange']
		self.add(kind, **kwargs)
		self.menuItems[label] = self.index(END)

	def add_cascade(self, **kwargs):
		self._add('cascade', **kwargs)

	def add_checkbutton(self, **kwargs):
		self._add('checkbutton', **kwargs)

	def add_command(self, **kwargs):
		self._add('command', **kwargs)

	def add_radiobutton(self, **kwargs):
		self._add('radiobutton', **kwargs)

	def add_separator(self, **kwargs):
		self.add('separator', **kwargs)	# bypass _add as never change state, color
		
	def configLabel(self, label, **kwargs):
		if label in self.menuItems:
			self.entryconfigure(self.menuItems[label], **kwargs)
		else:
			errmsg = 'Error: label "{}" not in menuItems'.format(label)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.error(errmsg)

	def changeAllStates(self, newState):
		statesVary = self.statesVary
		for label in statesVary:
			if statesVary[label]:
				self.configLabel(label, state=newState)

	def removeOnesSelf(self):
		self.menuButton.destroy()
		self.destroy()
# end class OoBarMenu

class TextPopup(Menu):
	_count = 0
	def __init__(self, master, histCmd=None):
		self.master = master
		TextPopup._count += 1
		Menu.__init__(self, master, tearoff=0)
		self.histCmd = histCmd
		self.add_command(label='Select all', command=self.selectAll)
		self.add_command(label='Begin Select', command=self.beginSelect)
		self.add_command(label='End Select', command=self.endSelect)
		self.add_separator()
		self.add_command(label='Search ...', command=self.openSearchBox)
		self.add_separator()
		self.add_command(label='Copy', command=self.copyText)
		self.add_command(label='Copy All', command=self.copyAllText)
		self.add_command(label='Paste', command=self.pasteText)
		self.add_separator()
		self.add_command(label='Delete', command=self.deleteText)
		self.add_command(label='Delete All', command=self.deleteAllText)
		self.add_separator()
		self.add_command(label='Undo delete', command=self.deleteUndo)
		self.searchStrings = []	# prev. search strings for history 
		self.createSearchBox()
		if histCmd:
			self.add_separator()
			self.add_command(label='Remove command', command=histCmd)
		
		self.master.bind('<Button-1>', self.recordTextPosn)
		self.master.bind('<Button-3>', self.openPopUpMenu)
		
		self.master.bind('<<Clear>>', self.deleteText)
		self.master.bind('<BackSpace>', self.deleteText)
		self.master.bind('<Delete>', self.deleteText)
		self.master.bind('<Alt-BackSpace>', self.deleteUndo)
		
		self.master.bind('<<Cut>>', self.cutText)
		self.master.bind('<Control-X>', self.cutText)
		self.master.bind('<<Copy>>', self.copyText)
		self.master.bind('<Control-C>', self.copyText)
		self.master.bind('<<Paste>>', self.pasteText)
		self.master.bind('<Control-V>', self.pasteText)
		self.master.bind('<<Undo>>', self.deleteUndo)
		self.master.bind('<Control-Z>', self.deleteUndo)

	def selectAll(self):
		txt = self.master
		txt.tag_remove(SEL, '1.0', END)
		txt.tag_add(SEL, '1.0', END)
		txt.tag_raise(SEL)
		self.selStart = '1.0'
		self.selEnd = END
		txt.focus_set()

	def beginSelect(self):
		txt = self.master
		txt.tag_remove(SEL, '1.0', END)
		selStart = self.formatMouseIndex()
		txt.tag_add(SEL, selStart) 		# this sets selection range of 1 char
		self.selStart = selStart
		self.selEnd = None
		txt.focus_set()					# often focus is in cmdLine, so this saves a click

	def formatMouseIndex(self, xOffset=None):
		txt = self.master
		[x, y] = self.rightMouseXY
		if xOffset is not None:
			x += xOffset
		return txt.index('@{},{}'.format(x-txt.winfo_rootx(), y-txt.winfo_rooty()))

	def endSelect(self):
		txt = self.master
		selStart = self.selStart
		selEnd = self.formatMouseIndex()
		if txt.compare(selStart, '>', selEnd): # backwards
			selStart, selEnd = selEnd, selStart
		selEnd = '{} +1c'.format(selEnd)
		if txt.compare(selEnd, '>', END):
			selEnd = txt.index(END)
		selEnd = txt.index(selEnd)
		txt.tag_remove(SEL, '1.0', END)
		txt.tag_add(SEL, selStart, selEnd)
		if len(txt.tag_ranges(SEL)) > 0:
			txt.tag_raise(SEL)
			self.selEnd = txt.index(SEL_LAST)
		txt.focus_set()

	def createSearchBox(self):
		self.top = self.master.winfo_toplevel()
		self.searchBox = TopWindow(self.top, 'Search for:', enduring=True, showNow=False)
		self.searchBox.bind('<Escape>', self.searchBox.closeTop)
		self.searchBox.bind('<Return>', self.handleCR)
		searchBoxFrame = self.searchBox.twFrame
		defaultFont = self.defaultFont = tkFont.nametofont(self.master.config('font')[-1])
		self.lineSpace = defaultFont.metrics('linespace')
		self.searchFontFace = defaultFont.cget('family')
		self.searchFontSize = defaultFont.cget('size')

		self.searchDirn = IntVar(value=1, name='textPopup_'+str(TextPopup._count)+'_searchDirn')
		# - default backwards=1 (.search also accepts forwards=0)
		self.searchResultLen = IntVar(name='textPopup_'+str(TextPopup._count)+'_searchResultLen') 
		# - search stores # of char.s if pattern found
		self.searchDirnFwd = Radiobutton(searchBoxFrame, variable=self.searchDirn, indicatoron=0,
										value=0, text='\\/', bg='#ddd', relief='raised', bd=2,
										 command=self.startSearch, font=defaultFont)
		self.searchDirnBck = Radiobutton(searchBoxFrame, variable=self.searchDirn, indicatoron=0,
										value=1, text='/\\', bg='#ddd', relief='raised', bd=2,
										 command=self.startSearch, font=defaultFont)
										 
		searchRegexText = 'Regex (POSIX extended REs with some extensions)'
		searchEntryWidth = len(searchRegexText)
		self.searchHistory = ScrollingListBox(searchBoxFrame, font=defaultFont, exportselection=0, height=5)
		scrollW = self.searchHistory.scrollbar.winfo_reqwidth()
		scrollW = int(3 * scrollW / defaultFont.measure('0'))
		self.searchHistory.config(width=searchEntryWidth - scrollW)
		self.searchHistory.bind('<<ListboxSelect>>', self.searchSelected)
		if len(self.searchStrings):
			self.searchHistory.setContents(self.searchStrings)
		
		self.searchHistToggle = Button(searchBoxFrame, text='\\/', bg='#ddd', relief='raised', bd=2,
										 command=self.toggleSearchHist, font=defaultFont)
		
		self.searchTarget = StringVar(name='textPopup_'+str(TextPopup._count)+'_searchTarget')
		setBtns = self.register(self.buttonState)
		self.searchTargetEntry = Entry(searchBoxFrame, textvariable=self.searchTarget,
										exportselection=0, bg='#ddd', width=searchEntryWidth,
										font=defaultFont, validate='key', validatecommand=(setBtns, '%P'))
		self.searchTargetEntryClear = Button(searchBoxFrame, text='Clear', font=defaultFont, state=DISABLED,
											command=lambda: self.searchTarget.set(''))
		
		self.searchAuxFrame = Frame(searchBoxFrame)
		self.searchCountBtn = Button(self.searchAuxFrame, text='Count', font=defaultFont, state=DISABLED,
									command=lambda: self.startSearch(counting=True))
		self.searchMarkall = Button(self.searchAuxFrame, text='Mark all', font=defaultFont, state=DISABLED,
									command=lambda: self.startSearch(marking=True))
									
		self.searchBackwards = IntVar(value=1, name='textPopup_'+str(TextPopup._count)+'_searchBackwards')
		# - default search up, backwards=1
		self.searchBackwardsBtn = Checkbutton(searchBoxFrame, variable=self.searchBackwards, pady=3,
											text='Backwards', font=defaultFont)	# pady=3 to match height of Button
		self.searchWordsOnly = IntVar(name='textPopup_'+str(TextPopup._count)+'_searchWordsOnly')
		# - default any match, word boundary not detected by tk.search
		self.searchWordsOnlyBtn = Checkbutton(searchBoxFrame, variable=self.searchWordsOnly, pady=3,
											text='Words only', font=defaultFont)
		self.searchCase = IntVar(value=1, name='textPopup_'+str(TextPopup._count)+'_searchCase')
		# - default insensitive, nocase=1
		self.searchCaseBtn = Checkbutton(searchBoxFrame, variable=self.searchCase, pady=3,
										text='Ignore case', font=defaultFont)
		self.searchWrap = IntVar(name='textPopup_'+str(TextPopup._count)+'_searchWrap')
		# - default off, stopindex='1.0' or END; search will wrap if not set
		self.searchWrapBtn = Checkbutton(searchBoxFrame, variable=self.searchWrap, pady=3,
										text='Wrap search', font=defaultFont)
		self.searchRegex = IntVar(name='textPopup_'+str(TextPopup._count)+'_searchRegex')
		# - default off, regexp=0 or exact=1; subset of Py's regexs: . ^ [c 1 …] (…) * + ? e1|e2
		self.searchRegexBtn = Checkbutton(searchBoxFrame, variable=self.searchRegex, pady=3,
										text=searchRegexText, font=defaultFont)
		self.searchLabelStr = StringVar(name='textPopup_'+str(TextPopup._count)+'_searchLabelStr')
		self.searchLabel = Label(searchBoxFrame, textvariable=self.searchLabelStr, font=defaultFont)

		gI = self.searchGridInfo = {}
		gI['DirnBck'] =   {'row': '0', 'column': '0', 'sticky': 'nw', 'padx': '4',  'pady': '4', 'columnspan': '1', 'rowspan': '1'}	#, 'ipady': '0', 'ipadx': '0' 
		gI['Entry'] =     {'row': '0', 'column': '1', 'sticky': 'w',  'padx': '4',  'pady': '4', 'columnspan': '2', 'rowspan': '1'}
		gI['Toggle'] =    {'row': '0', 'column': '3', 'sticky': 'w',  'padx': '4',  'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['Clear'] =     {'row': '0', 'column': '4', 'sticky': 'e',  'padx': '4',  'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['DirnFwd'] =   {'row': '1', 'column': '0', 'sticky': 'nw', 'padx': '4',  'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['History'] =   {'row': '1', 'column': '1', 'sticky': 'nw', 'padx': '12', 'pady': '4', 'columnspan': '2', 'rowspan': '3'}
		gI['Backwards'] = {'row': '1', 'column': '1', 'sticky': 'nw', 'padx': '12', 'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['WordsOnly'] = {'row': '1', 'column': '2', 'sticky': 'nw', 'padx': '12', 'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['Wrap'] =      {'row': '2', 'column': '1', 'sticky': 'nw', 'padx': '12', 'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['Case'] =      {'row': '2', 'column': '2', 'sticky': 'nw', 'padx': '12', 'pady': '4', 'columnspan': '1', 'rowspan': '1'}
		gI['Regex'] =     {'row': '3', 'column': '1', 'sticky': 'sw', 'padx': '12', 'pady': '4', 'columnspan': '3', 'rowspan': '1'}
		gI['Label'] =     {'row': '4', 'column': '0', 'sticky': 'nw', 'padx': '4',  'pady': '4', 'columnspan': '5', 'rowspan': '1'} # , 'ipadx': '4'

		gI['AuxFrame'] =  {'row': '1', 'column': '3', 'sticky': 'ne', 'padx': '4',  'pady': '0', 'columnspan': '2', 'rowspan': '2'}
		gI['Count'] =     {'row': '0', 'column': '0', 'sticky': 'ne', 'padx': '0',  'pady': '4', 'columnspan': '2', 'rowspan': '1'}
		gI['Markall'] =   {'row': '1', 'column': '0', 'sticky': 'se', 'padx': '0',  'pady': '4', 'columnspan': '2', 'rowspan': '1'}
		self.searchAuxFrame.grid(gI['AuxFrame'])
		self.searchCountBtn.grid(gI['Count'])
		self.searchMarkall.grid(gI['Markall'])

		self.searchDirnBck.grid(gI['DirnBck'])
		self.searchTargetEntry.grid(gI['Entry'])
		self.searchHistToggle.grid(gI['Toggle'])
		self.searchTargetEntryClear.grid(gI['Clear'])
		self.searchDirnFwd.grid(gI['DirnFwd'])
		self.searchBackwardsBtn.grid(gI['Backwards'])
		self.searchWordsOnlyBtn.grid(gI['WordsOnly'])
		self.searchWrapBtn.grid(gI['Wrap'])
		self.searchCaseBtn.grid(gI['Case'])
		self.searchRegexBtn.grid(gI['Regex'])
		self.searchLabel.grid(gI['Label'])
	
	def setupDimns(self):
		self.searchBox.deiconify()
		self.searchBox.lift()
		self.update_idletasks()
		self.searchWidth, self.searchHeight = self.searchBox.winfo_reqwidth(), self.searchBox.winfo_reqheight()
		self.searchWidth += self.searchBox.winfo_rootx()
		self.searchHeight += self.searchBox.winfo_rooty()
		
		yForBtns = self.searchLabel.winfo_y() - self.searchWordsOnlyBtn.winfo_y()
		dyHist = int((yForBtns - self.searchHistory.winfo_height()) / 2)
		self.searchGridInfo['History']['pady'] = dyHist

	def toggleSearchHist(self):
		if self.searchHistory.winfo_ismapped():
			self.searchHistory.closeBox()
			gI = self.searchGridInfo
			self.searchBackwardsBtn.grid(gI['Backwards'])
			self.searchWordsOnlyBtn.grid(gI['WordsOnly'])
			self.searchWrapBtn.grid(gI['Wrap'])
			self.searchCaseBtn.grid(gI['Case'])
			self.searchRegexBtn.grid(gI['Regex'])
		else:
			self.searchBackwardsBtn.grid_forget()
			self.searchWordsOnlyBtn.grid_forget()
			self.searchWrapBtn.grid_forget()
			self.searchCaseBtn.grid_forget()
			self.searchRegexBtn.grid_forget()
			self.searchHistory.restoreBox(**self.searchGridInfo['History'])
			searchStr = self.searchTargetEntry.get()
			if searchStr in self.searchStrings:
				idx = self.searchStrings.index(searchStr)
				self.searchHistory.see(idx)
				self.searchHistory.activate(idx)

	def searchSelected(self, event=None):
		currSelection = self.searchHistory.curselection() # returns tuple w/ indices of the selected element(s)
		if len(currSelection) > 0:
			searchStr = self.searchHistory.get(currSelection[0])
			self.searchTarget.set(searchStr)
			self.toggleSearchHist()
			self.searchTargetEntry.focus_set()
		return 'break'
		
	def updateSearchHistory(self, searchStr):
		if searchStr not in self.searchStrings:
			self.searchStrings.insert(0, searchStr)
			self.searchHistory.setContents(self.searchStrings)
			
	def buttonState(self, contents):
		if len(contents) == 0:
			self.searchTargetEntryClear.config(state=DISABLED)
			self.searchCountBtn.config(state=DISABLED)
			self.searchMarkall.config(state=DISABLED)
		else:
			self.searchTargetEntryClear.config(state=NORMAL)
			self.searchCountBtn.config(state=NORMAL)
			self.searchMarkall.config(state=NORMAL)
		return True						# allow all changes

	def getGeometry(self, widget, coords=False):
		widget.update_idletasks()
		info = widget.winfo_geometry()
		widgetSize, Xoff, Yoff = info.split('+')
		width, depth = widgetSize.split('x')
		if coords:
			return [int(Xoff), int(Yoff)]
		else:
			return [int(width), int(depth), int(Xoff), int(Yoff)]

	def openSearchBox(self):			# command for pop-up 'Search ...'
		font = tkFont.nametofont(self.master.config('font')[-1])
		if self.searchFontFace != font.cget('family') or self.searchFontSize != font.cget('size'):
			# rebuild searchBox when font changes
			mouseXY = None
			if hasattr(self.searchBox, 'mouseXY'):
				mouseXY = self.searchBox.mouseXY
			self.searchBox.destroy()
			self.createSearchBox()
			if mouseXY:
				self.searchBox.mouseXY = mouseXY
		if not hasattr(self, 'searchWidth'):
			self.setupDimns()
		searchBox = self.searchBox
		self.searchDirn.set(2)			# so neither button is on (using .deselect, tcl error "expecting float, got ''" <wierd>)
		self.searchLabelStr.set('')
		self.lastPatternFound = True
		self.patternMatched = False
		txt = self.master
		txtW = txtH = txtoffX = txtoffY = txtX = txtY = None
		openAbove = False
		selection = txt.tag_ranges(SEL)
		openedBefore = hasattr(searchBox, 'mouseXY')
		if len(selection) == 0:
			self.searchTargetEntry.focus_set()
		elif len(selection) == 2: 		# auto-add selection to Entry, set starting index
			selIdx = self.lastSearchIdx = txt.index(SEL_FIRST)
			selEndIdx = txt.index(SEL_LAST)
			searchStr = txt.get(selIdx, selEndIdx)
			self.searchTarget.set(searchStr)
			self.updateSearchHistory(searchStr)
			# check selection is visible so tkinter doesn't go BOOM
			selBbox = txt.bbox(selIdx)
			selEndBbox = txt.bbox(selEndIdx)
			if selBbox is not None and selEndBbox is not None:
				# create Rectangle's for txt, SEL & searchBox to check if there's an overlap
				txtW, txtH, txtoffX, txtoffY = self.getGeometry(txt) # calls update_idletasks
				txtX, txtY = txt.winfo_rootx(), txt.winfo_rooty()
				selULx, selULy, _, _ = selBbox 				# relative to txt
				selLRx, selLRy, width, height = selEndBbox	#   "
				if width > height:				# bbox returns very large width (>1000) for some char's, eg '\n'
					width = height//2
				selFullWidth = selLRy != selULy # spans multiple lines; ensure Rectangle is as wide as txt
				if not selFullWidth:
					selULx += txtX				# absolute for Upper Left
					selULy += txtY
					selLRx += width + txtX 		# absolute for Lower Right
					selLRy += height + txtY
					searchULx, searchULy = searchBox.mouseXY if openedBefore else self.searchOpenXY
					searchLRx = searchULx + self.searchWidth
					searchLRy = searchULy + self.searchHeight
					if 	(searchULx < selULx < searchLRx and searchULy < selULy < searchLRy) or \
						(searchULx < selLRx < searchLRx and searchULy < selLRy < searchLRy) or \
						selULx < searchULx < searchLRx < selLRx:
						# searchBox will overlap/cover selection
						openedBefore = False 	# force initial positon check below
						def searchInWindow(newX, newY):
							return txtX < newX < newX + self.searchWidth < txtX + txtW and \
								   txtY < newY < newY + self.searchHeight < txtY + txtH
						if searchInWindow(searchULx, selLRy): # below
							self.searchOpenXY = [searchULx, selLRy]
						elif searchInWindow(searchULx, selULy - self.searchHeight): # above
							self.searchOpenXY = [searchULx, selULy - self.searchHeight]
							openAbove = True
						else:
							openedBefore = hasattr(searchBox, 'mouseXY') # abort movement
		if openedBefore:
			searchBox.restoreTop()
		else:							# ensure initial search box stays inside app
			if txtW is None:	# no selection so not set above
				txtW, txtH, txtoffX, txtoffY = self.getGeometry(txt) # calls update_idletasks
				txtX, txtY = txt.winfo_rootx(), txt.winfo_rooty()
			appMinX, appMinY = txtX + txtoffX, txtY + txtoffY
			appMaxX, appMaxY = appMinX + txtW, appMinY + txtH
			
			searchOpenX, searchOpenY = self.searchOpenXY
			if searchOpenX + self.searchWidth > appMaxX:	# excceds right edge, right justify
				searchOpenX = appMaxX - self.searchWidth
				
			if searchOpenY > txtH / 2:
				searchOpenY -= (0 if openAbove else self.searchHeight) + 2 * self.lineSpace
			else:
				searchOpenY += 2 * self.lineSpace
			if searchOpenY < appMinY:						# excceds top edge, top justify
				searchOpenY = appMinY
			if searchOpenY + self.searchHeight > appMaxY:	# excceds bottom edge, bottom justify
				searchOpenY = appMaxY - self.searchHeight
			
			searchBox.showAtMouse([searchOpenX, searchOpenY])
	
	def handleCR(self, event=None):
		self.startSearch()
		return 'break'
		
	lastSearchIdx = ''					# starting position of last on a subsequent search on same pattern
	lastPattern = ''					# last pattern searched
	patternMatched = False
	lastPatternFound = True
	def startSearch(self, counting=False, marking=False):
		reverseSearch = self.searchBackwards.get()
		searchBack = self.searchDirn.get() 		# arrow buttons; for consistency, 1 => backwards
		if searchBack == 0 or searchBack == 1:	# came in via a button, they override searchBackwards
			self.searchDirn.set(2)				# reset button (ie. neither radiobutton)
		else:									# started w/ Return
			searchBack = reverseSearch
		pattern = self.searchTarget.get()
		if len(pattern) == 0:
			self.searchLabelStr.set('enter a target')
			return
		self.updateSearchHistory(pattern)
		txt = self.master
		wordsOnly = self.searchWordsOnly.get() == 1
		wrapping = self.searchWrap.get() == 1
		ignoreCase = self.searchCase.get() == 1
		regularExpn = self.searchRegex.get() == 1
		haveMarks = len(txt.tag_ranges('searchMark')) > 0
		self.patternMatched = pattern == self.lastPattern and self.lastPatternFound
		if not self.lastPattern or (marking and haveMarks):
			txt.tag_remove('searchMark', '1.0', END)
			self.searchMarkall.config(text='Mark all')
			if marking and haveMarks: 	# button acts as a toggle
				self.searchLabelStr.set('')
				return
		self.lastPattern = pattern
		if self.lastSearchIdx == '':	# first time visit
			searchFrom = self.lastSearchIdx = self.formatMouseIndex()
		else:
			searchFrom = self.lastSearchIdx if searchBack else '{} +1c'.format(self.lastSearchIdx)
		idx = searchFrom if searchBack else '{} -1c'.format(searchFrom)
		stopSearch = None if wrapping or counting or marking else '1.0' if searchBack else END
		findings = []
		found = False
		wrapped = False
		while not found or counting or marking:
			searchFrom = idx if searchBack else '{} +1c'.format(idx)
			idx = ''
			try:
				idx = txt.search(pattern, searchFrom, backwards=searchBack, stopindex=stopSearch,
								 count=self.searchResultLen, nocase=ignoreCase, elide=1, regexp=regularExpn)
			except TclError as exc:
				errmsg = 'TclError: \n{}\n\n(www.tcl.tk/man/tcl8.5/TclCmd/re_syntax.htm)'.format(
						exc.message.replace(':','\n'))
				openMessages.append(OoInfoBox(self.top, errmsg, font=self.defaultFont))
				debugLogger.error(errmsg)
			except Exception as exc:
				errmsg = 'Exception: {}'.format(exc)
				if dca.g['debug']:
					print(errmsg)
					print_exc()
					pdb.set_trace()
				else:
					debugLogger.exception(errmsg)

			found = idx != ''
			if not found: break
			foundLength = self.searchResultLen.get()
			if foundLength == 0: break # degenerate case for re's
			endIdx = txt.index('{}+{}c'.format(idx, foundLength))
			if wordsOnly:
				if txt.compare(idx, '!=', '{} wordstart'.format(idx)) or \
				   txt.compare('{} +1c'.format(endIdx), '!=', '{} wordend'.format(endIdx)): # it's not a word
					continue
			if not found and not (counting or  marking):
				break					# quit on 1st match in normal search
			if idx in findings:
				break					# we've wrapped around
			elif found:
				findings.append(idx)
				if marking:
					txt.tag_add('searchMark', idx, endIdx)
		haveMarks = len(txt.tag_ranges('searchMark')) > 0
		self.searchMarkall.config(text='Clear marks' if haveMarks else 'Mark all')
		if counting or marking:
			count = len(findings)
			self.searchLabelStr.set('{} matches {}'.format(
				('no' if count == 0 else count), ('found' if counting else 'marked')))
			return
		if stopSearch is None and found and self.lastPatternFound: # check if we wrapped
			wrapped = txt.compare(idx, '>=' if searchBack else '<=', self.lastSearchIdx)
		if found: 						# "line.char" of start of match
			txt.tag_remove(SEL, '1.0', END)
			txt.tag_add(SEL, idx, endIdx)
			txt.see(idx)
			self.patternMatched = True
			if wrapped:
				self.searchLabelStr.set('wrapped to {} of log'.format('end' if searchBack else 'start'))
			else:
				self.searchLabelStr.set('')
			self.lastSearchIdx = idx
		else: 					# search failed
			if self.lastPatternFound:
				txt.tag_remove(SEL, '1.0', END)
			self.searchLabelStr.set('no {}matches found'.format('more ' if self.patternMatched else ''))
			self.lastSearchIdx = '1.0' if searchBack else END
		self.lastPatternFound = True if self.patternMatched else found

	def cutText(self, event=None):
		self.copyText()
		self.deleteText()
		
	def copyText(self, event=None):		
		txt = self.master				# only executes if there's a selection
		if len(txt.tag_ranges(SEL)) > 0:
			text = txt.get(SEL_FIRST, SEL_LAST)
			self.clipboard_clear()
			self.clipboard_append(text)

	def copyAllText(self):
		txt = self.master
		text = txt.get('1.0', END)
		if len(text) > 1: 				# empty Text always has a '\n' char
			self.clipboard_clear()
			self.clipboard_append(text)

	def pasteText(self, event=None):
		txt = self.master
		text = self.clipboard_get()
		if txt.editable and len(text) > 0:
			if len(txt.tag_ranges(SEL)) > 0:
				index = txt.index(SEL_FIRST)
				txt.delete(SEL_FIRST, SEL_LAST)
				txt.tag_remove(SEL, '1.0', END)
				self.clearSelection()
			elif self.focus_get() == txt:
				index = txt.index(INSERT)
			else:
				index = txt.index('@{},{}'.format(self.rightMouseXY[0] - txt.winfo_rootx(), 
												  self.rightMouseXY[1] - txt.winfo_rooty()))
				txt.mark_set(INSERT, index)
			txt.insert(index, text)
			txt.update_idletasks()
			txt.focus_set()
		return 'break'

	def deleteUndo(self, event=None):	# only if edit_modified (else undo stack is cleared in openPopUpMenu)
		txt = self.master
		if not txt.edit_modified():
			if not txt.editable:
				txt.config(state=NORMAL)
			txt.edit_undo()				# undo all to separator or bottom of stack
			txt.edit_modified(False)
			if not txt.editable:
				txt.config(state=DISABLED)
			txt.update_idletasks()
			if self.delCount <= 1:
				self.delCount = 0
			else:
				self.delCount -= 1
		return 'break'

	def deleteText(self, event=None):	# only executes if there's a selection
		txt = self.master
		if len(txt.tag_ranges(SEL)) > 0:
			if not txt.editable:
				txt.config(state=NORMAL)
			txt.delete(SEL_FIRST, SEL_LAST)
			txt.tag_remove(SEL, '1.0', END)
			txt.edit_modified(False)
			if not txt.editable:
				txt.config(state=DISABLED)
			self.delCount += 1
			self.clearSelection()
			return 'break'	# if there's no selection, let cmd pass through 

	def deleteAllText(self):
		txt = self.master
		if len(txt.get('1.0', END)) > 1: # empty Text always has a '\n' char
			if not txt.editable:
				txt.config(state=NORMAL)
			txt.edit_reset()			# clear undo stack
			txt.delete('1.0', END)
			txt.tag_remove(SEL, '1.0', END)
			txt.edit_modified(False)
			if not txt.editable:
				txt.config(state=DISABLED)
			self.delCount = 1
			self.clearSelection()

	delCount = 0
	selStart = None
	selEnd = None
	def openPopUpMenu(self, event):
		txt = self.master
		txt.event_generate('<<closeAnyOpenFrames>>')
		self.rightMouseXY = [event.x_root, event.y_root]
		if hasattr(self, 'leftMouseXY'):
			self.searchOpenXY = self.leftMouseXY
			del self.leftMouseXY
		else:
			self.searchOpenXY = self.rightMouseXY[0:]
		noSel = len(txt.tag_ranges(SEL)) == 0
		empty = txt.compare(END, '<=', '2.0') and len(txt.get('1.0', END)) == 1
		if txt.edit_modified():
			txt.edit_reset()
			self.delCount = 0
		index = self.index(END)
		if index == 0: return
		index += 1
		while index > 0:
			index -= 1
			if self.type(index) in ['separator', 'tearoff']: # can also be 'cascade', 'checkbutton', 'command', 'radiobutton'
				continue
			label = self.entrycget(index, 'label')
			if label == 'Delete command':
				self.entryconfigure(index, state=NORMAL if not empty else DISABLED)
			elif label == 'Select all':
				self.entryconfigure(index, state=NORMAL if noSel and not empty else DISABLED)
			elif label == 'Begin Select':
				self.entryconfigure(index, state=NORMAL if self.selStart is None and not empty else DISABLED)
			elif label == 'End Select':
				self.entryconfigure(index, state=NORMAL if self.selStart is not None and self.selEnd is None else DISABLED)
			elif label == 'Search ...':
				self.entryconfigure(index, state=NORMAL if not empty else DISABLED)
			elif label == 'Copy':
				self.entryconfigure(index, state=DISABLED if noSel else NORMAL)
			elif label == 'Copy All':
				self.entryconfigure(index, state=DISABLED if empty else NORMAL)
			elif label == 'Paste':
				self.entryconfigure(index, state=NORMAL if txt.editable and len(self.clipboard_get()) > 0 else DISABLED)
			elif label == 'Delete':
				self.entryconfigure(index, state=DISABLED if noSel else NORMAL)
			elif label == 'Delete All':
				self.entryconfigure(index, state=DISABLED if empty else NORMAL)
			elif label == 'Undo delete':
				self.entryconfigure(index, state=NORMAL if self.delCount > 0 else DISABLED)
		self.post(*self.rightMouseXY)
		return 'break'

	def recordTextPosn(self, event):
		self.leftMouseXY = [event.x_root, event.y_root]
		self.clearSelection()
		self.lastSearchIdx = ''

	def clearSelection(self):
		if self.selEnd is not None:		# only clear outside begin/end select cycle
			self.selStart = None
			self.selEnd = None
# end class TextPopup
### openSearchBox

class ScrollbarPopup(Scrollbar):
	def __init__(self, master, associate):
		Scrollbar.__init__(self, master, width=SCROLLER_WIDTH, orient=VERTICAL)
		self.setAssociate(associate)
		self.popup = Menu(self, tearoff=0) #, postcommand=)
		self.popup.add_command(label='Scroll Here', command=self.scrollBodyHere)
		self.popup.add_separator()
		self.popup.add_command(label='Top', command=self.scrollTop)
		self.popup.add_command(label='Bottom', command=self.scrollBottom)
		self.popup.add_separator()
		self.popup.add_command(label='Page Up', command=self.scrollPageUp)
		self.popup.add_command(label='Page Down', command=self.scrollPageDown)
		self.popup.add_separator()
		self.popup.add_command(label='Scroll Up', command=self.scrollScrollUp)
		self.popup.add_command(label='Scroll Down', command=self.scrollScrollDown)
		self.bind_all('<Button-3>', self.openScrollPopUp, add='+')

	def setAssociate(self, associate):
		self.associate = associate
		self.associatedGroup = None
		self.config(command=associate.yview)

	def setAssociatedGroup(self, group):
		self.associatedGroup = group
		self.associate = None
		self.config(command=self.scrollGroup)
		
	def scrollGroup(self, *args):
		for widget in self.associatedGroup:
			widget.yview(*args)
			
	def openScrollPopUp(self, event): 	# bind_all needed to generate events in scrollbar
		if self != event.widget:
			return						# wrong instance, ignore event
		if self.winfo_class() == 'Scrollbar': # filter <Button-3> events
			self.rightMouseXY = [event.x_root, event.y_root]
			top, bottom = self.get()
			menu = self.popup
			index = menu.index(END)
			if index == 0: return
			index += 1
			while index > 0:
				index -= 1
				if menu.type(index) in ['separator', 'tearoff']: # can also be 'cascade', 'checkbutton', 'command', 'radiobutton'
					continue
				label = menu.entrycget(index, 'label')
				if label in ['Top', 'Page Up', 'Scroll Up']:
					menu.entryconfigure(index, state=NORMAL if top > 0 else DISABLED)
				elif label in ['Bottom', 'Page Down', 'Scroll Down']:
					menu.entryconfigure(index, state=NORMAL if bottom < 1 else DISABLED)
			menu.post(*self.rightMouseXY)
			return 'break'

	def getDepth(self):
		info = self.winfo_geometry()
		widgetSize, _, _ = info.split('+')
		_, depth = widgetSize.split('x')
		return int(depth)
	
	def scrollAssociate(self, *args):
		if self.associate:
			self.associate.yview(*args)
		else:
			self.scrollGroup(*args)

	def scrollBodyHere(self):
		# args to fraction() must be pixel coordinates relative to the scrollbar widget
		barX, barY = self.winfo_rootx(), self.winfo_rooty()
		mouseX, mouseY = self.rightMouseXY
		spot = self.fraction(mouseX - barX, mouseY - barY)
		top, bottom = self.get()		# relative positions (0.0...1.0) of slider
		middle = (bottom - top)/2		# offset to midpoint of the slider
		self.associate.yview_moveto(spot - middle)

	def scrollTop(self):
		self.scrollAssociate('moveto', 0)

	def scrollBottom(self):
		self.scrollAssociate('moveto', 1)

	def scrollPageUp(self):
		self.scrollAssociate('scroll', '-1', 'pages')

	def scrollPageDown(self):
		self.scrollAssociate('scroll', '1', 'pages')

	def scrollScrollUp(self):
		self.scrollAssociate('scroll', '-1', 'units')

	def scrollScrollDown(self):
		self.scrollAssociate('scroll', '1', 'units')	
# end class ScrollbarPopup

class ScrollingText(Text):
	def __init__(self, master, editable=False, histCmd=None, **kwargs):
		self.editable = editable
		self.frame = Frame(master)
		self.frame.rowconfigure(0, weight=1) # make frame stretchable
		self.frame.columnconfigure(0, weight=1)
		# frame is .grid'd by caller

		Text.__init__(self, self.frame, **kwargs)
		self.config(state=NORMAL if editable else DISABLED)
		self.rowconfigure(0, weight=1)	# make Text stretchable
		self.columnconfigure(0, weight=1)
		self.grid(row=0, rowspan=100, column=0, sticky=N+E+W+S)

		self.scrollbar = ScrollbarPopup(self.frame, self)
		self["yscrollcommand"] = self.scrollbar.set
		self.scrollbar.grid(row=0, rowspan=10, column=1, sticky=NS)
		self.popup = TextPopup(self, histCmd=histCmd)
# end class ScrollingText

class ScrollingListBox(Listbox):
	def __init__(self, master, label=None, suppressHelper=False, **kwargs):
		bg = kwargs['background'] if 'background' in kwargs else None
		if not bg:
			bg = kwargs['bg'] if 'bg' in kwargs else None
		self.lbFrame = Frame(master, background=bg)
		Listbox.__init__(self, self.lbFrame, **kwargs)
		self.scrollbar = ScrollbarPopup(self.lbFrame, self)
		self["yscrollcommand"] = self.scrollbar.set
		if not suppressHelper:
			self.bind('<KeyPress>', self.firstCharHelper)
		self.label = None
		row = 0
		if label:
			font = kwargs['font'] if 'font' in kwargs else None
			self.label = Label(self.lbFrame, text=label, font=font)
			self.label.grid(row=0, column=0, columnspan=2, sticky=E+W)
			row = 1
		self.grid(row=row, column=0, sticky=N+S+W)
		self.scrollbar.grid(row=row, column=1, sticky=N+S+E)
		
	def firstCharHelper(self, event):	# move to point in list where items start with key pressed
		keyPressed = event.char.lower()
		selection = self.get(0, END)
		if len(selection) == 0: return	# no items 
		choices = [sel for sel in selection if sel[0].lower() == keyPressed]
		if len(choices) == 0: return	# no items start with keyPressed
		first, last = selection.index(choices[0]), selection.index(choices[-1])
		top, bottom = self.nearest(0), self.nearest(self.winfo_height())
		selected = self.curselection()
		index = selected[0] if len(selected) > 0 else top
		firstChar = selection[index][0] if len(selection[index]) > 0 else ''
		firstOfNext = selection[index + 1][0] if len(selection) > index and len(selection[index]) > 0 else ''
		if firstChar.lower() == keyPressed and firstOfNext.lower() == keyPressed: # continue along thru group
			target = index + 1
		else:							# force scroll so more are visible
			if index <= last and index != first:	
				target = last if last > bottom else first	
			else:
				target = first if first < top else last
		if target == first and first != last:
			distance = (target - top) if target < top else (target - bottom - len(choices)) if target > bottom else 0
		else:											
			distance = (target - bottom) if target > bottom else (target - bottom - len(choices)) if target < top else 0
		self.yview('scroll', distance, 'units')
		self.selection_clear(0, END)
		self.selection_set(target)
		self.activate(target)

	def setContents(self, selection):
		self.delete(0, END)
		# for key in selection:
			# self.insert(END, key)
		self.insert(END, *selection)

	def closeBox(self):
		self.lbFrame.grid_remove()

	def restoreBox(self, **kwargs):
		self.lbFrame.grid(**kwargs)
# end class ScrollingListBox

class AppWindow(Frame):

## app variables ###########################################################

	client = None						# pointer to OoliteDebugConsoleProtocol instance
	connectedToOolite = False			# connection flag
	COLORS = {}							# working dict of all colors, local & oolite
	settings = {}						# local copy of oolite debug setting (w/o macros)
	afterLoopIDs = {}					# dict of ID # from tkinter's after cmd, saved for termination

## app setup ###############################################################
			
	def __init__(self):
		self.readConfigFile()
		self.init_toplevel()
		self.makeFonts()
		# app has 2 frames stacked vertically, for menubar and the paned window
		self.top.columnconfigure(0, weight=1)
		self.top.rowconfigure(0, minsize=self.lineSpace)
		self.top.rowconfigure(1, weight=1)
		self.menubar = Frame(self.top, background='#eeeeee')
		self.menubar.grid(row=0, sticky=E+W)
		Frame.__init__(self, self.top)		# constructor for the parent class, Frame
		self.rowconfigure(0, weight=1)		# make row 0 stretchable and
		self.columnconfigure(0, weight=1)	# make column 0 stretchable so it fills its frame
		self.grid(row=1, sticky=N+S+E+W)	# make the Application fill its cell of the top-level window
		self.gameStarted = IntVar(name='gameStarted')
		self.addTraceTkVar(self.gameStarted, self.checkGameStatus)
		self.createWindows()
		self.createDebugMenus()
		self.createOptionsMenus()
		self.createAliasFrame()
		self.createFontMenus()				# Settings menu is created upon connection, as they vary
		self.loadCmdHistory()
		self.setconnectPort()
		self.processMessage()
		self.sendSilentCmd()				# initiate polling
		self.top.bind_all('<<closeAnyOpenFrames>>', self.closeAnyOpenFrames)

	def init_toplevel(self):
		top = self.top = Tk(className='OoDebug2')
		top.minsize(MINIMUM_WIDTH, MINIMUM_HEIGHT)
		top.resizable(width=True, height=True)
		top.title(DEBUGGER_TITLE)
		top.protocol("WM_DELETE_WINDOW", self.exitCmd)

		# self.menubar = Menu(self.top)	# create a toplevel menu
		# self.top.config(menu=self.menubar)# display the menu
		# NB: menubar must precede .geometry call, else app shrinks by height of menubar (20) on each invocation
		#     - no longer relevant as not using toplevel menu, good to remember

		try:					# if geometry are not valid, revert to default
			top.geometry(self.localOptions['Geometry'])
		except:
			top.geometry(DEFAULT_GEOMETRY)# "500x380"
		iconFile = 'OoJSC256x256.png' if platformIsLinux else 'OoJSC.ico'

		if FROZEN:
			meipass = None
			if HAVE_MEIPASS:
				meipass = sys._MEIPASS
			elif '_MEIPASS2' in os.environ:# windows compiled runtime (pyInstall)
				meipass = os.environ['_MEIPASS2']
			if meipass:
				iconPath = os.path.join(meipass, iconFile)
		else:
			iconPath = os.path.join(SCRIPTPATH, iconFile)

		# Under Windows, the DEFAULT parameter can be used to set the icon
		# for the widget and any descendents that don't have an icon set
		# explicitly.  DEFAULT can be the relative path to a .ico file
		# (example: root.iconbitmap(default='myicon.ico') ).
		if platformIsWindows:
			try:
				top.iconbitmap(default=iconPath)
			except:
				try:
					top.iconbitmap(default=os.path.join(os.path.dirname(sys.argv[0]), iconFile))
				except:
					try:
						top.iconbitmap(default='@oojsc.xbm')
					except:
						pass
		else:
			try:
				tempicon = PhotoImage(file = iconPath)
				top.iconphoto(False, tempicon)
			except:
				try:
					top.iconbitmap(iconPath)
				except:
					try:
						top.iconbitmap(os.path.join(os.path.dirname(sys.argv[0]), iconFile))
					except:
						try:
							top.iconbitmap('@oojsc.xbm')
						except:
							pass

## app window and widgets ##################################################

	def makeFonts(self):
		opt = self.localOptions
		self.defaultFont = tkFont.Font(family=opt['Family'], size=opt['Size'],
									   weight=opt['Weight'], slant=opt['Slant'])
		self.lineSpace = self.defaultFont.metrics('linespace')
		self.emphasisFont = self.defaultFont.copy()
		self.searchMarkFont = self.defaultFont.copy()
		if opt['Weight'] == 'normal':
			self.emphasisFont.configure(weight='bold')
			self.searchMarkFont.configure(underline=1, weight='bold')
		elif opt['Slant'] == 'roman':
			self.emphasisFont.configure(slant='italic')
			self.searchMarkFont.configure(underline=1, slant='italic')
		else:
			self.emphasisFont.configure(size=opt['Size']+2)
			self.searchMarkFont.configure(underline=1, size=opt['Size']+2)
	
	def createWindows(self):
		self.tried=0					# counter for messages when there's no connection (see runCmd())

		self.appWindow = PanedWindow(self, orient=VERTICAL, sashwidth=5)
		self.appWindow.grid(sticky=S+E+W+N)
		# main display
		self.bodyText = ScrollingText(self.appWindow, editable=False, undo=True, font=self.defaultFont,
									 exportselection=0, wrap=WORD)
		self.bodyText.tag_config('emphasis', font=self.emphasisFont)
		self.bodyText.tag_config('searchMark', font=self.searchMarkFont)
		# command window
		self.cmdLine = ScrollingText(self.appWindow, editable=True, undo=True, histCmd=self.deleteCurrentCmd, 
									 font=self.defaultFont, exportselection=0, wrap=WORD)
		self.cmdLine.frame.config(bg=self.COLORS['background']) # behind buttons below
		self.cmdLine.tag_config('emphasis', font=self.emphasisFont)
		self.cmdLine.tag_config('searchMark', font=self.searchMarkFont)
		
		self.btnRun = Button(self.cmdLine.frame, text='Run', bg='#ccc', 
								font=self.defaultFont, command=self.runCmd)
		self.btnCmdClr = Button(self.cmdLine.frame, text='Clear', bg='#ccc', 
								font=self.defaultFont, command=self.cmdClear)

		self.cmdLine.scrollbar.grid(column=2)# move over to make room for buttons
		self.btnCmdClr.grid(row=0,  column=1, sticky=SE)
		self.btnRun.grid(	row=1,	column=1, sticky=SW)
		
		self.update_idletasks()
		runWidth, runHeight = self.btnRun.winfo_reqwidth(), self.btnRun.winfo_reqheight()
		clrWidth, clrHeight = self.btnCmdClr.winfo_reqwidth(), self.btnCmdClr.winfo_reqheight()
		self.btnRun.grid(ipadx=(clrWidth - runWidth)//2)
		btnsHeight = clrHeight + runHeight
		self.appWindow.add(self.bodyText.frame, minsize=btnsHeight, stretch='always')
		self.appWindow.add(self.cmdLine.frame,  minsize=btnsHeight, stretch='always', height=btnsHeight)
			
		self.cmdLine.bind('<Escape>', self.cmdClear)
		self.cmdLine.bind('<Return>', self.runCmd)
		self.cmdLine.bind('<Up>', self.cmdHistoryBack)
		self.cmdLine.bind('<Down>', self.cmdHistoryForward)
		self.cmdLine.bind('<Tab>', lambda e: self.cmdSearchHistory(-1))
		self.cmdLine.bind('<Shift-Tab>', lambda e: self.cmdSearchHistory(1))
		self.cmdLine.bind('<Control-Delete>', self.deleteCurrentCmd)
		self.cmdLine.bind('<Control-BackSpace>', self.deleteCurrentCmd)
		self.cmdLine.focus_set()
	
	def updateForFontChange(self):			# update cmdLine buttons, sash, menus after a font size change
		self.update_idletasks()
		runWidth, runHeight = self.btnRun.winfo_reqwidth(), self.btnRun.winfo_reqheight()
		clrWidth, clrHeight = self.btnCmdClr.winfo_reqwidth(), self.btnCmdClr.winfo_reqheight()
		self.btnRun.grid(ipadx=(clrWidth - runWidth)//2)
		btnsHeight = clrHeight + runHeight
		self.appWindow.paneconfig(self.bodyText.frame, minsize=clrHeight, sticky=S+E+W+N)
		self.appWindow.paneconfig(self.cmdLine.frame, minsize=btnsHeight, sticky=S+E+W+N, height=btnsHeight)
		
		self.update_idletasks()				# required for sash_place to work after above changes
		self.appWindow.sash_place(0, 0, self.btnCmdClr.winfo_rooty())
		self.screenLines = None				# recompute height of screen lines
		self.spaceLen = self.eSpaceLen = None # recompute length of spaces
		self.ellipsisLen = None
		self.measuredWords.clear()			# clear cached measurements
		self.measuredEWords.clear()			#   "
		self.aliasValueWidth = None
		font = self.defaultFont
		self.lineSpace = font.metrics('linespace')
		self.bodyText.popup.defaultFont = font 
		self.cmdLine.popup.defaultFont = font

		mouseXY = self.aliasWindow.mouseXY if hasattr(self.aliasWindow, 'mouseXY') else None
		self.aliasWindow.destroy()
		self.createAliasFrame()
		if mouseXY:
			self.aliasWindow.mouseXY = mouseXY
	
	def closeAnyOpenFrames(self, event=None): # a postcommand to pulldown menus, close any open frames
		if hasattr(self, 'aliasWindow') and self.aliasWindow.state() == 'normal':
			self.aliasWindow.closeTop()
			if hasattr(self.aliasWindow, 'mouseXY'):
				self.localOptions['AliasWindow'] = str(self.aliasWindow.mouseXY)
		if hasattr(self, 'fontSelectTop') and self.fontSelectTop.state() == 'normal':
			self.fontSelectTop.closeTop()
		if hasattr(self.bodyText.popup, 'searchBox') and self.bodyText.popup.searchBox.state() == 'normal':
			self.bodyText.popup.searchBox.closeTop()
		if hasattr(self.cmdLine.popup, 'searchBox') and self.cmdLine.popup.searchBox.state() == 'normal':
			self.cmdLine.popup.searchBox.closeTop()
		for msg in openMessages:
			msg.closeMessageBox()
		del openMessages[0:]

## Debug Menu ##############################################################

	debugOptions = {					# tkinter variables (NB: all debugOptions are off until connection)
		'showLog': None,				# IntVar for showing 'log' messages in console, a *local* option vs Mac
		'logMsgCls': {},		 		# a dict of class string and IntVar's
		'debugFlags': {},				# a dict of flag name and IntVar's
		'wireframe': None,				# IntVar for toggling wireframe graphics -is read-only
		'showFPS': None,				#  "			"	displaying fps stats (Shift-F)
		'timeAcceleration': None, 		# StringVar used to query current state
		'timeAccelerationSlow': None, 	# StringVar for slow menu
		'timeAccelerationFast': None, 	# IntVar for fast menu
	}
	
	consoleOptions = OrderedDict((
		# properties queryable from cmdLine but added for convenience
		('Detail level', detailLevels),
		('Max. detail level', 'maximumDetailLevel'),
		# ('FPS display', ['status', 'toggle']),	# already in debugOptions
		('pedanticMode', ['status', 'toggle']),
		('ignoreDroppedPackets', ['status', 'toggle']),
		('Platform details', ['platformDescription', 'glVendorString', 'glRendererString', 
							  'glFixedFunctionTextureUnitCount', 'glFragmentShaderTextureUnitCount',])
	))
	
	consoleFunctions = OrderedDict((
		# 0-arg functions available from cmdLine but added for convenience
		('clear console', 'console.clearConsole()'),
		('script stack', 'log(console.scriptStack())'),
		('write JS memory stats', 'console.writeJSMemoryStats()'),
		('garbage collect', 'log("collecting garbage: " + console.garbageCollect())'),
		('', ''),
		# ('use at your own risk!', ''),
		('write memory stats!', 'console.writeMemoryStats()'),
	))
### add 2nd version 'dump memory stats'	that's log file only
	TRANS_CHARS = ' .,!'	# char to be removed from key when assigning label
		
	def createDebugMenus(self):			# create an Debug pulldown menu
		debugMenu = self.debugMenu = OoBarMenu(self.menubar, label='Debug', 
										font=self.defaultFont,
										postcommand=self.closeAnyOpenFrames)
		debug = self.debugOptions

		# showLog is a local option placed here for consistency w/ Mac version
		debug['showLog'] = IntVar(value=1, name='dbgMenu_showLog')		
		debugMenu.add_checkbutton(label='Show Log', variable=debug['showLog'])

		self.logMsgMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		for cls in logMessageClasses.keys():
			debug['logMsgCls'][cls] = IntVar(name='dbgMenu_logMsg_'+cls.replace(' ', '_'))
			tkVar = debug['logMsgCls'][cls]
			self.logMsgMenu.add_checkbutton(label=cls, variable=tkVar,
						command=lambda tk=tkVar, s=cls: self.setDebugFromCheckButton('logMsgCls', tk, s))
		debugMenu.add_cascade(label='Log Message Classes', stateChange=True, 
								menu=self.logMsgMenu, state=DISABLED)

		debugMenu.add_command(label='Insert Log Marker', stateChange=True, 
								command=self.writeLogMarker, state=DISABLED)

		self.dbgFlagsMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		self.dbgFlagsMenu.add_command(label='Full debug on', command=lambda: self.setAllDebugFlags(False))
		self.dbgFlagsMenu.add_command(label='All debug flags off', command=lambda: self.setAllDebugFlags(True))
		self.dbgFlagsMenu.add_separator()
		debug['debugFlags']['allFlags'] = IntVar(name='dbgMenu_debugFlagsQuery') # var for all flags as rtn'd from oolite
		for flag in debugFlags.keys():
			debug['debugFlags'][flag] = IntVar(name='dbgMenu_dbgFlags'+flag[7:])
			tkVar = debug['debugFlags'][flag]
			self.dbgFlagsMenu.add_checkbutton(label=flag, variable=tkVar,
						command=lambda tk=tkVar, s=flag: self.setDebugFromCheckButton('debugFlags', tk, s))
		debugMenu.add_cascade(label='Debug Flags', stateChange=True, menu=self.dbgFlagsMenu, state=DISABLED)

		debug['wireframe'] = IntVar(name='dbgMenu_wireframe')
		debugMenu.add_checkbutton(label='Wireframe Graphics', 
						variable=debug['wireframe'], state=NORMAL,# DISABLED,
						command=lambda: self.setDebugFromCheckButton('wireframe', debug['wireframe']))

		debug['showFPS'] = IntVar(name='dbgMenu_showFPS')
		debugMenu.add_checkbutton(label='Display FPS', stateChange=True, 
						variable=debug['showFPS'], state=DISABLED,
						command=lambda: self.setDebugFromCheckButton('showFPS', debug['showFPS']))

		self.dbgtimeAccelSlowMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		debug['timeAcceleration'] = StringVar(name='dbgMenu_timeAccelQuery') # used only for queries
		self.addTraceTkVar(debug['timeAcceleration'], self.checkTimeAccel)
		debug['timeAccelerationSlow'] = StringVar(value='1', name='dbgMenu_timeAccelSlow')
		for factor in range(16):
			value = '1' if factor == 0 else '1/2' if factor == 8 else \
					'{}/4'.format(factor//4) if factor % 4 == 0 else \
					'{}/8'.format(factor//2) if factor % 2 == 0 else '{}/16'.format(factor)
			self.dbgtimeAccelSlowMenu.add_radiobutton(label=value, 
					variable=debug['timeAccelerationSlow'], font=self.defaultFont,
					value=value, command=lambda f=factor: self.setSlowTimeAcceleration(f))
		debugMenu.add_cascade(label='Time Acceleration slow', stateChange=True, 
								menu=self.dbgtimeAccelSlowMenu, state=DISABLED)
		
		debug['timeAccelerationFast'] = IntVar(value=1, name='dbgMenu_timeAccelFast')
		self.dbgtimeAccelFastMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		for factor in range(1, 17):
			self.dbgtimeAccelFastMenu.add_radiobutton(label=str(factor), 
					variable=debug['timeAccelerationFast'], font=self.defaultFont,
					value=str(factor), command=lambda f=factor: self.setFastTimeAcceleration(f))
		debugMenu.add_cascade(label='Time Acceleration fast', stateChange=True, 
								menu=self.dbgtimeAccelFastMenu, state=DISABLED)
		
		debugMenu.add_separator()
		plistTkvars = self.plistTkvars
		for show, key in showConsoleForDebug.items():
			plistTkvars[key] = IntVar(name='dbgMenu_'+key)	
			# these options are mirrored in Settings menu (here for consistency w/ Mac version)
			debugMenu.add_checkbutton(label=show, stateChange=True, 
						variable=plistTkvars[key], state=DISABLED,
						command=lambda k=key: self.setClientCheckButton(k, plistTkvars[k]))

		self.consolePropMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		self.consoleCmdMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		for key, value in self.consoleOptions.items():
			if isinstance(value, dict):
				self.detailLevelVar = StringVar(name='dbgMenu_detailLevel')
				subMenu = Menu(self.consolePropMenu, tearoff=0, font=self.defaultFont)
				for descr, level in value.items():
					cmd = 'console.detailLevel = "{}"; log("console.detailLevel: " + console.detailLevel)'.format(level)
					label = 'setDetailLevel{}'.format(level)
					subMenu.add_radiobutton(label=descr, variable=self.detailLevelVar, value=level, 
											command=lambda x=cmd, y=label: self.queueSilentCmd(x, y))
				self.consolePropMenu.add_cascade(label=key, menu=subMenu)
			elif isinstance(value, list):
				if value == ['status', 'toggle']:
					subMenu = Menu(self.consolePropMenu, tearoff=0, font=self.defaultFont)
					cmd = 'log("{}: " + console.{})'.format(key, key)
					label = 'status{}'.format(key.capitalize())
					subMenu.add_command(label='status', command=lambda x=cmd, y=label: self.queueSilentCmd(x, y))
					cmd = 'console.{0} = !console.{0}; log("{0}: " + console.{0})'.format(key)
					label = 'toggle{}'.format(key.capitalize())
					subMenu.add_command(label='toggle', command=lambda x=cmd, y=label: self.queueSilentCmd(x, y))
					self.consolePropMenu.add_cascade(label=key, menu=subMenu)
				else:
					self.consolePropMenu.add_separator()
					label = key.replace(' ', '')
					self.consolePropMenu.add_command(label='All {}'.format(key), 
						command=lambda x=value, y=label: self.queueSilentPropQueryList(x, y))
					subMenu = Menu(self.consolePropMenu, tearoff=0, font=self.defaultFont)
					for spec in value:
						cmd = 'log("{} = " + console.{})'.format(spec, spec)
						label = 'query{}'.format(spec.capitalize())
						subMenu.add_command(label=spec, command=lambda x=cmd, y=label: self.queueSilentCmd(x, y))
					self.consolePropMenu.add_cascade(label=key, menu=subMenu)
			else:
				cmd = 'log("{}: " + console.{})'.format(value, value)
				label = 'query{}'.format(value.capitalize())
				self.consolePropMenu.add_command(label=key, command=lambda x=cmd, y=label: self.queueSilentCmd(x, y))
		debugMenu.add_cascade(label='Console Properties', stateChange=True, menu=self.consolePropMenu, state=DISABLED)

		self.consoleCmdMenu = Menu(debugMenu, tearoff=0, font=self.defaultFont)
		removeChars = None if Python2 else ''.maketrans( '', '', self.TRANS_CHARS ) # delete chars in arg 3
		for key, value in self.consoleFunctions.items():
			if len(key) == 0 and len(value) == 0:
				self.consoleCmdMenu.add_separator()
			elif len(value) == 0:
				self.consoleCmdMenu.add_command(label=key, command=None)
			else:
				if Python2:	#  'alphabet code'.translate(None, 'abc')
					cmd = lambda x=value, y=key: self.queueSilentCmd(x, y.translate(None, self.TRANS_CHARS))
				else: 		#  'alphabet code'.translate(''.maketrans({'a': '', 'b':'', 'c':''}))
					# removeChars = ''.maketrans( {chr: '' for chr in self.TRANS_CHARS} ) # delete chars in arg 3
					cmd = lambda x=value, y=key: self.queueSilentCmd(x, y.translate(removeChars))
				self.consoleCmdMenu.add_command(label=key, command=cmd)
		debugMenu.add_cascade(label='Console Commands', stateChange=True, menu=self.consoleCmdMenu, state=DISABLED)
		
		debugMenu.add_separator()
		self.entityDumpVar = IntVar(name='entityDumpVar') # internal flag to restore Show Log if necessary
		self.addTraceTkVar(self.entityDumpVar, self.entityListDumped)
		debugMenu.add_command(label='Dump Entity List', stateChange=True, command=self.dumpEntityList, state=DISABLED)
		debugMenu.add_command(label='Dump Player State', stateChange=True, command=self.dumpPlayerState, state=DISABLED)
		self.playerHasTarget = IntVar(name='dbgMenu_playerHasTarget')		# off until connection says otherwise
		self.addTraceTkVar(self.playerHasTarget, self.dumpPlayersTarget)
		debugMenu.add_command(label='Dump Target State', stateChange=True, command=self.checkPlayersTarget, state=DISABLED)

		debugMenu.add_separator()
		debugMenu.add_command(label='Exit', command=self.exitCmd)
		
	def sixteenths(self, value):
		# arg 'factor' has time factor encoded 1..15 is a fractional value, factor/16
		factor = int(value)
		return '1' if factor == 0 else '1/2' if factor == 8 else \
				'{}/4'.format(factor//4) if factor % 4 == 0 else \
				'{}/8'.format(factor//2) if factor % 2 == 0 else '{}/16'.format(factor)
		
	def setSlowTimeAcceleration(self, factor):	# handler for timeAccelerationSlow subMenu: StringVar has '1', '1/2', etc
		cmd = 'timeAccelerationFactor = {}'.format(self.sixteenths(factor))
		self.queueSilentCmd(cmd, 'timeAccelSlow')
		self.queryTimeAcceleration()
					
	def setFastTimeAcceleration(self, factor):	# handler for timeAccelerationFast subMenu: IntVar has 0..16
		cmd = 'timeAccelerationFactor = {}'.format(factor)
		self.queueSilentCmd(cmd, 'timeAccelFast')
		self.queryTimeAcceleration()
		
	def queryTimeAcceleration(self):
		self.queueSilentCmd('timeAccelerationFactor', 'timeAccelQuery', self.debugOptions['timeAcceleration'])
	
	# handler for Tk var trace: debugOptions['timeAcceleration']
	def checkTimeAccel(self, *args):
		accel = float( self.debugOptions['timeAcceleration'].get() )
		self.debugOptions['timeAccelerationSlow'].set(
			'1' if accel == 1 else '' if accel > 1 else self.sixteenths(accel * 16))
		self.debugOptions['timeAccelerationFast'].set(0 if accel < 1 else int(accel))
		
	def queueSilentPropQueryList(self, cmds, label):
		cmd = 'log('
		last = cmds[-1]
		for cs in cmds:
			cmd += '"{0} = " + console.{0}'.format(cs)
			cmd += '' if cs == last else ' + "\\n" + '
		cmd += ');'
		self.queueSilentCmd(cmd, label)
			
	def writeLogMarker(self):
		self.queueSilentCmd('console.writeLogMarker()', 'logMarker')

	def dumpEntityList(self):			#  send IIFE as not in oolite-debug-console.js
		# don't worry about when enabled, as there exists player & ship @ start of game
		#  ie. 1st screen: 'Start new...', 'Load...'
		showLog = self.debugOptions['showLog'].get()
		if showLog:						# temporary suspend logging to console
			self.debugOptions['showLog'].set(0)
		cmd = ('(function() { '
				  'var text = ""; '
				  'var list = system.filteredEntities(console, function(){return true;}, player.ship); '
				  'for( let i = 0, len = list.length; i < len; i++ ) text += "\\n" + list[i]; '
				  'log("console", text); '
				  'return "no result<label:dumpEntityList><discard:yes>"; '
				'})()')
		self.queueSilentCmd(cmd, 'dumpEntityList')
		if showLog:
			cmd = ('(function() { return "no result<label:entityDumpVar><discard:yes>"; })()') # signals dump complete
			self.queueSilentCmd(cmd, 'entityDumpVar', self.entityDumpVar)
		self.colorPrint('')
		self.colorPrint('Entity list saved to   Latest.log')

	# handler for Tk var trace: entityDumpVar
	def entityListDumped(self, *args):
		self.debugOptions['showLog'].set(1)
	
	def dumpPlayerState(self):
		self.queueSilentCmd('player.ship.dumpState()', 'dumpPlayerState')
		self.colorPrint('')
		self.colorPrint('Player\'s state saved to   Latest.log')

	def checkPlayersTarget(self):
		cmd = 'player.ship.target !== undefined && player.ship.target !== null'
		self.queueSilentCmd(cmd, 'playerHasTarget', self.playerHasTarget)

	# handler for Tk var trace: playerHasTarget
	def dumpPlayersTarget(self, *args):
		if self.playerHasTarget.get() == 1:
			self.queueSilentCmd('player.ship.target.dumpState()', 'dumpPlayersTarget')
			self.colorPrint('')
			self.colorPrint('Player\'s target saved to   Latest.log')
		else:
			openMessages.append(OoInfoBox(self.top,'Player\'s ship has no target.', font=self.defaultFont, destruct=5))

	def setAllDebugFlags(self, setOff):
		cmd = 'console.debugFlags = {}'.format('0' if setOff else str(allDebugFlags))
		self.queueSilentCmd(cmd, 'debugFlags', self.debugOptions['debugFlags']['allFlags'])
		
	def setDebugFromCheckButton(self, varName, tkVar, key=None):
		value = tkVar.get()
		if varName == 'logMsgCls':
			cmd = 'console.setDisplayMessagesInClass("{}", {})'.format(key, 'true' if value else 'false')
			self.queueSilentCmd(cmd, 'set_{}'.format(key))
			cmd = 'console.displayMessagesInClass("{}")'.format(key)
			self.queueSilentCmd(cmd, key, self.debugOptions['logMsgCls'][key])
		elif varName == 'debugFlags':
			cmd = 'console.debugFlags {} {}'.format(' |= ' if value else ' &= ~', str(debugFlags[key]))
			self.queueSilentCmd(cmd, 'debugFlags', self.debugOptions['debugFlags']['allFlags'])
		elif varName == 'wireframe':
			openMessages.append(OoInfoBox(self.top,
				'"wireframe" option is unsupported at present.\n(it requires a fix in oolite)\nPost a message in the forum if you\'d use this option.',
				font=self.defaultFont, destruct=7))
			tkVar.set(0) # for now ...
			# cmd = 'Object.defineProperty(oolite.gameSettings, "wireframeGraphics", {value: {}, writable: true}'.format(1 if value else 0)
			# self.queueSilentCmd(cmd, 'set_wireframe') # returns dump of entire object
			# cmd = 'oolite.gameSettings["wireframeGraphics"]'
			# self.queueSilentCmd(cmd, 'wireframe', self.debugOptions['wireframe'])
		elif varName == 'showFPS':
			cmd = 'console.displayFPS = {}'.format('true' if value else 'false')
			self.queueSilentCmd(cmd, 'showFPS', self.debugOptions['showFPS'])
		else:
			errmsg = 'Unsupported button "{}", value = {}'.format(varName, value)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace(errmsg)
			else: 		
				debugLogger.debug(errmsg)

	def setDebugOption(self, label, value, tkVar): # called by handleMessage
		if label not in ['gameStarted', 'pollDebugFlags', 'pollStarSystem']:
			errmsg = 'Label: {}, value: {}, tkVar: {} = "{}"'.format(label, value, tkVar, tkVar.get())
			debugLogger.debug(errmsg)
			
		isStr = isinstance(value, str)
		isInt = isinstance(value, int)
		# if isInt or (isStr and value.isdigit()):
		if isInt or (isStr and (value.isdigit() or '-' in value)):
			intVal = int(value)
			if label in ['debugFlags', 'pollDebugFlags']:
				for flag, mask in debugFlags.items():
					self.debugOptions['debugFlags'][flag].set(1 if intVal & mask else 0)
			elif label == 'wireframe':
				# tkVar.set(1 if value else 0) # can't know type until implemented (?move below)
				tkVar.set(0) ## tmp until core starts polling gameSettings
			elif label == 'timeAccelQuery':
				self.debugOptions['timeAcceleration'].set(value)
			else: 		
				errmsg = 'Unsupported label: {}, value: {}, type: {}'.format(label, value, type(value))
				if dca.g['debug']:
					print(errmsg)
					print_exc()
					pdb.set_trace()
				else: 		
					debugLogger.warning(errmsg)
		elif isStr and label == 'pollStarSystem':
			system = value.strip('[]')	# eg System 0:240 "Raleen"
			currSystem = self.currStarSystem.get()
			if system != currSystem:
				self.currStarSystem.set(system)
		elif isStr and value in ['true', 'false']:
			tkVar.set(1 if value == 'true' else 0)
		elif isStr and all(v in '.0123456789' for v in value):
			tkVar.set(value)	# Tk's DoubleVar aren't doubles, leave as string
			# tkVar.set(float(value))
		else:
			errmsg = 'Wrong type for label: {}, value: {}, type: {}'.format(label, value, type(value))
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else: 		
				debugLogger.warning(errmsg)

## startup step 1				
	def initDebugMenu(self):	# also called by restoreMsgTraffic
		self.debugMenu.changeAllStates(NORMAL)
		debug = self.debugOptions
		self.queryTimeAcceleration()
		for lmc in logMessageClasses:
			self.queueSilentCmd('console.displayMessagesInClass("{}")'.format(lmc), lmc, debug['logMsgCls'][lmc])
		self.queueSilentCmd('console.debugFlags', 'debugFlags', debug['debugFlags']['allFlags'])
		# self.queueSilentCmd('oolite.gameSettings.wireframeGraphics', 'wireframe', debug['wireframe'])
		# - setting is read-only, must use in game options menu
		#   => can set value but ignored by game
		self.queueSilentCmd('console.displayFPS', 'showFPS', debug['showFPS'])
		self.queueSilentCmd('console.detailLevel', 'detailLevel', self.detailLevelVar)
		self.queryScriptProps()	# proceed to step 2
		self.sessionInitialized = 'in progress'

## Options Menu ############################################################

	localOptions = {  					# local options (except font*) from CFGFILE
		'SaveConfigOnExit': True,
		'SaveConfigNow': False,			# this is a local tkvar, not written to .cfg
		'SaveHistoryOnExit': True,
		'Geometry': DEFAULT_GEOMETRY,
		'AliasWindow': DEFAULT_ALIAS_POSN,
		'ConsolePort': 8563,
		'EnableShowConsole': True,
		'MacroExpansion': True,			# show 'macro-expansion' messages in console
		'TruncateCmdEcho': False,		# shorten commands echo'd to a single line
		'ResetCmdSizeOnRun': True,		# reset cmdLine's size after cmd is run
		'MsWheelHistory': False,		# allow mouse wheel to scroll through cmd history
		'PlistOverrides': True,
		'Aliases': {},
	}
	localOptnText = OrderedDict((
		('SaveConfigOnExit', 	'Save configuration on exit'),
		('SaveConfigNow', 		'Save configuration Now!'),
		('SaveHistoryOnExit', 	'Save command history on exit'),
		('EnableShowConsole', 	'Enable ShowConsole'),
		('MacroExpansion',		'Expand macro when executing'),
		('TruncateCmdEcho', 	'Truncate commands when echoing'),
		('ResetCmdSizeOnRun', 	'Resize the command window on Run'),
		('MsWheelHistory', 		'Mouse wheel scrolls History'),
		('PlistOverrides', 		'Use Oolite plist for local font/colors'),
	))
	localOptnVars = {}					# dict of tkinter vars for menus
	
	def createOptionsMenus(self): 		# create an Options pulldown menu
		self.optionsMenu = OoBarMenu(self.menubar, label='Options', 
										font=self.defaultFont, 
										postcommand=self.closeAnyOpenFrames)
		menu = self.optionsMenu
		opt = self.localOptions
		tkvars = self.localOptnVars
		text = self.localOptnText

		for key, text in text.items():
			tkvars[key] = IntVar(name='optMenu_'+key, value=1 if opt[key] else 0)
			menu.add_checkbutton(label=text, variable=tkvars[key],
							command=lambda k=key: self.setOptionFromCheckButton(k, tkvars[k]))

		menu.add_command(label='Aliases ...', command=self.showAliasWindow)
		self.sessionStartTime = StringVar(name='sessionStartTime')
		self.addTraceTkVar(self.sessionStartTime, self.sessionStarted)
		self.currentSessionTime = StringVar(name='currentSessionTime')
		self.addTraceTkVar(self.currentSessionTime, self.updateDebugMenu)

		menu.add_separator()
		for key, value in defaultConfig['Colors'].items():
			key = key.lower()
			menu.add_command(label=key, command=lambda k=key: self.pickLocalColour(k))
			self.setLocalColor(key, self.COLORS[key] if key in self.COLORS else value)

		# list of console.script's properties, to prevent collisions w/ aliases
		self.scriptPropsStr = StringVar(value='never set', name='scriptPropsStr')	
		self.addTraceTkVar(self.scriptPropsStr, self.loadScriptProps)

		menu.add_separator()
		self.logDebugMsgs = IntVar(name='logDebugMsgs', value=(1 if debugLogger.getEffectiveLevel() == DEBUG else 0))
		menu.add_checkbutton(label='toggle debug messsages', variable=self.logDebugMsgs, command=toggleDebugMsgs)

		## rest is debugging, to be deleted
		if dca.g['debug']:
			menu.add_command(label='open debugger', command=setTrace)

	def setOptionFromCheckButton(self, varName, tkVar):
		value = tkVar.get()
		opt = self.localOptions
		oldValue = opt[varName]
		opt[varName] = value
		if varName == 'PlistOverrides' and self.connectedToOolite:
			if oldValue and not value:	# switch to local values
				self.setFontFace(opt['Family'], skipUpdate=True)
				self.setFontSize(opt['Size'])	# these both call updateForFontChange, skipUpdate prevent unnecessary one
				for key, value in defaultConfig['Colors'].items():
					key = key.lower()
					self.setLocalColor(key, opt[key])
			elif not oldValue and value:# switch to values in oolite plist file
				self.setFontFace(self.settings['font-face'], skipUpdate=True)
				self.setFontSize(self.settings['font-size']) # these both call updateForFontChange, skipUpdate prevent unnecessary one
				for key, value in self.settings.items():
					if not key.endswith('-color'): continue
					self.setMsgColor(key, value)
		elif varName == 'MsWheelHistory':# redo bindings
			if platformIsLinux:
				if value == 0:
					self.cmdLine.unbind('<Button-4>')
					self.cmdLine.unbind('<Button-5>')
				else:
					self.cmdLine.bind('<Button-4>', self.mouseWheelEvent)
					self.cmdLine.bind('<Button-5>', self.mouseWheelEvent)
			else:
				if value == 0:
					self.cmdLine.unbind('<MouseWheel>')
				else:
					self.cmdLine.bind('<MouseWheel>', self.mouseWheelEvent)
		elif varName == 'SaveConfigNow':
			written = self.saveConfigFile()
			opt[varName] = False
			self.localOptnVars[varName].set(0)
			if written:
				dest = os.path.join(CFGFILE).replace(os.sep, '/')
				msg = 'configuration settings saved to   {}'.format(dest)
			else:
				msg = 'configuration not written as nothing has been changed'
			if self.connectedToOolite:
				cmd = 'log(console.script.name, "{}")'.format(msg)
				self.queueSilentCmd(cmd, 'save_Cfg')
			else:
				self.colorPrint('')
				self.colorPrint(msg)
		
	def mouseWheelEvent(self, event):
		if platformIsLinux:
			if event.num == 4: 			# scroll fwd
				self.cmdHistoryForward(event)
			elif event.num == 5: 		# scroll back
				self.cmdHistoryBack(event)
		else:
			if event.delta > 0 : 		#>= 120: # scroll fwd
				self.cmdHistoryForward(event)
			elif event.delta < 0: 		#<= -120: # scroll back
				self.cmdHistoryBack(event)

## Alias Functions #########################################################

	aliasDefns = {}						# dictionary of all defined aliases
	aliasCurrValues = {}				# dictionary of current value of alias
	aliasesPolled = {}					# dictionary of aliases polled
	aliasPollQueue = OrderedDict()
	def createAliasFrame(self):
		self.aliasWindow = TopWindow(self.top, 'Aliases', enduring=True, showNow=False)
		self.aliasWindow.bind('<Escape>', self.aliasWindow.closeTop)
		aliasFrame = self.aliasWindow.twFrame
		# NB: as this may be re-built, all vars must have aliasFrame as master (nope!)
		#                                       must be unset else become unreachable (nope!)
		#     (?Tk bug that Var's remain even after master destroy()'d)
		# Tkinter does not support variable unset, rather do variable deletion via __del__
		# - just make them permanent and outside aliasFrame
		defaultFont = self.defaultFont
		# row 0
		if not hasattr(self, 'currStarSystem'):
			self.currStarSystem = StringVar(name='currStarSystem')	# re-register aliases for each system
		if not hasattr(self, 'aliasMsgStr'):
			self.aliasMsgStr = StringVar(name='aliasMsgStr')
		self.aliasMsgLabel = Label(aliasFrame, textvariable=self.aliasMsgStr,
								   padx=4, anchor=W, font=defaultFont)
		if not hasattr(self, 'aliasRegStr'):
			self.aliasRegStr = StringVar(name='aliasRegStr')
		self.aliasRegLabel = Label(aliasFrame, textvariable=self.aliasRegStr,
								   padx=4, anchor=W, font=defaultFont)

		aliases = [k for k in self.aliasDefns.keys()]
		largest = 8 if len(self.aliasDefns) == 0 else max(len(a) for a in aliases)
		largest = max(largest, 8)
		aliasList = self.aliasListBox = ScrollingListBox(aliasFrame, width=largest,
										height=6, exportselection=0, font=defaultFont)
		aliases.sort(key=str.lower)
		aliasList.setContents(aliases)
		# row 1
		self.newAliasLabel = Label(aliasFrame, text='      Name:\nDefinition:',
									justify=LEFT, anchor=W, font=defaultFont)
		self.newAliasExample = Label(aliasFrame, text='Eg: ps\nEg: player.ship',
									justify=LEFT, anchor=W, font=defaultFont)
		if not hasattr(self, 'pollAliasVar'):
			self.pollAliasVar = IntVar(name='pollAliasVar')
		self.pollAliasCheck = Checkbutton(aliasFrame, variable=self.pollAliasVar, text='polled', 
										command=self.toggleAliasPoll, font=defaultFont)
		setAddBtn = self.register(self.setAliasButtonByEntry)
		if not hasattr(self, 'newAliasName'):
			self.newAliasName = StringVar(name='newAliasName')
		self.newAliasEntry = Entry(aliasFrame, textvariable=self.newAliasName,
									width=8, font=defaultFont, bg='#ddd', name='name',
									validate='key', validatecommand=(setAddBtn, '%P', '%W'))
		# row 2
		if not hasattr(self, 'aliasDefinition'):
			self.aliasDefinition = StringVar(name='aliasDefinition')
		self.aliasDefineEntry = Entry(aliasFrame, textvariable=self.aliasDefinition,
									  width=40, font=defaultFont, bg='#ddd', name='definition',
									  validate='key', validatecommand=(setAddBtn, '%P', '%W'))
		self.aliasDefineEntryClear = Button(aliasFrame, text='Clear', font=defaultFont,
											command=self.resetAliasEntry)
		# # row 3
		if not hasattr(self, 'aliasValue'):
			self.aliasValue = StringVar(name='aliasValue')
		self.aliasValueWidth = None
		self.aliasValueLabel = Label(aliasFrame, textvariable=self.aliasValue, anchor=W,
									  width=40, font=defaultFont, bg='#ccc', name='aliasValue')
		# row 4
		self.aliasDefineEntryAdd = Button(aliasFrame, text='Add', font=defaultFont,
											command=lambda: self.doAliasAction('add'))
		self.aliasDefineEntryDelete = Button(aliasFrame, text='Delete', font=defaultFont,
											command=lambda: self.doAliasAction('delete'))
		self.aliasDefineEntryUndo = Button(aliasFrame, text='Undo', font=defaultFont,
											command=lambda: self.doAliasAction('undo'))

		aliasList.restoreBox(rowspan=4, sticky=W)
		self.aliasMsgLabel.grid(			row=0,	column=1,	sticky=W, 	columnspan=3)
		self.aliasRegLabel.grid(			row=0,	column=3,	sticky=E, 	columnspan=2)
		self.newAliasLabel.grid(			row=1,	column=1, 	sticky=W, 	padx=4)
		self.newAliasEntry.grid(			row=1,	column=2,	sticky=W, 	padx=4, pady=2)
		self.newAliasExample.grid(			row=1, 	column=3, 	sticky=W)
		self.pollAliasCheck.grid(			row=1, 	column=4, 	sticky=E, 	columnspan=2)
		self.aliasDefineEntry.grid(			row=2,	column=1,	sticky=W, 	padx=4, columnspan=4)
		self.aliasDefineEntryClear.grid(	row=2,	column=5, 	sticky=E, 	padx=2)
		self.aliasValueLabel.grid(			row=3,	column=1,	sticky=W, 	padx=4, columnspan=5)
		self.aliasDefineEntryDelete.grid(	row=4,	column=1, 	sticky=S, 	padx=2)
		self.aliasDefineEntryUndo.grid(		row=4,	column=2, 	sticky=SE, 	padx=2)
		self.aliasDefineEntryAdd.grid(		row=4,	column=3, 	sticky=SE, 	padx=2)

		aliasList.bind('<Return>', self.selectAlias)
		aliasList.bind('<Double-ButtonRelease-1>', self.selectAlias)
		aliasList.bind('<<ListboxSelect>>', self.lookupAlias)
		self.newAliasEntry.bind('<Escape>', self.clearAliasEntry)
		self.newAliasEntry.bind('<Return>', self.newAliasAdd)
		self.aliasDefineEntry.bind('<Escape>', self.clearAliasEntry)
		self.aliasDefineEntry.bind('<Return>', lambda event: self.doAliasAction('add'))
		
		if 'AliasWindow' in self.loadedConfig and self.loadedConfig['AliasWindow'] != DEFAULT_ALIAS_POSN:
			mouseXY = self.loadedConfig['AliasWindow'].strip('[]')
			self.aliasWindow.mouseXY = list(map(int, mouseXY.split(',')))

	def resetAliasEntry(self, focus=True):# handler for 'Clear' button
		self.aliasDefinition.set('')
		self.aliasValue.set('')
		self.pollAliasVar.set(1)
		if focus:
			self.aliasDefineEntry.focus_set()
		
	aliasSelected = None				# index of alias selected
	def showAliasWindow(self):			# called from Options menu 
		aliases = [k for k in self.aliasDefns.keys()]
		aliases.sort(key=str.lower)
		aliasLB = self.aliasListBox
		aliasLB.select_clear(0, END)
		if self.aliasSelected is not None:
			aliasLB.activate(self.aliasSelected)
			aliasLB.see(self.aliasSelected)
		if self.aliasValueWidth is None:
			width = self.aliasDefineEntry.winfo_reqwidth() + self.aliasDefineEntryClear.winfo_reqwidth()
			self.aliasValueLabel.config(width=int(width / self.defaultFont.measure('0'))) 
			# - Tk uses spaces while the rest of the world uses em's
			self.aliasValueWidth = self.aliasValueLabel.winfo_reqwidth()
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		self.updateAliasButtons()
		aliasLB.focus_set()
		if hasattr(self.aliasWindow, 'mouseXY'):
			self.aliasWindow.restoreTop()
		else:
			try:									# initial opening of session
				aliasPosn = self.localOptions['AliasWindow']
				position = aliasPosn.strip('[]')
				posX, posY = map(int, position.split(','))
				if aliasPosn != DEFAULT_ALIAS_POSN: # open @ position from previous session
					self.aliasWindow.mouseXY = [posX, posY]
					self.aliasWindow.restoreTop()
				elif self.top.winfo_geometry() == DEFAULT_GEOMETRY:	# only use DEFAULT_ALIAS_POSN here
					self.aliasWindow.mouseXY = [posX, posY]
					self.aliasWindow.restoreTop()
				else:								
					self.aliasWindow.center()
			except:
				self.aliasWindow.center()

	def updateAliasButtons(self):
		currSelection = self.aliasListBox.curselection() if self.aliasListBox.size() > 0 else None
		self.aliasSelected = currSelection[0] if currSelection and len(currSelection) > 0 else None
		
		# print('updateAliasButtons, lb.size {}, curselection {}, aliasSelected {}'.format(
				# self.aliasListBox.size(), currSelection if currSelection and len(currSelection) else 'none',self.aliasSelected))
				
		self.aliasDefineEntryDelete['state'] = 	DISABLED	if self.aliasSelected is None 		else NORMAL 
		self.aliasDefineEntryUndo['state'] = 	NORMAL 		if len(self.aliasUndo) 				else DISABLED
		self.aliasDefineEntryAdd['state'] = 	NORMAL 		if len(self.newAliasName.get()) and \
																len(self.aliasDefinition.get()) else DISABLED

	def setAliasButtonByEntry(self, contents, who): # Entry validation for both fields
		name = contents if who.endswith('name') else self.newAliasName.get()
		defn = contents if who.endswith('definition') else self.aliasDefinition.get()
		if name == '':
			self.aliasDefineEntryAdd['state'] = DISABLED
			self.aliasDefineEntryDelete['state'] = DISABLED
		else:
			self.aliasDefineEntryAdd['state'] = DISABLED if defn == '' else NORMAL
			self.aliasDefineEntryDelete['state'] = NORMAL if name in self.aliasDefns else DISABLED
		if defn == '':
			self.aliasDefineEntryAdd['state'] = DISABLED
		else:
			self.aliasDefineEntryAdd['state'] = DISABLED if name == '' else NORMAL
		return True 					# allow all changes

	def updateAliasListBox(self, setSelection=None):
		aliases = [key for key in self.aliasDefns.keys()]
		aliases.sort(key=str.lower)
		self.aliasListBox.setContents(aliases)
		if setSelection and setSelection in aliases:
			self.setAliasListBoxTo( aliases.index(setSelection) )
		else:
			self.aliasListBox.selection_clear(0, END)

	def setAliasListBoxTo(self, index):
		if index is not None:
			self.aliasListBox.selection_clear(0, END)
			self.aliasListBox.selection_set(index)
			self.aliasListBox.see(index)
			self.aliasListBox.activate(index)
			alias = self.aliasListBox.get(index)
			self.newAliasName.set(alias)
			if alias in self.aliasDefns:
				aliasDef = self.aliasDefns[alias]
				self.aliasDefinition.set(aliasDef)
				self.setAliasPoll(alias)
	
	def doAliasAction(self, act): 		# handlers for buttons
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		if act == 'add':
			self.aliasEntryAdd()
		elif act == 'delete':
			self.aliasEntryDelete()
		elif act == 'undo':
			self.aliasEntryUndo()

	def clearAliasEntry(self, event=None):	# <Escape> handler for Entry fields
		if event.widget == self.newAliasEntry:
			self.newAliasName.set('')
		elif event.widget == self.aliasDefineEntry:
			self.aliasDefinition.set('')
			self.aliasValue.set('')
		self.updateAliasButtons()
		return 'break'

	def lookupAlias(self, event=None): 	# <<ListboxSelect>>
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		currSelection = self.aliasListBox.curselection() # returns tuple w/ indices of the selected element(s)
		if len(currSelection) > 0:
			self.aliasSelected = currSelection[0]
			alias = self.aliasListBox.get(currSelection[0])
			self.newAliasName.set(alias)
			self.verifyAlias(alias)
			if alias in self.aliasDefns:
				self.setAliasListBoxTo(self.aliasSelected)
				self.aliasMsgStr.set('')
			else:
				self.resetAliasEntry(focus=False)
				self.aliasMsgStr.set('alias not defined')
			self.updateAliasButtons()
		return 'break'
				
	def verifyAlias(self, alias):		# used by lookupAlias() (when <<ListboxSelect>> fires)
		self.aliasRegStr.set('')
		if self.connectedToOolite:
			# re-send every time for case where definition is dynamic, eg. ps.target
			self.sendAliasRegistration(alias)
		else:
			self.aliasRegStr.set('not connected')

	reserved = [ 'abstract', 'arguments', 'await', 'boolean', 'break', 'byte', 'case', 'catch', 'char',  
				 'class', 'const', 'constructor', 'continue', 'debugger', 'default', 'delete', 'do', 
				 'double', 'else', 'enum', 'eval', 'export', 'extends', 'false', 'final', 'finally', 
				 'float', 'for', 'function', 'goto', 'if', 'implements', 'import', 'in', 'instanceof', 
				 'int', 'interface', 'let', 'long', 'native', 'new', 'null', 'package', 'private', 
				 'protected', 'prototype', 'public', 'return', 'short', 'static', 'super', 'switch', 
				 'synchronized', 'this', 'throw', 'throws', 'transient', 'true', 'try', 'typeof', 'var', 
				 'void', 'volatile', 'while', 'with', 'yield' ]
				 
	def invalidAliasName(self, alias):
		if '\\' in repr(alias):
			self.aliasMsgStr.set('invalid character')
			return True
		if alias[0] not in '$_abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ':
			self.aliasMsgStr.set('must start w/ $, _, or letter')
			return True
		if alias in self.reserved:
			self.aliasMsgStr.set('reserved word')
			return True
		if any(ch in '\'"`' for ch in alias):
			self.aliasMsgStr.set('no quotes allowed in name')
			return True
		return False
		
	def newAliasAdd(self, event=None):	# <Return> in newAliasEntry
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		alias = self.newAliasName.get().strip()
		if self.invalidAliasName(alias):
			self.newAliasEntry.focus_set()
			return 'break'
		if len(alias):
			if alias in self.aliasDefns.keys():
				self.aliasMsgStr.set("alias '{}' already exists".format(alias))
				self.aliasDefinition.set(self.aliasDefns[alias])
			elif alias in self.scriptProps:
				self.aliasMsgStr.set("'{}' already in use".format(alias))
				self.newAliasName.set('')
				return 'break'					# remain
			else:								# update listbox and select it
				self.aliasDefns[alias] = ''
				self.updateAliasListBox(setSelection=alias) 
				self.aliasMsgStr.set("define new alias '{}'".format(alias))
			self.aliasDefineEntry.icursor(END)
			self.aliasDefineEntry.focus_set()	# move to definition box
			self.updateAliasButtons()
		else:
			self.aliasMsgStr.set('enter an alias name')
		return 'break'

	def validateDefinition(self, defn, report=True):
		defn = defn.strip().strip('\n\r\t\v')
		if defn.count('"') % 2 != 0:
			if report:
				self.aliasMsgStr.set('unbalanced "s')
			return False
		if defn.count("'") % 2 != 0:
			if report:
				self.aliasMsgStr.set("unbalanced 's")
			return False
		if defn.count("`") % 2 != 0:
			if report:
				self.aliasMsgStr.set("unbalanced `s")
			return False
		defn = defn.replace('"', "\'")	# need double quotes to submit alias (else syntax error)
		defn = defn.replace("'", "\'")
		defn = defn.replace("`", r"\`")
		return defn
			
	def aliasEntryAdd(self): 			# 'Add' button or <Return> in aliasDefineEntry
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		alias = self.newAliasName.get().strip()
		if self.invalidAliasName(alias):
			self.newAliasEntry.focus_set()
			return 'break'
		value = self.validateDefinition(self.aliasDefinition.get())
		if not value:
			return 
		if len(alias) == 0:
			self.aliasMsgStr.set('enter an alias name')
			self.newAliasEntry.focus_set()
		else:
			if len(value) > 0:
				self.addAlias(alias, value)
			else:	# executing a blank definition may be an attempt to delete
				msg = "{} '{}'".format('use Delete to remove' if alias in self.aliasDefns else 'define alias', alias)
				self.aliasMsgStr.set(msg)
		self.updateAliasButtons()
		
	def addAlias(self, alias, value, addUndo=True):
		if self.aliasDefns.get(alias) != value:
			exists = alias in self.aliasDefns and len(self.aliasDefns[alias]) > 0 # set to '' on creation
			if addUndo:
				addUndo = ['edit' if exists else 'del', alias, self.aliasDefns[alias] if exists else None]
				if len(self.aliasUndo) == 0 or self.aliasUndo[-1] != addUndo: 
					self.aliasUndo.append(addUndo)
				self.aliasMsgStr.set("'{}' {}".format(alias, 'changed' if exists else 'added'))
			else:						# performing an undo
				self.newAliasName.set(alias)
				self.aliasDefinition.set(value)
				self.aliasMsgStr.set("'{}' restored".format(alias))
			self.aliasDefns[alias] = value
			self.setAliasPoll(alias)
			self.updateAliasListBox(setSelection=alias)
			self.sendAliasRegistration(alias)
		elif addUndo:	# call initated by user, not undo mechanism
			self.aliasDefinition.set(self.aliasDefns[alias])
			self.aliasMsgStr.set("'{}' unchanged".format(alias))
	
	NO_ALIAS_FN_POLLING = compile(r'(?xs) [^f]* function | [^(]*[(]\s*function')
	def isAliasExec(self, defn):
		return self.NO_ALIAS_FN_POLLING.search(defn) is not None
	
	def defaultPolling(self, defn):		
		# set default based on: system... is dynamic
		#   worldScript... is usually static w/ one '.', unknowable otherwise
		#   never poll executables!
		if len(defn) == 0 or \
			(defn.startswith('worldScripts.') and defn.count('.') == 1 ) or \
			self.isAliasExec(defn):
			return False
		return defn.startswith('system.')

	def isAliasPolled(self, alias):
		return self.aliasesPolled[alias] if alias in self.aliasesPolled else self.defaultPolling(self.aliasDefns.get(alias, ''))
		
	def toggleAliasPoll(self):				# handler for 'polled' Checkbutton
		alias = self.newAliasName.get().strip()
		if len(alias) and not self.isAliasExec(self.aliasDefns.get(alias, '')):
			polled = self.isAliasPolled(alias)
			self.pollAliasVar.set(1 if not polled else 0)
			self.aliasesPolled[alias] = not polled
		else:
			self.pollAliasVar.set(0)
	
	def setAliasPoll(self, alias=None):
		alias = alias or self.newAliasName.get().strip()
		polled = False
		if len(alias):
			polled = self.isAliasPolled(alias) and not self.isAliasExec(self.aliasDefns.get(alias, ''))
			self.pollAliasVar.set(1 if polled else 0)
			self.aliasesPolled[alias] = polled
		return polled
			
	aliasUndo = []
	def aliasEntryUndo(self): 			# 'Undo' button
		# print('aliasEntryUndo, undos: {}'.format('nil' if len(self.aliasUndo) == 0 else '\n\t{}'.format(
				# ', '.join([str(x) for x in self.aliasUndo]))))
		if len(self.aliasUndo) > 0:
			self.aliasMsgStr.set('')
			self.aliasRegStr.set('')
			op, alias, value = self.aliasUndo.pop()
			if op == 'add':
				self.addAlias(alias, value, addUndo=False)
			elif op == 'del':
				self.deleteAlias(alias, addUndo=False)
			elif op == 'edit':
				self.addAlias(alias, value, addUndo=False)
				self.aliasMsgStr.set("'{}' un-edited".format(alias))
		self.updateAliasButtons()

	def selectAlias(self, event=None):	# <Double-ButtonRelease-1>/<Return> in listbox
		currSelection = self.aliasListBox.curselection() # returns tuple w/ indices of the selected element(s)
		if len(currSelection) > 0:
			alias = self.aliasListBox.get(currSelection[0])
			self.newAliasName.set(alias)
			self.aliasDefinition.set(self.aliasDefns[alias])
			self.aliasDefineEntry.icursor(END)
			self.aliasDefineEntry.focus_set()
			self.aliasMsgStr.set('')
		self.updateAliasButtons()
		return 'break' # so default event handlers don't fire
	
	ellipsisLen = None
	def showAliasValue(self, alias):
		font = self.defaultFont
		if self.ellipsisLen is None:		# 1st time or font's changed, see addWords()
			self.spaceLen = font.measure(' ')
			self.ellipsisLen = font.measure(' ...')
		spaceLen = self.spaceLen
		value = self.aliasCurrValues[alias].replace('\n', ' ').replace('\t', ' ')
		while '  ' in value:
			value = value.replace('  ', ' ')
		width, maxWidth = font.measure(value), self.aliasValueWidth
		if width > maxWidth:
			words, trunc = value.split(), ''
			measuredWords, width = self.measuredWords, self.ellipsisLen
			for word in words:
				if word not in measuredWords:
					measuredWords[word] = font.measure(word)
				wordLen = measuredWords[word]
				if width + wordLen > maxWidth: break
				trunc += word
				width += wordLen
				if width + spaceLen > maxWidth: break
				trunc += ' '
				width += spaceLen
			self.aliasValue.set(trunc.strip() + ' ...')
		else:
			self.aliasValue.set(value)
	
	def setAliasRegistry(self, label, value, tkVar=None):# used by processSilentCmd()
		_, alias, op = label.split('-')
		if op == 'send':								# NB: tkVar is None on 'send's
			self.aliasCurrValues[alias] = value
			valid = value != 'undefined' and not value.startswith('no result')
			if not valid: 		
				self.aliasRegistry[alias].set(0)
			if self.sessionInitialized:					# setup is complete (vs registerAllAliases stage of startup)
				if not valid: 							# do not delete as may be for diff oxp, still want it saved in cfg
					self.aliasMsgStr.set('invalid definition')
					self.reportRegistration(alias)
				elif alias not in self.aliasListBox.get(0, END):	# a newly created alias
					self.aliasMsgStr.set('definition accepted')
		elif op == 'poll':								# NB: tkVar is None on 'send's
			if alias in self.aliasPollsPending:
				del self.aliasPollsPending[alias]
			self.aliasCurrValues[alias] = value
			valid = value != 'undefined' and not value.startswith('no result')
			if not valid: 		
				self.aliasRegistry[alias].set(0)
		elif op == 'check':
			if alias in self.aliasRegistry:
				if isinstance(value, str) and value in ['true', 'false']:
					tkVar.set(1 if value == 'true' else 0)
					self.checkRegistration(alias)
				else:
					# tkVar.set(tkVar.get())				# trigger variable trace
					errmsg = 'setAliasRegistry, invalid value "{}" for alias "{}"'.format(value, alias)
					if dca.g['debug']:
						print(errmsg)
						print_exc()
						pdb.set_trace()
					else: 		
						debugLogger.error(errmsg)
		elif op == 'remove':
			tkVar.set(1 if value == 'false' else 0) # false => delete failed, so still registered
			self.reportOnDeletion(alias)
		else:
			errmsg = 'setAliasRegistry, invalid label "{}"'.format(label)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else: 		
				debugLogger.error(errmsg)

	aliasRegistry = {}					# dict of TkVars flags indicating successful registration
	def sendAliasRegistration(self, alias, followUp=True, poll=False):	# followUp is False only when initializing
		if self.connectedToOolite:
			if not poll:
				self.aliasRegStr.set('')
			if alias in self.aliasDefns:
				if alias not in self.aliasRegistry:
					self.aliasRegistry[alias] = IntVar(name='aliasReg_'+str(len(self.aliasRegistry))+'_'+alias)	# 0 => not registered
				defn = self.aliasDefns[alias].replace('\n', ' ')
				cmd = '''eval("console.script.{} = {}")'''.format(alias, defn)
				self.queueSilentCmd(cmd, 'alias-{}-{}'.format(alias, 'poll' if poll else 'send'))
				if followUp and not poll:
					self.sendRegistryCheck(alias)
				return True
		elif not poll:
			self.aliasRegStr.set('not connected')
		return False

	def reportRegistration(self, alias):# report on status of alias
		if alias and alias in self.aliasRegistry:
			registered = self.aliasRegistry[alias].get()
			if self.aliasRegistry[alias].get() == 1:
				self.aliasRegStr.set('Registered ok')
				self.updateAliasListBox(setSelection=alias)
			else:
				self.aliasRegStr.set('Did not register')
		else:
			errmsg = 'reportRegistration, alias is {}'.format('None' if alias is None else '"{}" is missing from aliasRegistry'.format(alias))
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else: 		
				debugLogger.error(errmsg)

	def sendRegistryCheck(self, alias):
		self.aliasRegistry[alias].set(-1)
		cmd = 'console.script.hasOwnProperty("{}")'.format(alias)
		self.queueSilentCmd(cmd, 'alias-{}-check'.format(alias), self.aliasRegistry[alias])

	def checkRegistration(self, alias):
		if alias and alias in self.aliasRegistry:
			registered = self.aliasRegistry[alias].get()
			if registered == 0:							# hasOwnProperty returned false, tkvar set to 0
				self.aliasRegStr.set('Unable to register')				
			else:
				self.showAliasValue(alias)
				self.reportRegistration(alias)
		else:
			errmsg = 'checkRegistration, alias is {}'.format('None' if alias is None else '"{}" is missing from aliasRegistry'.format(alias))
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else: 		
				debugLogger.error(errmsg)

	def aliasEntryDelete(self): 		# 'Delete' button
		self.aliasMsgStr.set('')
		self.aliasRegStr.set('')
		currSelection = alias = None
		listbox = list(self.aliasListBox.get(0, END))
		alias = self.newAliasName.get()
		if len(alias) == 0:				# deleting listbox entry?
			currSelection = self.aliasListBox.curselection() # - returns tuple w/ indices of the selected element(s)
			alias = listbox[currSelection[0]] if len(currSelection) > 0 else None
		self.deleteAlias(alias)
		self.updateAliasButtons()
			
	def deleteAlias(self, alias, addUndo=True):	# unregister prior to deletion / delete if never registered
		if alias and alias in self.aliasDefns:
			if addUndo:
				addUndo = ['add', alias, self.aliasDefns[alias]]
				if len(self.aliasUndo) == 0 or self.aliasUndo[-1] != addUndo: 
					self.aliasUndo.append(addUndo)
			if self.connectedToOolite:
				self.unregisterAlias(alias)
			elif self.aliasRegistry.get(alias, 0) < 1:
			# elif alias not in self.aliasRegistry or self.aliasRegistry[alias] < 1:
				self.removeAlias(alias)	# never registered during session
				self.newAliasName.set('')
				self.aliasDefinition.set('')
				self.aliasValue.set('')
			else:
				self.aliasMsgStr.set("connection required".format(alias))
			return

	def removeAlias(self, alias):				# remove alias from data base
		if self.newAliasName.get() == alias:	# user still has it selected (ie. was un-registered or didn't need to be)
			self.newAliasName.set('')
			self.aliasDefinition.set('')
			self.aliasValue.set('')
			self.aliasMsgStr.set("'{}' deleted".format(alias))
		if alias in self.aliasDefns:
			del self.aliasDefns[alias]
		if alias in self.aliasRegistry:
			if self.aliasRegistry[alias] == 1:
				self.unregisterAlias(alias)
			else:
				del self.aliasRegistry[alias]
				if alias in self.scriptProps:
					self.scriptProps.remove(alias)
		listbox = list(self.aliasListBox.get(0, END))
		if alias in listbox:
			index = listbox.index(alias) # one just deleted
			listbox.remove(alias)
			index = index if index < len(listbox) - 1 else len(listbox) - 1
			self.updateAliasListBox(setSelection=listbox[index] if 0 <= index < len(listbox) else None)

	def unregisterAlias(self, alias):
		if alias in self.aliasRegistry:
			if self.connectedToOolite:
				self.aliasRegistry[alias].set(-1)
				cmd = 'delete console.script["{}"]'.format(alias)
				self.queueSilentCmd(cmd, 'alias-{}-remove'.format(alias), self.aliasRegistry[alias])
			else:
				self.reportOnDeletion(alias) 
		else:
			self.removeAlias(alias)

	def reportOnDeletion(self, alias):
		if alias in self.aliasRegistry:	# in case it gets deleted while polling
			registered = self.aliasRegistry[alias].get()
			if registered == 0:					# delete returned false, tkvar set to 0
				if self.connectedToOolite:		
					self.aliasRegStr.set('Un-registered ok')
					self.removeAlias(alias)
				elif alias in self.aliasRegistry:
					self.aliasRegStr.set('Cannot un-register')
				else:
					self.aliasRegStr.set('') # was never registered
			elif registered == 1:
				self.aliasRegStr.set('Not un-registered')
			else:
				errmsg = 'reportOnDeletion, unsupported value for registered: {}'.format(registered)
				if dca.g['debug']:
					print(errmsg)
					print_exc()
					pdb.set_trace()
				else:
					debugLogger.warning(errmsg)

	aliasPollsPending = {}
	def pollAliases(self, count):
		if self.connectedToOolite:
			if len(self.aliasPollQueue) == 0:	# create new queue
				self.aliasPollQueue = OrderedDict(sorted([(k,v) for k,v in self.aliasDefns.items() \
											if k in self.aliasesPolled], key=lambda t: t[0]))
			while count > 0 and len(self.aliasPollQueue) > 0:
				alias, defn = self.aliasPollQueue.popitem(last=False) # False => FIFO
				if self.sendAliasRegistration(alias, poll=True):
					self.aliasPollsPending[alias] = clock() if Python2 else perf_counter()
					count -= 1

## Font Menu ############################################################

	FONTS = {							# like COLORS, these are internal working values
		# these 2 exist in console.settings(font-face, font-size), so changes of those also stored here (see PlistOverrides)
		'Family': 'arial',				# The font family name as a string.
		'Size': '10',					# The font height as an integer in points. To get a font n pixels high, use -n.
		# these 2 only appear locally in Font menu, as they are not supported in oolite
		'Weight': 'normal',				# "bold" for boldface, "normal" for regular weight.
		'Slant': 'roman',				# "italic" for italic, "roman" for unslanted.
	}
	fontOptionVars = {}					# dict of tkinter vars for fonts

	def createFontMenus(self): 			# create a Font pulldown menu
		self.fontMenu = OoBarMenu(self.menubar, label='Font', 
									font=self.defaultFont, 
									postcommand=self.closeAnyOpenFrames) 
		opt = self.FONTS
		tkvars = self.fontOptionVars

		# create font ListBox (even if no font-face in settings)
		self.fontMenu.add_command(label='Family (font-face) ...', command=self.selectFont)
		self.createFontSelectBox()

		# create font width menu
		fontSize = tkvars['font-size'] = IntVar(value=opt['Size'], name='fontMenu_font-size')
		self.fsizeMenu = Menu(self.fontMenu, tearoff=0)
		for size in range(8, 31):
			self.fsizeMenu.add_radiobutton(label=str(size), variable=fontSize, font=self.defaultFont,
					value=size, command=lambda s=size: self.setFontSize(s))
		self.fontMenu.add_cascade(label='Size (font-size)', menu=self.fsizeMenu)

		self.fontMenu.add_separator()
		fontWeight = tkvars['Weight'] = StringVar(value=opt['Weight'], name='fontMenu_Weight')
		self.weightMenu = Menu(self.fontMenu, tearoff=0)
		self.weightMenu.add_radiobutton(label='Normal', variable=fontWeight, font=self.defaultFont,
						value='normal', command=self.setFontWeight)
		self.weightMenu.add_radiobutton(label='Bold', variable=fontWeight, font=self.defaultFont,
						value='bold', command=self.setFontWeight)
		self.fontMenu.add_cascade(label='Font Weight', menu=self.weightMenu)

		fontSlant = tkvars['Slant'] = StringVar(value=opt['Slant'], name='fontMenu_Slant')
		self.weightMenu = Menu(self.fontMenu, tearoff=0)
		self.weightMenu.add_radiobutton(label='Roman', variable=fontSlant, font=self.defaultFont,
						value='roman', command=self.setFontSlant)
		self.weightMenu.add_radiobutton(label='Italic', variable=fontSlant, font=self.defaultFont,
						value='italic', command=self.setFontSlant)
		self.fontMenu.add_cascade(label='Font Slant', menu=self.weightMenu)
		
	def createFontSelectBox(self): 		# mk list of fonts, load into ListBox
		try:
			self.fontList = []
			families = tkFont.families()
			maxWidth = 0
			for item in families:
				if 'dings' in item: continue
				if item.startswith( 'Marlett' ): continue
				self.fontList.append(item)
				if len(item) > maxWidth: maxWidth = len(item)
			self.fontList.sort(key=str.lower)
			maxHeight = len(self.fontList)
			self.fontSelectTop = TopWindow(self.top, 'Select Font', enduring=True, showNow=False)
			self.fontSelectTop.bind('<Escape>', self.fontSelectTop.closeTop)
			fontBox = ScrollingListBox(self.fontSelectTop.twFrame, label='Oolite rocks!',
										width=20 if maxWidth == 0 else maxWidth, font=self.defaultFont,
										height=20 if maxHeight > 20 else maxHeight, exportselection=0)
			fontBox.restoreBox(sticky=S+E+W+N)
			# for item in self.fontList:
				# fontBox.insert(END, item)
			self.lowFontList = [font.lower() for font in self.fontList]
			fontBox.insert(END, *self.fontList)
			fontBox.bind('<<ListboxSelect>>', self.showFontFace)
			fontBox.bind('<Double-ButtonRelease-1>', self.fontSelected)
			fontBox.bind('<Return>', self.fontSelected)
			self.fontSelectListBox = fontBox
			savedFont = self.FONTS['Family']
			if savedFont.lower() in self.lowFontList:
				self.fontSelSelected = self.lowFontList.index(savedFont.lower())
			else:
				self.fontSelSelected = 0
		except Exception as exc: ########
			errmsg = 'Exception: {}'.format(exc)
			if dca.g['debug']:
				print(errmsg)
				pdb.set_trace() ########
				print_exc()
			else:
				debugLogger.exception(errmsg)

	def selectFont(self):				# open font selection box, set current font to inverse color
		fontBox = self.fontSelectListBox
		currFont = self.FONTS['Family']
		select = None
		if currFont in self.fontList:
			select = self.fontList.index(currFont)
		else:
			actual = self.defaultFont.actual('family')
			if actual in self.fontList:
				select = self.fontList.index(actual)
		for idx, item in list(enumerate(self.fontList)):
			fontBox.itemconfig(idx, foreground='black', background='white')
		if select is not None:
			fontBox.itemconfig(select, foreground='white', background='black')
		self.fontSelSelected = 0 if select is None else select
		fontBox.select_clear(0, END)
		fontBox.activate(self.fontSelSelected)
		fontBox.see(self.fontSelSelected)
		if not hasattr(self.fontSelectTop, 'mouseXY'):
			self.fontSelectTop.showAtMouse(self.winfo_pointerxy())
		else:
			self.fontSelectTop.restoreTop()
		fontBox.focus_set()

	def fontSelected(self, event):		# apply selected font, close dialog
		currSelection = self.fontSelectListBox.curselection() # returns tuple w/ indices of the selected element(s)
		if len(currSelection) > 0:
			self.setFontFace(self.fontList[ currSelection[0] ])
			self.fontSelectTop.closeTop()
		return 'break' 					# so default event handlers don't fire

	def showFontFace(self, event=None):	# re-write Label in current font
		selection = self.fontSelectListBox.curselection()
		if len(selection) > 0:
			self.updateFontBox(selection[0])

	def updateFontBox(self, index):
		fontBox = self.fontSelectListBox
		if index >= 0 and index < fontBox.size():
			fontBox.label.config(font=(self.fontList[index], self.FONTS['Size']))
			fontBox.select_clear(0, END)
			fontBox.selection_set(index)
			fontBox.see(index)
			self.fontSelSelected = index

	def setFontFace(self, face, plist=False, skipUpdate=False):	# plist only true when settings load upon connection to oolite
		override = self.localOptions['PlistOverrides']
		if not plist or override:
			self.FONTS['Family'] = face
			self.defaultFont.config(family=face)
			self.emphasisFont.config(family=face)
			self.updateFontBox(self.fontList.index(face))
			if not skipUpdate:							# to avoid back to back calls (see setOptionFromCheckButton())
				self.updateForFontChange()
		if not plist and override:					
			self.setClientSetting('font-face', face)	# self.settings is set in noteConfig, ie. upon confirmation

	def setFontSize(self, size, plist=False):	# plist only true when settings load upon connection to oolite
		override = self.localOptions['PlistOverrides']
		if not plist or override:
			self.FONTS['Size'] = size
			self.fontOptionVars['font-size'].set(size)	# reflect change in menu radiobutton
			self.defaultFont.config(size=size)
			self.emphasisFont.config(size=size)	
			self.updateFontBox(self.fontSelSelected)
			self.updateForFontChange()
		if not plist and override:				
			self.setClientSetting('font-size', size)	# self.settings is set in noteConfig, ie. upon confirmation

	def setFontWeight(self):
		weight = self.fontOptionVars['Weight'].get()
		self.FONTS['Weight'] = weight
		self.defaultFont.config(weight=weight)
		self.emphasisFont.config(weight=weight)

	def setFontSlant(self):
		slant = self.fontOptionVars['Slant'].get()
		self.FONTS['Slant'] = slant
		self.defaultFont.config(slant=slant)
		self.emphasisFont.config(slant=slant)

## Settings Menu ###########################################################

	# upon opening a new connection, oolite sends a dictionary of its settings, regardless of
	# whether or not the game has loaded/started.  We process those, then start polling
	# for the actual start before completing setup
	def initClientSettings(self, settings):	# create an Options pulldown menu; settings is a dict of all debugger settings
											# excepting 'font-face' & 'font-size', settings are booleans or colours
		self.disableClientSettings()	
		# this is not guaranteed to be called via connectionClosed (eg. terminate before disconnect), 
		#   so we do it here, using connectedToOolite flag to prevent looping
		self.connectedToOolite = True
		self.top.title('{}: {}'.format(DEBUGGER_TITLE, TCP_Port))
		if len(self.scriptProps):	# not the 1st connection in this session
			debugLogger.debug('connected {}'.format('=' * 70))
		self.settingsMenu = OoBarMenu(self.menubar, label='Oolite plist', 
										font=self.defaultFont, 
										postcommand=self.closeAnyOpenFrames) 
		settingsMenu, sortFn = self.settingsMenu, self.sortClientSettings
		pairs = OrderedDict( sorted(settings.items(), key=lambda t: sortFn( t[0] )) )
		settingsKeys = settings.keys()
		plistTkvars = self.plistTkvars
		colorsSep = False
		override = self.localOptions['PlistOverrides']
		for key, value in pairs.items():	# add menu items for each setting
			if 'macros' in key:
				continue					# NB: 's' as color keys use singular
			valueType = type(value)
			if key == 'font-face':
				if 'Family' not in self.loadedConfig or override:
					self.setFontFace(value, plist=True, skipUpdate='font-size' in settingsKeys)
				self.settings[ key ] = value
			elif key == 'font-size':
				if 'Size' not in self.loadedConfig or override:
					self.setFontSize(value, plist=True)
				self.settings[ key ] = value
			elif valueType == list:
				if not colorsSep and key.count('-') == 3:# add separator between general and event specific colors
					settingsMenu.add_separator()		 # - this only works because of sortClientSettings
					colorsSep = True
				settingsMenu.add_command(label=key, stateChange=True,
										state=DISABLED if self.pollingSuspended else NORMAL,
										command=lambda k=key: self.pickMsgColour(k))
				self.setMsgColor(key, value)
				if override and key.endswith('-color'): # check for missing fg/bg
					parts = key.split('-')
					keyClass = parts[0] if len(parts) == 3 else '{}-{}'.format(parts[0], parts[1])
					if '-foreground-color' in key and '{}-background-color'.format(keyClass) not in settingsKeys:
						if 'general-background-color' in self.COLORS:
							missingbg = self.COLORS['general-background-color']
						else:
							missingbg = self.COLORS['background']
						self.bodyText.tag_config(keyClass, background=missingbg)
						if keyClass == 'command':
							self.cmdLine.tag_config(keyClass, background=missingbg)
					elif '-background-color' in key and '{}-foreground-color'.format(keyClass) not in settingsKeys:
						if 'general-background-color' in self.COLORS:
							missingfg = self.COLORS['general-foreground-color']
						else:
							missingfg = self.COLORS['foreground']
						self.bodyText.tag_config(keyClass, foreground=missingfg)
						if keyClass == 'command':
							self.cmdLine.tag_config(keyClass, foreground=missingfg)
				self.settings[ key ] = value
			else:
				if valueType == bool or (valueType == int and value in [0, 1]) \
						or value in ['1', '0', 'true', 'false', 'yes', 'no']:
					if valueType == bool:
						tkValue = 1 if value else 0
					if valueType == int:
						tkValue = value
					else:
						tkValue = 1 if value in ['1', 'true', 'yes'] else 0
					if key not in plistTkvars:	# some are added when debug menu is created
						plistTkvars[ key ] = IntVar(name='oo_{}'.format(key))
					plistTkvars[ key ].set(tkValue)
					settingsMenu.add_checkbutton(label=key, stateChange=True, variable=plistTkvars[ key ],
												state=DISABLED if self.pollingSuspended else NORMAL,
												command=lambda k=key: self.setClientCheckButton(k, plistTkvars[k]))
					self.settings[ key ] = bool(tkValue)
				else:
					errmsg = 'Unsupported var {}: {}, type: {}'.format(key, value, valueType)
					if dca.g['debug']:
						print(errmsg)
						print_exc()
						pdb.set_trace()
					else:
						debugLogger.error(errmsg)
		self.cmdLine.tag_raise(SEL)
		self.initStartTime = clock() if Python2 else perf_counter()
		self.gameStarted.set(-1)			# var is traced, setting will initiate polling

	initStartTime = None
	sessionInitialized = False
	def disableClientSettings(self):	# disables Debug menu but destroys Settings menu as it is connection specific
		if not self.connectedToOolite:
			return 						# can be called more than once (oolite closed vs halted)
		self.connectedToOolite = False
		self.sessionInitialized = False
		debugLogger.debug('disconnected {}'.format('=' * 67))
		del self.requests[:]			# clear msg queues
		self.replyPending = self.replyPendingTimer = None
		for loopID in self.afterLoopIDs.values():
			# shut down any active .after cycles (tkinter won't complain if not active)
			self.after_cancel(loopID)
		self.afterLoopIDs.clear() 	
		self.top.title('{}: disconnected'.format(DEBUGGER_TITLE))
		if hasattr(self, 'settingsMenu'):
			self.settingsMenu.removeOnesSelf()
			del self.settingsMenu
		self.debugMenu.changeAllStates(DISABLED)

	plistTkvars = {}					# dict of tkinter variables for client settings
	def sortClientSettings(self, key):	# impt for menu order and color calc
		if key.startswith('font'):
			rank = 1
		elif not key.endswith('color'):
			rank = 2
		elif key.startswith('general'):
			rank = 3
		elif key.count('-') == 2:
			rank = 4
		else:
			rank = 5
		return '{}{}'.format(rank, key)

## startup step 2
	scriptProps = []
	def queryScriptProps(self): # mk list of console.script properties (for alias register)
		if 'gameStarted' in self.timedOutCmds:
			del self.timedOutCmds['gameStarted']
		cmd = ('(function() { var proplst = "", cs = console.script, first = true; '
		         'for( var prop in cs ) { '
		           'if( cs.hasOwnProperty( prop ) ) { '
		             'proplst += (first ? "" : ",") + prop; '
		             'first = false; } '
		         '} return proplst + "<label:scriptProps><discard:yes>"; '
		       '})()') # see mkCmdIIFE
		self.queueSilentCmd(cmd, 'scriptProps', self.scriptPropsStr)

	# handler for Tk var trace: scriptPropsStr
	def loadScriptProps(self, *args):			# create list of console.script's properties to avoid collision w/ aliases
		propStr = self.scriptPropsStr.get()
		if len(propStr) > 0:
			propStr = propStr.split(',')
			del self.scriptProps[:]
			self.scriptProps.extend(propStr)
			numProps = len(propStr)
			if numProps:
				cmd = 'console.script["$debugConsoleSessionStarted"] = "{}"'.format(asctime())
				# sign script to be able to detect game restart
				# - polling is started when cmd completes
				self.queueSilentCmd(cmd, 'signScript', self.sessionStartTime)	
				self.aliasPollQueue.clear()
				status = '* * obtained {} script property names'.format(numProps)
			else:
				self.sessionInitialized = False
				status = '* * failed to obtain property names, resetting sessionInitialized'.format(numProps)
			debugLogger.debug(status)

	# handler for Tk var trace: sessionStartTime
	def sessionStarted(self, *args):
		if self.initStartTime:
			msg = 'initialization took {}'.format((clock() if Python2 else perf_counter()) - self.initStartTime)
			if dca.g['debug']:
				print(msg)
			else:
				debugLogger.debug(msg)
			self.initStartTime = None
		self.sessionInitialized = True
		self.pollOolite()
	
## startup 3rd & final step
	pollCounter = 0
	pollElapsed = 0
	def pollOolite(self, event=None): 	# monitor for restart, system change, etc; update alias values
		if self.gameStarted.get() == 1:
			if self.pollElapsed % 1000 == 0:	# every second, poll one of the locals
				gamePoll = self.pollElapsed // 1000
				if gamePoll == 0:
					self.queueSilentCmd('console.debugFlags', 'pollDebugFlags', self.debugOptions['debugFlags']['allFlags'])
				elif gamePoll == 1:
					self.queueSilentCmd('system', 'pollStarSystem', self.currStarSystem)
				elif gamePoll == 2:
					self.queueSilentCmd( self.gameStatusCmd, 'gameStarted', self.gameStarted)
				if self.pollElapsed == 2000:
					self.pollElapsed = -1000
			if len(self.aliasPollsPending) == 0:
				self.pollAliases(5)				# only 5 at a time
			else:
				expired = []
				for alias, sentTime in self.aliasPollsPending.items():
					currTime = clock() if Python2 else perf_counter()
					if currTime - sentTime > 5:	# after 5 seconds, abandon poll	
						expired.append(alias)
				for alias in expired:
					del self.aliasPollsPending[alias]
					
			self.pollCounter += 1
			self.pollElapsed += 500
			self.afterLoop(500, self.pollOolite) # entire cycle takes 3000 ms unless there are >  aliases
													# locals get updated every 3 sec regardless of # of aliases
## prob: initialization takes too long (incl'g alias polling; ?del registerAllAliases

	# connection has been established, we wait for player's ship status to change from 
	# STATUS_START_GAME before completing setup			
	gameStatusCmd = 'player.ship.status !== "STATUS_START_GAME"'
	# handler for Tk var trace: gameStarted
	def checkGameStatus(self, *args):	# trace handler for self.gameStarted
		if self.connectedToOolite:
			gameStarted = self.gameStarted.get()
			if gameStarted < 0:			# new re-connection, no delay
				self.queueSilentCmd( self.gameStatusCmd, 'gameStarted', self.gameStarted)
			elif gameStarted == 0:		# keep checking until game is load/started
				self.afterLoop(900, self.queueSilentCmd, self.gameStatusCmd, 'gameStarted', self.gameStarted) # 900 => 1/sec ...?
				self.afterLoop(1500, self.checkGameStatus) 		# will be cancelled via afterLoop if queued cmd succeeds
				# - these do nothing loop are necessary as we cannot know when Oolite will ignore us during startup/game load
				# - send query 1/sec when Oolite responsive, reverts to CMD_TIMEOUT when ignoring us
			elif self.sessionInitialized == False:				# set to 'in progress' by initDebugMenu (prevents 2nd init)
				if 'gameStarted' in self.afterLoopIDs: 			# halt as no longer necessary
					self.after_cancel(self.afterLoopIDs[label])	# call is harmless if no after in effect
				self.initDebugMenu()
			# else:						# game loaded, initialization complete, nothing else to do
	
	def afterLoop(self, ms, fn, *args):	# manager for event looping
		label = fn.__name__
		if label in self.afterLoopIDs:	# terminate existing callback
			self.after_cancel(self.afterLoopIDs[label])
		self.afterLoopIDs[label] = self.after(ms, fn, *args)

	def addTraceTkVar(self, tkVar, func):	# func should expect args: vname1, vname2, mode (ie. *args)
		if Python2: 
			return tkVar.trace_variable('w', func)
		else:
			return tkVar.trace_add('write', func)
		
	def delTraceTkVar(self, tkVar):
		info = traceID = None
		try:
			info = tkVar.trace_vinfo() if Python2 else tkVar.trace_info()
			traces = len(info)
			if dca.g['debug'] and traces > 1:
				raise ValueError('delTraceTkVar, unexpected trace info: {}'.format(info))
			for idx, traceInfo in enumerate(info):
				if traces > 1 and idx == 0: continue;
				_, traceID = traceInfo
				if Python2:	
					tkVar.trace_vdelete('w', traceID)
				else:
					tkVar.trace_remove('write', traceID)
		except TclError as exc:
			errmsg = 'Exception {}: tkVar = {}, traceID = {}, trace_info = {}'.format(
							exc, tkVar, traceID, tkVar.trace_vinfo() if Python2 else tkVar.trace_info())
			if dca.g['debug']:
				print(errmsg)
				print_exc()
			else:
				debugLogger.exception(errmsg)
		except Exception as exc:
			errmsg = 'Exception {}: tkVar = {}, traceID = {}, trace_info = {}'.format(
							exc, tkVar, traceID, tkVar.trace_vinfo() if Python2 else tkVar.trace_info())
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.exception(errmsg)

## Client functions ########################################################

	def getClientSetting(self, key, default=None):
		if not self.connectedToOolite:
			return
		value = self.client.configurationValue(key)
		return value

	def setClientSetting(self, key, value):
		if not self.connectedToOolite:
			return
		if key not in self.settings.keys() and key not in ['font-face', 'font-size']: #####
			debugLogger.debug('missing {}; settings dump:\n{}'.format(key, self.settings)) #####
		self.client.setConfigurationValue(key, value)

	def setClientCheckButton(self, key, tkVar):
		if not self.connectedToOolite:
			return
		value = tkVar.get()
		if key in persistenceMap:
			setter = persistenceMap[key]
			self.queueSilentCmd('console.{} = {}'.format(setter, 'true' if value else 'false'), key)
		else:
			self.client.setConfigurationValue(key, value)

	def noteConfig(self, oolite): 		# ack from setConfigurationValue OR actual changes from macros!
		key = None
		value = None
		try:
			for key, value in oolite.items():
				if 'macros' in key:
					continue			# NB: 's' as color keys use singular
				if key.endswith('-color'):
					self.setMsgColor(key, value)
				elif key.startswith('font'):
					self.settings[key] = value
				else:
					value = str(value) if isinstance(value, int) else value
					value = True if value in ['1', 'true', 'yes',] else False
					self.settings[key] = value
		except Exception as exc:
			errmsg = 'Exception {}: key = {}, value = {}, hasattr(self, "settings") = {}'.format(
										exc, key, value, hasattr(self, "settings"))
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.exception(errmsg)

## Color functions #########################################################

	def contrastColor(self, color, tkColor):
		if tkColor in TKCOLORS:
			return 'white' if tkColor in ['green', 'blue', 'black'] else 'black'
		red = int(color[1:3], base=16)
		green = int(color[3:5], base=16)
		blue = int(color[5:7], base=16)
		average = sum((red, green, blue)) / 3
		contrast = 'white' if average < 96 else 'black'
		return contrast

	def codifyColor(self, value): 		# arg can be a TK|OO str, '#xxxxxx', list|tuple of float|int, return '#xxxxxx'
		if isinstance(value, str) and value[0] != '#': # a named color
			color = value
			if value in TKCOLORS.keys():
				color = TKCOLORS[ value ]
			ookey = value if value.endswith( 'Color' ) else value + 'Color'
			if ookey in OOCOLORS.keys():
				color = OOCOLORS[ ookey ] # can overwrite as OOCOLORS is a superset of TKCOLORS
			return color
		if isinstance(value, tuple) or isinstance(value, list):
			if isinstance(value, list):
				if len(value) > 3: value = value[0:3]
				rgb = tuple(value)
			if isinstance(value[0], float):
				rgb = (int(value[0]*255), int(value[1]*255), int(value[2]*255))
			color = '#%02x%02x%02x' % rgb
		elif isinstance(value, str) and value[0] == '#': #  a tk color str
			color = value
		else:
			debugLogger.debug('unable to classify value: {}'.format(value))
			return value, None, None
		return color

	def sameColour(self, c1, c2):		# return true if all r,g,b components are w/i +-2
		if c1 == c2: return True
		if not c1.startswith('#') or not c2.startswith('#'):
			debugLogger.debug('arg(s) have invalid format -- convert with codifyColor first!') #####
			return False
		return 	abs(int(c1[1:3],16)-int(c2[1:3],16)) < 3 and \
				abs(int(c1[3:5],16)-int(c2[3:5],16)) < 3 and \
				abs(int(c1[5:7],16)-int(c2[5:7],16)) < 3

	def findOoColour(self, color):
		oocolor = self.codifyColor(color)
		for k, v in OOCOLORS.items():
			if self.sameColour(self.codifyColor(v), oocolor):
				return k
		return None

	def findTkColour(self, color):
		tkColor = self.codifyColor(color)
		for k, v in TKCOLORS.items():
			if self.sameColour(self.codifyColor(v), tkColor):
				return k
		return None

	def pickLocalColour(self, key):
		cvalue = self.codifyColor(self.COLORS[key])
		newcolor, newcstr = tkColor.askcolor(color=cvalue, parent=self.top, title=key)
		if newcolor is None or self.sameColour(cvalue, newcstr):
			return
		self.setLocalColor(key, newcstr)

	def setLocalColor(self, key, value):
		color = self.codifyColor(value)
		tkColor = self.findTkColour(color)
		newColour = color if tkColor is None else tkColor
		self.COLORS[ key ] = newColour		# assign local colors for foreground, background & cmdLine
		if key == 'foreground':
			self.bodyText.config(foreground=newColour)
			self.bodyText.tag_config('foreground', foreground=newColour)
		elif key == 'background':
			self.bodyText.config(background=newColour)
			self.bodyText.tag_config('foreground', background=newColour)
			if 'command-background-color' not in self.COLORS or \
				not self.localOptions['PlistOverrides']:
				self.cmdLine.config(background=newColour)
				self.cmdLine.frame.config(bg=newColour)
		elif key == 'command':
			self.cmdLine.config(foreground=newColour, insertbackground=newColour) # cursor color
			self.bodyText.tag_config('command', foreground=newColour)
		elif key == 'selectfg':
			self.bodyText.config(selectforeground=newColour)
			self.bodyText.tag_config(SEL, foreground=newColour)
			self.cmdLine.config(selectforeground=newColour)
			self.cmdLine.tag_config(SEL, foreground=newColour)
		elif key == 'selectbg':
			self.bodyText.config(selectbackground=newColour, inactiveselectbackground=newColour)
			self.bodyText.tag_config(SEL, background=newColour)
			self.cmdLine.config(selectbackground=newColour, inactiveselectbackground=newColour)
			self.cmdLine.tag_config(SEL, background=newColour)
		contrast = self.contrastColor(color, tkColor)
		self.optionsMenu.configLabel(key, foreground=contrast, background=newColour)
		return color, tkColor

	def pickMsgColour(self, key):
		cvalue = self.codifyColor(self.settings[key])
		newcolor, newcstr = tkColor.askcolor(color=cvalue, parent=self.top, title=key)
		if newcolor is None or self.sameColour(cvalue, newcstr):
			return
		newrgb = [int(newcolor[0]), int(newcolor[1]), int(newcolor[2])]
		newrgb.append(255) 				# alpha
		self.setMsgColor(key, newrgb)
		oocolor = self.findOoColour(newcstr)
		self.client.setConfigurationValue(key, newrgb if oocolor is None else oocolor )

	def setMsgColor(self, key, value):
		color = self.codifyColor(value)
		tkColor = self.findTkColour(color)
		contrast = self.contrastColor(color, tkColor)
		newColour = color if tkColor is None else tkColor
		self.settingsMenu.configLabel(key, foreground=contrast, background=newColour)
		self.registerMsgColor(key, newColour)
		self.settings[ key ] = newColour
		return color, tkColor

	def registerMsgColor(self, key, color):
		self.COLORS[ key ] = color
		parts = key.split('-')
		classLen = len(parts)
		override = classLen == 4 or self.localOptions['PlistOverrides']
		keyClass = parts[0] if classLen == 3 else '{}-{}'.format(parts[0], parts[1])
		setTags = override or keyClass in ['error', 'exception', 'warning']
		if setTags and key.endswith('-foreground-color'):
			self.bodyText.tag_config(keyClass, foreground=color)
		elif setTags and key.endswith('-background-color'):
			self.bodyText.tag_config(keyClass, background=color)
		if not override:
			return
		if classLen == 3:				# apply to local colors
			if key == 'general-foreground-color':
				self.setLocalColor('foreground', color)
			elif key == 'general-background-color':
				self.setLocalColor('background', color)
			elif key == 'command-foreground-color':
				self.setLocalColor('command', color)
			elif key == 'command-background-color':
				self.cmdLine.config(background=color)

## app functions ###########################################################

###
	def suspendMsgTraffic(self):
		assert not hasattr(self, 'suspensionMenu')###
		self.debugMenu.changeAllStates(DISABLED)
		self.settingsMenu.changeAllStates(DISABLED)
		suspendMenu = OoBarMenu(self.menubar, label='Suspended', 
								font=self.defaultFont, 
								postcommand=self.closeAnyOpenFrames) 
		suspendMenu.add_command(label='Message traffic with Oolite')
		suspendMenu.add_command(label='is suspended while in the')
		suspendMenu.add_command(label='middle of a user command.')
		suspendMenu.add_command(label='Finish the command, enter a')
		suspendMenu.add_command(label='blank command or use the')
		suspendMenu.add_command(label='button below to resume traffic.')
		suspendMenu.add_separator()
		suspendMenu.add_command(label='Force Resumption', command=self.restoreMsgTraffic)
		self.suspensionMenu = suspendMenu

	def restoreMsgTraffic(self): 
		if hasattr(self, 'suspensionMenu'):			# were in a multi-line user cmd
			self.debugMenu.changeAllStates(NORMAL)
			self.settingsMenu.changeAllStates(NORMAL) 
			self.suspensionMenu.removeOnesSelf() 
			del self.suspensionMenu
			cmdLineHandler.inputReceiver.receiveUserInput('') # flush any unfinished command
		self.pollingSuspended = False
		cmd = 'console.script["$debugConsoleSessionStarted"]'
		self.queueSilentCmd(cmd, 'signScript', self.currentSessionTime) # fetch tag to detect game restart
		self.sendSilentCmd()						# looping halted by pollingSuspended

	# handler for Tk var trace: currentSessionTime
	def updateDebugMenu(self, *args):
		if self.currentSessionTime.get() != self.sessionStartTime.get():
			self.initDebugMenu()		# different session, re-init

	requests = []
	replyPending = None
	replyPendingTimer = None
	pollingSuspended = False
	# SilentMsg: namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')
	def queueSilentCmd(self, cmd, label, tkVar=None, discard=True):
		if hasattr(cmdLineHandler.inputReceiver,'receiveUserInput') and cmdLineHandler.inputReceiver.Active:
			if label == 'USER_CMD':		# suspend all message traffic w/ Oolite during user cmds
				if not self.pollingSuspended:
					self.pollingSuspended = True
					self.reSubmitPending()
				cmdLineHandler.inputReceiver.receiveUserInput(cmd)
				return
			# all internal cmds are submitted one at a time, the receipt of its reply triggering the next
			# - replies are guaranteed as while some cmds don't expect a reply, all are submitted as IIFE's
			#   that add the cmds label & echoing instructions (aka discard) to the reply (if any) in their return
			# debugLogger.debug('	replyPending {} => {}'.format(self.replyPending.label if self.replyPending else None,
					# 'return w/o queuing' if self.replyPending and label in ['gameStarted', 'pollDebugFlags', 'pollStarSystem'] else 'submitRequest'))
			if self.replyPending and label in ['gameStarted', 'pollDebugFlags', 'pollStarSystem']:
				return # only poll games status when idle
			self.submitRequest(SilentMsg(cmd, label, tkVar, discard, None))

	def submitRequest(self, request):	# ensure no duplicates in queue
		label, requests = request.label, self.requests
		if label in self.timedOutCmds:
			currentTick = clock() if Python2 else perf_counter()
			elapsed = currentTick - self.timedOutCmds[label].timeSent
			if label == 'gameStarted' and not self.sessionInitialized:	# reply not guaranteed during game load so keep sending
				# leave in timedOutCmds so processSilentCmd will process errant replies
				self.timedOutCmds[label] = self.timedOutCmds[label]._replace(timeSent=currentTick)
			elif elapsed > CMD_TIMEOUT_ABORT:# only process if not too stale
				del self.timedOutCmds[label]
			else:						# give it more time ??? 
				debugLogger.debug('submitRequest, giving "{}" more time (elapsed = {})'.format(label, elapsed))				
				return
		if label not in [msg.label for msg in requests]:
			self.requests.append(request)
		
	def reSubmitPending(self):			# re-enqueue replyPending
		msg = self.replyPending 
		if msg:
			if (msg.label == 'gameStarted' and self.gameStarted.get() == 0) or \
				msg.label not in ['gameStarted', 'pollDebugFlags', 'pollStarSystem',	# these are regularly polled
									'setDetailLevel', 'writeMemoryStats']: 				# and these can easily timeout
				self.submitRequest(msg)	# resubmit msg
		
			if dca.g['debug']:						 ###cag
				debugLogger.debug('resetting replyPending, msg.label = {}, # timedOut = {}: {}'.format(
					msg.label if msg else None,
					len(self.timedOutCmds), ', '.join(c for c in self.timedOutCmds.keys()) if len(self.timedOutCmds) else ''))
		self.replyPending = self.replyPendingTimer = None 	# allow sendSilentCmd to send next in queue

	def mkCmdIIFE(self, msg):			# wrap msg as an IIFE
		iife = '(function() {{ var result, label = "<label:{}><discard:{}>", noVal = "no result" + label; '.format(
				msg.label, 'yes' if msg.discard else 'no')
		iife += 'try {{ result = {}; }}'.format(msg.cmd)
		# iife += 'try {{ result = {}; }} catch (e) {{ return noVal; }} return result + label; }})()'.format(msg.cmd)
		if msg.discard:
			iife += ' catch (e) { return noVal; } return result + label; })()'
		else:
			iife += ' catch (e) { console.consoleMessage(e); return noVal; } return result + label; })()'
		return iife

	timedOutCmds = {}
	def sendSilentCmd(self):
		if self.pollingSuspended: return
		if len(self.pendingMessages) == 0:					# don't interfere w/ large outputs
			if not self.replyPending and len(self.requests):# wait for reply before sending next
				if hasattr(cmdLineHandler.inputReceiver,'receiveUserInput') and cmdLineHandler.inputReceiver.Active:
					msg = self.requests.pop(0)
					self.replyPendingTimer = clock() if Python2 else perf_counter()	# start timeout clock
					self.replyPending = msg._replace(timeSent=self.replyPendingTimer)
					# wrap all internal cmds in IIFE for label & discard
					silentCmd = msg.cmd if msg.cmd.startswith('(function()') else self.mkCmdIIFE(msg)
					cmdLineHandler.inputReceiver.receiveUserInput(silentCmd)
					
					# if dca.g['debug']:						 ###cag
						# numRequests, numTimedOut = len(self.requests), len(self.timedOutCmds)
						# if numRequests == 0 and numTimedOut == 0:
							# debugLogger.debug('w/ no requests and no timedOutCmds')
						# if numRequests:
							# debugLogger.debug('w/ {} requests{}'.format(numRequests, 
								# '' if not numRequests else ': "{}"'.format('", "'.join(r.label for r in self.requests))))
						# if numTimedOut:
							# debugLogger.debug('w/ {} timed out{}'.format(numTimedOut, 
								# '' if not numTimedOut else ': "{}"'.format('", "'.join(r for r in self.timedOutCmds))))
						# debugLogger.debug('==> {}: {}'.format(msg.label, msg.cmd)) 
							
			elif self.replyPendingTimer is not None: 		# monitor elapsed time to abort for non-reply
				currentTick = clock() if Python2 else perf_counter()
				elapsed = currentTick - self.replyPendingTimer
				timedOut = elapsed > CMD_TIMEOUT_LONG if self.replyPending.label \
									   in ['setDetailLevel', 'writeMemoryStats', ] else elapsed > CMD_TIMEOUT
				if timedOut:	# timeout after 2 or 4 secs
					self.timedOutCmds[self.replyPending.label] = self.replyPending
					self.reSubmitPending()
		self.after(50, self.sendSilentCmd)
		
	def handleMessage(self, message, colorKey, emphasisRanges):
		self.pendingMessages.append(( message, colorKey, emphasisRanges ))
		# must buffer incoming messages, as large volume can get OSError: [Errno 28] No space left on device
		length = len(self.pendingMessages)
		if length > 3 * self.messageBatchSize:
			self.messageBatchSize += self.messageBatchSize // 2
			status = 'handleMessage, buffer has {} messages, => larger messageBatchSize {}'.format(length, self.messageBatchSize)
			if dca.g['debug']:
				print(status)
			else:
				debugLogger.debug(status)
		if self.messageQueueID is None:
			self.messageQueueID = self.after(10, self.processMessage)

	pendingMessages = []
	messageBatchSize = 25
	messageQueueID = None
	def processMessage(self):
		if self.messageQueueID:
			self.after_cancel(self.messageQueueID)
			self.messageQueueID = None
		debugStatus = None
		try:
			numMsgs = min(self.messageBatchSize, len(self.pendingMessages))
			while numMsgs > 0:
				debugStatus = None
				numMsgs -= 1
				message, colorKey, emphasisRanges = self.pendingMessages.pop(0)	
				debugStatus = 'popped'
				if colorKey not in ['command', 'command-result']:	# it's an oolite message
					isLastOfRun = colorKey != self.pendingMessages[0][1] if numMsgs > 0 else True
					self.colorPrint(message, colorKey, emphasisRanges, lastInBatch=isLastOfRun)
					debugStatus = 'printed'
					continue
				msgLabel = None
				labelStart = message.find('<label:')
				if labelStart >= 0:
					labelStart += 7 		# len('<label:')
					labelEnd = message.find('>', labelStart)
					if labelEnd >= 0:
						msgLabel = message[ labelStart:labelEnd ]
				if msgLabel is None:		# must be part of a USER_CMD or its reply
					if message.startswith('_ '):	# multi-line user cmds get echoed w/ '_ ' prefix
						if not hasattr(self, 'suspensionMenu'):	# first time we know it's multi-line
							self.suspendMsgTraffic()
					elif self.pollingSuspended:		# no '_ ' prefix => user cmd reply
						self.restoreMsgTraffic()	# user cmd ends, release queue for internal ones
					self.colorPrint(message, colorKey, emphasisRanges, lastInBatch=True)
					debugStatus = 'printed'
					break
				if colorKey == 'command':			# never echo internal commands
					debugStatus = 'printed'
					continue
				# internal cmds always get a reply, though it may be 'no result' (done for firm control of traffic)
				if not self.replyPending or self.replyPending.label != msgLabel:	# unexpected reply
					# if dca.g['debug']:					###cag
						# debugLogger.debug('not expecting msgLabel = {}, replyPending = {}'.format(
									# msgLabel, self.replyPending.label if self.replyPending else None))
						# debugLogger.debug('# requests = {}: {}'.format(
									# len(self.requests), '' if len(self.requests) == 0 else [r.label for r in self.requests]))
						# debugLogger.debug('# timedOut = {}: {}'.format(
									# len(self.timedOutCmds), '' if len(self.timedOutCmds) == 0 else [r for r in self.timedOutCmds]))
					if 'discard:yes' not in message:
						self.colorPrint(message, colorKey, emphasisRanges)
						debugStatus = 'printed'
						msg = 'no reply expected for message, replyPending: {}'.format(self.replyPending)
						msg += '\n    colorKey {}, message: {}'.format(colorKey, message[:80] + (' ...' if len(message) > 80 else ''))
						if dca.g['debug']:
							print(msg)
							pdb.set_trace()
						else:
							debugLogger.warning(msg)
					if self.pollingSuspended:	# timed out due to user cmd 
						self.reSubmitPending()
						continue
				
				# if dca.g['debug']:
					# debugLogger.debug('processing {}\n'.format(message)) 

				debugStatus = self.processSilentCmd(msgLabel, message, colorKey, emphasisRanges, lastInBatch= (numMsgs == 0) )
			# endwhile
			if len(self.pendingMessages):
				self.messageQueueID = self.after(10, self.processMessage)
		except Exception as exc:
			errmsg = 'Exception: {}'.format(exc)
			if '[Errno 28] No space left on device' in errmsg:
				if debugStatus != 'printed':
					self.pendingMessages.insert(0, ( message, colorKey, emphasisRanges ))
				if self.messageBatchSize > 1:
					self.messageBatchSize = 1 if self.messageBatchSize < 4 else self.messageBatchSize // 2
					status = 'processMessage, smaller messageBatchSize {}'.format(self.messageBatchSize)
					if dca.g['debug']:
						print(status)
					else:
						debugLogger.debug(status)
			else:
				if dca.g['debug']:
					print(errmsg)
					print_exc()
					pdb.set_trace()
				else:
					debugLogger.error(errmsg)
	
	def processSilentCmd(self, msgLabel, message, colorKey, emphasisRanges, lastInBatch=True):
		debugStatus = 'popped'
		result = message[ : message.find('<label:') ]
		if self.replyPending and self.replyPending.label == msgLabel:
			request = self.replyPending
		elif msgLabel in self.timedOutCmds:
			# SilentMsg: namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')
			request = self.timedOutCmds[msgLabel]
			elapsed = (clock() if Python2 else perf_counter()) - request.timeSent
			if elapsed > CMD_TIMEOUT_ABORT:	# only process if not too stale
				del self.timedOutCmds[msgLabel]	# delete expired comand
				return 'printed'
		else:									# a timed out command that's expired
			return 'printed'
		if message.startswith('_ '):			# internal cmd failed
			debugLogger.warning('**** internal error: {}'.format(message))
			self.reSubmitPending()
		elif request.tkVar is not None:			# it's a command-result
			if request.label.startswith('alias-'):
				self.setAliasRegistry(request.label, result, request.tkVar)
			elif request.label in ['scriptProps', 'detailLevel', 'signScript', ]:
				request.tkVar.set(result)
			elif request.label == 'entityDumpVar':
				request.tkVar.set(1)			# signals dump complete
			elif result != 'no result':
				self.setDebugOption(request.label, result, request.tkVar)
			else:
				print('Yikes! unsupported result "{}" for label "{}"'.format(result, msgLabel))
				pdb.set_trace()
		elif request.label.startswith('alias-'):# the response from -send'g the alias definition
			self.setAliasRegistry(request.label, result)
		if not message.startswith('no result') and \
			   message.find('<discard:no>') >= 0:
			self.colorPrint(message, colorKey, emphasisRanges, lastInBatch)
			debugStatus = 'printed'
		if request == self.replyPending:
			self.replyPending = self.replyPendingTimer = None
		return debugStatus

	maxBufferSize = 200000
	screenLines = None
	def checkBufferSize(self):	# keep the buffer at a reasonable size, called 1/100 colorPrints
		txt = self.bodyText		#   (?cause of OSError [Errno 28] No space left on device)
		try:
			if self.screenLines is None:		# 1st check or font has changed (is reset in updateForFontChange)
				height = txt.winfo_reqheight()						# pix
				self.screenLines = int(height / self.lineSpace)		# number of lines on screen
			lines, chars = txt.count('1.0', END, 'lines', 'chars')
			if chars > self.maxBufferSize:
				txt.config(state=NORMAL)
				txt.delete('1.0', '{}.end'.format(int(lines / 2)))
				txt.config(state=DISABLED)		
		except Exception as exc:
			errmsg = 'Exception: {},  bodyText.index(END) "{}"'.format(exc, txt.index(END))
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.exception(errmsg)
	
	def setColorKey(self, key):
		colorKeys = self.COLORS.keys()
		if key == 'dumpObject':
			key = 'foreground' 		# bug in oolite-debug-console.js, function dumpObject()
		elif key == 'debugger':
			key = 'foreground' 		# msg from debugger
		key = key.lower() if key else 'foreground'
		if key == 'macro-expansion' and self.localOptnVars['MacroExpansion'].get() == 0:
			return None				# suppress print
		elif key == 'log':
			if self.debugOptions['showLog'].get() > 0:
				key = 'foreground' if key not in colorKeys else key
			else:
				return None			# suppress print
		return key
	
	def setColorTag(self, key):
		colorKeys = self.COLORS.keys()
		if key in colorKeys:
			tag = key
		elif key + '-foreground-color' in colorKeys:
			tag = key
		elif key + '-background-color' in colorKeys:
			tag = key
		else:
			tag = 'foreground'
		return tag
		
	printCount = 0
	stateNormal = False
	printBuffer = []
	printTag = None
	printKey = None
	def colorPrint(self, text, colorKey='debugger', emphasisRanges=None, lastInBatch=True):
		txt = self.bodyText
		try:
			sameColorKey = self.printKey and self.printKey == colorKey
			if lastInBatch or not sameColorKey:
				self.printKey = colorKey
				key = self.setColorKey(colorKey)
				if key is None: return			# print suppressed
				tag = self.setColorTag(key)
			else:		# avoid unnecessary calls to setColorKey/Tag
				key, tag = self.printKey, self.printTag
			sameColorTag = not self.printTag or self.printTag == tag

			self.printCount += 1
			if self.screenLines and self.printCount > 5 * self.screenLines:
				self.checkBufferSize()
				self.printCount = 0
			try:
				text = text.rstrip(' \t\n\r') + '\n'
			except UnicodeEncodeError:
				text = text.encode('utf-8').rstrip(' \t\n\r') + '\n'
			if not self.stateNormal:
				txt.config(state=NORMAL)
				self.stateNormal = True
				
			maxWidth = None
			if colorKey == 'command' and self.localOptnVars['TruncateCmdEcho'].get():
				self.bodyText.update_idletasks()# required for winfo_width
				maxWidth = self.bodyText.winfo_width()

			posn = 0
			if emphasisRanges is None and maxWidth is None:
				bufferLen = len(self.printBuffer)
				# here's where voluminous log statements can cause a bottleneck
				if not lastInBatch and sameColorKey and sameColorTag:	
					self.printBuffer.append(text)				# buffer lines to reduce # of .insert calls
				elif not lastInBatch and sameColorKey:			# new tag, flush buffer and restart buffering
					if bufferLen:
						txt.insert(END, ''.join(self.printBuffer), tag)
						del self.printBuffer[:]
					self.printTag = tag
					self.printBuffer.append(text)
				elif bufferLen and (lastInBatch or not sameColorKey):# flush buffer completely
					if sameColorTag:
						self.printBuffer.append(text)
					if bufferLen:
						txt.insert(END, ''.join(self.printBuffer), tag)
						del self.printBuffer[:]
					if not sameColorTag:
						txt.insert(END, text, tag)
					self.printKey = self.printTag = None
				else:
					txt.insert(END, text, tag)
			elif maxWidth is None:				# not trucating output
				while len(emphasisRanges) > 1:	# ranges come in pairs
					estart = emphasisRanges.pop(0)
					elen = emphasisRanges.pop(0)
					if posn < estart: 			# text before emphasis
						txt.insert(END, text[ posn:estart ], tag)
					posn = estart + elen		# emphasis text
					txt.insert(END, text[ estart:posn ], ('emphasis',tag))
					if len(emphasisRanges) < 2: break
					nextE = emphasisRanges[0]
					if posn < nextE: 			# text after emphases
						txt.insert(END, text[ posn:nextE ], tag)
						posn = nextE
				if posn < len(text): 			# text after all the emphases
					txt.insert(END, text[ posn: ], tag)
			else:
				self.addWords(text, tag, maxWidth, emphasisRanges)
		except Exception as exc:
			errmsg = 'Exception: {}'.format(exc)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.error(errmsg)
		finally:
			if lastInBatch:
				txt.config(state=DISABLED)
				self.stateNormal = False
				txt.yview(END)
				txt.tag_raise(SEL)

	spaceLen = eSpaceLen = None
	measuredWords = {}
	measuredEWords = {}
	def addWords(self, text, tag, maximumWidth, emphases=None):
		try:
			txt, font, efont = self.bodyText, self.defaultFont, self.emphasisFont
			measuredWords, measuredEWords = self.measuredWords, self.measuredEWords
			if self.spaceLen is None or self.eSpaceLen is None:	# 1st time or font's changed (see showAliasValue)
				self.spaceLen, self.eSpaceLen = font.measure(' '), efont.measure(' ')
			spaceLen, eSpaceLen = self.spaceLen, self.eSpaceLen
			words = text.split()
			hasEmphasis = False
			buffer, index, estop = [], 0, -1
			
			def nextEmphasis():
				if emphases is not None and len(emphases) > 1:	# ranges come in pairs
					start = emphases.pop(0)
					stop = start + emphases.pop(0)
				else:
					start = stop = maximumWidth
				return start, stop
				
			def measuredWidth(phrase):
				if hasEmphasis:
					if phrase in measuredEWords:
						return measuredEWords[phrase]
					width = measuredEWords[phrase] = efont.measure(phrase)
					return width
				else:
					if phrase in measuredWords:
						return measuredWords[phrase]
					width = measuredWords[phrase] = font.measure(phrase)
					return width
				
			
			[estart, estop] = nextEmphasis() 
			maxWidth, finished = maximumWidth, False
			for word in words:
				index = text.find(word, index)
				wordLen = len(word)
				wordEnd = index + wordLen
				if index > estop:
					[estart, estop] = nextEmphasis()
				hasEmphasis = index < estop and wordEnd > estart
				if hasEmphasis and (estart > index or estop <= wordEnd): # word partially emphasized
					wordStart = index
					wordIdx = 0
					del buffer[0:] # save word parts until we know whole word will fit
					while index < wordEnd:
						hasEmphasis = index >= estart
						wBreak = estop if hasEmphasis else estart
						output = word[ wordIdx:wBreak-wordStart ]
						width = measuredWidth(output)
						if wBreak >= wordEnd:	# detect last part, only then add spaceLen into calcs
							width += eSpaceLen if hasEmphasis else spaceLen
						if width > maxWidth:
							finished = True
							break
						buffer.append([output, ('emphasis',tag) if hasEmphasis else (tag,)])
						wordIdx += len(output)
						index += len(output)
						maxWidth -= width
						if index >= estop:
							[estart, estop] = nextEmphasis()
					if finished: break			# word does not fit
					for chs, tags in buffer:	# output word
						txt.insert(END, chs, tags)
					txt.insert(END, ' ', ('emphasis',tag) if hasEmphasis else tag)
				else:	# output whole word
					width = measuredWidth(word) + (eSpaceLen if hasEmphasis else spaceLen)
					if width > maxWidth: break
					txt.insert(END, '{} '.format(word), ('emphasis',tag) if hasEmphasis else tag)
					index += wordLen
					maxWidth -= width

		except Exception as exc:
			errmsg = 'Exception: {}'.format(exc)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.error(errmsg)

		txt.insert(END, '\n', tag)	# lose \n when tokenize
		return index, maxWidth

	def bodyClear(self):
		self.tried = 0
		self.bodyText.config(state=NORMAL)
		self.bodyText.delete('1.0', END)
		self.bodyText.edit_reset()
		self.bodyText.edit_modified(False)
		self.delCount = 0
		self.bodyText.config(state=DISABLED)

	def cmdClear(self, event=None):
		self.closeAnyOpenFrames()
		self.cmdSearchClear()
		self.cmdLine.delete('1.0', END)

	def setconnectPort(self):
		# Set up the console's port using the consolePort setting inside the .cfg file.
		# All dynamic, private, or ephemeral ports 'should' be between 49152-65535.
		# However, the default port is 8563.
		global TCP_Port
		TCP_Port = defaultOoliteConsolePort
		consolePort = 0
		try:
			if self.localOptions['ConsolePort'] is not None:
				consolePort = int(self.localOptions['ConsolePort'])
		except:
			pass
		if consolePort > 1 and consolePort < 65536:
			TCP_Port = consolePort
			self.colorPrint("Listening on port {}.".format(TCP_Port))
			self.top.title('{}: {}'.format(DEBUGGER_TITLE, TCP_Port))
		else:
			self.colorPrint("Invalid port specified. Using default port ({}).".format(TCP_Port))
			self.top.title('{}: disconnected'.format(DEBUGGER_TITLE))

	def conflictAbort(self, errmsg):
		oops = str(errmsg)
	#	oops = "\nAnother process is already listening on "
	#	oops += "\nthe default port." if (TCP_Port == defaultOoliteConsolePort) else "port " + str(TCP_Port) +"."
		oops += "\n\nThis debug console will close now.\n"
		self.top.minsize(1, 1)
		self.top.protocol("WM_DELETE_WINDOW", reactor.stop)
		self.menubar.destroy() 			# grid_forget does nothing!

		self.cmdLine.frame.destroy()
		self.bodyText.scrollbar.grid_forget()

		titleFont = tkFont.Font(family='Arial', size=16, weight='bold')
		self.btnOK = Button(self.bodyText, text='OK', font=titleFont, bg='#eee', padx=10, command=reactor.stop)
		self.btnOK.grid(row=0, column=0, sticky=S)
		self.btnOK.rowconfigure(0, minsize=50)
		self.btnOK.columnconfigure(0, minsize=50)
		self.btnOK.update_idletasks()
		errHeight = self.btnOK.winfo_reqheight()# start counting height of window
		
		txt = self.bodyText
		txt.config(bg="#eee", state=NORMAL)
		txt.delete('1.0', END) 			# txt.index(END) will return 2.0 as txt.get('1.0',END) = '\n'
		blankFont = tkFont.Font(family='Arial', size=self.localOptions['Size'])
		txt.tag_config('blankLine', font=blankFont)
		blankHeight = blankFont.metrics('linespace')
		txt.insert(END, '\n', 'blankLine')
		errHeight += blankHeight

		txt.tag_config('header', justify=CENTER, font=titleFont, foreground='#d00')
		txt.insert(END, 'Initialisation Error', 'header')
		errHeight += titleFont.metrics('linespace')

		txt.insert(END,'\n\n', 'blankLine')
		errHeight += blankHeight * 2

		errFont = tkFont.Font(family='Arial', size=12)
		txt.tag_config('center', justify=CENTER, font=errFont, foreground='#900')
		txt.insert(END, oops, 'center')
		txt.config(state=DISABLED)
		fullMsg = txt.get('1.0', END)
		breaks = fullMsg.count('\n')
		errHeight += errFont.metrics('linespace') * breaks

		self.top.geometry('320x{}'.format( str(errHeight) ))
		self.unbind_all('<Return>')
		self.unbind_all('<Escape>')
		self.bind_all('<Return>', lambda event: reactor.stop())
		self.bind_all('<Escape>', lambda event: reactor.stop())
		self.btnOK.focus_set()
		self.top.resizable(NO, NO) 		# will cause window to blink, so do last

	def runCmd(self, event=None):
		self.closeAnyOpenFrames()
		cmd = self.cmdLine.get('1.0', END).strip()
		if cmd.startswith('/quit'):
			self.exitCmd()
		else:
			if len(cmd) > 0:
				while cmd in self.cmdHistory:
					self.cmdHistory.remove(cmd)
				self.cmdHistory.append(cmd)
			self.cmdSearchClear()
			self.cmdHistoryIdx = -1	# so cmdHistoryBack will show this cmd first 
			if hasattr(cmdLineHandler.inputReceiver,'receiveUserInput') and cmdLineHandler.inputReceiver.Active:
				self.tried = 0
				# cmdLineHandler.inputReceiver.receiveUserInput(cmd)
				# - move user cmds through queue to avoid interupting replies for silentCmds
				self.queueSilentCmd(cmd, 'USER_CMD', discard=False)
				self.cmdLine.delete('1.0', END)
				if self.localOptions['ResetCmdSizeOnRun']:
					self.appWindow.sash_place(0, 0, self.btnCmdClr.winfo_rooty())
			else:
				if self.tried == 0:
					self.colorPrint("\n{}\nYou can only use the console after you're connected.".format(CONNECTMSG))
				elif self.tried == 1:
					self.colorPrint(' * Please connect to Oolite first! * ')
				self.tried +=1
		return 'break'
				
## cmd history  ############################################################

	def loadCmdHistory(self): 			# Restore CLI history from its savefile
		self.cmdHistory = None
		self.cmdHistoryIdx = -1
		try:
			hfile = open(HISTFILE, 'rb')
			self.cmdHistory = pickle_load(hfile)
			hfile.close()
		except IOError as exc:
			if exc.errno == ENOENT:
				debugLogger.debug('No command history file found')
			else:
				debugLogger.exception('IOError loading command history: {}'.format(exc))
		except Exception as exc:
			debugLogger.exception('Error loading command history: {}'.format(exc))
		if not isinstance(self.cmdHistory, list):
			self.cmdHistory = []
		self.loadedCommands = self.cmdHistory[:]
		self.trimHistory()

	def trimHistory(self):
		history = self.cmdHistory
		currLen = len(history)
		if currLen > MAX_HIST_CMDS:
			history = self.cmdHistory = history[-MAX_HIST_CMDS:]
			currLen = len(history)
		histSize = sum(len(cmd) for cmd in history)
		while histSize > MAX_HIST_SIZE and currLen:
			histSize -= len(history.pop(0))
			currLen -= 1
		self.cmdSearchClear(reset=True)
			
	loadedCommands = None
	def saveCmdHistory(self): 			# write CLI history to its savefile
		try:
			orig, curr = self.loadedCommands, self.cmdHistory
			currLen = len(curr)
			if len(orig) == currLen and all(cmd in orig for cmd in curr):
				# with file versioning, we now only write when there has been changes
				return
			self.trimHistory()
			hfile = open(nextVersion(HIST_BASE, HIST_EXT, MAX_HIST_VERSION), 'wb')
			pickle_dump(curr, hfile, protocol=2)
			hfile.close()
		except Exception as exc:
			debugLogger.exception('Failed to save command history: {}'.format(exc))

	def cmdHistoryBack(self, event):
		histLen = len(self.cmdHistory)
		if histLen:
			if self.cmdHistoryIdx < 0:	# just ran a cmd
				self.cmdHistoryIdx = histLen - 1
			elif self.cmdHistoryIdx > 0:
				self.cmdHistoryIdx -= 1
			self.cmdHistoryShow()
			self.cmdSearchClear(reset=not (0 <= self.cmdHistoryIdx < histLen))
		return 'break'

	def cmdHistoryForward(self, event):
		histLen = len(self.cmdHistory)
		if histLen:
			if 0 <= self.cmdHistoryIdx < histLen - 1:
				self.cmdHistoryIdx += 1
			self.cmdHistoryShow()
			self.cmdSearchClear(reset=not (0 <= self.cmdHistoryIdx < histLen))
		return 'break'

	def cmdHistoryShow(self, cmd=None):
		histLen = len(self.cmdHistory)
		self.cmdLine.delete('1.0', END)
		if 0 <= self.cmdHistoryIdx < histLen:
			cmd = self.cmdHistory[self.cmdHistoryIdx]
			self.cmdLine.insert(END, cmd.rstrip(), 'command')
		elif histLen == 0:
			self.cmdHistoryIdx = -1
	
	def cmdSearchClear(self, reset=False):
		if self.cmdSearchStr is not None:
			self.cmdSearchStr = None
		if reset:
			self.cmdHistoryIdx = len(self.cmdHistory) - 1
		
	cmdSearchStr = None
	def cmdSearchHistory(self, direction):
		try: #######
		
			histLen = len(self.cmdHistory)
			if histLen and self.cmdHistoryIdx < 0:	# just ran a cmd
				self.cmdHistoryIdx = len(self.cmdHistory) - 1
			if self.cmdHistoryIdx >= 0:
				cmd = self.cmdLine.get('1.0', '1.end').strip()
				if self.cmdSearchStr is None or len(cmd) == 0:
					self.cmdSearchStr = cmd if len(cmd) else None
					curr = self.cmdHistoryIdx = histLen - 1
				else:
					cmd = self.cmdSearchStr
					curr = self.cmdHistoryIdx + direction
					if curr < 0 or curr >= histLen:
						return
				cmdLen = len(cmd)
				history = self.cmdHistory
				while curr >= 0 and curr < histLen:
					if history[curr][:cmdLen] == cmd:
						self.cmdHistoryIdx = curr
						self.cmdHistoryShow()
						break
					curr += direction
			return 'break'

		except Exception as exc: ########
			errmsg = 'Exception: {}'.format(exc)
			if dca.g['debug']:
				print(errmsg)
				print_exc()
				pdb.set_trace()
			else:
				debugLogger.error(errmsg)
		
	def deleteCurrentCmd(self, event=None):
		histLen = len(self.cmdHistory)
		if histLen > 0 and 0 <= self.cmdHistoryIdx < histLen:
			cmd = self.cmdHistory[self.cmdHistoryIdx]
			self.cmdHistory.remove(cmd)
			if self.cmdHistoryIdx >= len(self.cmdHistory):
				self.cmdHistoryIdx = len(self.cmdHistory) - 1
			self.cmdHistoryShow()
		return 'break'

## config IO ###############################################################

	def initCfgParser(self):
		if Python2:
			cfg = configparser.ConfigParser()
		else:
			cfg = configparser.ConfigParser(empty_lines_in_values=False)
		cfg.SECTCRE = TRIMSECT_RE
		cfg.optionxform = str
		if Python2:
			self.loadCfgDict(cfg, defaultConfig)
		else:
			cfg.read_dict(defaultConfig)
		return cfg

	def loadCfgDict(self, cfg, defaults): # for Python2 (configparser doesn't have read_dict method)
		for sect, olist in defaults.items():
			if not cfg.has_section(sect):
				cfg.add_section(sect)
			for key, value in olist.items():
				cfg.set(sect, key, str(value) if isinstance(value, int) else value)
				
	loadedConfig = None
	def readConfigFile(self):
		global MAX_HIST_CMDS
		
		try:
			cfg = self.initCfgParser()
			opt, col, font = self.localOptions, self.COLORS, self.FONTS
			try:
				with open(CFGFILE, 'r') as fp:
					if Python2:
						cfg.readfp(fp)
					else:
						cfg.read_file(fp)
			except IOError as exc:
				if exc.errno == ENOENT:
					debugLogger.debug('No configuration file found')
				else:
					debugLogger.exception('IOError loading configuration: {}'.format(exc))
			except Exception as exc:
				debugLogger.exception('Error loading configuration: {}'.format(exc))

			opt['SaveConfigOnExit'] =	cfg.getboolean('Settings','SaveConfigOnExit')
			self.saveConfigRead = opt['SaveConfigOnExit']
			opt['MaxHistoryCmds'] =		cfg.getint('Settings','MaxHistoryCmds')
			MAX_HIST_CMDS = opt['MaxHistoryCmds']
			opt['SaveHistoryOnExit'] =	cfg.getboolean('Settings','SaveHistoryOnExit')
			opt['Geometry'] = 			cfg.get('Settings','Geometry')
			opt['AliasWindow'] = 		cfg.get('Settings','AliasWindow')
			opt['ConsolePort'] = 	 	cfg.getint('Settings','ConsolePort')
			opt['EnableShowConsole'] =  cfg.getboolean('Settings','EnableShowConsole')
			opt['MacroExpansion'] =  	cfg.getboolean('Settings','MacroExpansion')
			opt['TruncateCmdEcho'] =  	cfg.getboolean('Settings','TruncateCmdEcho')
			opt['ResetCmdSizeOnRun'] =  cfg.getboolean('Settings','ResetCmdSizeOnRun')
			opt['MsWheelHistory'] =  	cfg.getboolean('Settings','MsWheelHistory')
			opt['PlistOverrides'] = 	cfg.getboolean('Settings','PlistOverrides')
			self.maxBufferSize = 		cfg.getint('Settings','MaxBufferSize')

			opt['Family'] =	font['Family'] = cfg.get('Font','Family')
			opt['Size']   =	font['Size'] =   cfg.getint('Font','Size')
			opt['Weight'] =	font['Weight'] = cfg.get('Font','Weight')
			opt['Slant']  =	font['Slant'] =  cfg.get('Font','Slant')

			for key in defaultConfig['Colors'].keys():
				color = cfg.get('Colors', key)
				tkColor = self.findTkColour( self.codifyColor(color) ) # findTkColour expects a '#xxxxxx' string
				key = key.lower()
				opt[ key ] = col[ key ] = color if tkColor is None else tkColor

			for key in cfg.options('Aliases'):
				value = cfg.get('Aliases', key)
				polled, part, aliasDef = value.partition(':')
				if part != ':':		# user edited config file
					self.aliasesPolled[ key ] = self.defaultPolling(value)
					opt['Aliases'][key] = self.aliasDefns[ key ] = value
				else:
					self.aliasesPolled[ key ] = polled.lower() != 'n'
					opt['Aliases'][key] = self.aliasDefns[ key ] = aliasDef
				
			self.loadedConfig = self.copyConfig()	# save copy to detect changes on Save Config Now

		except Exception as exc:
			debugLogger.exception('Failed to read configuration file: {}'.format(exc))

	def copyConfig(self):	# return a copy of options dictionary
		config = self.localOptions.copy()
		if 'Aliases' not in config:
			config['Aliases'] = {}
		config['Aliases'].update(self.aliasDefns)
		return config	
		
	def saveConfigFile(self):
		writing = False
		try:
			opt, col, font = self.localOptions, self.COLORS, self.FONTS
			if opt['SaveConfigOnExit'] or \
					opt['SaveConfigNow'] or self.saveConfigRead:
				# - saveConfigRead is the SaveConfigOnExit when loaded; if user changed True -> False,
				#   still have to update that one option
				writing = True
				cfg = self.initCfgParser()
				if cfg.get('Settings','AliasWindow') == DEFAULT_ALIAS_POSN:
					cfg.remove_option('Settings','AliasWindow') # don't save any until user has opened
			else:
				return
			
			if opt['SaveConfigOnExit'] or opt['SaveConfigNow']:	## all values must be strings
				cfg.set('Settings', 'SaveConfigOnExit',  'yes' if opt['SaveConfigOnExit'] else 'no')
				cfg.set('Settings', 'PlistOverrides', 	 'yes' if opt['PlistOverrides'] else 'no')
				# cfg.set('Settings', 'MaxHistoryCmds', 	 str(MAX_HIST_CMDS)) # not set by user via app
				cfg.set('Settings', 'SaveHistoryOnExit', 'yes' if opt['SaveHistoryOnExit'] else 'no')
				cfg.set('Settings', 'Geometry', 		 self.top.geometry())
				if hasattr(self.aliasWindow, 'mouseXY'): # window was actually opened
					cfg.set('Settings', 'AliasWindow', 	 str(self.aliasWindow.mouseXY))
				cfg.set('Settings', 'ConsolePort', 		 str(opt['ConsolePort']))
				cfg.set('Settings', 'EnableShowConsole', 'yes' if opt['EnableShowConsole'] else 'no')
				cfg.set('Settings', 'MacroExpansion', 	 'yes' if opt['MacroExpansion'] else 'no')
				cfg.set('Settings', 'TruncateCmdEcho',   'yes' if opt['TruncateCmdEcho'] else 'no')
				cfg.set('Settings', 'ResetCmdSizeOnRun', 'yes' if opt['ResetCmdSizeOnRun'] else 'no')
				cfg.set('Settings', 'MsWheelHistory', 	 'yes' if opt['MsWheelHistory'] else 'no')
				cfg.set('Settings', 'MaxBufferSize', 	 str(self.maxBufferSize))

				cfg.set('Font', 'Family', font['Family'])
				cfg.set('Font', 'Size',   str(font['Size']))
				cfg.set('Font', 'Weight', font['Weight'])
				cfg.set('Font', 'Slant',  font['Slant'])

				for key in defaultConfig['Colors'].keys(): # prevent extra colors being saved
					cfg.set('Colors', key, col[key.lower()])

				sortedAliases = OrderedDict(sorted(self.aliasDefns.items(), key=lambda t: t[0]))
				for key, value in sortedAliases.items():
					cfg.set('Aliases', key, '{}:{}'.format('P' if self.aliasesPolled.get(key, True) else 'N', value))

			elif self.saveConfigRead:  # update that option only
				with open(CFGFILE, 'r') as fp:
					if Python2:
						cfg.readfp(fp)
					else:
						cfg.read_file(fp)
				cfg.set('Settings', 'SaveConfigOnExit', 'no')

			if writing and (opt['SaveConfigNow'] or self.optionsChanged()):
				fp = open(nextVersion(CFG_BASE, CFG_EXT), 'w')
				cfg.write(fp)
				fp.close()
				self.loadedConfig = self.copyConfig()	# record changes after successful write
				return True

		except Exception as exc:
			debugLogger.exception('Failed to save configuration file: {}'.format(exc))
		return False
				
	def optionsChanged(self):		# check if any options have changed before writing
		orig, curr = self.loadedConfig, self.localOptions
		if len(orig['Aliases']) != len(self.aliasDefns):
			return True
		for key, value in self.aliasDefns.items():
			if key not in orig['Aliases'] or value != orig['Aliases'][key]:
				return True
		if hasattr(self.aliasWindow, 'mouseXY'):	# window has been opened
			if 'AliasWindow' not in orig: 			# not in config file
				return True
			if str(self.aliasWindow.mouseXY) != orig['AliasWindow']:
				return True
		for key, value in curr.items():
			if key == 'SaveConfigNow': continue	# dummy option for making menu, never saved
			if key in orig and orig[key] != value:
				return True
		return False

	def exitCmd(self):
		self.saveConfigFile()
		if self.localOptions['SaveHistoryOnExit']:
			self.saveCmdHistory()
		reactor.stop()
# end class AppWindow 

def toggleDebugMsgs():
	current = debugLogger.getEffectiveLevel()
	if current == DEBUG:
		debugLogger.setLevel(WARNING)
	else:
		debugLogger.setLevel(DEBUG)

def setTrace():
	if dca.g['debug']:
		self = app
		pdb.set_trace()

def getInputReceiver():
	return currentInputReceiver

class OoDebugConsoleHandler(StreamHandler):
	_buffer = []
	def __init__(self):
		StreamHandler.__init__(self)
	def flush(self):
		if not app: return
		for line in self._buffer:
			app.colorPrint(line, colorKey='debug', emphasisRanges=[0,len(line)])
		del self._buffer[:]
	def emit(self, record):
		try:
			if app:
				app.colorPrint(self.format(record), colorKey='debug')
			else:
				self._buffer.append('{}: {}, {}(), line {}: {}'.format(
								record.levelname, record.filename, record.funcName, 
								record.lineno, record.msg))
				if not FROZEN and record.exc_info:
					if len(record.exc_info) > 2:
						tb = format_tb(record.exc_info[2])[0].split('\n')
						if len(tb) > 1:
							self._buffer.append('\n'.join(tb[1:]))
		except Exception:
			self.handleError(record)

def nextVersion(fn, ext, max=None):
	def fmtVernFn(num):
		return '{}{}{}'.format(fn, '.{}'.format(num) if num > 0 else '', ext)
	versToIncr = []
	maxVerNum = max if max else MAX_LOG_VERSION
	for vern in range(0, maxVerNum):
		currFn = fmtVernFn(vern)
		if os.path.exists(currFn):
			if os.path.getsize(currFn) == 0:
				os.remove(currFn)
			else:
				versToIncr.append((vern, currFn))
		else:	# leave older versions alone
			break
	for vern, currFn in reversed(versToIncr):
		nextFn = fmtVernFn(vern + 1)
		if vern + 1 == maxVerNum and os.path.exists(nextFn):
			os.remove(nextFn)
		if Python2:
			os.rename(currFn, nextFn)
		else:
			os.replace(currFn, nextFn)
	return fmtVernFn(0)

def initLogger():
	global consoleHandler, debugLogger
	# set up logging to file
	basicConfig(level=WARNING, filename=nextVersion(LOG_BASE, LOG_EXT), filemode='w',
						format='%(asctime)s %(levelname)-8s %(message)s (%(filename)s: %(funcName)s, line %(lineno)s)')
	if FROZEN or not sys.stdout.isatty():
		consoleHandler = OoDebugConsoleHandler()	# handler for WARNING messages or higher to debug console
	else:
		consoleHandler = StreamHandler()			# handler for WARNING messages or higher to sys.stderr
	consoleHandler.setLevel(WARNING)
	# set a format which is simpler for console use
	formatter = Formatter('%(name)-12s: %(levelname)-8s %(message)s')
	consoleHandler.setFormatter(formatter)			# tell the handler to use this format
	debugLogger = getLogger('DebugConsole')
	debugLogger.setLevel(WARNING)      				# activate debug logger output
	debugLogger.addHandler(consoleHandler)			# add the handler to the root logger
	debugLogger._srcfile = None						# speed optimizations
	debugLogger.logThreads = 0						#   "
	debugLogger.logProcesses = 0					#   "
	debugLogger.logMultiprocessing = 0				#   "
	if not dca.g['debug'] and (FROZEN or not sys.stdout.isatty()):
		debugLogger.write = debugLogger.debug		# consider all prints as debug information
		debugLogger.flush = lambda: None			# this may be called when printing
		sys.stdout = debugLogger
		sys.stderr = debugLogger
	elif dca.g['debug']:
		debugLogger.setLevel(DEBUG) 

app = None
def main():
	global app, cmdLineHandler
	
	initLogger()
	app = AppWindow()							## required global for SimpleConsoleDelegate
	consoleHandler.flush()

	# Set up console server protocol
	factory = Factory()
	factory.delegateClass = SimpleConsoleDelegate
	factory.activeCount = 0
	factory.protocol = OoliteDebugConsoleProtocol

	# Set up command line I/O protocol
	cmdLineHandler = OoliteDebugCLIProtocol()	## required global for SimpleConsoleDelegate
	cmdLineHandler.getInputReceiver = getInputReceiver
	stdio.StandardIO(cmdLineHandler)

	# Install the Reactor support
	tksupport.install(app.top)

	lineNum = app.bodyText.index(END).split('.')[0]
	if int(lineNum) > 2:
		app.colorPrint('') 				# add blank line after any error msg
	try:
		app.listener=reactor.listenTCP(TCP_Port, factory)
		app.colorPrint("Oolite Debug Console (version " + __version__ + ")")
		app.colorPrint("Use Up and Down arrows to scroll through the command history.")
		app.colorPrint("Type /quit to quit.")
		app.colorPrint("To (dis)re-connect a running Oolite: In-flight, pause and press 'c'.")
		app.colorPrint("Waiting for connection...")
	except Exception as exc:
		debugLogger.exception(exc)
		if app: app.conflictAbort(exc)

	# Wait for user input.
	reactor.run()
	shutdown()
	if os.path.exists(LOGFILE) and os.path.getsize(LOGFILE) == 0:
		os.remove(LOGFILE)

if __name__ == "__main__":
	if not dca.g['debug'] and (FROZEN or not sys.stdout.isatty()):
		try:
			main()
		except Exception as exc:
			errmsg = 'Exception: {}'.format(exc)
			debugLogger.exception(errmsg)
	else:
		main()
