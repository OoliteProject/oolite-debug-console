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
#  GUI stuff (c) 2019 cag CC BY-NC-SA 4
#

"""
A gui implementation of the Oolite JavaScript debug console interface.
"""

__author__	= "Jens Ayton <jens@ayton.se>, Kaks, cag"
__version__	= "2.0"

import sys, os, time, logging, errno, gc

import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import ttk
else:
	import tkinter as tk
	import tkinter.ttk as ttk

from ooliteConsoleServer import OoliteDebugConsoleProtocol, defaultOoliteConsolePort
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol

from twisted.internet import stdio, reactor, tksupport
from twisted.internet.error import CannotListenError
from twisted.python.failure import Failure
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import serverFromString
from twisted.internet.tcp import Port as TwistedPort
# from twisted.internet.defer import Deferred

import debugGUI.aliases as al
import debugGUI.appUtils as au
import debugGUI.buildApp as ba
# import debugGUI.bitmaps as bm
import debugGUI.cmdHistory as ch
import debugGUI.colors as cl
import debugGUI.comments as cmt
import debugGUI.config as cfg
import debugGUI.constants as con
import debugGUI.debugMenu as dm
# import debugGUI.findFile as ff
import debugGUI.fontMenu as fm
import debugGUI.globalVars as gv  
import debugGUI.miscUtils as mu
# import debugGUI.optionsMenu as om
import debugGUI.plistMenu as pm
import debugGUI.regularExpn as rx
import debugGUI.stringUtils as su
# import debugGUI.style as st
import debugGUI.widgets as wg

## module variables ###########################################################

if con.IS_WINDOWS_PC and sys.executable.endswith('pythonw.exe'):
	sys.stdout = open(os.devnull, 'w')
	sys.stderr = open(os.path.join(os.getcwd(),
						'stderr-' + os.path.basename(sys.argv[0])), 'w')

# network
_consoleHandler = None
# new in debugConsole ver. 1.6
connectPort = None	
connectEndPort = None
clientAddress = None

## network class ##############################################################

# noinspection PyMethodMayBeStatic
class SimpleConsoleDelegate:
	__active = Active = False

	def __init__(self, protocol):
		self.protocol = protocol
		self.identityString = "DebugConsole"
		self._host = ''
		self._port = 0

	# noinspection PyUnresolvedReferences
	def __del__(self):
		if self.__active: 
			self.protocol.factory.activeCount -= 1
		if _consoleHandler.inputReceiver is self:  
			_consoleHandler.inputReceiver = None

	def acceptConnection(self):
		return self.protocol.factory.activeCount < 1

	def connectionOpened(self, ooliteVersionString):
		self._host, self._port = self.protocol.transport.socket.getsockname()
		# - getpeername() is used for other end of connection (ie. Oolite)
		msg = 'Opened connection with Oolite version {} at {}:{}\n'.format(
				ooliteVersionString, self._host, self._port)
		gv.app.colorPrint(msg, emphasisRanges=[38,len(ooliteVersionString)])
		gv.bodyText.update_idletasks()
		gv.bodyText.edit_modified(False)
		self.protocol.factory.activeCount += 1
		self.__active = self.Active = True
		_consoleHandler.inputReceiver = self
		gv.app.client = self.protocol
		_stopOtherListeners(self._port)

	def loadConfig(self, config):		
		# settings received from client
		# - config is a dict of debugger settings
		if not gv.connectedToOolite:
			pm.initClientSettings(config)
			au.setAppTitle(au.fmtServerAddress(self._host, self._port))
		else:
			gv.app.noteConfig(config)

	def connectionClosed(self, message):
		if gv.root is None:
			# Oolite's disconnect packet snuck in before we could exit
			return
		pm.disableClientSettings()
		if message is None or su.is_str(message):
			if message is None or len(message) == 0:
				timeStr = time.strftime('%d %b %Y, %H:%M:%S')
				msg = 'Connection closed with no message at {}'.format(
															timeStr)
				gv.app.colorPrint(msg, emphasisRanges=[37,len(timeStr)])
			else:
				gv.app.colorPrint('Connection closed: "{}"'.format(
								message), emphasisRanges=[20,len(message)])
		if self.__active:
			self.protocol.factory.activeCount -= 1
			self.__active = self.Active = False
		gv.app.tried=0
		gv.app.client = None

	def writeToConsole(self, message, colorKey, emphasisRanges):
		gv.app.handleMessage(message, colorKey, emphasisRanges)

	def clearConsole(self):
		gv.app.bodyClear()

	def showConsole(self):
		if gv.CurrentOptions['Settings'].get('EnableShowConsole', False):
			if gv.root.state() != 'zoomed' and gv.root.state() != 'normal':
				gv.root.state('normal')
			gv.root.wm_attributes("-topmost", 1)
			gv.root.wm_attributes("-topmost", 0)
			gv.root.lift()
			gv.cmdLine.focus_set()

	def receiveUserInput(self, string):
		self.protocol.sendCommand(string)

	def closeConnection(self, message):
		self.protocol.closeConnection(message)
# end class SimpleConsoleDelegate

## logger class ###############################################################

class OoDebugConsoleHandler(logging.StreamHandler):
	_buffer = []
	def __init__(self):
		logging.StreamHandler.__init__(self)
		
	def flush(self):
		if gv.setupComplete:
			for line in self._buffer:
				gv.app.colorPrint(line, colorKey='debug', 
									emphasisRanges=[0,len(line)])
			del self._buffer[:]
			
	def emit(self, record):
		# noinspection PyBroadException
		try:
			if gv.setupComplete:
				gv.app.colorPrint(self.format(record), colorKey='debug')
			else:
				self._buffer.append('{}: {}, {}(), line {}: {}'.format(
						record.levelname, record.filename, record.funcName,
						record.lineno, record.msg))
				if not con.FROZEN and record.exc_info:
					if len(record.exc_info) > 2:
						tb = traceback.format_tb(record.exc_info[2])
						tb = tb[0].split(con.NL)
						if len(tb) > 1:
							self._buffer.append(con.NL.join(tb[1:]))
		except Exception:
			self.handleError(record)

###
class OOClientAddressFactory(Factory):
	def buildProtocol(self, addr):
		global clientAddress
### memory leak

		clientAddress = addr
		return Factory.buildProtocol(self, addr)

## application class ##########################################################

class AppWindow(ttk.Frame):

	client = None	# pointer to OoliteDebugConsoleProtocol instance
	aliases = None

## disabled override of Tk exception handling (needs work)
	# noinspection PyBroadException
	def __init__(self):
		top = gv.root = tk.Tk()
		top.minsize(con.MINIMUM_WIDTH, con.MINIMUM_HEIGHT)
		top.resizable(width=True, height=True)
		top.title(con.DEBUGGER_TITLE)
		top.protocol("WM_DELETE_WINDOW", self.exitCmd)
		top.bind('<FocusIn>', au.liftMainWindow)
		# app has 2 frames stacked vertically
		# for the menubar and the PanedWindow
		# left justify the frames
		top.columnconfigure(0, weight=1)	
		# PanedWindow, not menubar, stretches vertically
		top.rowconfigure(1, weight=1)
		
		# # override Tk exception handling
		# top.report_callback_exception = au.report_callback_exception

		# counter for messages when there's no connection (see runCmd())
		self.tried=0

		gv.menubar = ttk.Frame(top, name=mu.TkName('menubar'))
		ttk.Frame.__init__(self, top, name=mu.TkName('appFrame'))

		iconFile = 'OoJSC256x256.png' if con.IS_LINUX_PC else 'OoJSC.ico'
		iconPath = os.path.join(os.getcwd(), iconFile)
		if con.FROZEN:
			meipass = None
			if hasattr(sys, '_MEIPASS'):
				# noinspection PyProtectedMember
				meipass = sys._MEIPASS
			elif '_MEIPASS2' in os.environ:
				# windows compiled runtime (pyInstall)
				meipass = os.environ['_MEIPASS2']
			if meipass:
				iconPath = os.path.join(meipass, iconFile)

		# Under Windows, the DEFAULT parameter can be used to set the icon
		# for the widget and any descendants that don't have an icon set
		# explicitly.  DEFAULT can be the relative path to a .ico file
		# (example: root.iconbitmap(default='myicon.ico') ).
		if con.IS_WINDOWS_PC:
			try:
				top.iconbitmap(default=iconPath)
			except:
				try:
					top.iconbitmap(default=os.path.join(
								os.path.dirname(sys.argv[0]), iconFile))
				except:
					try:
						top.iconbitmap(default='@oojsc.xbm')
					except:
						pass
		else:
			try:
				top.iconphoto(False, PhotoImage(file=iconPath))
			except:
				try:
					top.iconbitmap(iconPath)
				except:
					try:
						top.iconbitmap(os.path.join(
									os.path.dirname(sys.argv[0]), iconFile))
					except:
						try:
							top.iconbitmap('@oojsc.xbm')
						except:
							pass

	def setupApp(self):
		gv.root.attributes('-alpha', 0.0)	# turn off while building
		gv.root.update_idletasks()
		au.monitorResolutions()

		# upper Frame
		gv.menubar.rowconfigure(0, weight=1)
		# for alias menu button frame, which is gridded into column 2
		# this ensures it's right justified
		gv.menubar.columnconfigure(1, weight=1) 
		gv.menubar.grid(row=0, column=0, sticky='new')

###	gv.app is self 
		
		# lower Frame
		# make the PanedWindow fill its Frame
		self.rowconfigure(0, weight=1)		
		self.columnconfigure(0, weight=1)
		self.grid(row=1, column=0, sticky='news')
		
		# check if geometry is valid, adjust as needed
		geom = gv.CurrentOptions['Settings'].get('Geometry', con.DEFAULT_GEOMETRY)
		width, height, xOffset, yOffset = au.fitToMonitors(geom)
		gv.root.geometry('{}x{}+{}+{}'.format(width, height, xOffset, yOffset))

		ba.buildGUI()
		ch.loadCmdHistory()
		self.setconnectPort()
		# initiate messaging and message processing
		au.afterLoop(gv.tkTiming['fast'], 'sendSilentCmd',self.sendSilentCmd)
		au.afterLoop(gv.tkTiming['fast'], 'processMessages',gv.app.processMessages)

## Client functions ###########################################################

	def getClientSetting(self, key):
		if not gv.connectedToOolite:
			return
		value = self.client.configurationValue(key)
		return value

	def setClientSetting(self, key, value):
		print(f'setClientSetting, {key}: {value}')
		if not gv.connectedToOolite:
			return
		self.client.setConfigurationValue(key, value)

	# these are console properties, with setter & getter fns; cannot use 
	# setConfigurationValue, as (3 of 4) values are stored in private 
	# properties (eg. __dumpStackForErrors); we'd get out of sync otherwise
	_consoleProps = {
		'dump-stack-for-errors':	'dumpStackForErrors',
		'dump-stack-for-warnings':	'dumpStackForWarnings',
		'show-error-locations':		'showErrorLocations',
		'show-error-locations-during-console-eval': \
					'showErrorLocationsDuringConsoleEval'
		}

	def setClientCheckButton(self, key, tkVar):
		if not gv.connectedToOolite:
			return
		value = tkVar.get()
		if key in self._consoleProps:
			setter = self._consoleProps[key]
			self.queueSilentCmd('console.{} = {}'.format(
							setter, 'true' if value else 'false'), key)
		else:
			self.client.setConfigurationValue(key, value)

	@staticmethod
	def noteConfig(oolite):
		# ack from setConfigurationValue OR actual changes from macros!
		# - can sometimes be initial settings dict if user hits 'c' repeatedly
		processingConnectonDict = len(gv.ooliteColors) > 0
		for key, value in oolite.items():
			if key == 'default-macros':
				continue
			if key.endswith('-color'):
				value = gv.Appearance.codifyColor(value)
				if processingConnectonDict:
					# still processing colors from connection settings dict,
					# so just add it to the queue
					gv.ooliteColors[key] = value
				else:
					cl.applyMsgColor(key, value)
					continue			# OoSettings set in applyMsgColor()
			elif key.startswith('font'):
				if key.endswith('face'):
					if fm.isAvailableFont(value):
						gv.OoSettings[key] = value
						if gv.appearance.usingOoColors():
							fm.setFontFace(value, send=False,
								   	   	   skipUpdate=processingConnectonDict)
				elif key.endswith('size'):
					gv.OoSettings[key] = value
					if gv.appearance.usingOoColors():
						fm.setFontSize(value, send=False)
			else: # values only need storing in OoSettings
				value = str(value) if isinstance(value, int) else value
				value = True if value.lower() in con.TRUE_STRS else False
				gv.OoSettings[key] = value

## app functions ##############################################################

	requests = []
	replyPending = None
	replyPendingTimer = None
	# namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')
	def queueSilentCmd(self, cmd, label, tkVar=None, discard=True):
		if self.cmdHandlerActive():
			if label == 'USER_CMD':		
				self.sendPriorityCmd(cmd)
				return
			# all internal commands are submitted one at a time, the receipt 
			# of its reply triggering the next
			# - replies are guaranteed as while some commands don't expect 
			#   a reply, all are submitted as IIFE's that add the commands 
			#   label & echoing instructions (aka discard) to the 
			#   reply (if any) in their return
			self.submitRequest(gv.SilentMsg(cmd, label, tkVar, discard, None))

	def queueImmediateCmd(self, cmd, label, tkVar=None, discard=True):
		if self.cmdHandlerActive():
			# currently only used for menubar buttons, this jumps the queue
			# by adding to top of queue and flushing any pending cmd
			self.submitRequest(
					gv.SilentMsg(cmd, label, tkVar, discard, None), now=True)
			self.reSubmitPending()

	def sendPriorityCmd(self, cmd):
		if not gv.pollingSuspended:
			# suspend all message traffic w/ Oolite during user commands
			gv.pollingSuspended = True
			self.reSubmitPending()
		self.sendCmdToHandler(cmd)

	@staticmethod
	def submitRequest(request, now=False):	# ensure no duplicates in queue
		label = request.label
		if label in gv.timedOutCmds:
			currentTime = mu.timeCount()
			elapsed = currentTime - gv.timedOutCmds[label].timeSent
			if now and label in gv.timedOutCmds:
				del gv.timedOutCmds[label]
			elif label == 'gameStarted' and gv.sessionInitialized == 0:
				# reply not guaranteed during game load so keep sending
				# leave in timedOutcommands so processSilentCmd will 
				# process errant replies
				# noinspection PyProtectedMember
				gv.timedOutCmds[label] = gv.timedOutCmds[label]._replace(
												timeSent=currentTime)
			elif elapsed > con.CMD_TIMEOUT_ABORT:
				# only process if not too stale
				errmsg = 'aborting "{}"(elapsed = {})'.format(label, elapsed)
				gv.debugLogger.debug(errmsg)
				del gv.timedOutCmds[label]
			else:						
				# give it more time
				errmsg = 'giving "{}" more time (elapsed = {})'.format(label, elapsed)
				gv.debugLogger.debug(errmsg)
				return
		if now:
			gv.requests.insert(0, request)
		elif label not in [m.label for m in gv.requests]:
			gv.requests.append(request)

	def reSubmitPending(self):			# re-enqueue replyPending
		msg = gv.replyPending
		if msg:
			if (msg.label == 'gameStarted' and gv.gameStarted.get() == 0) \
				or msg.label not in \
					['gameStarted', 'pollDebugFlags',
					 'currStarSystem',	# these are regularly polled
					 'setDetailLevel', 'writeMemoryStats']:
							# - these can easily time-out
				self.submitRequest(msg)	# resubmit msg
		# allow sendSilentCmd to send next in queue
		gv.replyPending = gv.replyPendingTimer = None 	

	@staticmethod
	def mkCmdIIFE(msg):			# wrap msg as an IIFE
		iife = '(function() { var result, label = '
		iife += '"<label:{}><discard:{}>", '.format(
					msg.label, 'yes' if msg.discard else 'no')
		iife += 'noVal = "no result" + label; '
		iife += 'try { result = ' + '{}{}'.format(msg.cmd,
								'' if msg.cmd.strip().endswith(';') else ';')
		iife += ' } catch (e) { '
		if not msg.discard:
			iife += 'console.consoleMessage(e); '
		iife += 'return noVal; } return result + label; })()'
		return iife

	lastSentTime = None ###
	def sendSilentCmd(self):
		au.removeAfter('sendSilentCmd')
		au.afterLoop(gv.tkTiming['lazy'], 'sendSilentCmd',self.sendSilentCmd)
		if gv.pollingSuspended:
			return
		if len(gv.pendingMessages) > 0:				
			# don't interfere w/ large outputs
			return
		if not gv.replyPending and len(gv.requests):
			# wait for reply before sending next
			if self.cmdHandlerActive():
				msg = gv.requests.pop(0)
				# start time-out clock
				gv.replyPendingTimer = mu.timeCount()
				# noinspection PyProtectedMember
				gv.replyPending = msg._replace(timeSent=gv.replyPendingTimer)
				# wrap all internal commands in IIFE for label & discard
				iife = self.mkCmdIIFE(msg)
				self.sendCmdToHandler(iife)
		elif gv.replyPendingTimer is not None: 		
			# monitor elapsed time to abort for non-reply
			elapsed = mu.timeCount() - gv.replyPendingTimer
			label = gv.replyPending.label
			if label in ['setDetailLevel', 'writeMemoryStats', ]:
				# a few commands can be time consuming
				timedOut = elapsed > con.CMD_TIMEOUT_LONG
			elif label.startswith('alias'):
				timedOut = elapsed > con.CMD_TIMEOUT_ABORT
			else:
				timedOut = elapsed > con.CMD_TIMEOUT
			if timedOut:
				gv.timedOutCmds[label] = gv.replyPending
				self.reSubmitPending()

	@staticmethod
	def _showLastCommand(message): # debug fn

		def head(array, begin=0, stop=None):
			_length = len(array)
			if stop is None:
				stop = _length
			else:
				stop = min(stop, _length)
			return array[begin:min(begin + _WIDTH, stop)]

		def tail(array, begin=0, stop=None):
			_length = len(array)
			if stop is None:
				stop = _length
			else:
				stop = min(stop, _length)
			if stop <= begin + _WIDTH: return ''
			return array[max(stop - _WIDTH, stop - (begin + _WIDTH)):stop]

		_WIDTH = 120
		if gv.lastCommand and con.CAGSPC:
			lenM = len(gv.lastCommand)
			print('>>> lastCommand ({}): {!r}{}'.format(
					lenM, head(gv.lastCommand),
					'' if lenM <= _WIDTH else '\n ... {!r}'.format(
							tail(gv.lastCommand))))
			lenM = len(message)
			print('>>> message ({}): {!r}{}'.format(
					lenM, head(message),
					'' if lenM <= _WIDTH else '\n ... {!r}'.format(
							tail(message))))

	def handleException(self, message, colorKey, emphasisRanges):
		self._showLastCommand(message)
		lowMsg = message.lower()
		try:
			if not gv.lastCommand or not gv.replyPending:
				# no info to find cause, just output it
				print('handleException, no info to find cause, just output it')
				gv.pendingMessages.append((message, colorKey, emphasisRanges))
				gv.lastCommand = None  # prevent being associated w/ future command
				return

			# problem: exception occurred but who caused it?
			# - user cmd -> is gv.pollingSuspended == True
			# - polling of alias -> is 'alias-' in lastCommand.label
			#   - not enough, as polling could reply later, in which
			#     case it's from an oxp

			# try checking active script
			isOxpScript = False
			if 'active script: ' in lowMsg:
				isOxpScript = 'oolite-debug-console.js' not in lowMsg \
							  and '<line out of range' not in lowMsg
				# - still not perfect
			# script = message.find('Active Script: ') # len is 15
			# if -1 < script:
			# 	active = message[script + 15 : message.find(':', script + 15)]
			# 	isOxpScript = active.startswith('oolite-debug-console')

			# check if alias was last command sent
			msgTag = rx.MSGLABEL_RE.search(gv.lastCommand)
			cmdPending = msgTag['label'] if msgTag else None
			aliasPending = cmdPending.startswith('alias') if cmdPending else False
			consoleLoad = '<line out of range' in lowMsg
			# - this can also happen registering long aliases
			print('handleException, msg label: {}, cmdPending: {}, aliasPending: {}'.format(
					msgTag['label'] if msgTag else 'nada', cmdPending, aliasPending))
			print('    pollingSuspended: {}, replyPending: {}'.format(
					gv.pollingSuspended, gv.replyPending.label))
			print('    isOxpScript: {}, consoleLoad: {}'.format(isOxpScript, consoleLoad))

			print('lastCommand\n', gv.lastCommand)

			if gv.pollingSuspended and not aliasPending:
				# must be result of user command
				print('handleException, user\'s fault, pollingSuspended and not aliasPending')
				gv.pendingMessages.append((message, colorKey, emphasisRanges))
			elif aliasPending and cmdPending == gv.replyPending.label: # not consoleLoad and
				# alias caused the exception

				# condition is not enough as this catches errors in closure loaded via console
				# added consoleLoad ...

				print('handleException, alias caused the exception')
				al.rptAliasError(msgTag, message, self.colorPrint)
			elif isOxpScript:
				# oxp caused exception
				script = lowMsg.find('active script: ')  # len is 15
				active = message[script + 15: message.find(':', script + 15)]
				print('handleException, oxp caused the exception: {}'.format(active))
				gv.pendingMessages.append((message, colorKey, emphasisRanges))
			elif cmdPending == gv.replyPending.label:
				# some other silentMsg is the cause
				print('handleException, some other silentMsg is the cause')
				gv.pendingMessages.append((message, colorKey, emphasisRanges))
			else:
				print('handleException, else case, have no clue')
				gv.pendingMessages.append((message, colorKey, emphasisRanges))
			gv.lastCommand = None	# prevent being associated w/ future command

		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()
# # #

# # #
	def handleMessage(self, message, colorKey, emphasisRanges):
		# queue up messages from Oolite
		if colorKey == 'command' and message.strip() != '>':
			# ie. not a blank cmd
			gv.lastCommand = message
		elif colorKey == 'exception':
			self.handleException(message, colorKey, emphasisRanges)
			return
		elif colorKey == 'command-result':
			BUTTON_STR = '<label:btn-'
			BUTTON_STR_LEN = len(BUTTON_STR)
			if gv.lastCommand and BUTTON_STR in gv.lastCommand:
				start = gv.lastCommand.find(BUTTON_STR) + BUTTON_STR_LEN
				end = gv.lastCommand.find('-', start)
				alias = '' if end < 0 else gv.lastCommand[start:end]
				if 'Error:' in message:
					# user's menubutton caught an Exception, trapped here
					# as silent cmd responses are usually discarded
					obj = gv.aliases.get(alias)
					if obj:
						prefix = 'menu button "'
						prefix += obj.match['fnName'] \
								if obj.match and obj.match['fnName'] else alias
						prefix += '": '
						message = prefix + message
					self.colorPrint(message, colorKey, emphasisRanges)
					return
			LABEL_STR = '<label:'
			LABEL_STR_LEN = len(LABEL_STR)
			DISCARD_STR = '><discard:'
			if BUTTON_STR in message:
				if message.startswith('undefined') \
						or message.endswith('<discard:yes>'):
					# clear queue for next cmd
					start = message.find(LABEL_STR) + LABEL_STR_LEN
					end = message.find(DISCARD_STR, start)
					label = '' if end < 0 else message[start:end]
					if label in gv.timedOutCmds:
						del gv.timedOutCmds[label]
					gv.replyPending = gv.replyPendingTimer = None
					return

		gv.pendingMessages.append((message, colorKey, emphasisRanges))
		# must buffer incoming messages, as sent faster than we can output 
		# (ie. in bursts, esp. at startup) but a large volume can still
		# get OSError: [Errno 28] No space left on device
		length = len(gv.pendingMessages)
		if length > 3 * self.messageBatchSize:
			self.messageBatchSize += self.messageBatchSize // 2
			status = 'buffer has {} messages, => '.format(length)
			status += 'larger messageBatchSize {}'.format(self.messageBatchSize)
			if con.CAGSPC:
				print('handleMessage' + status)
			else:
				gv.debugLogger.debug(status)

	# Oolite resends packet header after 8 ms & again after 16 ms
	#   but only retries sending packet body once, after 8 ms
	# - processMessages can exceed 8 ms for a particularly long message
	## ?add interrupt into colorPrint

	messageBatchSize = 25
	# messageQueueID = None
	def processMessages(self):			
		# deal with queued messages from Oolite
		debugStatus = message = colorKey = emphasisRanges = None
		try:
			pending = len(gv.pendingMessages)
			numMsgs = min(self.messageBatchSize, pending)
			au.removeAfter('processMessages')
			if numMsgs == 0:				
				# no messages to process
				au.afterLoop(gv.tkTiming['lazy'], 'processMessages', 
							self.processMessages)
				return
			if pending > numMsgs:			
				# more than can be processed in one call
				au.afterLoop(gv.tkTiming['fast'], 'processMessages', 
							self.processMessages)
			else:							
				# expect to process all this call (see below)
				au.afterLoop(gv.tkTiming['lazy'], 'processMessages', 
							self.processMessages)

			startTime = mu.timeCount()
			startCount = len(gv.pendingMessages)
			while numMsgs > 0 and len(gv.pendingMessages) > 0: # NB: .pop below
				# - added len() check for game reload causing Exception 
				# 	 'pop from empty list'
				# if you time it just right, the Tk var trace on 
				# sessionStartTime will occurs during this loop, which 
				# runs sessionCleanup, which calls this fn/iife ...
				#   ie. inadvertent recursion by Tk trace! 
				elapsed = (mu.timeCount() - startTime) * 1000
				if elapsed >= 8:  		
					# spent too much time processing, next call is done
					# quickly (8 ms is Oolite retry wait time)
					if con.CAGSPC:
						print('processMessages, quitting due to elapsed: {:3.4f} ms, startCount: {}'
							  .format(elapsed, startCount)) ###
						print('  pending ({}):\n  {}'.format(len(gv.pendingMessages),
								'\n  '.join('{}: {}'.format(pend[1], pend[0][:100])
										  for pend in gv.pendingMessages)))
					au.afterLoop(gv.tkTiming['fast'], 'processMessages', 
								self.processMessages)
					break
				debugStatus = None
				numMsgs -= 1
				message, colorKey, emphasisRanges = gv.pendingMessages.pop(0)
				debugStatus = 'popped'

				if colorKey not in ['command', 'command-result']:
					# it's an oolite message
					isLastOfRun = colorKey != gv.pendingMessages[0][1] \
									if numMsgs > 0 else True
					self.colorPrint(message, colorKey, emphasisRanges, 
									lastInBatch=isLastOfRun)
					debugStatus = 'printed'
					continue

				msgLabel = discard = msgTagStart = None
				msgTag = rx.MSGLABEL_RE.search(message)
				if msgTag:
					msgLabel, discard = msgTag['label'], msgTag['discard']
					msgTagStart = msgTag.start('msglabel')

				if msgLabel is None:		
					# must be part of a USER_CMD or its reply
					isEcho = message.startswith('_ ')
					if isEcho:				
						# multi-line user commands get echoed w/ '_ ' prefix
						if pm.suspendMenu is None:
							# first time we know it's multi-line
							pm.suspendMsgTraffic()
					elif gv.pollingSuspended:	
						# no '_ ' prefix => user cmd reply
						# user cmd ends, release queue for internal ones
						pm.restoreMsgTraffic()
					if gv.pollingSuspended or message != '> ': 
						# suppress trailing '>' line
						self.colorPrint(message, colorKey, emphasisRanges, 
										lastInBatch=True)
					debugStatus = 'printed'
					break

				if colorKey == 'command':	
					# never echo internal commands
					debugStatus = 'printed'
					continue

				# internal commands always get a reply, though it may be 
				# 'no result' (done for firm control of traffic)
				if not gv.replyPending or gv.replyPending.label != msgLabel:	
					# unexpected reply
					if discard != 'yes':
						self.colorPrint(message, colorKey, emphasisRanges)
						debugStatus = 'printed'
						msg = 'no reply expected for message, '
						msg += 'replyPending: {}'.format(gv.replyPending)
						msg += '\n    colorKey {}, message: {}'.format(
								colorKey, message[:80] \
										  + (' ...' if len(message) > 80 else ''))
						if con.CAGSPC:
							print(msg)
							traceback.print_exc()
							pdb.set_trace()
						else:
							gv.debugLogger.warning(msg)
					if gv.pollingSuspended:	
						# timed out due to user cmd
						self.reSubmitPending()
						# don't process stale msg
						continue		

				debugStatus = self.processSilentCmd(msgLabel, 
								discard, msgTagStart, message, colorKey, 
								emphasisRanges, lastInBatch=(numMsgs == 0) )
			# endwhile

		except IOError as exc:
			if exc.errno == errno.ENOSPC:	# 'No space left on device'
				if debugStatus != 'printed':
					# restore failed message
					gv.pendingMessages.insert(0, (message, colorKey, 
													emphasisRanges))
				gc.collect() # garbage collect to avoid? future occurrences
				if self.messageBatchSize > 1:
					self.messageBatchSize = 1 if self.messageBatchSize < 4 \
											else self.messageBatchSize // 2
					status = 'smaller messageBatchSize '
					status += str(self.messageBatchSize)
					if con.CAGSPC:
						print('processMessages, ' + status)
					else:
						gv.debugLogger.debug(status)
			else:
				errmsg = 'IOError: {!r}'.format(exc)
				gv.debugLogger.exception(errmsg)
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.error(errmsg)
		except Exception as exc:
			errmsg = 'Exception: {!r}'.format(exc)
			if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
			else:
				gv.debugLogger.error(errmsg)

	def processSilentCmd(self, msgLabel, discard, msgTagStart, message,
						colorKey, emphasisRanges, lastInBatch=True): 
		# silentCmd replies from Oolite
		debugStatus = 'popped'
		result = message[ : msgTagStart]
		# namedtuple('SilentMsg', 'cmd, label, tkVar, discard, timeSent')
		if gv.replyPending and gv.replyPending.label == msgLabel:
			request = gv.replyPending
			# clear before setting tkVars as some have traces that
			# will queueSilentCmd's and those will be dropped if 
			# replyPending is not None (eg. signScript)
			gv.replyPending = gv.replyPendingTimer = None
		elif msgLabel in gv.timedOutCmds:
			request = gv.timedOutCmds[msgLabel]
			elapsed = mu.timeCount() - request.timeSent
			if elapsed > con.CMD_TIMEOUT_ABORT:	
				# only process if not too stale
				del gv.timedOutCmds[msgLabel]	# delete expired command
				return 'printed'
		else:	
			# a timed out command that's expired
			return 'printed'

		if message.startswith('_ '):	# internal cmd failed
			gv.debugLogger.warning('**** internal error: {}'.format(message))
			self.reSubmitPending()
		elif request.label.startswith('alias'):
			al.reportAliasRegistration(request.label, result)
		elif request.tkVar is not None:	
			# it's a command-result
			if request.label in ['scriptProps', 'detailLevel',
									'signScript', 'timeAccelQuery']:
				try:
					request.tkVar.set(result)
				except Exception as exc:
					## Exception usually means there's a problem elsewhere but tkinter exception overrides/hides it
					if request.label == 'signScript' and request.tkVar.get() == result:
						print('  got {!r} during successful set of sessionStartTime'.format(result))
					else:
						print(exc, type(exc))
						traceback.print_exc()
						pdb.set_trace()

			elif request.label in ['entityDumpVar', 'filterMemStatsVar']:
				# signals dump is complete
				request.tkVar.set(1)	
			elif not result.startswith('no result'):
				dm.setDebugOption(request.label, result, request.tkVar)
			else:
				errmsg = 'unsupported result '
				errmsg += '"{}" for label "{}"'.format(result, msgLabel)
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.error(errmsg)
		elif msgLabel.startswith('del-') and msgLabel.endswith('-IProp'):
			if result != 'true':
				errmsg = 'error deleting iife property '
				errmsg += '"{}", result "{}"'.format(msgLabel, result)
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.error(errmsg)
		if not message.startswith('no result') and discard == 'no':
			self.colorPrint(message, colorKey, emphasisRanges, lastInBatch)
			debugStatus = 'printed'
		return debugStatus

	@staticmethod
	def checkBufferSize():
		# keep the buffer at a reasonable size, called 1/100 colorPrint's
		# (?cause of OSError [Errno 28] No space left on device)
		txt = gv.bodyText				
		if gv.screenLines is None:		
			# 1st check or font has changed (is reset in updateAppsFontChange)
			height = txt.winfo_reqheight()	# pixels
			# number of lines on screen
			gv.screenLines = int(height / gv.lineSpace)
		lines, chars = txt.count('1.0', 'end', 'lines', 'chars')
		if chars > gv.CurrentOptions['Settings'].get('MaxBufferSize', 200000):
			txt.config(state='normal')
			txt.delete('1.0', '{}.end'.format(int(lines / 2)))
			txt.config(state='disabled')

	printCount = 0
	stateNormal = False
	printBuffer = []
	printTag = None
	printKey = None
	filteringColorPrint = False
	def colorPrint(self, text, colorKey='debugger', 
					emphasisRanges=None, lastInBatch=True):
		txt = gv.bodyText
		try:
			if gv.colorPrintFilterREs is not None:
				# filter undesirable messages
				
				# if not self.filteringColorPrint \
						# and gv.colorPrintFilterREs[0].match(text):# block starts
					# self.filteringColorPrint = True
				# elif self.filteringColorPrint \
						# and gv.colorPrintFilterREs[1].match(text):# block ends
					# self.filteringColorPrint = False
				return

			sameColorKey = self.printKey and self.printKey == colorKey
			if lastInBatch or not sameColorKey:
				self.printKey = colorKey
				key = cl.setColorKey(colorKey)
				if key is None: 
					# print suppressed
					return	
				tag = cl.setColorTag(key)
			else:						
				# avoid unnecessary calls to setColorKey/Tag
				key, tag = self.printKey, self.printTag
			sameColorTag = not self.printTag or self.printTag == tag

			self.printCount += 1
			if gv.screenLines and self.printCount > 5 * gv.screenLines:
				self.checkBufferSize()
				self.printCount = 0

			if not self.stateNormal:
				txt.config(state='normal')
				self.stateNormal = True

			maxWidth = None
			if colorKey == 'command' \
					and gv.localOptnVars['TruncateCmdEcho'].get():
				gv.bodyText.update_idletasks()
				maxWidth = gv.bodyText.winfo_width()

			text = text.rstrip(' \t\n\r') + con.NL
			posn = 0
			if emphasisRanges is None and maxWidth is None:
				bufferLen = len(self.printBuffer)
				# here's where voluminous log statements can cause a bottleneck
				if not lastInBatch and sameColorKey and sameColorTag:
					# buffer lines to reduce # of .insert calls
					self.printBuffer.append(text)	
				elif not lastInBatch and sameColorKey:
					# new tag, flush buffer and restart buffering
					if bufferLen:
						txt.insert('end', ''.join(self.printBuffer), tag)
						del self.printBuffer[:]
					self.printTag = tag
					self.printBuffer.append(text)
				elif bufferLen and (lastInBatch or not sameColorKey):
					# flush buffer completely
					if sameColorTag:
						self.printBuffer.append(text)
					if bufferLen:
						txt.insert('end', ''.join(self.printBuffer), tag)
						del self.printBuffer[:]
					if not sameColorTag:
						txt.insert('end', text, tag)
					self.printKey = self.printTag = None
				else:
					txt.insert('end', text, tag)
			elif maxWidth is None:		# not truncating output
				while len(emphasisRanges) > 1:	# ranges come in pairs
					estart = emphasisRanges.pop(0)
					elen = emphasisRanges.pop(0)
					if posn < estart: 	# text before emphasis
						txt.insert('end', text[posn:estart], tag)
					posn = estart + elen# emphasis text
					txt.insert('end', text[estart:posn], ('emphasis',tag))
					if len(emphasisRanges) < 2: break
					nextE = emphasisRanges[0]
					if posn < nextE: 	# text after emphases
						txt.insert('end', text[posn:nextE], tag)
						posn = nextE
				if posn < len(text): 	# text after all the emphases
					txt.insert('end', text[posn:], tag)
			else:
				self.addWords(text, tag, maxWidth, emphasisRanges)
		except Exception as exc:
			errmsg = 'Exception: {!r}'.format(exc)
			if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
			else:
				gv.debugLogger.error(errmsg)
		finally:
			if lastInBatch:
				txt.config(state='disabled')
				self.stateNormal = False
				txt.yview('end')
				txt.tag_raise('sel')

	@staticmethod
	def addWords(text, tag, maximumWidth, emphases=None):
		def nextEmphasis():
			if emphases is not None and len(emphases) > 1:	
				# ranges come in pairs
				start = emphases.pop(0)
				stop = start + emphases.pop(0)
			else:
				start = stop = maximumWidth
			return start, stop

		def measuredWidth(phrase):
			if hasEmphasis:
				mFont, mCache = efont, measuredEWords
			else:
				mFont, mCache = font, measuredWords
			if phrase not in mCache:
				mCache[phrase] = mFont.measure(phrase)
			return mCache[phrase]

		txt, font = gv.bodyText, gv.OoFonts['default']
		efont = gv.OoFonts['emphasis']
		measuredWords, measuredEWords = gv.measuredWords, gv.measuredEWords
		spaceLen, eSpaceLen = gv.spaceLen, gv.eSpaceLen
		words = text.split()
		hasEmphasis = False
		buffer, index, estop = [], 0, -1

		[estart, estop] = nextEmphasis()
		maxWidth, finished = maximumWidth, False
		for word in words:
			index = text.find(word, index)
			wordLen = len(word)
			wordEnd = index + wordLen
			if index > estop:
				[estart, estop] = nextEmphasis()
			hasEmphasis = index < estop and wordEnd > estart
			if hasEmphasis and (estart > index or estop <= wordEnd): 
				# word partially emphasized
				wordStart = index
				wordIdx = 0
				# save word parts until we know whole word will fit
				del buffer[:] 		
				while index < wordEnd:
					hasEmphasis = index >= estart
					wBreak = estop if hasEmphasis else estart
					output = word[ wordIdx:wBreak-wordStart ]
					width = measuredWidth(output)
					if wBreak >= wordEnd:	
						# detect last part, only then add spaceLen into calcs
						width += eSpaceLen if hasEmphasis else spaceLen
					if width > maxWidth:
						finished = True
						break
					buffer.append([output, ('emphasis',tag) \
											if hasEmphasis else (tag,)])
					wordIdx += len(output)
					index += len(output)
					maxWidth -= width
					if index >= estop:
						[estart, estop] = nextEmphasis()
				if finished: break	# word does not fit
				for chs, tags in buffer:# output word
					txt.insert('end', chs, tags)
				txt.insert('end', ' ', ('emphasis',tag) \
										if hasEmphasis else tag)
			else:					
				# output whole word
				width = measuredWidth(word) \
						+ (eSpaceLen if hasEmphasis else spaceLen)
				if width > maxWidth: break
				txt.insert('end', '{} '.format(word), ('emphasis',tag) \
										if hasEmphasis else tag)
				index += wordLen
				maxWidth -= width

		txt.insert('end', con.NL, tag)	# lose \n when tokenize
		return index, maxWidth

	def bodyClear(self):
		self.tried = 0
		gv.bodyText.popup.deleteAllText()
		gv.bodyText.popup.resetUndoStack()

	# noinspection PyUnusedLocal
	def cmdClear(self, event=None):
		if gv.CurrentOptions['Settings'].get('OldClearBehaviour'):
			self.bodyClear()
		else:
			ch.cmdSearchClear()
			gv.cmdLine.delete('1.0', 'end')
			gv.cmdLine.focus_set()

	# noinspection PyBroadException
	def setconnectPort(self):
		# incorporated from version 1.6, which introduced ServerAddress,
		# Port and EndPort but implementation is still pending

		# Set up the console's port using the Port setting
		# inside CFGFILE. All dynamic, private, or ephemeral ports 
		# 'should' be between 49152-65535.
		# However, the default port is 8563.
		global connectPort, connectEndPort

		settings = gv.CurrentOptions['Settings']
		connectPort = defaultOoliteConsolePort
		connectEndPort = connectPort
		consolePort = settings.get('Port', connectPort)
		consoleEndPort = settings.get('EndPort', connectEndPort)
		if consolePort is not None:
			try:
				consolePort = int(consolePort)
			except:
				pass
			if 49151 < consolePort < 65536:
				connectPort = consolePort
				if consoleEndPort is not None:
					try:
						consoleEndPort = int(consoleEndPort)
					except:
						pass
					if consolePort < consoleEndPort < 65536:
						connectEndPort = consoleEndPort
					else:
						msg = 'EndPort setting ({}) should be greater than ' \
							  'Port setting ({}),'.format(consoleEndPort, consolePort)
						self.colorPrint(msg, emphasisRanges=[0,7, 47,4])
						msg = 'and less than 65536.'
						self.colorPrint(msg, emphasisRanges=[14,5])
						msg = 'EndPort setting will be ignored.'
						self.colorPrint(msg, emphasisRanges=[0,7])
						connectEndPort = connectPort
			else:
				msg = 'Invalid Port setting specified.'
				self.colorPrint(msg, emphasisRanges=[8,4])
				msg = 'Valid Port setting should be in the range of 49152-65535.'
				self.colorPrint(msg, emphasisRanges=[6,4, 46,11])
				msg = 'Trying listening on default port ({}).'.format(connectPort)
				self.colorPrint(msg, emphasisRanges=[34,len(str(connectPort))])
				if consoleEndPort is not None:
					msg = 'EndPort setting will be ignored.'
					self.colorPrint(msg, emphasisRanges=[0,7])
		else:
			if connectEndPort is not None:
				msg = 'EndPort setting without Port setting will be ignored.'
				self.colorPrint(msg, emphasisRanges=[0,7, 24,4])

	# noinspection PyUnresolvedReferences
	@staticmethod
	def cmdHandlerActive():
		return hasattr(_consoleHandler.inputReceiver,'receiveUserInput') \
			and _consoleHandler.inputReceiver.Active

	# noinspection PyUnresolvedReferences
	@staticmethod
	def sendCmdToHandler(cmd):
		_consoleHandler.inputReceiver.receiveUserInput(cmd)

	# noinspection PyUnusedLocal
	def runCmd(self, event=None):
		au.closeAnyOpenFrames()
		cmd = gv.cmdLine.get('1.0', 'end').strip()
		if cmd.startswith('/quit'):
			self.exitCmd()
		else:
			if len(cmd) > 0:
				ch.addCmdToHistory(cmd)
			ch.cmdSearchClear()
			if self.cmdHandlerActive():
				self.tried = 0
				# move user commands through queue to avoid interrupting
				# replies for silent commands
				self.queueSilentCmd(cmd, 'USER_CMD', discard=False)
				gv.cmdLine.delete('1.0', 'end')
				if gv.CurrentOptions['Settings'].get('ResetCmdSizeOnRun',False):
					au.positionAppSash()
			else:
				if self.tried == 0:
					msg = '\n{}\n'.format(con.CONNECTMSG)
					self.colorPrint(msg, emphasisRanges=[18, 6])
					msg = 'You can only use the console after you\'re connected.'
					self.colorPrint(msg, emphasisRanges=[29, 5])
				elif self.tried == 1:
					self.colorPrint('\n * Please connect to Oolite first! * ',
									emphasisRanges=[28,6])
				self.tried +=1
		return 'break'

	@staticmethod
	def exitCmd():
		au.closeAnyOpenFrames()
		cfg.writeCfgFile()
		if gv.CurrentOptions['Settings'].get('SaveHistoryOnExit', True):
			ch.saveCmdHistory()
		pm.sessionCleanup(abort=True)
		gv.app.update() # flush any pending after_idle's
		tksupport.uninstall()
		reactor.stop()
		gv.root.destroy()
		gv.app = gv.root = None

## application functions ######################################################

def _initLogger():
	try:
		# set up logging to file
		nextVer = cfg.nextVersion(con.BASE_FNAME, con.LOG_EXT)
		if not nextVer:
			nextVer = con.BASE_FNAME + con.LOG_EXT
			errmsg = '_initLogger, file versioning failed, '
			errmsg += 'overwriting {!r}'.format(nextVer)
			gv.startUpInfo['error'].append(errmsg)
		fStr = '%(asctime)s %(levelname)-8s %(message)s '
		fStr += '(%(filename)s: %(funcName)s, line %(lineno)s)'
		logging.basicConfig(level=logging.WARNING, filename=nextVer, 
							filemode='w',format=fStr)
		if con.FROZEN or not sys.stdout.isatty():
			# handler for WARNING messages or higher to debug console
			handler = OoDebugConsoleHandler()
		else:
			# handler for WARNING messages or higher to sys.stderr
			handler = logging.StreamHandler()
		handler.setLevel(logging.WARNING)
		# set a format which is simpler for console use
		fStr = '%(name)-12s: %(levelname)-8s %(message)s'
		formatter = logging.Formatter(fStr)
		handler.setFormatter(formatter)
		logger = logging.getLogger('DebugConsole')
		# activate debug logger output
		logger.setLevel(logging.WARNING)      		
		# add the handler to the root logger
		logger.addHandler(handler)
		# 4 speed optimizations
		logger._srcfile = None						
		logger.logThreads = 0
		logger.logProcesses = 0	
		logger.logMultiprocessing = 0
		if not con.CAGSPC and (con.FROZEN or not sys.stdout.isatty()):
			# consider all prints as debug information
			logger.write = logger.debug				
			# this may be called when printing
			logger.flush = lambda: None				
			sys.stdout = logger
			sys.stderr = logger
		elif con.CAGSPC:
			logger.setLevel(logging.DEBUG)
		gv.debugLogger = logger
	except Exception as exc:
		errmsg = '_initLogger, failed to initiate logger\n    {!r}'.format(exc)
		gv.startUpInfo['error'].append(errmsg)

def _haltLogger():
	logging.shutdown()
	# delete empty log file
	if os.path.exists(con.LOGFILE) \
			and os.path.getsize(con.LOGFILE) == 0:
		os.remove(con.LOGFILE)

def _formatErrs(suffix=''):
	errs = ''
	for msg in gv.startUpInfo['setup']:
		errs += msg + con.NL + suffix
	for msg in gv.startUpInfo['error']:
		errs += msg + con.NL + suffix
	return errs

def reportStartupInfo():
	report = _formatErrs()
	if len(report):
		print(report)

def _showAbortMsg(title=None):
	if gv.app:
		pm.sessionCleanup(abort=True)
		gv.root.destroy()
		gv.app = gv.root = None
	msg = _formatErrs()
	if len(msg):
		default = con.DEFAULT_GEOMETRY
		if len(gv.CurrentOptions):
			geom = gv.CurrentOptions['Settings'].get('Geometry', default)
			geom = geom[geom.find('+'):]
		else:
			geom = '+{0}+{0}'.format(default[default.find('+'):])
		abort = wg.StartUpAbort(msg, title if title \
									 else 'Initialisation Error')
		abort.root.geometry(geom)
		abort.mainloop()

def _startApp():
	try:
		settings = gv.CurrentOptions['Settings']
		server = settings.get('ServerAddress')
		port = settings.get('Port') or connectPort
		msg = au.fmtServerAddress(server, port)
		au.setAppTitle(msg)
		msg = 'Listening on {} ...'.format(msg)
		gv.app.colorPrint(msg, emphasisRanges=[13, len(msg) - 13])
		msg = '\nUse Up and Down arrows to scroll through the command history.'
		gv.app.colorPrint(msg, emphasisRanges=[4,2, 11,4])
		msg = '(Tab to search back, Shift-Tab search forward).'
		gv.app.colorPrint(msg, emphasisRanges=[1,3, 21,9])
		gv.app.colorPrint('\nType /quit to quit.')
		gv.app.colorPrint('Waiting for connection...')
	except Exception as exc:
		errmsg = 'Exception: {!r}'.format(exc)
		if gv.debugLogger:
			gv.debugLogger.exception(errmsg)
		if con.CAGSPC:
			traceback.print_exc()
			print(errmsg)
			pdb.set_trace()

openPorts = []
def _saveOpenPort(obj):
	openPorts.append(obj)

def _reportPortError(reason):
	if reason:
		gv.startUpInfo['error'].append(reason)
	_showAbortMsg('Port Error')

def _stopOtherListeners(port):
	for openPort in openPorts[:]:
		if openPort.port != port:
			openPort.stopListening()
			openPorts.remove(openPort)

listenErrors = []
def _startListeners():
	# Set up console server protocol
	# factory = Factory()
	factory = OOClientAddressFactory()
	factory.delegateClass = SimpleConsoleDelegate
	factory.activeCount = 0
	factory.protocol = OoliteDebugConsoleProtocol
	portSpan = list(range(connectPort, connectEndPort + 1))
	# include deprecated defaultOoliteConsolePort for case where no port
	# is specified in either CFGFILE or debugConfig.plist
	if defaultOoliteConsolePort not in portSpan:
		portSpan.append(defaultOoliteConsolePort)
	serverAddr = gv.CurrentOptions['Settings'].get('ServerAddress')
	if serverAddr is None: # key present but value never set
		serverAddr = '127.0.0.1'
	listeningPorts = 0
	for port in portSpan:
		try:
			# listenPorts.append(reactor.listenTCP(port, factory))
			# add local network connections
			sStr = 'tcp:{}:interface={}'.format(port, serverAddr)
			# listener = serverFromString(reactor, sStr).listen(factory)
			# serverFromString returns an instance of
			#   twisted.internet.endpoints.TCP4ServerEndpoint
			server =  serverFromString(reactor, sStr)
			# listen returns a Deferred whose 'result' attr is an instance of
			#   twisted.internet.tcp.Port
			listener = server.listen(factory)

			if isinstance(listener.result, TwistedPort):
				# listener.addCallback(_saveOpenPort)
				listener.addCallbacks(_saveOpenPort, _reportPortError)
				listeningPorts += 1
			elif isinstance(listener.result, Failure):
				listenErrors.append(listener.result.value)

		except Exception as exc:
			errmsg = '_startListeners, {!r}'.format(exc)
			gv.startUpInfo['error'].append(errmsg)
			print(f'unexpected  {exc!r}')
			if con.CAGSPC:
				pdb.set_trace()

	if listeningPorts == 0:
		oops = '\n'.join(str(lE) for lE in listenErrors) \
				if listenErrors else ''
		oops += "\n\nNo available ports to start listening for Oolite connections."
		oops += "\nPlease, try again later."
		gv.startUpInfo['setup'].append(oops)
		_showAbortMsg()
		if con.CAGSPC:
			reportStartupInfo()
		return False
	elif len(listenErrors):
		gv.startUpInfo['setup'].extend('CannotListenError, IP address: {}, port: {}\n  {}'
									   .format(lE.interface, lE.port, lE.socketError)
									   for lE in listenErrors)
	return True

###
def runConsole():
	global _consoleHandler

	erred = False
	try:
		_initLogger()
		try:
			gv.app = AppWindow()
			# initConfig called early as setup relies on it
			cfg.initConfig()
			gv.initVars()			
			gv.app.setupApp()
			if not _startListeners():
				return True
			errors = _formatErrs(con.NL)
			if len(errors):
				gv.app.colorPrint(errors)
				gv.app.colorPrint(con.NL)

		except Exception as exc:
			errmsg = 'runConsole, Error setting up app: {!r}'.format(exc)
			gv.startUpInfo['setup'].append(errmsg)
			if con.CAGSPC:
				traceback.print_exc()
				print(errmsg)
				pdb.set_trace()
			raise


		# Set up command line I/O protocol
		# (required global for SimpleConsoleDelegate)
		_consoleHandler = OoliteDebugCLIProtocol()
		stdio.StandardIO(_consoleHandler)

		gv.root.attributes('-alpha', 1.0)
		gv.setupComplete = True
		gc.collect()

		# display any alias errors from CFGFILE
		for alias, obj in gv.aliases.items():
			check = cmt.checkJSsyntax(obj, silent=True)
			if check is not True: # returns tuple/error instead of False
				gv.app.colorPrint('alias {!r} encountered {}'.format(
										alias, check[0]))
		_startApp()

	except Exception as exc:
		erred = True
		msg, kind = cfg.parseErr(exc)
		errmsg = 'Exception: '
		if kind:
			errmsg += '  ({})\n  {}'.format(kind, msg)
		else:
			errmsg += '\n  ' + msg
		errmsg += '\n\n  ' + traceback.format_exc()
		gv.startUpInfo['setup'].append(errmsg)
		if gv.debugLogger:
			gv.debugLogger.exception(errmsg)
		_showAbortMsg()
		if con.CAGSPC:
			reportStartupInfo()
	else:
		# Install the Reactor support & start listening
		tksupport.install(gv.app)
		# Wait for user input.
		reactor.run()
	finally:
		return erred

def main():
	# noinspection PyUnusedLocal
	erred = False
	try:
		erred = runConsole()
	except Exception as exc:
		erred = True
		reportStartupInfo()
		errmsg = 'Exception: {!r}'.format(exc)
		if gv.debugLogger:
			gv.debugLogger.exception(errmsg)
		elif not con.FROZEN and sys.stdout.isatty():
			print(errmsg)
		if con.CAGSPC:
			traceback.print_exc()
			pdb.set_trace()
	finally:
		_haltLogger()
		sys.exit(1 if erred else 0)


if __name__ == "__main__":
	main()


