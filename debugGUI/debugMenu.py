# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys
from collections import OrderedDict
import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
else:
	import tkinter as tk

import debugGUI.appUtils as au
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.plistMenu as pm
import debugGUI.stringUtils as su
import debugGUI.widgets as wg

# strings for menu labels
_debugMenuStrs ={
	'showLog':			'Show Log',
	'logMsgCls':		'Log Message Classes',
	'insLog':			'Insert Log Marker',
	'debugFlags':		'Debug Flags',
	'wireframe':		'Wireframe Graphics',
	'showFPS':			'Display FPS',
	'timeAccelSlow':	'Time Acceleration slow',
	'timeAccelFast':	'Time Acceleration fast',
	# next three come from _showConsoleForDebug
	'show-on-log':	'Show Console for Log Messages',
	'show-on-warning':'Show Console for Warnings',
	'show-on-error':	'Show Console for Errors',
	'conProps':			'Console Properties',
	'conCmds':			'Console Commands',
	'dumpEnt':			'Dump Entity List',
	'dumpPlayer':		'Dump Player State',
	'dumpTarget':		'Dump Target State',
}

_dbgFlagsStrs = {'on': 'Full debug on', 'off': 'All debug flags off'}

_debugFlags = OrderedDict((
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

_showConsoleForDebug = {
	'Show Console for Log Messages': 'show-console-on-log',
	'Show Console for Warnings': 'show-console-on-warning',
	'Show Console for Errors': 'show-console-on-error',
}

_detailLevels = OrderedDict((
	('Minimum', 	'DETAIL_LEVEL_MINIMUM'),
	('Normal', 		'DETAIL_LEVEL_NORMAL'),
	('Shaders', 	'DETAIL_LEVEL_SHADERS'),
	('Extras', 		'DETAIL_LEVEL_EXTRAS'),
))

_consoleOptions = OrderedDict((
	# properties queryable from cmdLine but added for convenience
	('Detail level', 			_detailLevels),
	('Max. detail level', 		'maximumDetailLevel'),
	# already in debugOptions
	# ('FPS display', 			['status', 'toggle']),	
	('pedanticMode', 			['status', 'toggle']),
	('ignoreDroppedPackets',	['status', 'toggle']),
	('Platform details', 	   ['platformDescription',
								'glVendorString',
								'glRendererString',
								'glFixedFunctionTextureUnitCount',
								'glFragmentShaderTextureUnitCount',]
							)
))

_consoleFunctions = OrderedDict((
	# 0-arg functions available from cmdLine but added for convenience
	('clear console', 'console.clearConsole()'),
	('script stack', 'log(console.scriptStack())'),
	('write JS memory stats', 'console.writeJSMemoryStats()'),
	('garbage collect', 'log("collecting garbage: " + console.garbageCollect())'),
	# add button to execute fns in debugMenu.py
	# 2nd string is button text:tkvar name:executed fn:cleanup fn
	# - tkvar name is assumed to end in 'Var', as its Tk name is [:-3]
	('<insert local fn>', 
	  'dump memory stats, log only:filterMemStatsVar:dumpMemStatsLogOnly:memStatsDumped'),
	('', ''),		 				# adds separator
	# ('use at your own risk!', ''),
	('write memory stats!', 'console.writeMemoryStats()'),
))


def createDebugMenus():					# create an Debug pull down menu
	font, disabled = gv.OoFonts['default'], gv.OoFonts['disabled']
	debugMenu = wg.OoBarMenu(gv.menuFrame, label='Debug',
								font=font, disabledFont=disabled,
								name=mu.TkName('debugMenu'),
								style='OoBarMenu.TMenubutton',
								postcommand=au.closeAnyOpenFrames)
	gv.debugMenu = debugMenu
	gv.debugConsoleMenus.append(debugMenu)

	# showLog, a local option, is here for consistency w/ Mac version
	gv.debugOptions['showLog'] = tk.IntVar(value=1, 
								name=mu.TkName('dbgMenu', 'showLog'))
	debugMenu.add_checkbutton(label=_debugMenuStrs['showLog'], 
								variable=gv.debugOptions['showLog'])

	# Log Message Classes submenu
	logMsgMenu = tk.Menu(debugMenu, tearoff=0, font=font, 
								name=mu.TkName('logMsgMenu'))
	for cls in con.logMessageClasses.keys():
		lmcName = mu.TkName('dbgMenu', 'logMsg', cls.replace(' ', '_'))
		gv.debugOptions['logMsgCls'][cls] = tk.IntVar(name=lmcName)
		tkVar = gv.debugOptions['logMsgCls'].get(cls)
		logMsgMenu.add_checkbutton(label=cls, variable=tkVar,
					command=lambda tkv=tkVar, s=cls: _setLogMsgCls(tkv, s))
	debugMenu.add_cascade(label=_debugMenuStrs['logMsgCls'],
								menu=logMsgMenu,
								stateChange=True, state='disabled',
								**gv.CASCADE_KWS)

	# Insert Log Marker cmd
	debugMenu.add_command(label=_debugMenuStrs['insLog'],
								command=_writeLogMarker,
								stateChange=True, state='disabled')

	# Debug Flags submenu
	dbgFlagsMenu = tk.Menu(debugMenu, tearoff=0, font=font, 
								name=mu.TkName('dbgFlagsMenu'))
	# var for all flags as returned from Oolite
	vName = mu.TkName('dbgMenu', 'debugFlagsQuery')
	tkVar = gv.debugOptions['debugFlags']['allFlags'] = tk.IntVar(name=vName)
	dbgFlagsMenu.add_command(label=_dbgFlagsStrs['on'],
								command=lambda: _setAllDebugFlags(setOn=True))
	dbgFlagsMenu.add_command(label=_dbgFlagsStrs['off'],
								command=lambda: _setAllDebugFlags(setOn=False))
	dbgFlagsMenu.add_separator()
	# debugFlags are polled, so no validation is needed
	for flag in _debugFlags.keys():
		vName = mu.TkName('dbgMenu', 'dbgFlags', flag)
		gv.debugOptions['debugFlags'][flag] = tk.IntVar(name=vName)
		tkVar = gv.debugOptions['debugFlags'].get(flag)
		dbgFlagsMenu.add_checkbutton(label=flag, variable=tkVar,
						command=lambda f=flag: _setDebugFlag(f))
	debugMenu.add_cascade(label=_debugMenuStrs['debugFlags'], 
								menu=dbgFlagsMenu,
								stateChange=True, state='disabled', 
								**gv.CASCADE_KWS)

	# Wireframe Graphics ==> awaiting change in core
	vName = mu.TkName('dbgMenu', 'wireframe')
	gv.debugOptions['wireframe'] = tk.IntVar(name=vName)
	debugMenu.add_checkbutton(label=_debugMenuStrs['wireframe'], 
								state='normal',# 'disabled',
								variable=gv.debugOptions['wireframe'], 
								command=_setWireFrame)

	# Display FPS cmd
	vName = mu.TkName('dbgMenu', 'showFPS')
	gv.debugOptions['showFPS'] = tk.IntVar(name=vName)
	debugMenu.add_checkbutton(label=_debugMenuStrs['showFPS'], 
								variable=gv.debugOptions['showFPS'],
								stateChange=True, state='disabled', 
								command=_setShowFPS)

	# Time Acceleration slow submenu
	timeAccelSlowMenu = tk.Menu(debugMenu, tearoff=0, font=font,
								name=mu.TkName('dbgtimeAccelSlowMenu'))
	vName = mu.TkName('dbgMenu', 'timeAccelQuery')
	# used only for queries
	gv.debugOptions['timeAccel'] = tk.StringVar(name=vName) 
	mu.addTraceTkVar(gv.debugOptions['timeAccel'], _checkTimeAccel)
	vName = mu.TkName('dbgMenu', 'timeAccelSlow')
	gv.debugOptions['timeAccelSlow'] = tk.StringVar(value='1', name=vName)
	for factor in range(16):
		value = _sixteenths(factor)
		timeAccelSlowMenu.add_radiobutton(label=value,
								variable=gv.debugOptions['timeAccelSlow'], 
								font=font, value=value, 
						command=lambda f=factor: _setSlowTimeAcceleration(f))
	debugMenu.add_cascade(label=_debugMenuStrs['timeAccelSlow'],
								menu=timeAccelSlowMenu,
								stateChange=True, state='disabled',
								**gv.CASCADE_KWS)

	# Time Acceleration fast submenu
	vName = mu.TkName('dbgMenu', 'timeAccelFast')
	gv.debugOptions['timeAccelFast'] = tk.IntVar(value=1, name=vName)
	timeAccelFastMenu = tk.Menu(debugMenu, tearoff=0, font=font,
								name=mu.TkName('dbgtimeAccelFastMenu'))
	for factor in range(1, 17):
		timeAccelFastMenu.add_radiobutton(label=str(factor),
								variable=gv.debugOptions['timeAccelFast'], 
								font=font, value=str(factor), 
						command=lambda f=factor: _setFastTimeAcceleration(f))
	debugMenu.add_cascade(label=_debugMenuStrs['timeAccelFast'],
								menu=timeAccelFastMenu,
								stateChange=True, state='disabled',
								**gv.CASCADE_KWS)

	# Show Console for ... commands
	debugMenu.add_separator()
	for show, key in _showConsoleForDebug.items():
		gv.plistTkvars[key] = tk.IntVar(name=mu.TkName('dbgMenu', key))
		# these options are mirrored in Settings menu 
		# - here for consistency w/ Mac version
		debugMenu.add_checkbutton(label=show, variable=gv.plistTkvars[key],
								stateChange=True, state='disabled',
				command=lambda k=key: _setShowConsoleOptn(k, gv.plistTkvars[k]))

	silentCmd = gv.app.queueSilentCmd	# for shortening lambda's below

	# Console Properties submenu
	consolePropMenu = tk.Menu(debugMenu, tearoff=0, font=font,
								name=mu.TkName('consolePropMenu'))
	for key, value in _consoleOptions.items():
		if key == 'Detail level':
			vName = mu.TkName('dbgMenu', 'detailLevel')
			gv.detailLevelVar = tk.StringVar(name=vName)
			subMenu = tk.Menu(consolePropMenu, tearoff=0, 
								font=gv.OoFonts['default'],
								name=mu.TkName(key, 'submenu'))
			for descr, level in value.items():
				cmd = 'console.detailLevel = "{}"; '.format(level)
				cmd += 'log("console.detailLevel: " + console.detailLevel)'
				label = 'setDetailLevel{}'.format(level)
				subMenu.add_radiobutton(label=descr, value=level,
								variable=gv.detailLevelVar,
								command=lambda x=cmd, y=label: silentCmd(x, y))
			consolePropMenu.add_cascade(label=key,
								menu=subMenu, **gv.CASCADE_KWS)
		elif isinstance(value, list):
			if value == ['status', 'toggle']:
				subMenu = tk.Menu(consolePropMenu, tearoff=0, 
								font=gv.OoFonts['default'],
								name=mu.TkName(key, 'submenu'))
				status = 'log("{}: " + console.{})'.format(key, key)
				label = 'status{}'.format(key.capitalize())
				subMenu.add_command(label='status',
							command=lambda x=status, y=label: silentCmd(x, y))
				toggle = 'console.{0} = !console.{0}; '.format(key)
				toggle += status
				label = 'toggle{}'.format(key.capitalize())
				subMenu.add_command(label='toggle',
							command=lambda x=toggle, y=label: silentCmd(x, y))
				consolePropMenu.add_cascade(label=key, 
								menu=subMenu, **gv.CASCADE_KWS)
			else:
				consolePropMenu.add_separator()
				label = key.replace(' ', '')
				# noinspection PyDefaultArgument
				consolePropMenu.add_command(label='All {}'.format(key),
					command=lambda x=value, y=label: _queuePropQueryList(x, y))
				subMenu = tk.Menu(consolePropMenu, tearoff=0, 
								font=gv.OoFonts['default'],
								name=mu.TkName(key, 'submenu'))
				for spec in value:
					cmd = 'log("{} = " + console.{})'.format(spec, spec)
					label = 'query{}'.format(spec.capitalize())
					subMenu.add_command(label=spec,
								command=lambda x=cmd, y=label: silentCmd(x, y))
				consolePropMenu.add_cascade(label=key, 
								menu=subMenu, **gv.CASCADE_KWS)
		else:
			cmd = 'log("{}: " + console.{})'.format(value, value)
			label = 'query{}'.format(value.capitalize())
			consolePropMenu.add_command(label=key,
								command=lambda x=cmd, y=label: silentCmd(x, y))
	debugMenu.add_cascade(label=_debugMenuStrs['conProps'], 
							menu=consolePropMenu,
							stateChange=True, state='disabled', 
							**gv.CASCADE_KWS)

	# Console Commands submenu
	consoleCmdMenu = tk.Menu(debugMenu, tearoff=0, font=font,
								name=mu.TkName('consoleCmdMenu'))
	for key, value in _consoleFunctions.items():
		if len(key) == 0 and len(value) == 0:# ('', '') in consoleFunctions
			consoleCmdMenu.add_separator()
		elif len(value) == 0:			# '' for value => print message
			consoleCmdMenu.add_command(label=key, command=None)
		elif key == '<insert local fn>':		
			# template for adding function calls to this file
			menuLabel, tkvarName, localFnName, cleanupFnName = value.split(':')
			# internal flag for when cmd is complete
			setattr(gv, tkvarName, tk.IntVar(name=mu.TkName(tkvarName[:-3])))
			mu.addTraceTkVar(getattr(gv, tkvarName), 
								globals().get(cleanupFnName))
			consoleCmdMenu.add_command(label=menuLabel,
								command=globals().get(localFnName))
		else:							# key is button label, value is executed
			cmd = lambda x=value, y=key: silentCmd(x,
								''.join(ch for ch in y if ch not in ' -_;:'))
			consoleCmdMenu.add_command(label=key, command=cmd)
	debugMenu.add_cascade(label=_debugMenuStrs['conCmds'], 
								menu=consoleCmdMenu,
								stateChange=True, state='disabled', 
								**gv.CASCADE_KWS)

	# Dump ... commands
	debugMenu.add_separator()
	gv.entityDumpVar = tk.IntVar(name=mu.TkName('entityDumpVar')) 
	mu.addTraceTkVar(gv.entityDumpVar, _entityListDumped)
	debugMenu.add_command(label=_debugMenuStrs['dumpEnt'],
								stateChange=True, state='disabled',
								command=_dumpEntityList)
								
	debugMenu.add_command(label=_debugMenuStrs['dumpPlayer'],
								stateChange=True, state='disabled',
								command=_dumpPlayerState)
	
	vName = mu.TkName('dbgMenu', 'playerHasTarget')
	gv.playerHasTarget = tk.IntVar(name=vName)
	mu.addTraceTkVar(gv.playerHasTarget, _dumpPlayersTarget)
	debugMenu.add_command(label=_debugMenuStrs['dumpTarget'],
								stateChange=True, state='disabled',
								command=_checkPlayersTarget)
	debugMenu.add_separator()
	debugMenu.add_command(label='Exit', command=gv.app.exitCmd)

def _setLogMsgCls(tkVar, key):
	value = tkVar.get()
	logProp = con.logMessageClasses.get(key)
	if logProp:
		cmd = 'console.setDisplayMessagesInClass("{}", {})'.format(
								logProp, 'true' if value else 'false')
		gv.app.queueSilentCmd(cmd, 'set{}'.format(key))
		# verify change
		cmd = 'console.displayMessagesInClass("{}")'.format(logProp)
		gv.app.queueSilentCmd(cmd, key, tkVar)

def _writeLogMarker():
	gv.app.queueSilentCmd('console.writeLogMarker()', 'logMarker')

def _setAllDebugFlags(setOn=False):
	# the individual flag Checkbutton's are updated when the updated
	# 'allFlags' value is returned by the cmd (see setDebugOption)
	allDebugFlags = 0
	if setOn:
		allDebugFlags = sum(flag for flag in _debugFlags.values())
	cmd = 'console.debugFlags = {}'.format(allDebugFlags)
	gv.app.queueSilentCmd(cmd, 'debugFlags', 
							gv.debugOptions['debugFlags']['allFlags'])
				
def _setDebugFlag(flag):
	# each flag has its own Tk var, gv.debugOptions['debugFlags'][flag]
	# which reflects the Checkbutton state
	# Oolite's value, which is returned by the cmd, is stored separately
	# in gv.debugOptions['debugFlags']['allFlags']
	# - when set, all the individual flag Checkbutton's are updated
	#  (see setDebugOption)
	cmd = 'console.debugFlags ^= {}'.format(str(_debugFlags[flag]))
	gv.app.queueSilentCmd(cmd, 'debugFlags',
			gv.debugOptions['debugFlags']['allFlags'])

def _setWireFrame():
	msg = '"wireframe" option is unsupported at present.\n'
	msg += '(it requires a fix in oolite)\n'
	msg += 'Post a message in the forum if you\'d use this option.'
	wg.OoInfoBox(gv.root, msg, font=gv.OoFonts['default'], destruct=7)
	tkVar = gv.debugOptions['wireframe']
	tkVar.set(0) # for now ...
	# value = tkVar.get()
	# cmd = 'Object.defineProperty(oolite.gameSettings, "wireframeGraphics", '
	# cmd += '{value: {}, writable: true}'.format(1 if value else 0)
	# gv.app.queueSilentCmd(cmd, 'set_wireframe') 
	# - returns dump of entire object
	# cmd = 'oolite.gameSettings["wireframeGraphics"]'
	# gv.app.queueSilentCmd(cmd, 'wireframe', tkVar)
	
def _setShowFPS():
	tkVar = gv.debugOptions['showFPS']
	value = tkVar.get()
	cmd = 'console.displayFPS = {}'.format('true' if value else 'false')
	gv.app.queueSilentCmd(cmd, 'showFPS', tkVar)

def _sixteenths(value):
	# arg has time factor encoded as # of sixteenths: 
	#   [0..15] 0 => 1 else x => x/16
	factor = int(value)
	return '1' if factor == 0 \
			else '1/2' if factor == 8 \
			else '{}/4'.format(factor//4) if factor % 4 == 0 \
			else '{}/8'.format(factor//2) if factor % 2 == 0 \
			else '{}/16'.format(factor)

def _setSlowTimeAcceleration(factor):	# handler for timeAccelSlow subMenu: 
										# StringVar has '1', '1/2', etc
	cmd = 'timeAccelerationFactor = {}'.format(_sixteenths(factor))
	gv.app.queueSilentCmd(cmd, 'timeAccelSlow')
	au.queryTimeAcceleration()

def _setFastTimeAcceleration(factor):	# handler for timeAccelFast subMenu: 
										# IntVar has 0..16
	cmd = 'timeAccelerationFactor = {}'.format(factor)
	gv.app.queueSilentCmd(cmd, 'timeAccelFast')
	au.queryTimeAcceleration()

# handler for Tk var trace: debugOptions['timeAccel']
# noinspection PyUnusedLocal
def _checkTimeAccel(*args):
	accel = float(gv.debugOptions['timeAccel'].get())
	# update slow submenu
	gv.debugOptions['timeAccelSlow'].set(
		'1' if accel == 1 else '' if accel > 1 else _sixteenths(accel * 16))
	# update fast submenu
	gv.debugOptions['timeAccelFast'].set(0 if accel < 1 else int(accel))

def _setShowConsoleOptn(key, tkVar):
	if not gv.connectedToOolite:
		return
	value = tkVar.get()
	gv.app.client.setConfigurationValue(key, value)
	if value:
		# ensure master switch is on
		gv.CurrentOptions['Settings']['EnableShowConsole'] = True
		# ensure options menu is up to date
		gv.localOptnVars['EnableShowConsole'].set(1)

# sole Console Properties that didn't have inline command
def _queuePropQueryList(cmds, label):
	cmd = 'log('
	last = cmds[-1]
	for cs in cmds:
		cmd += '"{0} = " + console.{0}'.format(cs)
		cmd += '' if cs == last else ' + "\\n" + '
	cmd += ');'
	gv.app.queueSilentCmd(cmd, label)

# only example use of the  '<insert local fn>' template in consoleFunctions
# - allow for additional fns to be called from this file

_filterStart = None
def dumpMemStatsLogOnly():				
	global _filterStart
	
	gv.app.colorPrint('dumping memory statistics, be patient ...', 
						emphasisRanges=[30,7])
	_filterStart = mu.timeCount()
	# set filter before console.writeMemoryStats()
	gv.colorPrintFilterREs = True
	# gv.colorPrintFilterREs = [rx.MEM_STATS_START_RE, rx.MEM_STATS_END_RE]
	gv.app.queueSilentCmd('console.writeMemoryStats()', 'filteredMemStats')
	
	# signal dump complete; see memStatsDumped
	cmd = '(function() { return "no result"; })()'
	gv.app.queueSilentCmd(cmd, 'filterMemStatsVar', gv.filterMemStatsVar)

# handler for Tk var trace: filterMemStatsVar
# noinspection PyUnusedLocal
def memStatsDumped(*args):
	elapsed = mu.timeCount() - _filterStart
	# reset filter after console.writeMemoryStats()
	gv.colorPrintFilterREs = None
	msg = '... done, saved to  Latest.log  '
	msg += '(in only {:.2f} seconds)'.format(elapsed)
	gv.app.colorPrint(msg, emphasisRanges=[19,10])

# 1st of 3 'Dump ...' commands

def _dumpEntityList():					
	# send IIFE as not in oolite-debug-console.js
	# don't worry about when enabled, as there exists player & ship
	# at start of game ie. 1st screen: 'Start new...', 'Load...'
	showLog = gv.debugOptions['showLog'].get()
	if showLog:							# temporary suspend logging to console
		gv.debugOptions['showLog'].set(0)
	cmd = ('(function() { '
			  'var text = ""; '
			  'var list = system.filteredEntities(console, '
							'function(){return true;}, player.ship); '
			  'for( let i = 0, len = list.length; i < len; i++ ) '
					'text += "\\n" + list[i]; '
			  'log("console", text); '
			  'return "no result"; '
			'})()')
	gv.app.queueSilentCmd(cmd, 'dumpEntityList')
	if showLog:
		# signals dump complete; see _entityListDumped
		cmd = '(function() { return "no result"; })()'
		gv.app.queueSilentCmd(cmd, 'entityDumpVar', gv.entityDumpVar)
	gv.app.colorPrint('')
	gv.app.colorPrint('Entity list saved to  Latest.log')

# handler for Tk var trace: entityDumpVar
# noinspection PyUnusedLocal
def _entityListDumped(*args):
	# restore logging to console that was suspended 
	# prior to logging all entities
	gv.debugOptions['showLog'].set(1)

def _dumpPlayerState():
	gv.app.queueSilentCmd('player.ship.dumpState()', 'dumpPlayerState')
	gv.app.colorPrint('')
	gv.app.colorPrint('Player\'s state saved to  Latest.log')

_QUERYTARGET = 'player.ship.target !== undefined && player.ship.target !== null'
def _checkPlayersTarget():
	gv.app.queueSilentCmd(_QUERYTARGET, 'playerHasTarget', gv.playerHasTarget)

_GETTARGETDUMP = 'player.ship.target.dumpState()'
# handler for Tk var trace: playerHasTarget
# noinspection PyUnusedLocal
def _dumpPlayersTarget(*args):
	if gv.playerHasTarget.get() == 1:
		gv.app.queueSilentCmd(_GETTARGETDUMP, 'dumpPlayersTarget')
		gv.app.colorPrint('')
		gv.app.colorPrint('Player\'s target saved to  Latest.log')
	else:
		wg.OoInfoBox(gv.root, 'Player\'s ship has no target.',
							font=gv.OoFonts['default'], destruct=5)

# handles replies from Oolite
def setDebugOption(label, value, tkVar): # called by processSilentCmd
	isStr, isInt = su.is_str(value), isinstance(value, int)
	if isInt or (isStr and (value.isdigit() or '-' in value)):
		intVal = int(value)
		if label in ['debugFlags', 'pollDebugFlags']:
			try:
				for flag, mask in _debugFlags.items():
					val = 1 if intVal & mask else 0
					gv.debugOptions['debugFlags'].get(flag).set(val)
				tkVar.set(intVal)
			except Exception as exc:
				print(exc)
				traceback.print_exc()
				pdb.set_trace()
		elif label == 'wireframe':
			# can't know type until implemented (?move below)
			# tkVar.set(1 if value else 0) 
			tkVar.set(0) ## tmp until core starts polling gameSettings
		else:
			errmsg = 'unsupported label: {}, value: {}, type: {}'.format(
						label, value, type(value))
			if con.CAGSPC:
				print(errmsg)
				traceback.print_exc()
				pdb.set_trace()
			else:
				gv.debugLogger.warning(errmsg)
	elif isStr and label == 'currStarSystem':
		# eg [System 0:150 "Xeer"] => System 0:150 "Xeer"
		system = value.strip('[]')	
		currSystem = gv.currStarSystem.get()
		if len(currSystem) and system != currSystem:
			# extra test avoids double init on startup
			pm.pollOolite(initial=True)
		if system != currSystem:
			gv.currStarSystem.set(system)
	elif isStr and value in ['true', 'false']:
		tkVar.set(1 if value == 'true' else 0)
	elif isStr and all(v in '.0123456789' for v in value):
		# Tk's DoubleVar aren't floats, leave as string
		tkVar.set(value)			
	else:
		errmsg = 'wrong type for label: {}, value: {}, type: {}'.format(
					label, value, type(value))
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.warning(errmsg)
