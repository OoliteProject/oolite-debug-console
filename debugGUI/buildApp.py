# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, os
import pdb, traceback
from collections import OrderedDict

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import ttk
	import tkFileDialog
else:
	import tkinter as tk
	import tkinter.ttk as ttk
	import tkinter.filedialog as tkFileDialog

# try:
	# import debugGUI.aliases as al
# except Exception as exc:
	# print(exc)
	# traceback.print_exc()
	# pdb.set_trace()
	
# from . import aliases as al
#?why getting 'ImportError: cannot import name aliases'
#also, try prepending debugGUI to sys.path
import debugGUI.aliases as al
import debugGUI.appUtils as au
import debugGUI.bitmaps as bm
import debugGUI.colors as cl
import debugGUI.constants as con
import debugGUI.cmdHistory as ch
import debugGUI.debugMenu as dm
import debugGUI.findFile as ff
import debugGUI.fontMenu as fm
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.optionsMenu as om
import debugGUI.plistMenu as pm
import debugGUI.style as st
import debugGUI.widgets as wg

## main application ###########################################################

# options that record Tk widget position
_popupWindows = [
	'AliasWindow', 'FinderWindow', 
	'SearchLog', 'SearchCmd', 'SearchAlias', 'SearchContext'
]

def buildGUI():
	fm.makeFonts()
	con.LISTBOX_OPTIONS.update({'font': gv.OoFonts['default']})
	bm.createBitmaps()
	style = st.initStyle()
	gv.appearance = gv.Appearance(style,
								  st.updateStyle, cl.updateAppColors,
								  cl.setMenuColors, cl.setPopupColors)
	gv.appearance.updateTkOptionDb()

	# gv.menubar = tk.Menu(gv.root)	# create a toplevel menu
	# gv.root.config(menu=gv.menubar)	# display the menu
	# NB: menubar must precede .geometry call, else app shrinks by height 
	# 	  of menubar (20) on each invocation
	# - no longer relevant as not using toplevel menu, good to remember
	
	gv.menuFrame = ttk.Frame(gv.menubar, name=mu.TkName('menuFrame'))
	gv.menuFrame.grid(row=0, column=0, sticky='nw')

	# build menus - order they are created dictate order on menubar
	dm.createDebugMenus()
	om.createOptionsMenus()
	fm.createFontMenus()
	pm.initConnectionVars()
	# - the Settings menu is created upon connection, as they vary		

	settings = gv.CurrentOptions['Settings']
	history = gv.CurrentOptions['History']
	gv.sashPosns['SashOffset'] = settings.get('SashOffset')
	gv.sashPosns['AliasSashOffset'] = history.get('AliasSashOffset')
	gv.sashPosns['FindSashOffset'] = history.get('FindSashOffset')
	# build app widgets
	_createWindows()
	searches = history.get('SearchTerms')
	if searches is not None:
		gv.bodyText.popup.searchBox.searchTarget.setList(searches)

	_createFileFind()
	# load option values from CFGFILE
	_initFindOptions()

	_createAliasFrame()

	gv.geometries.update(
		{'Geometry': gv.root,
		'AliasWindow': gv.aliasWindow,
		'FinderWindow': gv.grepWindow,
	})

	_configTextFonts()
	gv.appearance.updateApp()
	toolTips = settings['ToolTips']
	if toolTips != 'all':
		wg.ToolTip.limitToolTips(toolTips)

	# now is ok to add aliases to menubar
	gv.root.update_idletasks()
	gv.aliasWindow.geometry(con.DEFAULT_ALIAS_GEOMETRY)
	al.setAllMenuButtons()
	au.positionAliasSash(gv.sashPosns['AliasSashOffset']) 
	# setAllMenuButtons & positionAliasSash will generate <Configure>, so
	# .bind must follow them
	# noinspection PyUnresolvedReferences

	# trying aliasDefn 2Cif can use it in au.PositionSash
	gv.aliasDefn.bind('<Configure>', au.aliasConfig)

	# restore saved window positions 
	gv.popupWindows = dict(zip(_popupWindows,
							[gv.aliasWindow, gv.grepWindow,
							 gv.bodyText.popup, gv.cmdLine.popup, 
							 gv.aliasDefn.popup, gv.contextText.popup]))
	# - last 4 are for search windows, shared amongst ScrollingText
	
	for name, tkEnt in gv.popupWindows.items():
		if name.startswith('Search'): # coordinates of upper left corner
			openXY = history.get(name)
			if openXY:	# initialize positions using CFGFILE values
				tkEnt.searchBox.searchXY \
					= [int(x) for x in openXY.strip('[]').split(',')]
			# tkEnt.bind('<Configure>', au.dragSearchbox)
		else: # window entries are geometry strings
			geom = history.get(name)
			if geom:
				width, height, xOffset, yOffset = au.fitToMonitors(geom)
				history[name] = '{}x{}+{}+{}'.format(width, height,
													 xOffset, yOffset)

	# building complete, initialize sash vertical position
	au.positionAppSash(settings.get('SashOffset'), init=True)
	# binding must follow positionAppSash as it'll generate a <Configure> event
	gv.bodyText.frame.bind('<Configure>', au.paneConfig)
	gv.appWidth, gv.appHeight = mu.getAppDimns(gv.root)	
	gv.root.bind_all('<<closeAnyOpenFrames>>', au.closeAnyOpenFrames)
		
	# restrict <Configure> events to app (ie. not menu)
	gv.root.unbind('<Configure>')
	gv.app.bind('<Configure>', au.appConfig)

_textStyle = {	'undo': True, 'wrap': 'none', 
			'exportselection': 0, 'hScroll': True}
	
def _configTextFonts():
	emphasis = gv.OoFonts['emphasis'], 
	searchMark = gv.OoFonts['searchMark']
	for text in gv.textWidgets:
		text.tag_config('emphasis', font=emphasis)
		text.tag_config('searchMark', font=searchMark)

def _createWindows():
	gv.appWindow = ttk.PanedWindow(gv.app, orient='vertical',
								name=mu.TkName('paned'))
	_textStyle.update({'font': 		gv.OoFonts['default'],
					'disabledFont': gv.OoFonts['disabled']})
	# main display
	bodyText = wg.ScrollingText(gv.appWindow, name=mu.TkName('bodyText'),
								searchPrefix='Output', 
								editable=False, **_textStyle)
	gv.bodyText = bodyText
	gv.textWidgets.append(bodyText)
	# command window
	cmdFrame = ttk.Frame(gv.appWindow, name=mu.TkName('cmdFrame'))
	cmdLine = wg.ScrollingText(cmdFrame, name=mu.TkName('cmdLine'),
								searchPrefix='Command', 
								histCmd=ch.deleteCurrentCmd,
								editable=True, **_textStyle)
	gv.cmdLine = cmdLine						
	cmdLine.bind('<Escape>', gv.app.cmdClear)
	cmdLine.bind('<Return>', gv.app.runCmd)
	ch.setHistoryBindings(cmdLine)
	gv.textWidgets.append(cmdLine)

	# command window Buttons
	cmdbuttonFrame = ttk.Frame(cmdFrame, name=mu.TkName('cmdbuttonFrame'))
	# make both buttons same width, len('Clear') + 2 spaces = 7
	btnRun = ttk.Button(cmdbuttonFrame, text='Run', 
								name=mu.TkName('btnRun'),
								width=7, command=gv.app.runCmd)
	gv.btnRun = btnRun
	btnCmdClr = ttk.Button(cmdbuttonFrame, text='Clear', 
								name=mu.TkName('btnCmdClr'),
								width=7, command=gv.app.cmdClear)
	gv.btnCmdClr = btnCmdClr
	
	# row 1 is unoccupied; giving it weight makes it stretchy and the
	#   buttons remain in Frame's corners
	cmdbuttonFrame.rowconfigure(1,		weight=1) 
	# in cmdbuttonFrame
	btnCmdClr.grid(		row=0,	column=0,	sticky='ne')
	btnRun.grid(		row=2,	column=0,	sticky='se')
	
	cmdFrame.rowconfigure(		0,		weight=1)
	cmdFrame.columnconfigure(	0,		weight=1)
	# in cmdFrame
	cmdLine.frame.grid(	row=0,	column=0,	sticky='news')
	cmdbuttonFrame.grid(row=0,	column=1,	sticky='ns')

	# in appWindow (bodyText & cmdFrame don't .grid -> .add to appWindow)
	gv.appWindow.add(bodyText.frame,	weight=1)
	gv.appWindow.add(cmdFrame) 
	
	# in gv.app
	gv.appWindow.grid(	row=0,	column=0,	sticky='news')

## alias editor ###############################################################

def _createAliasFrame():					# build alias frame
	aliasWindow = wg.TopWindow(gv.root, title='Aliases', 
								enduring=True, showNow=False, 
								name=mu.TkName('aliasWindow'))
	gv.aliasWindow = aliasWindow
	aliasWindow.resizable(width=True, height=True)
	aliasWindow.transient('') # override default in TopWindow

	paned = ttk.PanedWindow if con.ALIAS_PANED == 'ttk' else tk.PanedWindow
	aliasPaned = paned(aliasWindow.twFrame, orient='horizontal',
					   name=mu.TkName('aliasPaned'))
	gv.aliasPaned = aliasPaned			
	aliasFrame = ttk.Frame(aliasPaned, name=mu.TkName('aliasFrame'))
	gv.aliasFrame = aliasFrame # tmp4debug
	
	# row 0
	msgFrame = ttk.Frame(aliasFrame, name=mu.TkName('msgFrame'))
	gv.aliasMsgStr = tk.StringVar(name=mu.TkName('aliasMsgStr'))
	aliasMsgLabel = ttk.Label(msgFrame, name=mu.TkName('aliasMsgLabel'),
								anchor='w', textvariable=gv.aliasMsgStr)
	gv.aliasRegStr = tk.StringVar(name=mu.TkName('aliasRegStr'))
	aliasRegLabel = ttk.Label(msgFrame, name=mu.TkName('aliasRegLabel'),
								anchor='e', textvariable=gv.aliasRegStr)

	# ScrollingListBox has its own frame (.lbFrame)
	aliasList = wg.ScrollingListBox(aliasPaned, gv.OoFonts['disabled'],
									lbColumn=2, name=mu.TkName('aliasListBox'))
	gv.aliasListBox = aliasList
	# create column lines: this style has foreground and columns are
	# gridded w/ spacing (see below)
	aliasList.lbFrame.config(style='selector.TFrame')

	# extra listboxes inside lbframe
	# - in a groupAssociates list to keep movements synchronized
	#   (see ScrollbarPopup)
	polledList = tk.Listbox(aliasList.lbFrame, width=2,
							name=mu.TkName('polledListBox'),
							**con.LISTBOX_OPTIONS)
	gv.polledListBox = polledList

	inMenuList = tk.Listbox(aliasList.lbFrame, width=2,
							name=mu.TkName('inMenuListBox'),
							**con.LISTBOX_OPTIONS)
	gv.inMenuListBox = inMenuList
	
	gv.aliasListBoxes = [inMenuList, polledList, aliasList]
	# - order in list must match order in lbFrame
	aliasList.scrollbar.groupAssociates(gv.aliasListBoxes)	
	_bindAliasListBoxes()

	# row 1
	headerFrame = ttk.Frame(aliasFrame, name=mu.TkName('headerFrame'))
	nameFrame = ttk.Frame(headerFrame, name=mu.TkName('nameFrame'))
	aliasNameLabel = ttk.Label(nameFrame, 
								name=mu.TkName('aliasNameLabel'),
								relief='flat', text='Name:', 
								justify='left', anchor='e')

	_='''
validate= specifies which events will trigger the routine, can be:
	'focus', 'focusin', 'focusout', 'key', 'all', 'none'
	(a paste is treated as key, so may get more than 1 char when triggered)

args to .register specify what info is sent when triggered
	'%d' action 0=deletion 1=insertion -1=focus in/out or textvariable changed
	'%i' is index of insertion/deletion
	'%S' is str being inserted/deleted
	'%s' is value before change
	'%P' is value if change allowed
	'%v' is current value of Entry['validate'] option,
	'%V' is reason for callback: 'focusin',  'focusout', 'key', 'forced' 
		'forced' is when the textvariable was changed
	'%W' is name of the widget

'%d',   '%i',  '%S', '%s',   '%P',  '%v',    '%V',   '%W'
action, where, what, before, after, trigger, reason, name

NB: if your validation alters either the Entry or textvariable, tkinter 
	will shut off validation (else endless recursion).  
	To restore validation, user either 
	self.entry.after_idle(lambda: self.entry.configure(validate='key'))
	or:
	self.entry.after_idle(self.entry.configure, {'validate': 'key'})
	You will need this in any invalidcommand method too!
'''

	setButtonState = (aliasWindow.register(al.setAliasButtonsByEntry),
					'%d', '%i', '%S', '%s', '%P', '%v', '%V', '%W')
	gv.aliasNameVar = tk.StringVar(name=mu.TkName('aliasNameVar'))
	aliasNameEntry = ttk.Entry(nameFrame, name=mu.TkName('aliasNameEntry'),
							   width=8, validate='key',
							   textvariable=gv.aliasNameVar,
							   validatecommand=setButtonState,
							   **con.ENTRY_OPTIONS)
	gv.aliasNameEntry = aliasNameEntry

	tipDelay = gv.CurrentOptions['Settings'].get('FindToolTipDelayMS', 0)

	pollCheck = ttk.Button(headerFrame, compound='left',
								name=mu.TkName('aliasPollCheck'),
								style='pollingAlias.TButton',
								image=gv.OoBitmaps[con.ALIASPOLLINGTEXT[None]['image']],
								command=al.toggleAliasPoll)
	pollCheck.state(['disabled'])
	gv.aliasPollCheck = pollCheck

	msg = con.toolTips.get('aliasPollButton', '').strip()
	wg.ToolTip(pollCheck, msg, tipDelay)

	font = gv.OoFonts['default']
	zeroLen = font.measure('0')
	maxTextWidth = max(1 + (font.measure(spec['text'])) // zeroLen
	 				   for spec in con.ALIASPOLLINGTEXT.values())
	# - a bit too narrow so +1
	pollCheck.config(width=maxTextWidth)
	al.setAliasPollButton()	

	gv.aliasButtonFrames = [] # created on demand, see setNumButtonFrames
	asButton = ttk.Button(headerFrame, compound='left',
								name=mu.TkName('aliasAsButton'),
								style='aliasInMenu.TButton',
								command=al.toggleAliasInMenu)
	asButton.state(['disabled'])
	gv.aliasAsButton = asButton
	maxTextWidth = max(1 + (font.measure(spec['text'])) // zeroLen
	 				   for spec in con.ALIASINMENUTEXT.values())
	asButton.config(width=maxTextWidth)
	msg = con.toolTips.get('aliasMenuButton', '').strip()
	wg.ToolTip(asButton, msg, tipDelay)

	# row 2 - ScrollingText has its own frame (.frame)
	aliasDefn = wg.ScrollingText(aliasFrame, name=mu.TkName('aliasDefn'),
								searchPrefix='Alias', insertwidth=4, 
								relief='ridge', padx=2, editable=True, 
								tabs=font.measure(' ' * con.CFG_TAB_LENGTH),
								tabstyle='wordprocessor', **_textStyle)
	gv.aliasDefn = aliasDefn
	gv.textWidgets.append(aliasDefn)
	aliasDefn.edit_modified(False)
	aliasDefn.bind('<KeyRelease>', al.aliasTextValidate)
	# aliasDefn.bind('<KeyPress>', al.aliasTextValidate)
	# these 2 not included in general KeyPress
	aliasDefn.bind('<KeyPress-BackSpace>', al.aliasTextValidate)
	aliasDefn.bind('<KeyPress-Delete>', al.aliasTextValidate)
	aliasDefn.bind('<<Cut>>', al.aliasTextValidate)
	aliasDefn.bind('<<Paste>>', al.aliasTextValidate)
	# - last 2 needed for when user changes focus, returns then cut/paste
	#   (button state was not updating)

	aliasDefn.unbind('<<Undo>>')
	aliasDefn.unbind('<Control-Z>')
	# - get interference from textPopup

	# row 3
	gv.aliasValueVar = tk.StringVar(name=mu.TkName('aliasValueVar'))
	aliasValue = ttk.Label(aliasFrame, anchor='w', width=40, 
								name=mu.TkName('aliasValueVar'),
								style='alias.TLabel', 
								textvariable=gv.aliasValueVar)
	gv.aliasValueLabel = aliasValue
	
	# row 4
	buttonFrame = ttk.Frame(aliasFrame, name=mu.TkName('buttonFrame'))
	addBtn = ttk.Button(buttonFrame, name=mu.TkName('aliasAddBtn'),
								text='Add', command=al.aliasAdd)
	gv.aliasAddBtn = addBtn
	delBtn = ttk.Button(buttonFrame, name=mu.TkName('aliasDelBtn'),
								text='Delete',
								command=al.aliasDelete)
	gv.aliasDelBtn = delBtn
	undoBtn = ttk.Button(buttonFrame, name=mu.TkName('aliasUndoBtn'),
								text='Undo', command=al.aliasUndo)
	gv.aliasUndoBtn = undoBtn
	redoBtn = ttk.Button(buttonFrame, name=mu.TkName('aliasRedoBtn'),
								text='Redo', command=al.aliasRedo)
	gv.aliasRedoBtn = redoBtn

	# main/bigger widgets should be packed/gridded last

	msgFrame.rowconfigure(				0, 	weight=1)
	msgFrame.columnconfigure(			1, 	weight=1)
	# in msgFrame
	aliasMsgLabel.grid(		row=0, column=0, sticky='w', 	padx=2)
	aliasRegLabel.grid(		row=0, column=1, sticky='e', 	padx=2)

	# in nameFrame
	aliasNameLabel.grid(	row=0, column=0, sticky='e', 	padx=2)
	aliasNameEntry.grid(	row=0, column=1, sticky='w', 	padx=2)

	headerFrame.columnconfigure(		0,	weight=1)	# evenly spaced
	headerFrame.columnconfigure(		1,	weight=1)
	headerFrame.columnconfigure(		2,	weight=1)
	# in headerFrame
	nameFrame.grid(			row=0, column=0, sticky='w')
	pollCheck.grid(			row=0, column=1, 				padx=2)
	asButton.grid(			row=0, column=2, sticky='e', 	padx=2)

	buttonFrame.columnconfigure(		0, 	weight=1)	# evenly space buttons
	buttonFrame.columnconfigure(		1, 	weight=1)
	buttonFrame.columnconfigure(		2, 	weight=1)
	buttonFrame.columnconfigure(		3, 	weight=1)
	# in buttonFrame
	delBtn.grid(			row=0, column=0, 				padx=2, pady=2)
	redoBtn.grid(			row=0, column=1, 				padx=2, pady=2)
	undoBtn.grid(			row=0, column=2, 				padx=2, pady=2)
	addBtn.grid(			row=0, column=3, 				padx=2, pady=2)

	aliasFrame.rowconfigure(			2,	weight=1)	# 2 is aliasDefn (Text) widget
	aliasFrame.columnconfigure(			1,	weight=1)
	# in aliasFrame
	msgFrame.grid(			row=0, column=1, sticky='ew', 	padx=0, pady=0)
	headerFrame.grid(		row=1, column=1, sticky='ew', 	padx=0, pady=2)
	aliasDefn.rowconfigure(				0, 	weight=1)	# for scrollbar
	aliasDefn.columnconfigure(			0, 	weight=1)
	aliasDefn.frame.grid(	row=2, column=0, sticky='news',	padx=0, pady=0,	columnspan=4)
	aliasValue.grid(		row=3, column=0, sticky='ew', 	padx=0, pady=2,	columnspan=4)
	buttonFrame.grid(		row=4, column=0, sticky='sew', 	padx=0, pady=0,	columnspan=4)

	aliasList.lbFrame.rowconfigure(		0, 	weight=1)
	aliasList.lbFrame.columnconfigure(	2,	weight=1)	# for aliasList
	# in lbFrame (padx spacing allows colored frame to show through)
	inMenuList.grid(		row=0, column=0, sticky='ns', 	padx=0)
	polledList.grid(		row=0, column=1, sticky='ns', 	padx=(1, 1))
	aliasList.grid(			row=0, column=2, sticky='news', padx=0)

	# make row 0 & column 0 stretchable so lbFrame & aliasFrame fills aliasPaned
	aliasPaned.rowconfigure(			0,	weight=1)
	aliasPaned.columnconfigure(			0,	weight=1)
	# in aliasPaned (PanedWindow uses add instead of grid)
	if con.ALIAS_PANED == 'ttk':
		aliasPaned.add(aliasList.lbFrame)
		aliasPaned.add(aliasFrame)
	else:
		aliasPaned.add(aliasList.lbFrame, sticky='nsw',	padx=2)
		aliasPaned.add(aliasFrame, sticky='news',	padx=2)

	# make row 0 and column 0 stretchable so aliasPaned fills twFrame
	aliasWindow.twFrame.rowconfigure(	0,	weight=1)
	aliasWindow.twFrame.columnconfigure(0,	weight=1)
	# in aliasWindow.twFrame
	aliasPaned.grid(		row=0, column=0, 	sticky='news')

	# make row 0 and column 0 stretchable so twFrame fills aliasWindow
	aliasWindow.rowconfigure(			0,	weight=1)
	aliasWindow.columnconfigure(		0,	weight=1)
	# in aliasWindow
	aliasWindow.twFrame.grid(row=0, column=0, 	sticky='news')

	# high level event bindings
	msgFrame.bind('<Escape>', aliasWindow.closeTop)
	headerFrame.bind('<Escape>', aliasWindow.closeTop)
	aliasValue.bind('<Escape>', aliasWindow.closeTop)
	buttonFrame.bind('<Escape>', aliasWindow.closeTop)
	aliasNameEntry.bind('<Escape>', al.clearAliasEntry)
	aliasDefn.bind('<Escape>', al.clearAliasText)

	aliasNameEntry.bind('<Return>', al.newAliasAdd)

# aliasListBox frame has 2 extra synchronized listboxes, for polling and
# menubar; simply binding <<ListboxSelect>> to lookupAlias for each
# results in each one firing upon a single click (?common master, lbFrame),
# so we manage the bindings upon entry/exit from each listbox
def _enterAliasList(event=None):
	for box in gv.aliasListBoxes:
		if box is event.widget:
			box.bind('<<ListboxSelect>>', al.lookupAlias)
		else:
			box.unbind('<<ListboxSelect>>')
	return 'break'

def _leaveAliasList(event=None):
	event.widget.unbind('<<ListboxSelect>>')
	return 'break'

def _bindAliasListBoxes():
	gv.aliasListBox.bind('<Return>', al.editAlias)		
	gv.polledListBox.bind('<Return>', al.toggleAliasPoll)
	gv.inMenuListBox.bind('<Return>', al.toggleAliasInMenu)
	for box in gv.aliasListBoxes:
		# all 3 listboxes synchronized via sole ScrollingListBox
		# box['yscrollcommand'] = gv.aliasListBox.scrollbar.set
		box['yscrollcommand'] = gv.aliasListBox.setStopper
		# <<ListboxSelect>> only active in one box at a time
		box.bind('<Enter>', _enterAliasList)
		box.bind('<Leave>', _leaveAliasList)
		box.bind('<KeyPress-Up>', al.aliasListUpArrow)
		box.bind('<KeyPress-Down>', al.aliasListDownArrow)
		box.bind('<KeyPress-Left>', al.aliasListLeftArrow)
		box.bind('<KeyPress-Right>', al.aliasListRightArrow)
		box.unbind('<space>')

## file searcher ##############################################################

def _createFileFind():
	settings = gv.CurrentOptions['History']
	defaults = con.defaultConfig['History']
	gv.grepWindow = wg.TopWindow(gv.root, title='File Search', enduring=True,
							showNow=False, name=mu.TkName('grepWindow'))
	gv.grepWindow.protocol('WM_DELETE_WINDOW', _closeFinder)
	twFrame = gv.grepWindow.twFrame
	gv.grepWindow.resizable(width=True, height=True)
	gv.grepWindow.transient('')  # override default in TopWindow
	font, disabled = gv.OoFonts['default'], gv.OoFonts['disabled']

	inputFrame = ttk.Frame(twFrame, name=mu.TkName('grepInputFrame'))
	canvasFrame = wg.ScrolledWindow(inputFrame,
									name=mu.TkName('grepScrollInput'))
	cvFrame = canvasFrame.cvFrame
	gv.grepCanvas = canvasFrame
	gv.grepCanvas.cvFrame.config(style='selector.TFrame')

	## search results widgets #############################################

	outputFrame = ttk.Frame(twFrame, name=mu.TkName('grepOutputFrame'))
	grepPaned = ttk.PanedWindow(outputFrame, orient='vertical',
								name=mu.TkName('grepPaned'))
	gv.grepPaned = grepPaned

	gv.filesList = wg.ScrollingListBox(grepPaned, disabled,
									   name=mu.TkName('grepFilesList'))

	gv.contextText = wg.ScrollingText(grepPaned, searchPrefix='File',
									  name=mu.TkName('grepContextText'),
									  editable=False, **_textStyle)
	gv.textWidgets.append(gv.contextText)
	gv.contextText.tag_configure('fileSearch', font=gv.OoFonts['emphasis'])

	## search path widgets ################################################

	tipDelay = gv.CurrentOptions['Settings'].get('FindToolTipDelayMS', 0)

	gv.pathEntry = wg.OoSelector(cvFrame, 'grepPath', 'Search in:',
								 tipDelay)
	gv.pathEntry.preProcessFn = lambda v: v.strip(con.PATH_STRIP_CHARS)
	pathButton = ttk.Checkbutton(gv.pathEntry.oosFrame,
								 style='pathButton.TCheckbutton',
								 name=mu.TkName('grepPath', 'Button'),
								 command=_getSearchPath)
	pathButton.grid(row=0, column=3, sticky='e', padx=4, columnspan=5)
	gv.pathButton = pathButton

	# search sub-folders
	value = settings.get('FindSubDirs',
						defaults.get('FindSubDirs'))
	gv.subDirs = tk.IntVar(value=1 if value else 0, name=mu.TkName('grepSubDirs'))
	subDirsBtn = ttk.Checkbutton(gv.pathEntry.oosFrame, variable=gv.subDirs,
							name=mu.TkName('grepSubDirsBtn'),
							text=' sub-folders', # ' Include sub-folders'
							**con.CHECKBUTTON_OPTIONS)
	subDirsBtn.grid(row=2, column=0, sticky='w', padx=4)

	# search oxz files
	value = settings.get('FindOxzFiles',
						defaults.get('FindOxzFiles'))
	gv.oxzFiles = tk.IntVar(value=1 if value else 0, name=mu.TkName('grepOxzFiles'))
	oxzFilesBtn = ttk.Checkbutton(gv.pathEntry.oosFrame, variable=gv.oxzFiles,
							name=mu.TkName('grepOxzFilesBtn'),
							text=' oxz files', # ' Include oxz files'
							**con.CHECKBUTTON_OPTIONS)
	msg = con.toolTips.get('grepOxzFiles', '').strip()
	wg.ToolTip(oxzFilesBtn, msg, tipDelay)
	oxzFilesBtn.grid(row=2, column=2, sticky='e', padx=4, columnspan=5)

	## file type widgets ##################################################

	gv.exclEntry = wg.OoSelector(cvFrame, 'grepExcl', 'Excluded:',
								 tipDelay, selectors=1)
								# choiceList=[[' ', ' X']]) # is default choices
								# - first choice is treated as unselected

	gv.inclEntry = wg.OoSelector(cvFrame, 'grepIncl', 'Included:',
								 tipDelay, selectors=1)

	## search text widgets ################################################

	gv.textEntry = wg.OoSelector(cvFrame, 'grepText', 'Search text:',
								 tipDelay, selectors=1)

	## search button widgets ##############################################

	btnFrame = ttk.Frame(cvFrame, name=mu.TkName('grepBtnFrame'))
	searchBtn = ttk.Button(btnFrame,
							name=mu.TkName('grepSearchBtn'),
							text='Search',
							command=ff.startFileFind)
	cancelBtn = ttk.Button(btnFrame,
							name=mu.TkName('grepCancelBtn'),
							text='Cancel',
							command=ff.cancelFileFind)

	## search options widgets #############################################

	optnsFrame = ttk.Frame(cvFrame, name=mu.TkName('grepOptionsFrame'))

	# case insensitive
	value = settings.get('FindIgnoreCase',
						defaults.get('FindIgnoreCase'))
	gv.ignoreCase = tk.IntVar(value=1 if value else 0,
							name=mu.TkName('grepIgnoreCase'))
	ignoreCaseBtn = ttk.Checkbutton(optnsFrame, variable=gv.ignoreCase,
							name=mu.TkName('grepIgnoreCaseBtn'),
							text=' Ignore case',
							**con.CHECKBUTTON_OPTIONS)

	# match all token (vs any)
	value = settings.get('FindMatchAll',
						defaults.get('FindMatchAll'))
	gv.matchAll = tk.IntVar(value=1 if value else 0,
							name=mu.TkName('grepMatchAll'))
	matchAllBtn = ttk.Checkbutton(optnsFrame, variable=gv.matchAll,
							name=mu.TkName('grepMatchAllBtn'),
							text=' Match all (vs any)',
							**con.CHECKBUTTON_OPTIONS)
	msg = con.toolTips.get('grepMatchAll', '').strip()
	wg.ToolTip(matchAllBtn, msg, tipDelay)

	# quit on first match
	value = settings.get('FindQuitOnFirst',
						defaults.get('FindQuitOnFirst'))
	gv.quitOnFirst = tk.IntVar(value=1 if value else 0,
							name=mu.TkName('grepQuitOnFirst'))
	quitOnFirstBtn = ttk.Checkbutton(optnsFrame, variable=gv.quitOnFirst,
							name=mu.TkName('grepQuitOnFirstBtn'),
							text=' Skip rest of file (faster)',
							**con.CHECKBUTTON_OPTIONS)
	msg = con.toolTips.get('grepQuitOnFirst', '').strip()
	wg.ToolTip(quitOnFirstBtn, msg, tipDelay)
	#
	# # search sub-folders
	# value = settings.get('FindSubDirs',
	# 					defaults.get('FindSubDirs'))
	# gv.subDirs = tk.IntVar(value=1 if value else 0, name=mu.TkName('grepSubDirs'))
	# subDirsBtn = ttk.Checkbutton(optnsFrame, variable=gv.subDirs,
	# 						name=mu.TkName('grepSubDirsBtn'),
	# 						text=' Include sub-folders',
	# 						**con.CHECKBUTTON_OPTIONS)
	#
	# # search oxz files
	# value = settings.get('FindOxzFiles',
	# 					defaults.get('FindOxzFiles'))
	# gv.oxzFiles = tk.IntVar(value=1 if value else 0, name=mu.TkName('grepOxzFiles'))
	# oxzFilesBtn = ttk.Checkbutton(optnsFrame, variable=gv.oxzFiles,
	# 						name=mu.TkName('grepOxzFilesBtn'),
	# 						text=' Include oxz files',
	# 						**con.CHECKBUTTON_OPTIONS)
	# msg = con.toolTips.get('grepOxzFiles', '').strip()
	# wg.ToolTip(oxzFilesBtn, msg, tipDelay)

	# context lines
	value = settings.get('FindContextLines',
						defaults.get('FindContextLines', 3))
	gv.contextNum = tk.IntVar(value=value, name=mu.TkName('grepContextNum'))
	contextLabel = ttk.Label(optnsFrame, text='# of context lines',
							name=mu.TkName('grepContextLabel'), anchor='w')
	contextNumBtn = tk.Spinbox(optnsFrame, textvariable=gv.contextNum,
							name=mu.TkName('grepContextNumBtn'),
							exportselection=0, from_=0, to=20, #
							increment=1, font=font, width=2)
	gv.contextNumBtn = contextNumBtn # needed for color changes
	msg = con.toolTips.get('grepContextNum', '').strip()
	# 4th parm is group so both widgets get same tip
	wg.ToolTip(contextLabel, msg, tipDelay, 'grepContextNum')
	wg.ToolTip(contextNumBtn, msg, tipDelay, 'grepContextNum')

	# treat tokens as a 'Token', 'Substring', 'Word', 'Regex' or 'File'
	# - Token will ignore spaces adjacent to any '()[]{}'
	# - File option treats tokens as filenames and shows which folders or
	# oxz files contain those filenames (wildcards supported)
	treatFrame = ttk.Frame(cvFrame, name=mu.TkName('grepTreatFrame'))

	treatLabel = ttk.Label(treatFrame, text='Treat search text as:',
							name=mu.TkName('grepTreatLabel'), anchor='w')
	value = settings.get('FindTreatment',
						defaults.get('FindTreatment', 'Token'))
	gv.treatText = tk.StringVar(value=value,
							name=mu.TkName('grepTreatText'))
	treatStrs = OrderedDict({
		'Token': 	['Token(s) (ignore spaces, ',
					 ' punctuation, etc.)', ],
		'Word': 	['Word (hemmed by spaces, ',
					 ' trailing punctuation)', ],
		'Substring':['Substring (all characters, ',
					 ' contiguous, anywhere)', ],
		'Regex': 	['Regular Expression', ],
		'File': 	['File (locate in folders, oxz\'s)', ],
	})
	_radioButtonKWs = {'variable': gv.treatText,
					  'style': 'grep.TRadiobutton',
					  'compound': 'left'}
	treatButtons = []
	for treat, strList in treatStrs.items():
		name = 'grepTreat' + treat
		radio = ttk.Radiobutton(treatFrame,
							name=mu.TkName(name),
							text='\n'.join(strList),
							value=treat, **_radioButtonKWs)
		if name in con.toolTips:
			msg = con.toolTips.get(name).strip()
			if msg is not None:
				wg.ToolTip(radio, msg, tipDelay)
		treatButtons.append(radio)

	## inputFrame #########################################################

	# make stretchable so buttons touch bottom, split apart
	btnFrame.rowconfigure(0, weight=1)
	btnFrame.columnconfigure(1, weight=1)
	# in btnFrame
	cancelBtn.grid(row=0, column=0, sticky='sw', padx=8, pady=8)
	searchBtn.grid(row=0, column=2, sticky='se', padx=8, pady=8)

	# in optnsFrame
	optnGrid = {'sticky': 'nw', 'padx': 4, 'pady': 4,}
	optnSpanGrid = optnGrid.copy()
	optnSpanGrid.update({'column': 0, 'columnspan': 2})

	ignoreCaseBtn.grid(	row=0, **optnSpanGrid)
	matchAllBtn.grid(	row=1, **optnSpanGrid)
	quitOnFirstBtn.grid(row=2, **optnSpanGrid)
	# subDirsBtn.grid(	row=3, **optnSpanGrid)
	# oxzFilesBtn.grid(	row=4, **optnSpanGrid)
	contextNumBtn.grid(	row=5, column=0, **optnGrid)
	contextNumBtn.grid(sticky='n')
	contextLabel.grid(	row=5, column=1, **optnGrid)

	# in treatFrame
	treatLabel.grid(	row=0, **optnSpanGrid)
	for row, treat in enumerate(treatButtons):
		treat.grid(row=row + 1, **optnSpanGrid)

	# make stretchable
	cvFrame.rowconfigure(0, weight=1)
	cvFrame.columnconfigure(0, weight=1)
	# in cvFrame
	frameGrid = {'column': 0, 'sticky': 'news', 'pady': (0, 2)}
	for row, frame in enumerate(
			[gv.pathEntry.oosFrame,
			 gv.inclEntry.oosFrame,
			 gv.exclEntry.oosFrame,
			 gv.textEntry.oosFrame,
			 btnFrame, optnsFrame, treatFrame]):
		if frame is treatFrame:
			frameGrid['pady'] = 0
		frame.grid(row=row, **frameGrid)

	# make stretchable
	inputFrame.rowconfigure(0, weight=1)
	inputFrame.columnconfigure(0, weight=1)
	# in canvasFrame
	canvasFrame.grid(row=0, column=0, sticky='news')

# 								    - contextText
# twFrame - outputFrame - grepPaned - filesList - lbFrame (not yet used) - 
#
#									 - .scrollbar
# 		  - inputFrame - canvasFrame - .canvas - .cvFrame	- pathEntry.oosFrame - pathEntry
#															- gv.inclEntry.oosFrame - inclEntry
#															- gv.exclEntry.oosFrame - exclEntry,  exclBtn
#															- textEntry.oosFrame - textEntry
#															- optnsFrame - treatText et.al.
#															- btnFrame - searchBtn,  cancelBtn

	## outputFrame ########################################################

	gv.filesList.lbFrame.rowconfigure(0, weight=1)
	gv.filesList.lbFrame.columnconfigure(0, weight=1)
	# in filesList.lbFrame
	gv.filesList.grid(sticky='news')

	# make row 0 and column 0 stretchable so filesList &
	# contextText fills aliasPaned
	grepPaned.rowconfigure(0, weight=1)
	grepPaned.columnconfigure(0, weight=1)
	# in grepPaned (PanedWindow uses add instead of grid)
	grepPaned.add(gv.filesList.lbFrame)
	grepPaned.add(gv.contextText.frame, weight=1)

	# make row 0 and column 0 stretchable so PanedWindow fills frame
	outputFrame.rowconfigure(0, weight=1)
	outputFrame.columnconfigure(0, weight=1)
	# in outputFrame
	grepPaned.grid(row=0, column=0, sticky='news')

	twFrame.rowconfigure(0, weight=1)
	twFrame.columnconfigure(1, weight=1)
	# in twFrame, aka grepWindow.twFrame
	inputFrame.grid( row=0, column=0, sticky='nw')
	outputFrame.grid(row=0, column=1, sticky='news')

	gv.grepWindow.rowconfigure(0, weight=1)
	gv.grepWindow.columnconfigure(0, weight=1)
	# in grepWindow
	twFrame.grid(	row=0, column=0, sticky='news')

	# input bindings
	gv.findComboboxes = {
		'FindPaths': gv.pathEntry, 'FindTypes': gv.inclEntry,
		'FindExcls': gv.exclEntry, 'FindSearches': gv.textEntry, }
	for box in gv.findComboboxes.values():
		box.bind('<Escape>', box.lbCancel)
		box.bind('<Return>', lambda ev, bx=box: _addListItem(ev, bx))
	# box.config(postcommand=box.adjustEntry) # maintain lists as LIFO
	## - is default in OoCombobox

	# output bindings
	gv.filesList.bind('<<ListboxSelect>>', ff.showFindContext)

	# high level event bindings
	inputFrame.bind('<Return>', ff.startFileFind)
	inputFrame.bind('<Escape>', gv.grepWindow.closeTop)
	outputFrame.bind('<Escape>', gv.grepWindow.closeTop)
	gv.contextText.frame.bind('<Configure>', au.finderConfig, add=True)


def _initFindOptions():
	def initList(widget, listTag, checkTag):
		items = settings.get(listTag)
		if items is None:
			empty, parts, selections = gv.defaultSelector(widget, listTag)
		else:
			# items is list(part, list(selections))
			if len(items) > 0:
				first, _ = items[0]
				empty = first == con.NO_SELECTION
			else:
				empty = True
			cleaned = [[item, checks] for item, checks in items
						if item != con.NO_SELECTION]
			if len(cleaned) > 0:
				parts, selections = map(list, zip(*cleaned))
			else:
				parts, selections = None, None
		widget.set('' if empty or parts is None else parts[0])
		widget.setList(parts, selections)
		if parts is not None:
			# need list of list, not list of tuple for equality tests
			settings[listTag] = [list(ps) for ps in zip(parts, selections)]
		value = settings.get(checkTag, defaults.get(checkTag, '')).lower()
		widget.useAll.set(1 if value == 'all' else 0)
		widget.useChecked.set(1 if value == 'checked' else 0)
		widget.checkSelectionCount(selections=selections)

	settings = gv.CurrentOptions['History']
	defaults = con.defaultConfig['History']

	# initialize paths list
	setEntry = True
	values = settings.get('FindPaths')
	if values is not None and values[0] == con.NO_SELECTION:
		values = [value for value in values
				   if value != con.NO_SELECTION]
		settings[listTag] = values
		setEntry = False
	if values is None or len(values) == 0:
		values = _findOoliteDirs()
		setEntry = True
	gv.pathEntry.setList(values)
	if setEntry:
		gv.pathEntry.current(0)

	# initialize file types list
	# pdb.set_trace()
	initList(gv.inclEntry, 'FindTypes', 'FindIncluding')

	# initialize file exclusion list
	initList(gv.exclEntry, 'FindExcls', 'FindExcluding')

	# initialize search history
	initList(gv.textEntry, 'FindSearches', 'FindSearching')


def _closeFinder():
	ff.setFindOptions()
	gv.grepWindow.closeTop()


_targets = ['ManagedAddOns', 'oolite-saves',
			'Resources', 'Oolite', 'AddOns', 'Logs']
def _findOoliteDirs():
	# initialize search paths if empty
	# - include starting folder, target parent/children
	# - also check for Users on current drive only

	def checkFolder(curr):
		for folder in _targets:
			if 'Oolite' in curr and curr.endswith(folder) and curr not in folders:
				folders.append(curr)
				return

	def checkChildren(folder):
		for path, dirs, files in os.walk(folder):
			for each in dirs:
				if each in _targets:
					checkFolder(os.path.join(path, each))

	cwd = os.getcwd()
	folders = [cwd]
	checkChildren(cwd)
	# check parent folders
	head = cwd[:-len(os.sep)] if cwd.endswith(os.sep) else cwd
	while True:
		head, tail = os.path.split(head)
		if len(tail) == 0:
			break
		checkFolder(head)
	# check Users folder
	import getpass
	user = getpass.getuser()
	drive, _ = os.path.splitdrive(cwd)
	if drive == '':
		users = os.path.join(os.sep, 'Users', user)
	elif not drive.endswith(os.sep):
		users = os.path.join(drive, os.sep, 'Users', user)
	else:
		users = os.path.join(drive, 'Users', user)
	if os.path.exists(users):
		checkChildren(users)
	return folders


# noinspection PyUnusedLocal
def _addListItem(event, history):
	value = history.get()
	if history is gv.pathEntry:
		value = os.path.normpath(value)
		if value and not os.path.exists(value):
			_invalidPath(value)
			return 'break'
	if len(value) and not value.isspace():
		history.addEntry(value)
	return 'break'


def _invalidPath(folder):
	msg = 'Invalid or missing Search Path.\n'
	msg += folder + con.NL
	wg.OoInfoBox(gv.root, label='Invalid path', msg=msg)

def _getSearchPath(initDir=None):
	if initDir is None:
		initDir = gv.pathEntry.get()
	if len(initDir) == 0:
		inList = gv.pathEntry.getList()
		if len(inList) > 0:
			initDir = inList[0]
	if len(initDir) == 0:
		initDir = os.getcwd()
	folder = tkFileDialog.askdirectory(
				parent=gv.grepWindow, initialdir=initDir)
	if folder:
		if os.path.exists(folder):
			gv.pathEntry.addEntry(os.path.normpath(folder))
			return 'break'
	# validate existing if aborted file dialog
	curr = gv.pathEntry.get()
	folder = os.path.normpath(curr) if len(curr) > 0 else ''
	if len(folder) == 0 or not os.path.exists(folder):
		_invalidPath(folder)
	return 'break'

