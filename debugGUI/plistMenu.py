# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, time
from collections import OrderedDict
import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
else:
	import tkinter as tk

import debugGUI.aliases as al
import debugGUI.appUtils as au
import debugGUI.colors as cl
import debugGUI.comments as cmt
import debugGUI.constants as con
import debugGUI.fontMenu as fm
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.widgets as wg

# upon opening a new connection, oolite sends a dictionary of its
# settings, regardless of whether or not the game has loaded/started.
# We process those, then start polling for the actual start before
# completing setup

_scriptPropsStr = None	# list of console.script's properties, 
						# to prevent collisions w/ aliases

def initConnectionVars():
	global _scriptPropsStr
	vName = mu.TkName('_scriptPropsStr')
	_scriptPropsStr = tk.StringVar(value='never set', name=vName)
	mu.addTraceTkVar(_scriptPropsStr, _loadScriptProps)

	vName = mu.TkName('sessionStartTime')
	gv.sessionStartTime = tk.StringVar(name=vName)
	mu.addTraceTkVar(gv.sessionStartTime, _sessionStarted)
	
	vName = mu.TkName('currentSessionTime')
	gv.currentSessionTime = tk.StringVar(name=vName)
	mu.addTraceTkVar(gv.currentSessionTime, _checkGameStatus)
	
	vName = mu.TkName('gameStarted')
	gv.gameStarted = tk.IntVar(name=vName)
	mu.addTraceTkVar(gv.gameStarted, _checkGameStatus)

	vName = mu.TkName('currStarSystem')
	gv.currStarSystem = tk.StringVar(name=vName)

###
def initClientSettings(settings):
	# create a pull down menu for Oolite options (see debugConfig.plist)
	# - menu will remain while the connection is up
	# - 'settings' is a dict of all debugger options sent from Oolite:
	#   flags, macros, colours & fonts (we have no use for the macros)
	# NB: 'font-face' & 'font-size' are the only font related ones in
	#     OoSettings; the rest (weight, slant & disabled) are local only
	disableClientSettings()
	# - this is not guaranteed to be called via connectionClosed
	#   (eg. terminate before disconnect), so we do it here, using the
	#   connectedToOolite flag to prevent looping
	gv.connectedToOolite = True
	if len(gv.scriptProps):		# not the 1st connection in this session
		gv.debugLogger.debug('connected {}'.format('=' * 70))
	OoMenu = wg.OoBarMenu(gv.menuFrame, label='Oolite plist',
							font=gv.OoFonts['default'],
							disabledFont=gv.OoFonts['disabled'],
							name=mu.TkName('ooliteMenu'),
							style='OoBarMenu.TMenubutton',
							postcommand=au.closeAnyOpenFrames)
	gv.ooliteMenu = OoMenu
	gv.debugConsoleMenus.append(gv.ooliteMenu)
	pairs = OrderedDict(sorted(settings.items(),
								key=lambda t: _sortSettings(t[0])))
	gv.ooliteColors.clear()
	colorsSep = 0
	for key, value in pairs.items():	# add menu items for each setting
		if key == 'default-macros':
			continue
		# # send back 'forced' so that values are saved in .GNUstepDefaults
		# gv.app.client.setConfigurationValue(key, value, forced=True)
## test that this does in fact happen when user changes plist item
		if key in ['font-face', 'font-size', 'console-host', 'console-port']:
			gv.OoSettings[key] = value
		elif isinstance(value, list):	# a color option
			if colorsSep == 0:			# add separator at start of colors
				colorsSep = 1			# only works because of _sortSettings
				OoMenu.add_separator()
			elif colorsSep == 1 and key.count('-') == 3:
				# add separator between general and event specific colors
				colorsSep = 2
				OoMenu.add_separator()
			OoMenu.add_command(label=key, stateChange=True,
					state='disabled' if gv.pollingSuspended else 'normal',
					command=lambda k=key: cl.pickMsgColor(k))
			gv.ooliteColors[key] = value
			gv.OoSettings[key] = gv.Appearance.codifyColor(value)
		else:							# a boolean option
			if key.lower().startswith('show-console-on'):
				# these 3 appear in the 'Debug' menu instead of this one
				#   to be consistent w/ MacOS debugger
				continue
			isInt = isinstance(value, int)
			isTrue = (isInt and value) or value.lower() in con.TRUE_STRS
			isFalse = (isInt and not value) or value.lower() in con.FALSE_STRS
			if isTrue or isFalse:
				tkValue = 1 if isTrue else 0
				# some are added when debug menu is created
				if key not in gv.plistTkvars:	
					gv.plistTkvars[key] = tk.IntVar(name=mu.TkName('oo_', key))
				gv.plistTkvars[key].set(tkValue)
				OoMenu.add_checkbutton(label=key, stateChange=True, 
						variable=gv.plistTkvars[key],
						state='disabled' if gv.pollingSuspended else 'normal',
						command=lambda k=key: \
							gv.app.setClientCheckButton(k, gv.plistTkvars[k]))
				gv.OoSettings[key] = bool(tkValue)
			else:
				errmsg = 'unsupported var {}: {}, type: {}'.format(
						key, value, type(value))
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.error(errmsg)
	# end for loop
	if len(gv.ooliteColors) > 0:
		# waiting 'lazy' to allow collection of any following 
		#   noteConfig wrt color
		au.afterLoop(gv.tkTiming['lazy'], 'repeatProcOoColors', 
						_repeatProcOoColors)
	gv.cmdLine.tag_raise('sel')
	gv.initStartTime = mu.timeCount()
	# gameStarted is Traced, .set upon fn exit will
	#   initiate _checkGameStatus loop
	gv.gameStarted.set(0)				

def _sortSettings(key):		# important for menu order and color calc
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

def disableClientSettings():			
	# disables debugMenu but destroys ooliteMenu as it is connection specific
	if not gv.connectedToOolite:
		# can be called more than once (oolite closed vs halted)
		return
	for obj in gv.aliases.values():
		obj.resetPoll()
	gv.connectedToOolite = False
	sessionCleanup()
	gv.debugLogger.debug('disconnected {}'.format('=' * 67))
	if gv.ooliteMenu:
		if gv.root:
			gv.ooliteMenu.removeOnesSelf()
		if gv.ooliteMenu in gv.debugConsoleMenus:
			gv.debugConsoleMenus.remove(gv.ooliteMenu)
		gv.ooliteMenu = None
		cl.menuColorExcl.pop('ooliteMenu', None)
	if gv.root:
		gv.root.title('{}: disconnected'.format(con.DEBUGGER_TITLE))
		au.afterLoop(gv.tkTiming['slow'], 'gridMenuButtons', 
						al.gridMenuButtons)
		gv.debugMenu.changeAllStates('disabled')

def sessionCleanup(abort=False):
	gv.sessionInitialized = 0
	gv.sessionStartTime.set('')
	del gv.requests[:]				# clear msg queues
	gv.replyPending = gv.replyPendingTimer = None
	for fn in list(gv.afterLoopIDs.keys()):
		# shut down any active .after cycles
		au.removeAfter(fn)
	gv.afterLoopIDs.clear()
	wg.ToolTip.cancelAnyAfters()
	al.clearPollQueues()
	if abort:
		return
	# re-initiate messaging for next session
	au.afterLoop(gv.tkTiming['fast'], 'sendSilentCmd', gv.app.sendSilentCmd)
	# flush pending messages and re-initiate messaging processing
	au.afterLoop(gv.tkTiming['fast' if len(gv.pendingMessages) else 'lazy'],
				 'processMessages', gv.app.processMessages)
	gv.gameStarted.set(0)				# var is Traced, .set upon fn exit

def _repeatProcOoColors():				
	# process 1 color per call to avoid packet loss from time-out
	au.removeAfter('repeatProcOoColors')
	if len(gv.ooliteColors) > 0:
		key, value = gv.ooliteColors.popitem()
		_procOneOoColor(key)
		au.afterLoop(gv.tkTiming['fast'], 'repeatProcOoColors', 
						_repeatProcOoColors)
	else:							# now ready to set colors
		if gv.appearance.usingOoColors():
			if 'font-face' in gv.OoSettings:
				# skipUpdate will prevent call to updateAppsFontChange
				# which will be done in setFontSize, if applicable
				fm.setFontFace(gv.OoSettings['font-face'], send=False, 
								skipUpdate='font-size' in gv.OoSettings)
			if 'font-size' in gv.OoSettings:
				fm.setFontSize(gv.OoSettings['font-size'], send=False)
			gv.appearance.updateApp()
		else:
			cl.setOoliteColorCmds()

def _procOneOoColor(key):
	# OoSettings[key] was set in initClientSettings (using Appearance.codifyColor)
	color = gv.OoSettings[key]
	cl.setMsgColor(key, color, skipUpdate=True)
	match = cl.parseOoColorKey(key)
	if match:
		keyClass, plane = match['key'], match['plane']
		if plane == 'foreground':
			missingKey = keyClass + '-background-color'
			if missingKey not in gv.OoSettings:
				# set missing background to general-background so Text tags
				# have complete pair of fg/bg
				default = gv.CurrentOptions['Colors']['general-background']
				missing = gv.OoSettings.get('general-background-color',
												default)
				missingBg = gv.Appearance.codifyColor(missing)
				# it's possible, when switching among different Oolite
				# installations in the same session that both fg & bg
				# could be similar colors
				if cl.sameColor(missingBg, color):
					contrast = gv.appearance.contrastColor(color)
					errmsg = 'missing ' + missingKey
					errmsg += ', missing background (' + missing
					errmsg += ') conflicts with current foreground ('
					errmsg += color + '), assigning contrast: ' + contrast
					gv.debugLogger.error(errmsg)
					missingBg = contrast
				gv.OoSettings[missingKey] = missingBg
				gv.bodyText.tag_config(keyClass, background=missingBg)
				# if keyClass == 'command':
				# 	gv.cmdLine.tag_config(keyClass, background=missingBg)
				# - cmdLine is strictly a local color
		elif plane == 'background':
			missingKey = keyClass + '-foreground-color'
			if missingKey not in gv.OoSettings:
				# set missing foreground to general-foreground so Text tags
				# have complete pair of fg/bg
				default = gv.CurrentOptions['Colors']['general-foreground']
				missingFg = gv.OoSettings.get('general-foreground-color', 
												default)
				missingFg = gv.Appearance.codifyColor(missingFg)
				gv.OoSettings[missingKey] = missingFg
				gv.bodyText.tag_config(keyClass, foreground=missingFg)
				# if keyClass == 'command':
				# 	gv.cmdLine.tag_config(keyClass, foreground=missingFg)
				# - cmdLine is strictly a local color

def _repeatCheckGameStatus():			
	# between game loads, all pending queries are flushed
	# ie. cannot rely on Oolite to kickstart initialization
	au.removeAfter('repeatCheckGameStatus')
	if gv.connectedToOolite and gv.gameStarted.get() == 0:
		# queue repeated calls in case Oolite doesn't respond
		# - cancelled in _checkGameStatus if queued cmd succeeds
		# (we cannot know when Oolite will ignore us during startup/game load)
		# au.afterLoop(gv.tkTiming['lazy'], 'gameStarted', gv.app.queueSilentCmd,
		# 						_GAMESTATUSCMD, 'gameStarted', gv.gameStarted)
		au.afterLoop(gv.tkTiming['lazy'], '_pollGameStarted', _pollGameStarted)
		au.afterLoop(gv.tkTiming['slow'], 'repeatCheckGameStatus',
								_repeatCheckGameStatus)

# connection has been established, we wait for player's ship status to
# change from STATUS_START_GAME before completing setup
# - alt. tests: ps.equipment.length == 0,  
# 				Object.keys(worldScripts).length == 0

# handler for Tk var trace: gameStarted AND currentSessionTime
# - gameStarted regularly polled (see pollOolite)
# noinspection PyUnusedLocal
def _checkGameStatus(*args):
	# au.removeAfter('gameStarted')
	au.removeAfter('_pollGameStarted')
	au.removeAfter('repeatCheckGameStatus')
	if gv.connectedToOolite:
		gameStarted = gv.gameStarted.get()
		if gameStarted == 0:				
			# keep checking until game is load/started
			_repeatCheckGameStatus()
		elif gv.sessionInitialized == 0:	
			# initial value; set by sessionCleanup
			_initDebugMenu()
		# elif gv.sessionInitialized == 1:		
			# _initDebugMenu, calls _queryScriptProps()
		# elif gv.sessionInitialized == 2:		
			# _queryScriptProps; var trace (_scriptPropsStr) -> _loadScriptProps()
		# elif gv.sessionInitialized == 3:		
			# querySessionStart; var trace (sessionStartTime) -> _sessionStarted()
		elif gv.sessionInitialized == 4:	
			# _sessionStarted; initialization complete
			# re-init if session has changed
			if gv.currentSessionTime.get() == 'undefined':	
				# current session terminated
				print('_checkGameStatus, calling sessionCleanup')
				sessionCleanup()
				gv.currentSessionTime.set('')

## startup step 1
def _initDebugMenu():
	gv.sessionInitialized = 1		# initialization is underway
	_queryScriptProps()
	au.queryTimeAcceleration()
	_pollLogMsgClasses()
	_pollDebugFlags()
	_pollDisplayFPS()
	_pollDetailLevel()
	# gv.app.queueSilentCmd('oolite.gameSettings.wireframeGraphics', 
	# 						'wireframe', gv.debugOptions['wireframe'])
	# - setting is read-only, must use in game options menu
	#   => can set value but ignored by game
	gv.debugMenu.changeAllStates('normal')

_msgClassCounter = 0
def _pollLogMsgClasses():				# check if log msg classes have changed
	global _msgClassCounter
	
	# logMessageClasses has 9 items to query; done in batches of 3
	debug = gv.debugOptions
	# query 1 in 3 on each call
	count = _msgClassCounter % 3
	for lmc, logProp in con.logMessageClasses.items():
		if count % 3 == 0:
			cmd = 'console.displayMessagesInClass("{}")'.format(logProp)
			gv.app.queueSilentCmd(cmd, lmc, debug['logMsgCls'].get(lmc, True))
			# - if .get default is used, error logged in processSilentCmd
		count += 1
	_msgClassCounter += 1

def _pollDebugFlags():					# check if debug flags have changed
	gv.app.queueSilentCmd('console.debugFlags', 'pollDebugFlags',
							gv.debugOptions['debugFlags']['allFlags'])

def _pollDisplayFPS():					# check if player toggled FPS display
	gv.app.queueSilentCmd('console.displayFPS', 'showFPS', 
							gv.debugOptions['showFPS'])

def _pollDetailLevel():					# check if player changed detail level
	gv.app.queueSilentCmd('console.detailLevel', 'detailLevel', 
							gv.detailLevelVar)

def _pollStarSystem():					# check if system has changed
	gv.app.queueSilentCmd('system', 'currStarSystem', gv.currStarSystem)

def _pollGameStarted():					# check if game status has changed
	gv.app.queueSilentCmd(_GAMESTATUSCMD, 'gameStarted', gv.gameStarted)

_GAMESTATUSCMD = 'player.ship.status !== "STATUS_START_GAME"'
_SIGNATURECMD = 'console.script["{}"]'.format(con.SESSION_SIGNATURE)

def _pollSessionSign():					# fetch tag to detect game restart
	gv.app.queueSilentCmd(_SIGNATURECMD, 'signScript', gv.currentSessionTime)

## startup step 2

_QUERYPROPSCMD = '(function() { return Object.getOwnPropertyNames(console.script);} )()'
# see mkCmdIIFE
def _queryScriptProps():
	# mk list of console.script properties (for alias register)
	gv.timedOutCmds.pop('gameStarted', None)
	del gv.scriptProps[:]
	gv.sessionInitialized = 2
	gv.app.queueSilentCmd(_QUERYPROPSCMD, 'scriptProps', _scriptPropsStr)
	au.afterLoop(gv.tkTiming['slow'], 'waitForScriptProps', 
								_waitForScriptProps)

def _waitForScriptProps():		
	# between game loads, all pending queries are flushed
	# ie. cannot rely on Oolite to continue initialization
	au.removeAfter('waitForScriptProps')
	if len(gv.scriptProps) == 0:
		# queue repeated calls until Oolite responds
		# - cancelled in _loadScriptProps when queued cmd succeeds
		au.afterLoop(gv.tkTiming['slow'], 'waitForScriptProps', 
								_waitForScriptProps)

# handler for Tk var trace: _scriptPropsStr
# noinspection PyUnusedLocal
def _loadScriptProps(*args):
	# create list of console.script's properties to avoid collision w/ aliases
	au.removeAfter('waitForScriptProps')
	# noinspection PyUnresolvedReferences
	propStr = _scriptPropsStr.get()
	if len(propStr) > 0:
		propStr = propStr.split(',')
		# limit scriptProps to those in oolite-debug-console.js
		# aliases from previous sessions may end up orphaned otherwise
		# ie. cannot register/delete aliases present when debug launches
		numProps = len(propStr)
		lastProp = propStr.index('evaluate')
		lastIndex = lastProp + 1 if lastProp < numProps else numProps
		gv.scriptProps.extend(propStr[:lastIndex])
		if numProps:
			# check for errors & parse prior to polling
			al.checkLoadedAliases()	
			# check for orphaned IIFE_PROPERTY_TAG props
			for prop in gv.scriptProps:	
				if prop.startswith(con.IIFE_PROPERTY_TAG):
					alias = prop.replace(con.IIFE_PROPERTY_TAG, '')
					if alias in gv.aliases \
							and gv.aliases[alias].iife is None:
						gv.scriptProps.remove(prop)
						gv.removeIIFEprop(alias)
			_querySessionStart()
		else:
			msg = '_loadScriptProps, calling disableClientSettings, '
			msg += 'as numProps = {}'.format(numProps)
			print(msg)
			disableClientSettings()
## vs sessionCleanup? can we restart session init by querying OoSettings dict NOT its constituents
			status = '* * failed to obtain property names, '
			status += 'resetting sessionInitialized'
			gv.debugLogger.debug(status)
##

## startup step 3
def _querySessionStart():
	gv.sessionInitialized = 3
	cmd = 'console.script["{}"] = "{}"'.format(con.SESSION_SIGNATURE, 
								time.strftime('%d %b %Y, %H:%M:%S'))
	# sign script to be able to detect game restart
	# - polling is started when cmd completes (see _sessionStarted)
	gv.app.queueSilentCmd(cmd, 'signScript', gv.sessionStartTime)
	au.afterLoop(gv.tkTiming['slow'], 'waitForSessionStart', 
								_waitForSessionStart)

def _waitForSessionStart():		
	# between game loads, all pending queries are flushed
	# ie. cannot rely on Oolite to continue initialization
	au.removeAfter('waitForSessionStart')
	if gv.sessionInitialized != 4:
		# queue repeated calls until Oolite responds
		# - cancelled in _sessionStarted if queued cmd succeeds
		au.afterLoop(gv.tkTiming['slow'], 'waitForSessionStart', 
								_waitForSessionStart)

## startup step 4
# handler for Tk var trace: sessionStartTime
# - sessionStartTime is cleared in sessionCleanup, set in _loadScriptProps
# - restoreMsgTraffic queries signature via currentSessionTime
# noinspection PyUnusedLocal
def _sessionStarted(*args):
	au.removeAfter('waitForSessionStart')
	startTime = gv.sessionStartTime.get()
	sessionTime = gv.currentSessionTime.get()
	if len(startTime):					# session started
		# must check as TkVar is Traced; call before sessionInitialized = 4
		if startTime != sessionTime:	
			gv.currentSessionTime.set(startTime)
			currTime = mu.timeCount()
			msg = 'initialization took {:.2f}s ({:.2f}s after startup)'.format(
					currTime - gv.initStartTime, currTime)
			if con.CAGSPC:
				print(msg)
			else:
				gv.debugLogger.debug(msg)
		pollOolite(initial=True)
		gv.sessionInitialized = 4		# initialization is complete
	elif sessionTime == 'undefined':	# session terminated or new game loaded
		au.removeAfter('pollOolite')
		msg = '_sessionStarted, sessionTime == undefined, '
		msg += 'pendingMessages: {}'.format(len(gv.pendingMessages))
		print(msg)

## startup complete, game polling begins
_pollCounter = 0				# serial counter for alternating primary stats
_pollingTime = 500				# ms between calls
_meanPollTime = [500]			# running average for quick recovery after a user
								# delay (eg. opened menu)

def pollOolite(initial=False):
	# monitor for restart, system change, etc; update alias values
	global _pollCounter, _pollingTime
	
	au.removeAfter('pollOolite')
	au.afterLoop(_pollingTime, 'pollOolite', pollOolite)

	# only poll when idle
	if gv.gameStarted.get() != 1 or gv.replyPending is not None \
			or gv.pollingSuspended or len(gv.pendingMessages) != 0:
		return
		
	# on each call, 1 of 3 primary stats is polled: 
	#   currentSessionTime, system, gameStarted
	# also, alias polling cycles; they are suspended while there is 
	# any other traffic
	_pollCounter += 1
	# adjust speed of polling based of # request pending
	# to interval 200 ms - 1000 ms
	if _pollCounter % 5 == 0:			# evaluate every 5 calls
		mean = sum(_meanPollTime) / len(_meanPollTime)
		# adjust by 1/2 diff from mean or 50, whichever is larger
		adjust = max(50, int(abs(mean - _pollingTime) / 2))
		if len(gv.requests) == 0:		# speed up
			_pollingTime = max(200, _pollingTime - adjust)
		else:							# slow down
			_pollingTime = min(1000, _pollingTime + adjust)
		# running average of last 5 adjustments
		_meanPollTime.append(_pollingTime)
		if len(_meanPollTime) > 5:
			_meanPollTime.pop(0)

	# _pollingTime is between 0.2 - 1.0 sec, so each case is 
	#   polled every 0.8 - 4 sec
	# 3 primary stats are interleaved with user alterable states
	gamePoll = _pollCounter % 4
	if gamePoll == 0:		
		_pollSessionSign()
		_pollDisplayFPS()
		au.queryTimeAcceleration()
	elif gamePoll == 1:	
		_pollStarSystem()
		_pollDebugFlags()
	elif gamePoll == 2:				# check if game status has changed
		_pollGameStarted()
		_pollDetailLevel()
	else:
		_pollLogMsgClasses()		# sends 3 of 9 total queries each call
		# ie. takes 3 calls (2.4 - 12 sec) to query all msg classes
		# - not a timing issue, as user changes are immediate,
		#   this just ensures we're synchronized with Oolite

	# alias polling uses silent msg scheme but not its time-out mechanism
	# - they're cycled constantly, in small batches
	if initial:					
		# do nothing else this cycle to let pending commands finish
		al.resetPolling()
	else:
		pending = [(k, v) for k, v in gv.aliases.items() if v.pollTime > 0]
		if len(pending) == 0:	# aliases are polled in batches
			al.pollAliases(con.ALIAS_POLL_BATCH_SIZE)
		else:					# awaiting last batch finish
			currTime = mu.timeCount()
			for alias, obj in pending:
				if currTime - obj.pollTime > con.CMD_TIMEOUT:
					# abandon poll; it may yet return but won't hold up others
					obj.pollTime = -1

suspendMenu = None
def suspendMsgTraffic():
	global suspendMenu
	
	gv.debugMenu.changeAllStates('disabled')
	gv.ooliteMenu.changeAllStates('disabled')
	suspendMenu = wg.OoBarMenu(gv.menubar, label='Suspended',
								font=gv.OoFonts['default'],
								name=mu.TkName('suspendMenu'),
								style='OoBarMenu.TMenubutton',
								postcommand=au.closeAnyOpenFrames)
	gv.debugConsoleMenus.append(suspendMenu)
	suspendMenu.add_command(label='Message traffic with Oolite')
	suspendMenu.add_command(label='is suspended while in the')
	suspendMenu.add_command(label='middle of a user command.')
	suspendMenu.add_command(label='Finish the command, enter a')
	suspendMenu.add_command(label='blank command or use the')
	suspendMenu.add_command(label='button below to resume traffic.')
	suspendMenu.add_separator()
	suspendMenu.add_command(label='Force Resumption', 
							command=restoreMsgTraffic)
	au.afterLoop(gv.tkTiming['slow'], 'gridMenuButtons', 
				al.gridMenuButtons)

def restoreMsgTraffic():
	global suspendMenu

	if suspendMenu is not None:
		# were in a multi-line user cmd
		gv.debugMenu.changeAllStates('normal')
		gv.ooliteMenu.changeAllStates('normal')
		# noinspection PyUnresolvedReferences
		suspendMenu.removeOnesSelf()
		if suspendMenu in gv.debugConsoleMenus:
			gv.debugConsoleMenus.remove(suspendMenu)
		gv.app.sendCmdToHandler('')	# flush any unfinished command
		au.afterLoop(gv.tkTiming['slow'], 'gridMenuButtons', 
					al.gridMenuButtons)
		suspendMenu = None
	gv.pollingSuspended = False
	cmd = 'console.script["{}"]'.format(con.SESSION_SIGNATURE)
	# fetch tag to detect game restart
	gv.app.queueSilentCmd(cmd, 'signScript', gv.currentSessionTime)

