# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys
from collections import OrderedDict

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import tkFont
else:
	import tkinter as tk
	import tkinter.font as tkFont

import debugGUI.aliases as al
import debugGUI.appUtils as au
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.widgets as wg

_FONT_SELECT_LABEL = 'Explore all 8 Galaxy Charts!'

_fontMenuStrs = {'face':	'Family (font-face) ...',
				'size':		'Size (font-size)',
				'weight':	'Font Weight',
				'slant':	'Font Slant',
				'disabled':	'Font disabled'}

def makeFonts():
	fonts = gv.CurrentOptions['Font']
	defFont = con.defaultConfig['Font']

	default = tkFont.Font(name=mu.TkName('defaultFont'),
			family=fonts.get('Family', defFont.get('Family', 'Arial')),
			size=fonts.get('Size',	   defFont.get('Size',   '10')),
			weight=fonts.get('Weight', defFont.get('Weight', 'normal')),
			slant=fonts.get('Slant',   defFont.get('Slant',  'roman')))
	gv.OoFonts['default'] = default
	
	emphasis = tkFont.Font(name=mu.TkName('emphasisFont'),
									**default.actual())
	gv.OoFonts['emphasis'] = emphasis
	
	searchMark = tkFont.Font(name=mu.TkName('searchMarkFont'),
									**default.actual())
	gv.OoFonts['searchMark'] = searchMark
	
	if fonts['Weight'] == 'normal':
		emphasis.configure(weight='bold')
		searchMark.configure(underline=1, weight='bold')
	elif fonts['Slant'] == 'roman':
		emphasis.configure(slant='italic')
		searchMark.configure(underline=1, slant='italic')
	else:
		emphasis.configure(size=fonts['Size']+2)
		searchMark.configure(underline=1, size=fonts['Size']+2)
		
	disabled = tkFont.Font(name=mu.TkName('disabledFont'), 
							**default.actual())
	gv.OoFonts['disabled'] = disabled
	if fonts.get('disabled', defFont.get('disabled', 'normal')) \
			== 'overstrike':
		disabled.configure(overstrike=1)

	tipFont = tkFont.Font(name=mu.TkName('tipFont'),
						   **default.actual())
	mu.tooltipFontSize(tipFont, default.cget('size'))
	gv.OoFonts['tipFont'] = tipFont

	gv.genCharMeasures()
	# register fonts (used to calculate menu button widths)
	gv.Alias.registerFonts(default, disabled)

_fontTkVars = {}	# dict of tkinter vars for fonts
def createFontMenus(): 				
	# create a Font pull down menu
	font = gv.OoFonts['default']
	options = gv.CurrentOptions['Font']
	fontMenu = wg.OoBarMenu(gv.menuFrame, label='Font',
							font=font, name=mu.TkName('fontMenu'),
							style='OoBarMenu.TMenubutton', 
							postcommand=au.closeAnyOpenFrames)
	gv.fontMenu = fontMenu
	gv.debugConsoleMenus.append(fontMenu)

	# create font ListBox
	fontMenu.add_command(label=_fontMenuStrs['face'], 
						command=_selectFont)
	_createFontSelectBox()

	# create font size submenu
	_fontTkVars['font-size'] = tk.IntVar(value=options['Size'], 
										name=mu.TkName('fontSize'))
	fsizeMenu = tk.Menu(fontMenu, tearoff=0, name=mu.TkName('sizeMenu'))
	for size in range(con.MIN_FONT_SIZE, con.MAX_FONT_SIZE + 1):
		fsizeMenu.add_radiobutton(label=str(size), 
					variable=_fontTkVars['font-size'],
					value=size, font=font,
					command=lambda s=size: setFontSize(s))

	fontMenu.add_cascade(label=_fontMenuStrs['size'],
						menu=fsizeMenu, **gv.CASCADE_KWS)
	fontMenu.add_separator()

	# create font weight submenu
	_fontTkVars['Weight'] = tk.StringVar(value=options['Weight'], 
										name=mu.TkName('fontWeight'))
	weightMenu = tk.Menu(fontMenu, tearoff=0, 
						name=mu.TkName('weightMenu'))
	weightMenu.add_radiobutton(label='Normal', 
								variable=_fontTkVars['Weight'],
								value='normal', font=font, 
								command=_setFontWeight)
	weightMenu.add_radiobutton(label='Bold', 
								variable=_fontTkVars['Weight'],
								value='bold', font=font, 
								command=_setFontWeight)
	fontMenu.add_cascade(label=_fontMenuStrs['weight'],
						menu=weightMenu, **gv.CASCADE_KWS)

	# create font slant submenu
	_fontTkVars['Slant'] = tk.StringVar(value=options['Slant'], 
										name=mu.TkName('fontSlant'))
	slantMenu = tk.Menu(fontMenu, tearoff=0, 
						name=mu.TkName('slantMenu'))
	slantMenu.add_radiobutton(label='Roman', 
								variable=_fontTkVars['Slant'],
								value='roman', font=font, 
								command=_setFontSlant)
	slantMenu.add_radiobutton(label='Italic', 
								variable=_fontTkVars['Slant'],
								value='italic', font=font, 
								command=_setFontSlant)
	fontMenu.add_cascade(label=_fontMenuStrs['slant'],
						menu=slantMenu, **gv.CASCADE_KWS)
	fontMenu.add_separator()

	# create font disabled submenu
	_fontTkVars['disabled'] = tk.StringVar(value=options['disabled'], 
										name=mu.TkName('fontDisabled'))
	disabledMenu = tk.Menu(fontMenu, tearoff=0, 
							name=mu.TkName('disabledMenu'))
	disabledMenu.add_radiobutton(label='Normal', 
								variable=_fontTkVars['disabled'],
								value='normal', font=font, 
								command=_setFontDisabled)
	disabledMenu.add_radiobutton(label='Overstrike', 
								variable=_fontTkVars['disabled'],
								value='overstrike', font=font, 
								command=_setFontDisabled)
	fontMenu.add_cascade(label=_fontMenuStrs['disabled'],
						menu=disabledMenu, **gv.CASCADE_KWS)

_fontList = []		# contents of the font select ListBox
def isAvailableFont(font):
	return font in _fontList

def _createFontSelectBox(): 			
	# mk list of fonts, load into ListBox
	families = tkFont.families()
	for item in families:
		if 'dings' in item: continue
		if item.startswith('Marlett'): continue
		_fontList.append(item)
	maxWidth = au.largestMeasure(_fontList)
	maxWidth //= gv.zeroLen
	_fontList.sort(key=str.lower)
	maxHeight = len(_fontList)
	
	fontSelect = wg.TopWindow(gv.root, title='Select Font', 
								name=mu.TkName('fontSelect'),
								enduring=True, showNow=False)
	gv.fontSelect = fontSelect
	fontSelect.bind('<Escape>', fontSelect.closeTop)
	
	fontBox = wg.ScrollingListBox(fontSelect.twFrame, gv.OoFonts['disabled'],
								  label=_FONT_SELECT_LABEL,
								  name=mu.TkName('fontSelectListBox'),
								  width=20 if maxWidth == 0 else maxWidth,
								  height=20 if maxHeight > 20 else maxHeight,)
	gv.fontSelectListBox = fontBox
	fontBox.restoreBox(sticky='news')
	
	fontBox.insert('end', *_fontList)
	fontBox.bind('<<ListboxSelect>>', _showFontFace)
	fontBox.bind('<Return>', _fontSelected)
	fontBox.bind('<Double-ButtonRelease-1>', _fontSelected)
	
def _selectFont():						
	# open font selection box, set current font to inverse color
	if gv.appearance.usingOoColors():
		currFont = gv.OoSettings.get('font-face', 'Arial')
	else:
		currFont = gv.CurrentOptions['Font'].get('Family', 'Arial')
	select = None
	if isAvailableFont(currFont):
		select = _fontList.index(currFont)
	else:
		actual = gv.OoFonts['default'].actual('family')
		if isAvailableFont(actual):
			select = _fontList.index(actual)
			
	fontBox, fontSelect = gv.fontSelectListBox, gv.fontSelect
	fontBox.delete(0, 'end')	# undo color inversion
	fontBox.insert('end', *_fontList)
	if select is not None:				
		# invert color of currently active font
		fg, bg = gv.appearance.getCurrentFgBg()
		fontBox.itemconfig(select, foreground=bg, background=fg)
		fontBox.see(select)

	if fontSelect.mouseXY is None:
		fontSelect.showAtMouse(fontBox.winfo_pointerxy())
	else:
		fontSelect.restoreTop()
	fontBox.focus_set()

# noinspection PyUnusedLocal
def _fontSelected(event=None):
	# apply selected font, close dialog
	currSelection = gv.fontSelectListBox.curselection() 
	# - returns tuple w/ indices of the selected element(s)
	if len(currSelection) > 0:
		setFontFace(_fontList[currSelection[0]])
		gv.fontSelect.closeTop()
	return 'break'	# so default event handlers don't fire

# noinspection PyUnusedLocal
def _showFontFace(event=None):
	# re-write Label in current font
	selection = gv.fontSelectListBox.curselection()
	if len(selection) > 0:
		_updateFontBox(selection[0])

def _updateFontBox(index):
	fontBox = gv.fontSelectListBox
	if -1 < index < fontBox.size():
		size = gv.CurrentOptions['Font'].get('Size', 10)
		fontBox.label.config(font=(_fontList[index], size))
		fontBox.selection_clear(0, 'end')
		fontBox.selection_set(index)
		fontBox.see(index)

def _configFonts(key, value):
	for name, font in gv.OoFonts.items():
		if name == 'tipFont' and key == 'size':
			mu.tooltipFontSize(font, value)
		else:
			# font._call('font', 'config', font.name, '-'+key, value)
			font.config(**{key: value})
		
def setFontFace(face, send=True, skipUpdate=False):
	if isAvailableFont(face):
		if gv.appearance.usingOoColors():
			if send:
				# send is only False when loading settings dict
				gv.app.setClientSetting('font-face', face)
				# - gv.OoSettings is set in noteConfig,  ie. upon confirmation
		else:
			gv.CurrentOptions['Font']['Family'] = face
		useFontFace(face, skipUpdate)
		
def useFontFace(face, skipUpdate=False):
	if isAvailableFont(face):
		_configFonts('family', face)
		_updateFontBox(_fontList.index(face))
		if not skipUpdate:
			# avoids back to back calls
			# (see om._setOptionFromCheckButton)
			_updateAppsFontChange()

def setFontSize(size, send=True):
	if gv.appearance.usingOoColors():
		if send:
			# send is only False when loading settings dict
			gv.app.setClientSetting('font-size', size)
			# - gv.OoSettings is set in noteConfig, ie. upon confirmation
	else:
		gv.CurrentOptions['Font']['Size'] = size
	useFontSize(size)
		  
def useFontSize(size):
	_configFonts('size', size if isinstance(size, int) else int(size))
	# reflect change in menu radiobutton
	_fontTkVars['font-size'].set(size)
	_updateAppsFontChange()

def _setFontWeight():
	# this font option is local only, not stored in Oolite's .GNUstepDefaults
	weight = _fontTkVars['Weight'].get()
	gv.CurrentOptions['Font']['Weight'] = weight
	_configFonts('weight', weight)
	_updateAppsFontChange()

def _setFontSlant():
	# this font option is local only, not stored in Oolite's .GNUstepDefaults
	slant = _fontTkVars['Slant'].get()
	gv.CurrentOptions['Font']['Slant'] = slant
	_configFonts('slant', slant)

def _setFontDisabled():
	# this font option is local only, not stored in Oolite's .GNUstepDefaults
	disabled = _fontTkVars['disabled'].get()
	gv.CurrentOptions['Font']['disabled'] = disabled
	gv.OoFonts['disabled'].config(overstrike=0 \
						if disabled == 'normal' else 1)

def _updateAppsFontChange():			
	# update cmdLine buttons, sash, menus after a font size change

	# recompute length of special characters (must do before update_idletasks
	# call as some event handlers rely on them)
	gv.genCharMeasures()

	# there may be '<Configure>' events pending or generated below, so preserve
	# the current (correct) sash positions and update on exit
	sashPositions = gv.sashPosns.copy()

	al.gridMenuButtons()
	runWidth = gv.btnRun.winfo_reqwidth()
	clrWidth = gv.btnCmdClr.winfo_reqwidth()
	gv.btnRun.grid(ipadx=(clrWidth - runWidth)//2)

	gv.screenLines = None		# recompute height of screen lines
	gv.measuredWords.clear()	# clear cached measurements
	gv.measuredEWords.clear()	#   "
	gv.aliasValueWidth = None

	gv.sashPosns.update(sashPositions)
	au.positionAliasSash()
	au.positionFindSash()
	settings = gv.CurrentOptions['Settings']
	if settings.get('ResetCmdSizeOnRun', False):
		au.positionAppSash()


