# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys
import pdb, traceback

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import ttk
else:
	import tkinter as tk
	import tkinter.ttk as ttk

import debugGUI.globalVars as gv
import debugGUI.bitmaps as bm
import debugGUI.constants as con
import debugGUI.miscUtils as mu
import debugGUI.widgets as wg

OoStyle = None
def initStyle():
	# static elements (ie. not user configurable)
	global OoStyle

	font = gv.OoFonts['default']
	tipFont = gv.OoFonts['tipFont']
	# set default style
	OoStyle = ttk.Style()
	OoStyle.theme_use('default')
	# apply to ttk widgets
	OoStyle.configure('.', insertwidth=con.CURSOR_WIDTH)

	# standard Menubutton w/ indicator removed
	OoStyle.layout('OoBarMenu.TMenubutton', [
		('Menubutton.border', {'children': [
			('Menubutton.focus', {'children': [
				('Menubutton.padding', {'children': [
					('Menubutton.label', {'sticky': ''})],
						# 'side': 'left', ## cannot set 'side': '' ... boom!
				'expand': '1', 'sticky': 'we'})],
			'sticky': 'news'})],
		'sticky': 'news'})])
	OoStyle.configure('OoBarMenu.TMenubutton', relief='flat', font=font)
	OoStyle.map('OoBarMenu.TMenubutton', relief=[('active', 'groove'), ],)

	# bigger scroll bar elements
	OoStyle.configure('Vertical.TScrollbar', arrowsize=con.SCROLL_WIDTH)
	OoStyle.configure('Horizontal.TScrollbar', arrowsize=con.SCROLL_HEIGHT)

	# as different themes have different options, the safe (theme independent)
	# approach of creating new OoStyle elements is used
	
	# .configure sets default, .map sets states that change default
	# - static ones here, dynamic ones in updateOoStyle
	# eg. TButton's relief is static, so it is set here
	#     while its foreground is user configurable, except when disabled (gray)
	#     and its background is always user configurable, so not here at all
	
	btnRelief = {'default': 'groove', 
				 'states':	[('disabled', 'flat'), 
							('pressed', 'sunken'), 
							('active', 'raised')]}

	OoStyle.configure('TButton', borderwidth=2, focusthickness=2,
					  font=font, relief=btnRelief['default'])
	OoStyle.map('TButton', relief=btnRelief['states'])

	OoStyle.configure('TCheckbutton', font=font, focusthickness=2,
					  justify='left', relief=btnRelief['default'])
	OoStyle.map('TCheckbutton', relief=btnRelief['states'])

	OoStyle.configure('TRadiobutton', font=font, borderwidth=2, justify='left')

	# ensure no extra pixels
	OoStyle.configure('TFrame', borderwidth=0, relief='flat')

	OoStyle.configure('TLabel', relief='flat')

	OoStyle.configure('toolTip.TButton', font=tipFont, borderwidth=2)
	OoStyle.configure('toolTip.TLabel', borderwidth=2, relief='groove',
										justify='left')

	# OoCombobox
	OoStyle.configure('TEntry', relief='ridge')

	# standard Checkbutton w/ custom indicator
	OoStyle.element_create('customCheck.indicator', 'image',
						   gv.OoBitmaps['checkedBoxBitMap'],
						   ('!selected', gv.OoBitmaps['unCheckedBoxBitMap']))
	OoStyle.layout('custom.TCheckbutton', [
		('Checkbutton.padding', {'children': [
			('customCheck.indicator', {'side': 'left', 'sticky': 'w'}),
			('Checkbutton.focus', {'children': [
				('Checkbutton.label', {'sticky': 'news'})],
			 'side': 'left', 'sticky': 'w'})],
		'sticky': 'news'})])
	OoStyle.configure('custom.TCheckbutton', anchor='w')

	# standard Checkbutton w/ indicator removed for custom bitmap
	# history arrow to toggle listbox
	OoStyle.layout('history.TCheckbutton', [
		('Checkbutton.padding', {'children': [
			('Checkbutton.focus', {'children': [
				('Checkbutton.label', {'sticky': 'news'})],
			 'side': 'left', 'sticky': 'w'})],
		 'sticky': 'news'})])
	OoStyle.configure('history.TCheckbutton', anchor='e',
					  image=gv.OoBitmaps['historyOpenBitMap'])

	# aliases #################################################################

	# OoStyle.configure('aliasList.TFrame', borderwidth=2, relief='groove')

	# surround alias value label
	OoStyle.configure('alias.TLabel', relief='ridge')

	# search box ##############################################################

	# search box direction arrows
	# NB: replacing .indicator, removes options 'borderwidth', etc.
	OoStyle.element_create('searchUp.indicator', 'image',
						   gv.OoBitmaps['searchUpBitMap'],
						   ('pressed', '!disabled', gv.OoBitmaps['searchUpPressed']))
	OoStyle.layout('searchUp.TRadiobutton',
				   [('Radiobutton.padding', {'children': [
					   ('Radiobutton.focus', {'children': [
						   ('searchUp.indicator', {'side': 'left', 'sticky': ''}),
					   ], 'sticky': 'news'}),
				   ], 'sticky': 'news'})])

	OoStyle.element_create('searchDown.indicator', 'image',
						   gv.OoBitmaps['searchDownBitMap'],
						   ('pressed', '!disabled', gv.OoBitmaps['searchDownPressed']))
	OoStyle.layout('searchDown.TRadiobutton',
				   [('Radiobutton.padding', {'children': [
					   ('Radiobutton.focus', {'children': [
						   ('searchDown.indicator', {'side': 'left', 'sticky': ''}),
							], 'sticky': 'news'}),
						], 'sticky': 'news'})])

	# Finder ##################################################################

	# standard Radiobutton w/ indicator removed
	OoStyle.layout('grep.TRadiobutton', [
		('Radiobutton.padding', {'children': [
			# ('Radiobutton.indicator', {'side': 'left', 'sticky': ''})],
			# - removal also removes borderwidth option; would have to revert
			#   to tk's Radiobutton which supports 'indicatoron' option
			('Radiobutton.focus', {'children': [
				('Radiobutton.label', {'sticky': 'news'})],
			'side': 'left', 'sticky': ''})],
		'sticky': 'news'})])	
	OoStyle.configure('grep.TRadiobutton',
					image=gv.OoBitmaps['radioButtonOffBitMap'])
	OoStyle.map('grep.TRadiobutton',
					image=[('selected', gv.OoBitmaps['radioButtonOnBitMap'])])

	# standard Checkbutton w/ indicator removed for custom bitmap
	# for Finder's path button, image static
	OoStyle.layout('pathButton.TCheckbutton', [
		('Checkbutton.padding', {'children': [
			('Checkbutton.focus', {'children': [
				('Checkbutton.label', {'sticky': 'news'})],
			 'side': 'left', 'sticky': 'w'})],
		 'sticky': 'news'})])
	OoStyle.configure('pathButton.TCheckbutton', anchor='e',
					  image=gv.OoBitmaps['grepFolderBitMap'])

	# for debugging grid
	OoStyle.configure('red.TFrame', background='red')
	OoStyle.configure('blue.TFrame', background='blue')
	OoStyle.configure('green.TFrame', background='green')
	OoStyle.configure('yellow.TFrame', background='yellow')
	OoStyle.configure('cyan.TFrame', background='cyan')
	OoStyle.configure('magenta.TFrame', background='magenta')

	return OoStyle	# convenience return for buildGUI()
	
# ttk states: active, alternate, background, disabled, focus, invalid, pressed, readonly, selected

# If you want to define a new type of widget (or a variation of an existing
# widget) for your application, you'll need to do it separately and differently 
# for each theme your application uses 
# (i.e., at least three for a cross-platform application).

def updateStyle():
	try:
		# set option database
		fg, bg, sFg, sBg = gv.appearance.updateTkOptionDb()
		# apply to ttk widgets
		OoStyle.configure('.', background=bg, foreground=fg,
							   fieldbackground=bg, insertcolor=fg,
							   selectbackground=sBg, selectforeground=sFg)

		# colored frame to show through using padx, pady on children
		OoStyle.configure('ComboboxPopdownFrame', background=fg)
		OoStyle.configure('selector.TFrame', background=fg)

		# prevent default system color when nothing to scroll
		OoStyle.configure('Vertical.TScrollbar', background=bg, foreground=fg)
		OoStyle.map('Vertical.TScrollbar', background=[('disabled', bg), ],
										   foreground=[('disabled', fg), ])
		OoStyle.configure('Horizontal.TScrollbar', background=bg, foreground=fg)
		OoStyle.map('Horizontal.TScrollbar', background=[('disabled', bg), ],
											 foreground=[('disabled', fg), ])

		# prevent color change when pressed
		for style in ['TMenubutton', 'TRadiobutton',]:
			OoStyle.map(style, background=[('!disabled', bg)],
							   foreground=[('!disabled', fg)])

		for style in ['TButton', 'custom.TCheckbutton', 'history.TCheckbutton',
					  'searchDown.TRadiobutton', 'searchUp.TRadiobutton']:
			OoStyle.configure(style, focuscolor=fg)
			# for system independence ...
			OoStyle.map(style,
						foreground = [('disabled', fg),
									  ('pressed', fg),
									  ('active', fg)],
						background = [('disabled', bg),
									  ('pressed', '!focus', bg),
									  ('active', bg)],
						indicatorcolor = [('selected', bg),
										  ('pressed', bg)])

		# custom TEntry to color fieldbackground
		OoStyle.configure('TEntry', fieldbackground=bg)

	except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()
