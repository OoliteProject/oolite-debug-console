# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import pdb
import sys, os, logging
from collections import OrderedDict

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
else:
	import tkinter as tk

import debugGUI.aliases as al
import debugGUI.appUtils as au
import debugGUI.colors as cl
import debugGUI.cmdHistory as ch
import debugGUI.constants as con
import debugGUI.config as cfg
import debugGUI.findFile as ff
import debugGUI.fontMenu as fm
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.widgets as wg

_localOptionsText = OrderedDict((
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

def createOptionsMenus(): 				# create an Options pull down menu
	optionsMenu = wg.OoBarMenu(gv.menuFrame, label='Options',
								font=gv.OoFonts['default'],
								name=mu.TkName('optionsMenu'),
								style='OoBarMenu.TMenubutton',
								postcommand=au.closeAnyOpenFrames)
	gv.optionsMenu = optionsMenu
	gv.debugConsoleMenus.append(optionsMenu)
	
	options = gv.CurrentOptions['Settings']
	defaults = con.defaultConfig['Settings']
	tkvars = gv.localOptnVars

	for key, text in _localOptionsText.items():
		val = 1 if options.get(key, defaults[key]) else 0
		tkvars[key] = tk.IntVar(name=mu.TkName('optMenu', key), value=val)
		optionsMenu.add_checkbutton(label=text, variable=tkvars[key],
				command=lambda k=key: _setOptionFromCheckButton(k, tkvars[k]))
	optionsMenu.add_command(label='Aliases ...', command=al.showAliasWindow)
	optionsMenu.add_command(label='File search ...', command=ff.showFileFind)

	optionsMenu.add_separator()
	for key, value in con.defaultConfig['Colors'].items():
		key = key.lower()
		optionsMenu.add_command(label=key, 
								command=lambda k=key: cl.pickLocalColor(k))

	optionsMenu.add_separator()
	for text in ['colored Menus', 'colored Buttons', 'colored Popups']:
		item = text[:].replace('ed ', '')
		tkVar = item + 'Var'
		key = '{}{}'.format(item[0].upper(), item[1:])
		value = 1 if options.get(key, True) else 0
		setattr(gv.app, tkVar, tk.IntVar(name=mu.TkName(tkVar), value=value))
		optionsMenu.add_checkbutton(label=text, variable=getattr(gv.app, tkVar),
							command=lambda i=item, k=key: _setColorItems(i, k))

	logDebugMsgs = tk.IntVar(name=mu.TkName('logDebugMsgs'),
					value=(1 if gv.debugLogger
								and gv.debugLogger.getEffectiveLevel()
								== logging.DEBUG
						   else 0))
	optionsMenu.add_checkbutton(label='toggle debug messages',
						 variable=logDebugMsgs, command=gv.toggleDebugMsgs)
	optionsMenu.add_command(label='reset window positions',
						 	command=_resetWindowPositions)

	## rest is debugging
	if con.CAGSPC:
		optionsMenu.add_command(label='open debugger', command=gv.setTrace)

def _resetWindowPositions():
	# make alias, finder and 3 searchBoxes 0,0 wrt app's root
	appXoff, appYoff = mu.getWidgetRoot(gv.bodyText)
	for name, tkEnt in gv.popupWindows.items():
		if name.startswith('Search'):
			top = tkEnt.master.winfo_toplevel()
			top.mouseXY = None
			Xoff, Yoff = [0, 0]
			if name in ['SearchAlias', 'SearchContext']:
				# check if parent window has been opened this session
				if top.mouseXY is None: # it has not!
					Xoff, Yoff = mu.getWidgetRoot(top)
					top.geometry('+{}+{}'.format(Xoff, Yoff))
				else:
					# its parent has already been moved,
					top.geometry('+0+0')
			else:
				Xoff, Yoff = mu.getWidgetRoot(tkEnt.master)
			tkEnt.searchBox.searchXY = [Xoff, Yoff]
		else:
			tkEnt.mouseXY = [0, 0]
			width, height = mu.getWidgetReqWH(tkEnt)
			newGeom = '{}x{}+{}+{}'.format(width, height, appXoff, appYoff)
			tkEnt.geometry(newGeom)
			gv.CurrentOptions['History'][name] = newGeom

def _setColorItems(item, key):			# handler for debug color menu items
	tkVar = item + 'Var'
	value = True if getattr(gv.app, tkVar).get() == 1 else False
	gv.CurrentOptions['Settings'][key] = value
	if item == 'colorMenus':
		gv.appearance.updateMenu()
	elif item == 'colorPopups':
		gv.appearance.updatePopup()
	elif item == 'colorButtons':
		gv.appearance.updateButton()

def _setOptionFromCheckButton(varName, tkVar):
	options = gv.CurrentOptions['Settings']
	defaults = con.defaultConfig['Settings']
	value = tkVar.get()
	oldValue = options.get(varName, defaults[varName])
	# toggle option value
	newValue = options[varName] = True if value else False
	if varName == 'PlistOverrides':
		# change font & colors to alternate set
		defFonts = con.defaultConfig['Font']
		family = size = None
		if oldValue and not newValue:	
			# Checkbutton toggled off, switch to local values
			store = gv.CurrentOptions['Font']
			family = store.get('Family', defFonts['Family'])
			size = store.get('Size', defFonts['Size'])
		elif gv.initStartTime is None:
			# have yet to connect to Oolite
			return
		elif not oldValue and newValue:
			# Checkbutton toggled on, switch to values 
			# stored in Oolite's debugConfig.plist
			store = gv.OoSettings
			family = store.get('font-face', defFonts['Family'])
			size = store.get('font-size', defFonts['Size'])
		# these both call updateAppsFontChange, 
		#   skipUpdate prevents an unnecessary call
		if family is not None:
			fm.useFontFace(family, skipUpdate=True)
		if size is not None:
			fm.useFontSize(size)
		gv.appearance.updateApp()
	elif varName == 'MsWheelHistory':	# redo bindings
		if con.IS_LINUX_PC:
			if value == 0:
				gv.cmdLine.unbind('<Button-4>')
				gv.cmdLine.unbind('<Button-5>')
			else:
				gv.cmdLine.bind('<Button-4>', _mouseWheelEvent)
				gv.cmdLine.bind('<Button-5>', _mouseWheelEvent)
		else:
			if value == 0:
				gv.cmdLine.unbind('<MouseWheel>')
			else:
				gv.cmdLine.bind('<MouseWheel>', _mouseWheelEvent)
	elif varName == 'SaveConfigNow':
		written = cfg.writeCfgFile(saveNow=True)
		gv.localOptnVars[varName].set(0)
		if written:
			dest = os.path.join(os.getcwd(), con.CFGFILE).replace(os.sep, '/')
			msg = 'configuration settings saved to   {}'.format(dest)
		else:
			msg = 'configuration not written as nothing has been changed'
		if gv.connectedToOolite:
			cmd = 'log(console.script.name, "{}")'.format(msg)
			gv.app.queueSilentCmd(cmd, 'save_Cfg')
		else:
			gv.app.colorPrint('')
			gv.app.colorPrint(msg)

def _mouseWheelEvent(event):
	if con.IS_LINUX_PC:
		if event.num == 4: 				# scroll fwd
			ch.cmdHistoryForward(event)
		elif event.num == 5: 			# scroll back
			ch.cmdHistoryBack(event)
	else:
		if event.delta > 0: 			# >= 120: # scroll fwd
			ch.cmdHistoryForward(event)
		elif event.delta < 0: 			# <= -120: # scroll back
			ch.cmdHistoryBack(event)
