# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
from __future__ import division
import sys
from collections import OrderedDict

# try:
	# from sys import frozen
	# FROZEN = True
# except:
	# FROZEN = False
FROZEN = hasattr(sys, 'frozen')	## cannot test until build exe
IS_WINDOWS_PC = sys.platform.startswith('win')
IS_LINUX_PC = sys.platform.startswith('linux')
IS_MACOS_PC = sys.platform.startswith('darwin')

# Tkinter
MINIMUM_WIDTH = 800
MINIMUM_HEIGHT = 600
CURSOR_WIDTH = 4
SCROLL_WIDTH = 20
SCROLL_HEIGHT = 20

ENTRY_OPTIONS = {'exportselection': 0}
CHECKBUTTON_OPTIONS = {'compound': 'left', 'style': 'custom.TCheckbutton'}
LISTBOX_OPTIONS = {
	'borderwidth': 0, 'relief': 'flat', 'highlightthickness': 0,
	'activestyle': 'dotbox', 'selectmode': 'single', 'exportselection': 0
}

DEFAULT_MENU_COLOR = 'black'
DEFAULT_MENU_BACKGND = 'ivory2'
DEFAULT_WIDGET_COLOR = 'black'
DEFAULT_WIDGET_BACKGND = 'gray86'
DEFAULT_WIDGET_DISABLED = 'gray36'

DEFAULT_GEOMETRY = '{}x{}+0+0'.format(MINIMUM_WIDTH, MINIMUM_HEIGHT)
DEFAULT_ALIAS_GEOMETRY = '{}x{}+30+30'.format(MINIMUM_WIDTH - 60, 
											int(MINIMUM_HEIGHT*2/3))
DEFAULT_FINDER_GEOMETRY = '{}x{}+30+30'.format(MINIMUM_WIDTH - 60, 
											int(MINIMUM_HEIGHT))
SESSION_SIGNATURE = '$debugConsoleSessionStarted'

# app messages
Python2 = sys.version_info[0] == 2
DEBUGGER_TITLE = 'Oolite - Javascript Debug Console ({})'.format(
				'executable' if FROZEN else 'Python2' if Python2 else 'Python3')
CONNECTMSG = "Please (re)start Oolite in order to connect."

# files
BASE_FNAME = 'DebugConsole'
CFG_EXT = '.cfg'
HIST_EXT = '.dat'
LOG_EXT = '.log'
HISTFILE = BASE_FNAME + HIST_EXT
LOGFILE = BASE_FNAME + LOG_EXT
MAX_HIST_VERSION = 5
MAX_CFG_VERSION = 5
MAX_LOG_VERSION = 5
MAX_HIST_CMDS = 200
MAX_HIST_SIZE = MAX_HIST_CMDS * 1000
# if we're using the compiled version, it's OoDebugConsole.cfg 
# rather than DebugConsole.cfg
if FROZEN: BASE_FNAME = 'Oo' + BASE_FNAME
CFGFILE = BASE_FNAME + CFG_EXT

# file find
PATH_STRIP_CHARS = ' \'"'
CHECKED = 'X'
UNCHECKED = ' '
NO_SELECTION = '<empty>'
DEFAULT_INCL = ('*.js', '*.plist', '*.txt', '*.js, *.zip',
				'*.js, *.plist', '*.js, *.txt', '*.plist, *.txt'
				'*.js; *.plist; *.txt')
DEFAULT_EXCL = ('*.dat; *.fragment, *.vertex', '.mtl .obj',
				'Oolite_Readme.txt', 'oolite.app/', '*.oolite-save',
				'*.pdf *.rtf', 'Resources/', '.zip',)

# config file
CFG_TAB_LENGTH = 4

# times in seconds
CMD_TIMEOUT = 2			# elapsed time before sending next in queue 
						#   (current msg is in timedOutcommands)
CMD_TIMEOUT_LONG = 4	# elapsed except for a couple long running commands
CMD_TIMEOUT_ABORT = 10	#    "  when cmd is abandoned as data considered stale

# aliases
MIN_ALIAS_CHAR = 5		# min. width for alias selection listbox
MAX_UNDOS = 100			# max. size of undo stack
ALIAS_PANED = 'tk' 	# 'tk' or 'ttk', undecided
NL = '\n'
NO_BREAK_WS = '\t '
WHITESPACE = '\t\n '
ELLIPSIS = ' ...'
QUOTES = '''"'`'''
ALIAS_TOOLTIP = 'tooltip:'
ALIASINMENUTEXT = {			# Checkbutton data for aliasAsButton
	True:  dict(text='is in menubar',	image='aliasMenuBtnSay'),
	False: dict(text='add to menubar',	image='aliasMenuBtnAsk')
}
ALIASPOLLINGTEXT = {
	None: 	  dict(text='polling not set',	image='aliasPollingNotSet'),
	False: 	  dict(text='is not polled',	image='aliasNotPolled'),
	'halted': dict(text='polling halted',	image='aliasPollHalted'),
	True: 	  dict(text='being polled',		image='aliasIsPolled'),
}

# padding for right justifying, abandoned; see fontPadded()
UNI_WHITESPACE = OrderedDict((				# in Verdana 12
	('EM SPACE', 			'\u2003',),		# measures 16
	('EN SPACE', 			'\u2002',),		# measures 8
	('FOUR-PER-EM SPACE',	'\u2005',),		# measures 4
	('THIN SPACE', 			'\u2009',),		# measures 2
	('HAIR SPACE', 			'\u200a',),		# measures 1
))

# alias comments
CONTEXT_RADIUS = 20

# characters added by JS .toString
JS_OPENERS = '[{(' # assumed to be in matching order! for JS_OPENER_PAIRS
JS_CLOSERS = ']})' # - regex require brackets be first
JS_ENCLOSERS = JS_CLOSERS + JS_OPENERS
JS_ENCLOSING = {'[':']', ']':'[', '{':'}', '}':'{', '(':')', ')':'('}
PARENTHESES = ['{', '}']
# NB: closers must precede openers in a regex character set
JS_ADDED_NOT_WS = JS_ENCLOSERS + ';'
JS_ADDED_CHARS = JS_ADDED_NOT_WS + WHITESPACE
JS_ADDED_NO_NL = JS_ADDED_NOT_WS + NO_BREAK_WS

# line number in oolite-debug-console.js to subtract from Oolite error message
DEBUG_TRY_EVAL_LINE = 843	

# alias registration, ie. set as property of console.script
ALIAS_POLLING = -1
ALIAS_UNREGISTERED = 0
ALIAS_REGISTERED = 1
ALIAS_INVALID = 2
ALIAS_SUSPENDED = 3
ALIAS_POLL_BATCH_SIZE = 5	# number of aliases sent each polling loop
ALIAS_POLL_RETRYS = 3		# number of register attempts before halting
DEBUG_ALIAS = ['UNREGISTERED', 'REGISTERED', 'INVALID', 'SUSPENDED', 'POLLING']
# - used only in __repr__ of Alias
IIFE_PROPERTY_TAG = '_$_'

## color data #################################################################

# when searching either _TKCOLORS or _OOCOLORS, all 3 primary colors being 
# within this amount is considered a match
COLOR_TOLERANCE = 8

TKCOLORS = {
	'AliceBlue':    		'#f0f8ff',    'alice blue': '#f0f8ff',
	'AntiqueWhite': 		'#faebd7',    'antique white': '#faebd7',
	'AntiqueWhite1':		'#ffefdb',
	'AntiqueWhite2':		'#eedfcc',
	'AntiqueWhite3':		'#cdc0b0',
	'AntiqueWhite4':		'#8b8378',
	'aquamarine':   		'#7fffd4',    'aquamarine1': '#7fffd4',
	'aquamarine2':  		'#76eec6',
	'MediumAquamarine': 	'#66cdaa',    'aquamarine3': '#66cdaa',    'medium aquamarine': '#66cdaa',
	'aquamarine4':  		'#458b74',
	'azure':				'#f0ffff',    'azure1': '#f0ffff',
	'azure2':   			'#e0eeee',
	'azure3':   			'#c1cdcd',
	'azure4':   			'#838b8b',
	'beige':				'#f5f5dc',
	'bisque':   			'#ffe4c4',    'bisque1': '#ffe4c4',
	'bisque2':  			'#eed5b7',
	'bisque3':  			'#cdb79e',
	'bisque4':  			'#8b7d6b',
	'black':				'#000000',    'gray0': '#000000',    'grey0': '#000000',
	'BlanchedAlmond':   	'#ffebcd',    'blanched almond': '#ffebcd',
	'blue': 				'#0000ff',    'blue1': '#0000ff',
	'BlueViolet':   		'#8a2be2',    'blue violet': '#8a2be2',
	'blue2':				'#0000ee',
	'MediumBlue':   		'#0000cd',    'blue3': '#0000cd',    'medium blue': '#0000cd',
	'DarkBlue': 			'#00008b',    'blue4': '#00008b',    'dark blue': '#00008b',
	'brown':				'#a52a2a',
	'brown1':   			'#ff4040',
	'brown2':   			'#ee3b3b',
	'brown3':   			'#cd3333',
	'brown4':   			'#8b2323',
	'burlywood':    		'#deb887',
	'burlywood1':   		'#ffd39b',
	'burlywood2':   		'#eec591',
	'burlywood3':   		'#cdaa7d',
	'burlywood4':   		'#8b7355',
	'CadetBlue':    		'#5f9ea0',    'cadet blue': '#5f9ea0',
	'CadetBlue1':   		'#98f5ff',
	'CadetBlue2':   		'#8ee5ee',
	'CadetBlue3':   		'#7ac5cd',
	'CadetBlue4':   		'#53868b',
	'chartreuse':   		'#7fff00',    'chartreuse1': '#7fff00',
	'chartreuse2':  		'#76ee00',
	'chartreuse3':  		'#66cd00',
	'chartreuse4':  		'#458b00',
	'chocolate':    		'#d2691e',
	'chocolate1':   		'#ff7f24',
	'chocolate2':   		'#ee7621',
	'chocolate3':   		'#cd661d',
	'SaddleBrown':  		'#8b4513',    'chocolate4': '#8b4513',    'saddle brown': '#8b4513',
	'coral':				'#ff7f50',
	'coral1':   			'#ff7256',
	'coral2':   			'#ee6a50',
	'coral3':   			'#cd5b45',
	'coral4':   			'#8b3e2f',
	'CornflowerBlue':   	'#6495ed',    'cornflower blue': '#6495ed',
	'cornsilk': 			'#fff8dc',    'cornsilk1': '#fff8dc',
	'cornsilk2':    		'#eee8cd',
	'cornsilk3':    		'#cdc8b1',
	'cornsilk4':    		'#8b8878',
	'cyan': 				'#00ffff',    'cyan1': '#00ffff',
	'cyan2':				'#00eeee',
	'cyan3':				'#00cdcd',
	'DarkCyan': 			'#008b8b',    'cyan4': '#008b8b',    'dark cyan': '#008b8b',
	'DarkGoldenrod':		'#b8860b',    'dark goldenrod': '#b8860b',
	'DarkGray': 			'#a9a9a9',    'DarkGrey': '#a9a9a9',    'dark gray': '#a9a9a9',    'dark grey': '#a9a9a9',
	'DarkGreen':    		'#006400',    'dark green': '#006400',
	'DarkKhaki':    		'#bdb76b',    'dark khaki': '#bdb76b',
	'DarkMagenta':  		'#8b008b',    'dark magenta': '#8b008b',    'magenta4': '#8b008b',
	'DarkOliveGreen':   	'#556b2f',    'dark olive green': '#556b2f',
	'DarkOrange':   		'#ff8c00',    'dark orange': '#ff8c00',
	'DarkOrchid':   		'#9932cc',    'dark orchid': '#9932cc',
	'DarkRed':  			'#8b0000',    'dark red': '#8b0000',    'red4': '#8b0000',
	'DarkSalmon':   		'#e9967a',    'dark salmon': '#e9967a',
	'DarkSeaGreen': 		'#8fbc8f',    'dark sea green': '#8fbc8f',
	'DarkSlateBlue':		'#483d8b',    'dark slate blue': '#483d8b',
	'DarkSlateGray':		'#2f4f4f',    'DarkSlateGrey': '#2f4f4f',    'dark slate gray': '#2f4f4f',    'dark slate grey': '#2f4f4f',
	'DarkTurquoise':		'#00ced1',    'dark turquoise': '#00ced1',
	'DarkViolet':   		'#9400d3',    'dark violet': '#9400d3',
	'DarkGoldenrod1':   	'#ffb90f',
	'DarkGoldenrod2':   	'#eead0e',
	'DarkGoldenrod3':   	'#cd950c',
	'DarkGoldenrod4':   	'#8b6508',
	'DarkOliveGreen1':  	'#caff70',
	'DarkOliveGreen2':  	'#bcee68',
	'DarkOliveGreen3':  	'#a2cd5a',
	'DarkOliveGreen4':  	'#6e8b3d',
	'DarkOrange1':  		'#ff7f00',
	'DarkOrange2':  		'#ee7600',
	'DarkOrange3':  		'#cd6600',
	'DarkOrange4':  		'#8b4500',
	'DarkOrchid1':  		'#bf3eff',
	'DarkOrchid2':  		'#b23aee',
	'DarkOrchid3':  		'#9a32cd',
	'DarkOrchid4':  		'#68228b',
	'DarkSeaGreen1':		'#c1ffc1',
	'DarkSeaGreen2':		'#b4eeb4',
	'DarkSeaGreen3':		'#9bcd9b',
	'DarkSeaGreen4':		'#698b69',
	'DarkSlateGray1':   	'#97ffff',
	'DarkSlateGray2':   	'#8deeee',
	'DarkSlateGray3':   	'#79cdcd',
	'DarkSlateGray4':   	'#528b8b',
	'DeepPink': 			'#ff1493',    'DeepPink1': '#ff1493',    'deep pink': '#ff1493',
	'DeepSkyBlue':  		'#00bfff',    'DeepSkyBlue1': '#00bfff',    'deep sky blue': '#00bfff',
	'DeepPink2':    		'#ee1289',
	'DeepPink3':    		'#cd1076',
	'DeepPink4':    		'#8b0a50',
	'DeepSkyBlue2': 		'#00b2ee',
	'DeepSkyBlue3': 		'#009acd',
	'DeepSkyBlue4': 		'#00688b',
	'DimGray':  			'#696969',    'DimGrey': '#696969',    'dim gray': '#696969',    'dim grey': '#696969',    'gray41': '#696969',    'grey41': '#696969',
	'DodgerBlue':   		'#1e90ff',    'DodgerBlue1': '#1e90ff',    'dodger blue': '#1e90ff',
	'DodgerBlue2':  		'#1c86ee',
	'DodgerBlue3':  		'#1874cd',
	'DodgerBlue4':  		'#104e8b',
	'firebrick':    		'#b22222',
	'firebrick1':   		'#ff3030',
	'firebrick2':   		'#ee2c2c',
	'firebrick3':   		'#cd2626',
	'firebrick4':   		'#8b1a1a',
	'FloralWhite':  		'#fffaf0',    'floral white': '#fffaf0',
	'ForestGreen':  		'#228b22',    'forest green': '#228b22',
	'gainsboro':    		'#dcdcdc',
	'GhostWhite':   		'#f8f8ff',    'ghost white': '#f8f8ff',
	'gold': 				'#ffd700',    'gold1': '#ffd700',
	'gold2':				'#eec900',
	'gold3':				'#cdad00',
	'gold4':				'#8b7500',
	'goldenrod':    		'#daa520',
	'goldenrod1':   		'#ffc125',
	'goldenrod2':   		'#eeb422',
	'goldenrod3':   		'#cd9b1d',
	'goldenrod4':   		'#8b6914',
	'gray': 				'#bebebe',    'grey': '#bebebe',
	'gray1':				'#030303',    'grey1': '#030303',
	'gray2':				'#050505',    'grey2': '#050505',
	'gray3':				'#080808',    'grey3': '#080808',
	'gray4':				'#0a0a0a',    'grey4': '#0a0a0a',
	'gray5':				'#0d0d0d',    'grey5': '#0d0d0d',
	'gray6':				'#0f0f0f',    'grey6': '#0f0f0f',
	'gray7':				'#121212',    'grey7': '#121212',
	'gray8':				'#141414',    'grey8': '#141414',
	'gray9':				'#171717',    'grey9': '#171717',
	'gray10':   			'#1a1a1a',    'grey10': '#1a1a1a',
	'gray11':   			'#1c1c1c',    'grey11': '#1c1c1c',
	'gray12':   			'#1f1f1f',    'grey12': '#1f1f1f',
	'gray13':   			'#212121',    'grey13': '#212121',
	'gray14':   			'#242424',    'grey14': '#242424',
	'gray15':   			'#262626',    'grey15': '#262626',
	'gray16':   			'#292929',    'grey16': '#292929',
	'gray17':   			'#2b2b2b',    'grey17': '#2b2b2b',
	'gray18':   			'#2e2e2e',    'grey18': '#2e2e2e',
	'gray19':   			'#303030',    'grey19': '#303030',
	'gray20':   			'#333333',    'grey20': '#333333',
	'gray21':   			'#363636',    'grey21': '#363636',
	'gray22':   			'#383838',    'grey22': '#383838',
	'gray23':   			'#3b3b3b',    'grey23': '#3b3b3b',
	'gray24':   			'#3d3d3d',    'grey24': '#3d3d3d',
	'gray25':   			'#404040',    'grey25': '#404040',
	'gray26':   			'#424242',    'grey26': '#424242',
	'gray27':   			'#454545',    'grey27': '#454545',
	'gray28':   			'#474747',    'grey28': '#474747',
	'gray29':   			'#4a4a4a',    'grey29': '#4a4a4a',
	'gray30':   			'#4d4d4d',    'grey30': '#4d4d4d',
	'gray31':   			'#4f4f4f',    'grey31': '#4f4f4f',
	'gray32':   			'#525252',    'grey32': '#525252',
	'gray33':   			'#545454',    'grey33': '#545454',
	'gray34':   			'#575757',    'grey34': '#575757',
	'gray35':   			'#595959',    'grey35': '#595959',
	'gray36':   			'#5c5c5c',    'grey36': '#5c5c5c',
	'gray37':   			'#5e5e5e',    'grey37': '#5e5e5e',
	'gray38':   			'#616161',    'grey38': '#616161',
	'gray39':   			'#636363',    'grey39': '#636363',
	'gray40':   			'#666666',    'grey40': '#666666',
	'gray42':   			'#6b6b6b',    'grey42': '#6b6b6b',
	'gray43':   			'#6e6e6e',    'grey43': '#6e6e6e',
	'gray44':   			'#707070',    'grey44': '#707070',
	'gray45':   			'#737373',    'grey45': '#737373',
	'gray46':   			'#757575',    'grey46': '#757575',
	'gray47':   			'#787878',    'grey47': '#787878',
	'gray48':   			'#7a7a7a',    'grey48': '#7a7a7a',
	'gray49':   			'#7d7d7d',    'grey49': '#7d7d7d',
	'gray50':   			'#7f7f7f',    'grey50': '#7f7f7f',
	'gray51':   			'#828282',    'grey51': '#828282',
	'gray52':   			'#858585',    'grey52': '#858585',
	'gray53':   			'#878787',    'grey53': '#878787',
	'gray54':   			'#8a8a8a',    'grey54': '#8a8a8a',
	'gray55':   			'#8c8c8c',    'grey55': '#8c8c8c',
	'gray56':   			'#8f8f8f',    'grey56': '#8f8f8f',
	'gray57':   			'#919191',    'grey57': '#919191',
	'gray58':   			'#949494',    'grey58': '#949494',
	'gray59':   			'#969696',    'grey59': '#969696',
	'gray60':   			'#999999',    'grey60': '#999999',
	'gray61':   			'#9c9c9c',    'grey61': '#9c9c9c',
	'gray62':   			'#9e9e9e',    'grey62': '#9e9e9e',
	'gray63':   			'#a1a1a1',    'grey63': '#a1a1a1',
	'gray64':   			'#a3a3a3',    'grey64': '#a3a3a3',
	'gray65':   			'#a6a6a6',    'grey65': '#a6a6a6',
	'gray66':   			'#a8a8a8',    'grey66': '#a8a8a8',
	'gray67':   			'#ababab',    'grey67': '#ababab',
	'gray68':   			'#adadad',    'grey68': '#adadad',
	'gray69':   			'#b0b0b0',    'grey69': '#b0b0b0',
	'gray70':   			'#b3b3b3',    'grey70': '#b3b3b3',
	'gray71':   			'#b5b5b5',    'grey71': '#b5b5b5',
	'gray72':   			'#b8b8b8',    'grey72': '#b8b8b8',
	'gray73':   			'#bababa',    'grey73': '#bababa',
	'gray74':   			'#bdbdbd',    'grey74': '#bdbdbd',
	'gray75':   			'#bfbfbf',    'grey75': '#bfbfbf',
	'gray76':   			'#c2c2c2',    'grey76': '#c2c2c2',
	'gray77':   			'#c4c4c4',    'grey77': '#c4c4c4',
	'gray78':   			'#c7c7c7',    'grey78': '#c7c7c7',
	'gray79':   			'#c9c9c9',    'grey79': '#c9c9c9',
	'gray80':   			'#cccccc',    'grey80': '#cccccc',
	'gray81':   			'#cfcfcf',    'grey81': '#cfcfcf',
	'gray82':   			'#d1d1d1',    'grey82': '#d1d1d1',
	'gray83':   			'#d4d4d4',    'grey83': '#d4d4d4',
	'gray84':   			'#d6d6d6',    'grey84': '#d6d6d6',
	'gray85':   			'#d9d9d9',    'grey85': '#d9d9d9',
	'gray86':   			'#dbdbdb',    'grey86': '#dbdbdb',
	'gray87':   			'#dedede',    'grey87': '#dedede',
	'gray88':   			'#e0e0e0',    'grey88': '#e0e0e0',
	'gray89':   			'#e3e3e3',    'grey89': '#e3e3e3',
	'gray90':   			'#e5e5e5',    'grey90': '#e5e5e5',
	'gray91':   			'#e8e8e8',    'grey91': '#e8e8e8',
	'gray92':   			'#ebebeb',    'grey92': '#ebebeb',
	'gray93':   			'#ededed',    'grey93': '#ededed',
	'gray94':   			'#f0f0f0',    'grey94': '#f0f0f0',
	'gray95':   			'#f2f2f2',    'grey95': '#f2f2f2',
	'WhiteSmoke':   		'#f5f5f5',    'gray96': '#f5f5f5',    'grey96': '#f5f5f5',    'white smoke': '#f5f5f5',
	'gray97':   			'#f7f7f7',    'grey97': '#f7f7f7',
	'gray98':   			'#fafafa',    'grey98': '#fafafa',
	'gray99':   			'#fcfcfc',    'grey99': '#fcfcfc',
	'gray100':  			'#ffffff',    'grey100': '#ffffff',    'white': '#ffffff',
	'green':				'#00ff00',    'green1': '#00ff00',
	'GreenYellow':  		'#adff2f',    'green yellow': '#adff2f',
	'green2':   			'#00ee00',
	'green3':   			'#00cd00',
	'green4':   			'#008b00',
	'honeydew': 			'#f0fff0',    'honeydew1': '#f0fff0',
	'honeydew2':    		'#e0eee0',
	'honeydew3':    		'#c1cdc1',
	'honeydew4':    		'#838b83',
	'HotPink':  			'#ff69b4',    'hot pink': '#ff69b4',
	'HotPink1': 			'#ff6eb4',
	'HotPink2': 			'#ee6aa7',
	'HotPink3': 			'#cd6090',
	'HotPink4': 			'#8b3a62',
	'IndianRed':    		'#cd5c5c',    'indian red': '#cd5c5c',
	'IndianRed1':   		'#ff6a6a',
	'IndianRed2':   		'#ee6363',
	'IndianRed3':   		'#cd5555',
	'IndianRed4':   		'#8b3a3a',
	'ivory':				'#fffff0',    'ivory1': '#fffff0',
	'ivory2':   			'#eeeee0',
	'ivory3':   			'#cdcdc1',
	'ivory4':   			'#8b8b83',
	'khaki':				'#f0e68c',
	'khaki1':   			'#fff68f',
	'khaki2':   			'#eee685',
	'khaki3':   			'#cdc673',
	'khaki4':   			'#8b864e',
	'lavender': 			'#e6e6fa',
	'LavenderBlush':		'#fff0f5',    'LavenderBlush1': '#fff0f5',    'lavender blush': '#fff0f5',
	'LavenderBlush2':   	'#eee0e5',
	'LavenderBlush3':   	'#cdc1c5',
	'LavenderBlush4':   	'#8b8386',
	'LawnGreen':    		'#7cfc00',    'lawn green': '#7cfc00',
	'LemonChiffon': 		'#fffacd',    'LemonChiffon1': '#fffacd',    'lemon chiffon': '#fffacd',
	'LemonChiffon2':		'#eee9bf',
	'LemonChiffon3':		'#cdc9a5',
	'LemonChiffon4':		'#8b8970',
	'LightBlue':    		'#add8e6',    'light blue': '#add8e6',
	'LightCoral':   		'#f08080',    'light coral': '#f08080',
	'LightCyan':    		'#e0ffff',    'LightCyan1': '#e0ffff',    'light cyan': '#e0ffff',
	'LightGoldenrod':   	'#eedd82',    'light goldenrod': '#eedd82',
	'LightGoldenrodYellow': '#fafad2',    'light goldenrod yellow': '#fafad2',
	'LightGray':    		'#d3d3d3',    'LightGrey': '#d3d3d3',    'light gray': '#d3d3d3',    'light grey': '#d3d3d3',
	'LightGreen':   		'#90ee90',    'PaleGreen2': '#90ee90',    'light green': '#90ee90',
	'LightPink':    		'#ffb6c1',    'light pink': '#ffb6c1',
	'LightSalmon':  		'#ffa07a',    'LightSalmon1': '#ffa07a',    'light salmon': '#ffa07a',
	'LightSeaGreen':		'#20b2aa',    'light sea green': '#20b2aa',
	'LightSkyBlue': 		'#87cefa',    'light sky blue': '#87cefa',
	'LightSlateBlue':   	'#8470ff',    'light slate blue': '#8470ff',
	'LightSlateGray':   	'#778899',    'LightSlateGrey': '#778899',    'light slate gray': '#778899',    'light slate grey': '#778899',
	'LightSteelBlue':   	'#b0c4de',    'light steel blue': '#b0c4de',
	'LightYellow':  		'#ffffe0',    'LightYellow1': '#ffffe0',    'light yellow': '#ffffe0',
	'LightBlue1':   		'#bfefff',
	'LightBlue2':   		'#b2dfee',
	'LightBlue3':   		'#9ac0cd',
	'LightBlue4':   		'#68838b',
	'LightCyan2':   		'#d1eeee',
	'LightCyan3':   		'#b4cdcd',
	'LightCyan4':   		'#7a8b8b',
	'LightGoldenrod1':  	'#ffec8b',
	'LightGoldenrod2':  	'#eedc82',
	'LightGoldenrod3':  	'#cdbe70',
	'LightGoldenrod4':  	'#8b814c',
	'LightPink1':   		'#ffaeb9',
	'LightPink2':   		'#eea2ad',
	'LightPink3':   		'#cd8c95',
	'LightPink4':   		'#8b5f65',
	'LightSalmon2': 		'#ee9572',
	'LightSalmon3': 		'#cd8162',
	'LightSalmon4': 		'#8b5742',
	'LightSkyBlue1':		'#b0e2ff',
	'LightSkyBlue2':		'#a4d3ee',
	'LightSkyBlue3':		'#8db6cd',
	'LightSkyBlue4':		'#607b8b',
	'LightSteelBlue1':  	'#cae1ff',
	'LightSteelBlue2':  	'#bcd2ee',
	'LightSteelBlue3':  	'#a2b5cd',
	'LightSteelBlue4':  	'#6e7b8b',
	'LightYellow2': 		'#eeeed1',
	'LightYellow3': 		'#cdcdb4',
	'LightYellow4': 		'#8b8b7a',
	'LimeGreen':    		'#32cd32',    'lime green': '#32cd32',
	'linen':				'#faf0e6',
	'magenta':  			'#ff00ff',    'magenta1': '#ff00ff',
	'magenta2': 			'#ee00ee',
	'magenta3': 			'#cd00cd',
	'maroon':   			'#b03060',
	'maroon1':  			'#ff34b3',
	'maroon2':  			'#ee30a7',
	'maroon3':  			'#cd2990',
	'maroon4':  			'#8b1c62',
	'MediumOrchid': 		'#ba55d3',    'medium orchid': '#ba55d3',
	'MediumPurple': 		'#9370db',    'medium purple': '#9370db',
	'MediumSeaGreen':   	'#3cb371',    'medium sea green': '#3cb371',
	'MediumSlateBlue':  	'#7b68ee',    'medium slate blue': '#7b68ee',
	'MediumSpringGreen':    '#00fa9a',    'medium spring green': '#00fa9a',
	'MediumTurquoise':  	'#48d1cc',    'medium turquoise': '#48d1cc',
	'MediumVioletRed':  	'#c71585',    'medium violet red': '#c71585',
	'MediumOrchid1':		'#e066ff',
	'MediumOrchid2':		'#d15fee',
	'MediumOrchid3':		'#b452cd',
	'MediumOrchid4':		'#7a378b',
	'MediumPurple1':		'#ab82ff',
	'MediumPurple2':		'#9f79ee',
	'MediumPurple3':		'#8968cd',
	'MediumPurple4':		'#5d478b',
	'MidnightBlue': 		'#191970',    'midnight blue': '#191970',
	'MintCream':    		'#f5fffa',    'mint cream': '#f5fffa',
	'MistyRose':    		'#ffe4e1',    'MistyRose1': '#ffe4e1',    'misty rose': '#ffe4e1',
	'MistyRose2':   		'#eed5d2',
	'MistyRose3':   		'#cdb7b5',
	'MistyRose4':   		'#8b7d7b',
	'moccasin': 			'#ffe4b5',
	'NavajoWhite':  		'#ffdead',    'NavajoWhite1': '#ffdead',    'navajo white': '#ffdead',
	'NavajoWhite2': 		'#eecfa1',
	'NavajoWhite3': 		'#cdb38b',
	'NavajoWhite4': 		'#8b795e',
	'NavyBlue': 			'#000080',    'navy': '#000080',    'navy blue': '#000080',
	'OldLace':  			'#fdf5e6',    'old lace': '#fdf5e6',
	'OliveDrab':    		'#6b8e23',    'olive drab': '#6b8e23',
	'OliveDrab1':   		'#c0ff3e',
	'OliveDrab2':   		'#b3ee3a',
	'OliveDrab3':   		'#9acd32',    'YellowGreen': '#9acd32',    'yellow green': '#9acd32',
	'OliveDrab4':   		'#698b22',
	'orange':   			'#ffa500',    'orange1': '#ffa500',
	'OrangeRed':    		'#ff4500',    'OrangeRed1': '#ff4500',    'orange red': '#ff4500',
	'orange2':  			'#ee9a00',
	'orange3':  			'#cd8500',
	'orange4':  			'#8b5a00',
	'OrangeRed2':   		'#ee4000',
	'OrangeRed3':   		'#cd3700',
	'OrangeRed4':   		'#8b2500',
	'orchid':   			'#da70d6',
	'orchid1':  			'#ff83fa',
	'orchid2':  			'#ee7ae9',
	'orchid3':  			'#cd69c9',
	'orchid4':  			'#8b4789',
	'PaleGoldenrod':		'#eee8aa',    'pale goldenrod': '#eee8aa',
	'PaleGreen':    		'#98fb98',    'pale green': '#98fb98',
	'PaleTurquoise':		'#afeeee',    'pale turquoise': '#afeeee',
	'PaleVioletRed':		'#db7093',    'pale violet red': '#db7093',
	'PaleGreen1':   		'#9aff9a',
	'PaleGreen3':   		'#7ccd7c',
	'PaleGreen4':   		'#548b54',
	'PaleTurquoise1':   	'#bbffff',
	'PaleTurquoise2':   	'#aeeeee',
	'PaleTurquoise3':   	'#96cdcd',
	'PaleTurquoise4':   	'#668b8b',
	'PaleVioletRed1':   	'#ff82ab',
	'PaleVioletRed2':   	'#ee799f',
	'PaleVioletRed3':   	'#cd687f',
	'PaleVioletRed4':   	'#8b475d',
	'PapayaWhip':   		'#ffefd5',    'papaya whip': '#ffefd5',
	'PeachPuff':    		'#ffdab9',    'PeachPuff1': '#ffdab9',    'peach puff': '#ffdab9',
	'PeachPuff2':   		'#eecbad',
	'PeachPuff3':   		'#cdaf95',
	'PeachPuff4':   		'#8b7765',
	'peru': 				'#cd853f',    'tan3': '#cd853f',
	'pink': 				'#ffc0cb',
	'pink1':				'#ffb5c5',
	'pink2':				'#eea9b8',
	'pink3':				'#cd919e',
	'pink4':				'#8b636c',
	'plum': 				'#dda0dd',
	'plum1':				'#ffbbff',
	'plum2':				'#eeaeee',
	'plum3':				'#cd96cd',
	'plum4':				'#8b668b',
	'PowderBlue':   		'#b0e0e6',    'powder blue': '#b0e0e6',
	'purple':   			'#a020f0',
	'purple1':  			'#9b30ff',
	'purple2':  			'#912cee',
	'purple3':  			'#7d26cd',
	'purple4':  			'#551a8b',
	'red':  				'#ff0000',    'red1': '#ff0000',
	'red2': 				'#ee0000',
	'red3': 				'#cd0000',
	'RosyBrown':    		'#bc8f8f',    'rosy brown': '#bc8f8f',
	'RosyBrown1':   		'#ffc1c1',
	'RosyBrown2':   		'#eeb4b4',
	'RosyBrown3':   		'#cd9b9b',
	'RosyBrown4':   		'#8b6969',
	'RoyalBlue':    		'#4169e1',    'royal blue': '#4169e1',
	'RoyalBlue1':   		'#4876ff',
	'RoyalBlue2':   		'#436eee',
	'RoyalBlue3':   		'#3a5fcd',
	'RoyalBlue4':   		'#27408b',
	'salmon':   			'#fa8072',
	'salmon1':  			'#ff8c69',
	'salmon2':  			'#ee8262',
	'salmon3':  			'#cd7054',
	'salmon4':  			'#8b4c39',
	'SandyBrown':   		'#f4a460',    'sandy brown': '#f4a460',
	'SeaGreen': 			'#2e8b57',    'SeaGreen4': '#2e8b57',    'sea green': '#2e8b57',
	'SeaGreen1':    		'#54ff9f',
	'SeaGreen2':    		'#4eee94',
	'SeaGreen3':    		'#43cd80',
	'seashell': 			'#fff5ee',    'seashell1': '#fff5ee',
	'seashell2':    		'#eee5de',
	'seashell3':    		'#cdc5bf',
	'seashell4':    		'#8b8682',
	'sienna':   			'#a0522d',
	'sienna1':  			'#ff8247',
	'sienna2':  			'#ee7942',
	'sienna3':  			'#cd6839',
	'sienna4':  			'#8b4726',
	'SkyBlue':  			'#87ceeb',    'sky blue': '#87ceeb',
	'SkyBlue1': 			'#87ceff',
	'SkyBlue2': 			'#7ec0ee',
	'SkyBlue3': 			'#6ca6cd',
	'SkyBlue4': 			'#4a708b',
	'SlateBlue':    		'#6a5acd',    'slate blue': '#6a5acd',
	'SlateGray':    		'#708090',    'SlateGrey': '#708090',    'slate gray': '#708090',    'slate grey': '#708090',
	'SlateBlue1':   		'#836fff',
	'SlateBlue2':   		'#7a67ee',
	'SlateBlue3':   		'#6959cd',
	'SlateBlue4':   		'#473c8b',
	'SlateGray1':   		'#c6e2ff',
	'SlateGray2':   		'#b9d3ee',
	'SlateGray3':   		'#9fb6cd',
	'SlateGray4':   		'#6c7b8b',
	'snow': 				'#fffafa',    'snow1': '#fffafa',
	'snow2':				'#eee9e9',
	'snow3':				'#cdc9c9',
	'snow4':				'#8b8989',
	'SpringGreen':  		'#00ff7f',    'SpringGreen1': '#00ff7f',    'spring green': '#00ff7f',
	'SpringGreen2': 		'#00ee76',
	'SpringGreen3': 		'#00cd66',
	'SpringGreen4': 		'#008b45',
	'SteelBlue':    		'#4682b4',    'steel blue': '#4682b4',
	'SteelBlue1':   		'#63b8ff',
	'SteelBlue2':   		'#5cacee',
	'SteelBlue3':   		'#4f94cd',
	'SteelBlue4':   		'#36648b',
	'tan':  				'#d2b48c',
	'tan1': 				'#ffa54f',
	'tan2': 				'#ee9a49',
	'tan4': 				'#8b5a2b',
	'thistle':  			'#d8bfd8',
	'thistle1': 			'#ffe1ff',
	'thistle2': 			'#eed2ee',
	'thistle3': 			'#cdb5cd',
	'thistle4': 			'#8b7b8b',
	'tomato':   			'#ff6347',    'tomato1': '#ff6347',
	'tomato2':  			'#ee5c42',
	'tomato3':  			'#cd4f39',
	'tomato4':  			'#8b3626',
	'turquoise':    		'#40e0d0',
	'turquoise1':   		'#00f5ff',
	'turquoise2':   		'#00e5ee',
	'turquoise3':   		'#00c5cd',
	'turquoise4':   		'#00868b',
	'violet':   			'#ee82ee',
	'VioletRed':    		'#d02090',    'violet red': '#d02090',
	'VioletRed1':   		'#ff3e96',
	'VioletRed2':   		'#ee3a8c',
	'VioletRed3':   		'#cd3278',
	'VioletRed4':   		'#8b2252',
	'wheat':				'#f5deb3',
	'wheat1':   			'#ffe7ba',
	'wheat2':   			'#eed8ae',
	'wheat3':   			'#cdba96',
	'wheat4':   			'#8b7e66',
	'yellow':   			'#ffff00',    'yellow1': '#ffff00',
	'yellow2':  			'#eeee00',
	'yellow3':  			'#cdcd00',
	'yellow4':  			'#8b8b00',
}

OOCOLORS = {
	'blackColor':		'#000000',
	'darkGrayColor':	'#555555',
	'lightGrayColor':	'#2a2a2a',
	'whiteColor':		'#ffffff',
	'grayColor':		'#808080',
	'redColor':			'#ff0000',
	'greenColor':		'#00ff00',
	'blueColor':		'#0000ff',
	'cyanColor':		'#00ffff',
	'yellowColor':		'#ffff00',
	'magentaColor':		'#ff00ff',
	'orangeColor':		'#ff8000',
	'purpleColor':		'#800080',
	'brownColor':		'#996633',
}

## debug menu #################################################################

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

## font menu ##################################################################

MIN_FONT_SIZE = 8
MAX_FONT_SIZE=30

## config file ################################################################

TRUE_STRS = ['1', 'yes', 'true', 'on']
FALSE_STRS = ['0', 'no', 'false', 'off']
NIL_STRS = [None, '', 'None', 'null']

# the names of any new sections must be added to SECTION_RE in regularExpn.py

optionsAreInts = ['ConsolePort', 'Port', 'EndPort', 'MaxHistoryCmds',	# Settings
				   'MaxBufferSize', 'SashOffset', 'BaseTimingMS',
				   'FindToolTipDelayMS', 'SearchToolTipDelayMS',
				   'Size', 												# Font
				   'AliasSashOffset', 'FindSashOffset', 	 			# History
				   'FindContextLines']

optionsAreLists = ['ToolTips',											# Settings
					'FindPaths', 'FindTypes', 'FindExcls',  	 		# History
					'FindSearches', 'SearchTerms']

optionsAreSelections = ['FindTypes', 'FindExcls', 'FindSearches']		# History

# options that can be absent, ie. those generated by user's actions
# - these are not set in CurrentOptions until necessary, and won't
#   be output to CFGFILE if absent
# - all settings in History apply too
settingsNotRequired = ['SaveConfigNow', 'Geometry', 'SashOffset'] 		# Settings

## configuration template #####################################################

defaultConfig = OrderedDict((
	('Settings', OrderedDict((
		('SaveConfigOnExit', 	True),
		('SaveConfigNow', 		False),	# placeholder (menu tkvar), not written to .cfg
		('SaveHistoryOnExit', 	True),
		('Port', 				49999),	# from ver 1.6: console listens to port 49999 rather than to default port 8563
		('EndPort', 			50003),	# from ver 1.6: enable multiple console execution on the same machine
		('ServerAddress', 		'127.0.0.1'),
		# ('ConsolePort', 		8563), retired (initially my creation? configParser?)
		('HideDefaultComments', False),	# toggles appearence of default comments (like this one!)
		('EnableShowConsole',	True),
		('OldClearBehaviour',	False),	# make the [Clear] button clear main console window instead of command window
		('MacroExpansion',		True),	# show 'macro-expansion' messages in console
		('TruncateCmdEcho',		False),	# shorten commands echoed to a single line
		('ResetCmdSizeOnRun',	True),	# reset cmdLine's size after cmd is run
		('MsWheelHistory', 		False),	# allow mouse wheel to scroll through cmd history
		('PlistOverrides', 		True),	# here ends the options menu, the rest are only available via CFGFILE
		('FormatAliasFns',		False),	# functions/IIFEs are returned using JS's .toString, comments restored after
		('MaxHistoryCmds', 		MAX_HIST_CMDS),	# maximum # of commands in the command history
		('MaxBufferSize', 		MAX_HIST_SIZE),# upper limit on the size (bytes) of the command history
		('ColorMenus', 			False),	# toggle for applying colors to menus
		('ColorPopups', 		False),	# toggle for applying colors to popup menus
		('ColorButtons', 		False),	# toggle for applying colors to buttons
		('Geometry', 			DEFAULT_GEOMETRY),
		('SashOffset', 			None),
		('BaseTimingMS', 		5),		# changes tkTiming, this being 'fast', 'lazy' is 8 *, 'slow' is 24 *
		('FindToolTipDelayMS', 	1000),	# delay in milliseconds to show tool tip; 0 turns them off
		('SearchToolTipDelayMS',1000),
		('ToolTips', 			'all'),
	)) ),
	('Font', OrderedDict((
		# Family & Size exist in console.settings(font-face, font-size), so
		# changes of those also stored here (see PlistOverrides)
		('Family', 		'Arial'),		# The font family name as a string.
		('Size', 		10),			# The font height as an integer in points. To get a font n pixels high, use -n.
		# these 3 only appear locally in Font menu, as they
		# are not supported in oolite
		('Weight', 		'normal'),		# "bold" for boldface, "normal" for regular weight.
		('Slant', 		'roman'),		# "italic" for italic, "roman" for un-slanted.
		('disabled', 	'normal'),		# "overstrike" or "normal"
	)) ),
	('Colors', OrderedDict((			# working dict for local colors, which are independent of oolite's
		('General-foreground',	'yellow'),
		('General-background',	'black'),
		('Command-foreground',	'cyan'),
		('Command-background',	'NavyBlue'),
		('Select-foreground',	'black'),
		('Select-background',	'white'),
	)) ),
	('History', OrderedDict((			# window/sash positions, listbox histories
		('AliasWindow', 		DEFAULT_ALIAS_GEOMETRY),
		('AliasSashOffset', 	None),
		('FinderWindow', 		DEFAULT_FINDER_GEOMETRY),
		('FindSashOffset', 		None),
		('SearchTerms', 		None),
		('SearchLog', 			None),
		('SearchCmd', 			None),
		('SearchAlias', 		None),
		('SearchContext', 		None),
		('FindPaths', 			None),
		('FindTypes', 			DEFAULT_INCL),
		('FindIncluding', 		'current'),
		('FindExcls', 			DEFAULT_EXCL),
		('FindExcluding', 		'all'),
		('FindSearches', 		None),
		('FindSearching', 		'current'),
		('FindIgnoreCase', 		True),
		('FindMatchAll', 		False),
		('FindQuitOnFirst', 	False),
		('FindSubDirs', 		True),
		('FindOxzFiles', 		True),
		('FindContextLines', 	3),
		('FindTreatment', 		'Token'),
	)) ),
	('Aliases', OrderedDict()
	),
))
defaultSections = list(defaultConfig.keys())

# comments as documentation of settings
# - are written when no CFGFILE present or it's from previous
# version (determined by presence of 'FormatAliasFns' option)
CMT_OPTION_LINE_ALIGN = 35
_CMT_PAD = ' ' * CMT_OPTION_LINE_ALIGN

defaultComments = OrderedDict((
	('Settings', OrderedDict((
		('HideDefaultComments',
			[ '// toggles the appearance of default comments (like this one) in this file\n', ]),
		('EnableShowConsole',
			[ '// master toggle for 3 "Show Console for ..." in Debug menu\n',
			  _CMT_PAD + '//   will be automatically set if any of the 3 are turned on\n', ]),
		('MacroExpansion',
			[ '// show "macro-expansion" messages when executing macros\n', ]),
		('OldClearBehaviour',
			[ '''// command box 'Clear' button clears the output (upper) window, not the command line\n''', ]),
		('TruncateCmdEcho',
			[ '// shorten command echos to a single line\n', ]),
		('ResetCmdSizeOnRun',
			[ '// resize cmdLine window after a command is run\n', ]),
		('MsWheelHistory',
			[ '// toggle for using the mouse wheel to scroll the command history\n', ]),
		('PlistOverrides',
			[ '// if yes, colors & fonts are replaced with those from Oolite\n', ]),
		('FormatAliasFns',
			[ '// toggle formatting an alias that is a function/IIFE\n',
			  _CMT_PAD + '//   also used to detect .cfg from previous version\n',
			  _CMT_PAD + '//   (if you want to restore all default comments, just delete this option)\n',
			]),
		('MaxHistoryCmds',
			[ '// maximum # of commands in the command history\n', ]),
		('MaxBufferSize',
			[ '// upper limit on the size (bytes) of the command history\n', ]),
		('ColorMenus',
			[ '// toggle for applying colors to menus\n', ]),
		('ColorPopups',
			[ '// toggle for applying colors to popup menus\n', ]),
		('ColorButtons',
			[ '// toggle for applying colors to buttons\n', ]),
		('Geometry',
			[ '-/*\n' # leading '-' character => precede option; list must be len==1
			  + ' * internal, alter at your own risk\n'
			  + ' */\n',
			]),
		('BaseTimingMS',
			[ '// base rate (milliseconds) for network msgs\n', ]),
		('FindToolTipDelayMS',
			[ '// delay (milliseconds) before showing tool tips in Finder window\n',
			  _CMT_PAD + '//  - set to 0 to disable them\n',
			]),
		('SearchToolTipDelayMS',
			[ '// delay (milliseconds) before showing tool tips in text window Search box\n',
			  _CMT_PAD + '//  - set to 0 to disable them\n',
			]),
		('ToolTips',
			# the leading '-' character flags this to precede option
		 	# (no leading NL as previous comment ends so)
			[ '-/*\n'
		 	  + " * list of remaining tool tips.  Can also be set to all or none\n"
			  + ' */\n',
			]),
	)) ),
	('Font', OrderedDict((
		('[Font]',
			[ '\n/*\n',
			  ' * these 2 exist in console.settings (as font-face, font-size),\n',
			  ' * so changes of these are also stored there, when PlistOverrides is set\n',
			  ' */\n',
			]),
		('Size',
			[ '/* Tk: "The font height as an integer in points.\n',
			  _CMT_PAD + ' ' * 8 + 'To get a font n pixels high, use -n" */\n',
			]),
		('Weight',
			# the leading '-' character flags this to precede option
		 	# (no leading NL as previous comment ends so)
			[ '-/*\n'
			  + ' * these 3 are only saved locally, as they are not a part of Oolite\n'
			  + ' */\n',
			  '// "bold" for boldface, "normal" for regular weight\n',
			]),
		('Slant',
			[ '// "italic" for italic, "roman" for un-slanted\n', ]),
		('disabled',
			[ '// "overstrike" or "normal" (adds strike-through for visibility)\n', ]),
	)) ),
	('Colors', OrderedDict((
		('[Colors]',
			[ '\n/*\n',
			  ' * colors used in debug console, when PlistOverrides is not set\n',
			  ' * they can be specified by any of the 502 (!) Tk names, like:\n',
			  ' *   black, red, green, blue, cyan, yellow, magenta, white, gray100, deep pink,\n',
			  ' *   deep sky blue, turquoise4, LawnGreen, goldenrod1, MediumOrchid1,\n',
			  ' *   cornflower blue, blanched almond, peach puff, PaleVioletRed, saddle brown, ...\n',
			  ' * or Oolite color names:\n',
			  ' *   blackColor, darkGrayColor, grayColor, lightGrayColor,\n',
			  ' *   whiteColor, redColor, greenColor, blueColor, cyanColor,\n',
			  ' *   yellowColor, magentaColor, orangeColor, purpleColor, brownColor\n',
			  ' * or custom colors as a string in the format "#rrggbb" (or "#rgb"),\n',
			  ' *   where rr, gg, bb are 2 digit hexadecimals, so the first list starts with:\n',
			  ' *   #000000, #ff0000, #00ff00, #0000ff, #00ffff, #ffff00, #ff00ff, #ffffff\n',
			  ' */\n',
			]),
	)) ),
	('History', OrderedDict((
		('AliasWindow',
			[ '// geometry of alias editor.\n', ]),
		('FinderWindow',
			[ '// geometry of file search window\n', ]),
		('SearchTerms',
			[ '// common listbox history (max. 20) of search windows\n', ]),
		('SearchLog',
			[ '// location of output search window\n', ]),
		('FindPaths',
			[ '-/*\n' # the leading '-' character flags this to precede option
			  + ' * listbox history (max. 20) of file Search paths\n'
			  + ' */\n',
			]),
		('FindTypes',
			[ '-/*\n'
			  + " * listbox history (max. 20) of file search File types & its 'checked' status\n"
			  + ' */\n',
			]),
		('FindIncluding',
			[ '// file search option for including all/checked file types\n',
			  _CMT_PAD + '//   in the list or just the current one\n',
			  ]),
		('FindExcls',
			[ '-/*\n'
			  + " * listbox history (max. 20) of file Search excluded types & its 'checked' status\n"
			  + ' */\n',
			]),
		('FindExcluding',
			[ '// file search option for excluding all/checked file types\n',
			  _CMT_PAD + '//   in the list or just the current one\n',
			]),
		('FindSearches',
			[ '-/*\n'
			  + " * listbox history (max. 20) of file Search text & its 'checked' status\n"
			  + ' */\n',
			]),
		('FindSearching',
			[ '// file search option for matching all/checked search terms\n',
			  _CMT_PAD + '//   in the list or just the current one\n',
			]),
		('FindIgnoreCase',
			[ '// file search toggle for case sensitivity\n', ]),
		('FindMatchAll',
			[ '// file search toggle for matching all (vs any) terms\n', ]),
		('FindQuitOnFirst',
			[ '// file search toggle for halting search of a file once\n',
			  _CMT_PAD + '//   a match has been found (faster search)\n',
			]),
		('FindSubDirs',
			[ '// file search toggle for searching sub-folders\n', ]),
		('FindContextLines',
			[ '// # of surrounding lines to display with file search matches\n', ]),
		('FindTreatment',
			[ '// one of \'Token\', \'Word\', \'Substring\', \'Regex\' or \'File\'\n',
			  _CMT_PAD + '//   for how search terms should be considered\n',
			]),
	)) ),
	('Aliases', OrderedDict((
		('[Aliases]',
			[ '\n/*\n',
			  ' * an alias is a way to reduce keystrokes/errors.  They are added as properties\n',
			  ' * to console.script.  There are 4 pre-defined aliases in the Basic-debug.oxp script\n',
			  ' * "oolite-debug-console.js":\n',
			  ' *   P = player,  PS = player.ship,  S = system &  M = missionVariables\n',
			  ' * An alias can be a reference, like these, or a value, object, function or an IIFE!\n',
			  ' * NB: if entering one manually, use <name> := ...\n',
			  ' *     this make parsing much easier, as := is not valid in JavaScript\n',
			  ' */\n',
			  ]),
	))
	),
))

## file finder & alias tooltips ###############################################

REGEX_TEXT = ' Regex (POSIX extended REs with some extensions)'
_REGEX_EXPL = '^$ match beginning and end of line, and\n' \
			  + '., [^ sequences will never match the newline character.'

_TYPE_SPEC = '''Special characters:
    *  : any # of any char  \t[seq]   : any char in seq 
    ? : any single char     \t[!seq] : any char not in seq\n'''

_TYPE_SEP = 'Items can be separated by  ,  or  ;\n'

_REMOVES_FROM_LIST = \
'''Control-Delete or Control-BackSpace will remove 
the current entry from the drop down list.
(or you could edit your .cfg file's [History] section)\n'''

_TOKEN_SPLIT = \
''''Search text' is split into pieces by spaces and matched individually.\n'''

_QUOTED_PHRASES = \
'''Quotes are supported for searches containing spaces.\n'''

toolTips = {
	'searchBackwards':
		'Search proceeds backwards through the text when\n'
		'using the Enter key; no effect on arrows.',
	'searchWrap':
		'Search won\'t halt at top or bottom; a message\n'
		'will inform you when you wrap around.',
	'searchRegex':
		_REGEX_EXPL,
	'searchWordsOnly':
		'Your target will match whole words only,\n'
		'no sub-string matches.',
	'searchTargetEntry':
		_REMOVES_FROM_LIST,
	'searchTargetClear':
		'Clears the text entry window for a new search.\n'
		'Existing target will not be saved, unless\n'
		'used in a previous search.',
	'searchCountBtn':
		'Displays the total number of matches found.',
	'searchMarkall':
		'Highlights all the matches found.',
	'grepPath':
		_REMOVES_FROM_LIST,
	'grepExcl':
		_TYPE_SEP
		+ 'Folders must end in \'/\'.  Those with spaces don\'t need quotes\n'
		+ _TYPE_SPEC + 'NB: excluded types override included types.\n',
	'grepIncl':
		_TYPE_SEP + _TYPE_SPEC,
	'grepText':
		_REMOVES_FROM_LIST,
	'grepMatchAll':
		'When more than one target is specified.\n'
		'Applies only to Token, Word and Regular Expression searches.',
	'grepQuitOnFirst':
		'Quit searching rest of file once a match is found.'
		' (faster but less info)',
	'grepOxzFiles':
		'Will read any zip format file unless excluded.\n'
		'Folder exclusions apply to folders inside these files too.',
	'grepContextNum':
		'Blank lines are not included in the count.',
	'grepTreatToken':
		_TOKEN_SPLIT
		+ _QUOTED_PHRASES,
	'grepTreatWord':
		_TOKEN_SPLIT
		+ 'Matches are limited to a natural language context.\n'
		+ '(for searching text or when Token results in too many matches)\n'
		+ _QUOTED_PHRASES,
	'grepTreatSubstring':
		'Exact match of \'Search text\' anywhere in a file.\n'
		'Encompassing quotes WILL be included in search',
	'grepTreatRegex':
		REGEX_TEXT + NL
		+ _REGEX_EXPL,
	'grepTreatFile':
		'Search text is used for the filename\n' + _TYPE_SPEC
		+ 'all options apply except:\n'
		' \'Included:\',  \'Match all\'...,  \'Skip rest\'...  '
		'and  \'# of context lines\'',
	'aliasPollButton':
		'Toggles polling (1/sec) of the current alias.\n'
		'Many aliases do not change over the course of a game\n'
		'or are only used occasionally or are task specific.\n'
		'Fewer being polled is better.',
	'aliasMenuButton':
		'Make alias a menu button for easy access.\n'
		'Add/remove a menu button for the current alias, its name being that\n'
		'of the alias.  If it is a function/iife and is named, then that name is used.\n'
		'If the function takes parameters, the call will appear in the\n'
		'command window awaiting completion.  Otherwise it executes when clicked\n.'
		'A tooltip can be added by having a comment that starts with "tooltip:".\n'
		'This allows you to pack in more buttons without having to memorize what each\n'
		'one does.  When you add/edit a tooltip, toggle this to rebuild the button.',
}

import os
CAGSPC = os.path.exists(r'C:\Users\cag')
