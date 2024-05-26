# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import pdb
import sys

_Python2 = sys.version_info[0] == 2
if _Python2:
	import tkColorChooser
else:
	import tkinter.colorchooser as tkColorChooser

import debugGUI.globalVars as gv
import debugGUI.constants as con
import debugGUI.regularExpn as rx
import debugGUI.widgets as wg

## utility functions ##########################################################

def sameColor(c1, c2):					
	# return true if all r,g,b components are 
	# within con.COLOR_TOLERANCE
	if c1 == c2:
		return True
	if not c1.startswith('#'):
		c1 = gv.Appearance.codifyColor(c1)
	if not c2.startswith('#'):
		c2 = gv.Appearance.codifyColor(c2)
	red1, red2 = int(c1[1:3], base=16), int(c2[1:3], base=16)
	grn1, grn2 = int(c1[3:5], base=16), int(c2[3:5], base=16)
	blu1, blu2 = int(c1[5:7], base=16), int(c2[5:7], base=16)
	dRed = abs(red1 - red2)
	dGrn = abs(grn1 - grn2)
	dBlu = abs(blu1 - blu2)
	margin = con.COLOR_TOLERANCE
	if abs(red2 - grn2) <= 2 and abs(grn2 - blu2) <= 2  \
			and abs(blu2 - red2) <= 2:
		margin = 3					# for Tkinter's gray levels
	return dRed <= margin and dGrn <= margin and dBlu <= margin

def _findOoColor(color):				
	# return Oolite color str if 'color' is a close match
	oocolor = gv.Appearance.codifyColor(color)
	if oocolor:
		for k, v in con.OOCOLORS.items():
			if sameColor(v, oocolor):
				return k
	return None

def findTkColor(color):					
	# return a Tk color str if 'color' is a close match
	tkColor = gv.Appearance.codifyColor(color)
	if tkColor:
		for k, v in con.TKCOLORS.items():
			if sameColor(v, tkColor):
				return k
	return None

## menu coloring ##############################################################

def _updateMenu(menu, fg, bg, excl=None):
	font, disabled = gv.OoFonts['default'], gv.OoFonts['disabled'] 
	index = menu.index('end') + 1	# +1 as decremented at start of loop
	if index == 1: 
		return						# .index returned 0
	while index > 0:
		index -= 1
		kind = menu.type(index)
		if kind in ['separator', 'tearoff']: 
			# these have no 'label' or 'font'
			menu.entryconfigure(index, background=bg)
			continue
		label = menu.entrycget(index, 'label')
		if excl and label in excl:
			continue
		state = menu.entrycget(index, 'state')
		menuFont = font if state == 'normal' else disabled
		if kind in ['checkbutton', 'radiobutton']:
			menu.entryconfigure(index, font=menuFont, selectcolor=fg,
								background=bg, foreground=fg)
		else:	# kind in ['cascade', 'command']
			menu.entryconfigure(index, font=menuFont, 
								background=bg, foreground=fg)
		if kind != 'cascade':
			continue
		cascadeName = menu.entrycget(index, 'menu')
		cascade = menu.nametowidget(cascadeName)
		_updateMenu(cascade, fg, bg)
				
menuColorExcl = {}
def _initMenuExcl():
	# init dict of menu commands to be excluded from app color changes
	# ie. color selection menu commands
	if len(menuColorExcl) == 0:		# first call, initialize dict
		# noinspection PyProtectedMember
		menuColorExcl.update({menu._name: [] \
							for menu in gv.debugConsoleMenus})
		menuColorExcl['optionsMenu'].extend(color.lower()  \
					for color in con.defaultConfig['Colors'].keys())
	if len(gv.OoSettings):
		ooColors = list(gv.appearance.OoliteColors().keys())
		if 'ooliteMenu' not in menuColorExcl:
			menuColorExcl['ooliteMenu'] = ooColors
		else:
			menuColorExcl['ooliteMenu'].extend(oc for oc in ooColors \
								if oc not in menuColorExcl['ooliteMenu'])

def setMenuColors():			
	# no Menu in ttk; here we .entryconfigure (except color commands)
	_initMenuExcl()
	fg, bg, _ = gv.appearance.getOptionalColors('ColorMenus')
	for menu in gv.debugConsoleMenus:
		# noinspection PyProtectedMember
		_updateMenu(menu, fg, bg, excl=menuColorExcl.get(menu._name))

def setPopupColors():					
	# no Menu in ttk; here we .entryconfigure
	fg, bg, colored = gv.appearance.getOptionalColors('ColorPopups')
	for text in gv.textWidgets:
		_updateMenu(text.popup, fg, bg)
		if hasattr(text, 'hScrollbar'):
			_updateMenu(text.hScrollbar.popup, fg, bg)
		_updateMenu(text.vScrollbar.popup, fg, bg)
	_updateMenu(gv.aliasListBox.scrollbar.popup, fg, bg)

## color menu commands ########################################################
			
def _setColorMenuCmds(menu, colors, defaults): 
	# set all color selection menu commands
	# color menu commands have color as background 
	# with text in a contrasting color
	index = menu.index('end') + 1		# +1 as decremented at start of loop
	if index == 1: 
		return							# .index returned 0
	while index > 0:
		index -= 1
		# types: 'cascade', 'checkbutton', 'command', 
		# 		'radiobutton', 'separator', 'tearoff'
		if menu.type(index) != 'command':
			continue
		label = menu.entrycget(index, 'label')
		color = colors.get(label, defaults.get(label))
		if color is not None:
			bg = gv.Appearance.codifyColor(color)
			fg = gv.Appearance.contrastColor(bg, color)
			menu.entryconfigure(index, foreground=fg, background=bg)
		
def _setOptionsColorCmds():				
	# set colors for 'Options' menu color picking commands
	colors = gv.CurrentOptions['Colors']
	defaults = con.defaultConfig['Colors']
	_setColorMenuCmds(gv.optionsMenu, colors, defaults)

def setOoliteColorCmds():
	if gv.ooliteMenu is None:	# not connected
		return
	# set colors for 'Oolite plist' menu color picking commands
	colors = gv.appearance.OoliteColors()
	if colors and len(colors):			# have connected at least once
		_setColorMenuCmds(gv.ooliteMenu, colors, colors)

def _setColoredCmd(menu, label, color):	
	# set color in a color selection menu command (user driven)
	# color menu commands have color as background with
	# text in a contrasting color
	bg = gv.Appearance.codifyColor(color)
	fg = gv.Appearance.contrastColor(bg, color)
	index = menu.index('end') + 1		
	# +1 as decremented at start of loop
	if index == 1: 
		return							# .index returned 0
	while index > 0:
		index -= 1
		if menu.type(index) == 'command' \
				and menu.entrycget(index, 'label') == label:
			menu.entryconfigure(index, foreground=fg, background=bg)
			break

## app specific functions #####################################################

def updateAppColors():	
	# update all colors in application
	_setOptionsColorCmds()
	setOoliteColorCmds()
	_setAllTextColors()
	_setListboxColors()
	_setSpinboxColors()

def _setAllTextColors():				
	# no Text in ttk; here we .config & .tag_config all
	if gv.appearance.usingOoColors():
		colors = gv.appearance.OoliteColors()
		colorFn = setMsgColor
		# include selection colors
		selects = {tag: color for tag, color
					  in gv.CurrentOptions['Colors'].items()
					  if tag.startswith('select')}
		for key, color in selects.items():
			_setTextTagsColors(key, color)
	else:
		colors = gv.CurrentOptions['Colors']
		colorFn = _setTextTagsColors
	for key, color in colors.items():
		if key.count('-') > 2:		# skip message specific colors
			continue
		colorFn(key, color)

def _setListboxColors():				
	#  no Listbox in ttk; here we set colors
	fg, bg = gv.appearance.getCurrentFgBg()
	sFg, sBg = gv.appearance.getSelectFgBg()
	font = gv.OoFonts['default']
	kws = {'font': font, 'background': bg, 'foreground': fg,
		   'selectbackground': sBg, 'selectforeground': sFg}
	listboxes = gv.aliasListBoxes[:]
	listboxes.extend([gv.fontSelectListBox, gv.filesList])
	for box in listboxes:
		box.config(**kws)
	for box in wg.OoCombobox.instances:
		box.pdList.config(**kws)
		for check in box.checkboxes:
			check.config(**kws)

def _setSpinboxColors():				
	#  no Spinbox in ttk; here we set all its colors
	fg, bg = gv.appearance.getCurrentFgBg()
	sFg, sBg = gv.appearance.getSelectFgBg()
	font = gv.OoFonts['default']
	widgets = [gv.contextNumBtn]
	if hasattr(wg.OoInfoBox, 'msgBoxSpinbox'):
		widgets.append(wg.OoInfoBox.msgBoxSpinbox)
	for widget in widgets:
		widget.config(font=font,
					foreground=fg, background=bg,
					selectforeground=sFg, selectbackground=sBg,
					buttonbackground=bg,
					readonlybackground=bg,
					insertbackground=fg)
	
## user specified colors ######################################################

def pickLocalColor(key):				
	# use tkColorChooser to set a local debug console color
	color = gv.CurrentOptions['Colors'].get(key,
					con.defaultConfig['Colors'][key.capitalize()])
	color = gv.Appearance.codifyColor(color)
	# askcolor returns color as a 3-tuple with
	# floats from 0 to 255.99609375 and as
	# a string '#0088ff' (ie. hex doublets)
	newColor, newCStr = tkColorChooser.askcolor(color=color,
								parent=gv.root, title=key)
	if newColor is None or sameColor(color, newCStr):
		return
	gv.CurrentOptions['Colors'][key] = findTkColor(newCStr) or newCStr
	gv.appearance.updateApp()		

def _setTextTagsColors(key, value):		
	# apply local color to app widgets
	color = gv.Appearance.codifyColor(value)
	# assign local colors for foreground, background, 
	# cmdLine & alias widget
	if key == 'general-foreground':
		for text in gv.textWidgets:
			if text is gv.cmdLine:	# its colors unique to debug console
				continue
			text.config(foreground=color,
							insertbackground=color) # cursor color
			text.tag_config('general-foreground', 
								foreground=color)
	elif key == 'general-background':
		for text in gv.textWidgets:
			if text is gv.cmdLine:	# its colors unique to debug console
				continue
			text.config(background=color)
			text.tag_config('general-foreground', 
								background=color)
	elif key == 'command-foreground':
		gv.cmdLine.config(foreground=color,
							insertbackground=color) # cursor color
		gv.bodyText.tag_config('command', 
								foreground=color)
	elif key == 'command-background':
		gv.cmdLine.config(background=color)
		gv.bodyText.tag_config('command', 
								background=color)
	elif key == 'select-foreground':
		for text in gv.textWidgets:
			text.config(selectforeground=color)
			text.tag_config('sel', foreground=color)
			if text is gv.contextText:
				text.tag_config('fileSearch', foreground=color)
	elif key == 'select-background':
		for text in gv.textWidgets:
			text.config(selectbackground=color, 
						inactiveselectbackground=color)
			text.tag_config('sel', background=color)
			if text is gv.contextText:
				text.tag_config('fileSearch', background=color)

def pickMsgColor(key):					
	# use tkColorChooser to set an Oolite color
	# (OoSettings' colors are codifyColor'd)
	cvalue = gv.OoSettings[key]		
	# askcolor returns color as a 3-tuple with
	# floats from 0 to 255.99609375 and as
	# a string '#0088ff' (ie. hex doublets)
	newColor, newCStr = tkColorChooser.askcolor(color=cvalue,
								parent=gv.root, title=key)
	if newColor is None or sameColor(cvalue, newCStr):
		return
	ooColor = _findOoColor(newCStr)
	if ooColor is None:
		newRGB = list(map(int, newColor))
		newRGB.append(255) 				# alpha
		finalColor = newRGB
	else:
		finalColor = ooColor
	# menu cmd's color is set upon ack from oolite in noteConfig()
	# which in turn calls applyMsgColor()
	gv.app.client.setConfigurationValue(key, finalColor)

def applyMsgColor(key, value): 			
	# apply new Oolite color to app widgets
	gv.OoSettings[key] = value 
	setMsgColor(key, value)
	if len(gv.ooliteColors) > 0:		
		# not finished processing Oolite colors from connection dict
		return
	if gv.appearance.usingOoColors():		
		gv.appearance.updateApp()		

_colorMatches = {}	# regex matches performed on OoSettings 
def parseOoColorKey(key):				
	# parse color string and memoize result
	colParse = _colorMatches.get(key)
	if colParse:
		return colParse
	match = rx.OOLITE_COLOR_RE.match(key)
	if match:
		colParse = {'isa_ooColor': match['isa_ooColor'],
					'isa_dcColor': match['isa_dcColor'],
					'key': match['key'], 
					'plane': match['plane']}
		_colorMatches[key] = colParse
		return colParse

def setMsgColor(key, color, skipUpdate=False): 
	# apply Oolite color to app widgets
	# 'color' is codifyColor'd by caller
	# skipUpdate is for connection setup, so we don't 
	# call _setTextTagsColors twice
	usingOoColors = gv.appearance.usingOoColors()
	if hasattr(gv.app, 'ooliteMenu') and not usingOoColors:
		# ooliteMenu is destroyed when connection ends but this fn 
		# may still be called if user toggles oolite plist option
		# when usingOoColors, updateApp() (via updateAppColors) 
		# will set all menu commands
		_setColoredCmd(gv.ooliteMenu, key, color)
		
	match = parseOoColorKey(key)
	if not match:
		return
	keyClass, plane = match['key'], match['plane']
	override = match['isa_dcColor'] or usingOoColors
	setTags = override \
			or keyClass in ['error', 'exception', 'warning']
	if setTags and plane == 'foreground':
		gv.bodyText.tag_config(keyClass, foreground=color)
	elif setTags and plane == 'background':
		gv.bodyText.tag_config(keyClass, background=color)
	if not override or skipUpdate:
		return
	if match['isa_dcColor']:			# it's not a msg specific color
		if keyClass in ['general', 'command']:
			_setTextTagsColors(keyClass + '-' + match['plane'], color)

## color support colorPrint() #################################################

def setColorKey(key): 					
	# return key or None for Text output
	if key == 'dumpObject':
		# bug in oolite-debug-console.js, function dumpObject()
		key = 'general-foreground' 		
	elif key == 'debugger':
		key = 'general-foreground' 		# msg from debugger
	key = key.lower() if key else 'general-foreground'
	if key == 'macro-expansion' \
			and gv.localOptnVars['MacroExpansion'].get() == 0:
		return None						# suppress print
	elif key == 'log':
		if gv.debugOptions['showLog'].get() > 0:
			colorKeys = gv.CurrentOptions['Colors'].keys()
			key = 'general-foreground' \
					if key not in colorKeys else key
		else:
			return None					# suppress print
	return key

# local colors use: 
# 	'general-foreground' in place of 'general',
#	'command-foreground' in place of 'command' & 'command-result'
# - 2 'select' colors are debug console only and always used
# when 'PlistOverrides', use OoSettings colors if possible
def setColorTag(key): 					
	# return appropriate tag for 'key' to output to Text
	if not gv.appearance.usingOoColors():
		if key in ['general', 'command', 'select']:
			return key + '-foreground'
		if key == 'command-result':
			return 'command-foreground'
	# always use plist colors for Oolite messages, 
	# regardless of PlistOverrides
	if key + '-foreground-color' in gv.OoSettings:
		return key
	if key + '-background-color' in gv.OoSettings:
		return key
	# fall-back color if no match found
	return 'general-foreground'			

