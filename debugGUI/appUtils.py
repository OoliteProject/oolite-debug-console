# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
# misc functions that DO need any global accessed (vs miscUtils)
import pdb
import traceback
from operator import itemgetter

import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.widgets as wg

## tkinter utilities ##########################################################

def report_callback_exception(*args): 	# replacement for Tk's
	import traceback
	# NLs included in returned list of strings
	errmsg = ''.join(traceback.format_exc())
	wg.OoInfoBox(gv.root, errmsg,
				 label=repr(args[0]) if args else None, error=True) // tmp4test
	if con.CAGSPC:
		if args:
			print('args:', args)
		print(errmsg)
		gv.setTrace()
# args[0]: <class 'OSError'>
# args[1]: [Errno 28] No space left on device
# args[2]: <traceback object at 0x0000017712CB81C0>
	else:
		gv.debugLogger.exception(errmsg)
		wg.OoInfoBox(gv.root, errmsg,
					 label=repr(args[0])if args else None, error=True)

def afterLoop(ms, label, fn, *args):	# manager for event looping
	removeAfter(label)
	# NB: by clearing pending, we reset pending call to new ms,
	# 	  so DO NOT USE IN a tight loop
	#     (if this doesn't work, save also timeCount()
	# 	   in dict and cmp duration to ms)
	gv.afterLoopIDs[label] = gv.root.after(ms, fn, *args)

def removeAfter(label):
	if label in gv.afterLoopIDs:		# terminate existing callback
		# Tk will ignore a cancel command if ID does not exist
		gv.root.after_cancel(gv.afterLoopIDs[label])
		del gv.afterLoopIDs[label]

## searchBox utilities ########################################################

def dragSearchbox(event=None):
	if gv.popupWindows is None or len(gv.popupWindows) == 0:
		# building of app not yet complete
		return 'break'
	# if we're already waiting, afterLoop restarts clock (removes last one)
	afterLoop(gv.tkTiming['slow'], 'recordSearchPosn', recordSearchPosn)
	return 'break' # nothing more to do

def recordSearchPosn():
	removeAfter('recordSearchPosn')
	gv.root.update_idletasks()
	for name, tkEnt in gv.popupWindows.items():
		if not name.startswith('Search'):
			continue
		box = tkEnt.searchBox
		if box.searchUser is box and box.shared.winfo_ismapped():
			# searchBox is a shared widget, .searchUser is set when opened
			_, _, Xoff, Yoff = mu.parseGeometry(box)
			if Xoff == 0 and Yoff == 0:
				# newly minted widget, ie. never mapped
				# don't clobber any existing saved values
				return
			box.__class__.searchUser.searchXY = [Xoff, Yoff]
			# in Windows, Xoff will be 8 less than actual coords (part of resizing handles?)
			# - doesn't need to be 'fixed', as it corrects for this; (-6,0) will position
			#   widget at top of display, 2 pixels if from the left
			# Linux/MaxOS: don't know, will see if anyone reports window creeping
			#              to the right on every load
			return

## finder utilities ###########################################################

# noinspection PyUnusedLocal
def finderConfig(event=None):
	gv.root.update_idletasks()
	gv.sashPosns['FindSashOffset'] = gv.grepPaned.sashpos(0)
	return 'continue' # allow OoCombobox <Configure>

def positionFindSash(yOffset=None):
	if yOffset is None:
		posn = gv.sashPosns['FindSashOffset']
		if posn is None:
			posn = gv.CurrentOptions['History'].get('FindSashOffset')
	else:
		posn = yOffset
	if posn:
		# suspend '<Configure>' events as sashpos will generate some
		binding = gv.contextText.frame.bind('<Configure>')
		gv.contextText.frame.bind('<Configure>', '')
		gv.root.update_idletasks() # required for sashpos to work correctly
		gv.grepPaned.sashpos(0, posn)
		gv.root.update_idletasks()
		gv.contextText.frame.bind('<Configure>', binding)

# noinspection PyBroadException
def monitorResolutions():
	if con.IS_WINDOWS_PC:
		import ctypes
		try:  # Windows 8.1 and later
			ctypes.windll.shcore.SetProcessDpiAwareness(2)
		except:
			try:  # Before Windows 8.1
				ctypes.windll.user32.SetProcessDPIAware()
			except:  # Windows 8 or before
				pass
		user32 = ctypes.windll.user32
		gv.monitorsWidth = user32.GetSystemMetrics(78)
		gv.monitorsHeight = user32.GetSystemMetrics(79)
		return
	elif con.IS_LINUX_PC:
		try:
			import Xlib.display
			resolution = Xlib.display.Display().screen().root.get_geometry()
			gv.monitorsWidth = resolution.width
			gv.monitorsHeight = resolution.height
			return
		except:
			proc = None
			try:
				if "xrandr" in os.environ['PATH']:
					args = ["xrandr", "-q", "-d", ":0"]
					proc = subprocess.Popen(args, stdout=subprocess.PIPE)
					# Screen 0: minimum 320 x 200, current 1920 x 1080, maximum 1920 x 1920
					for line in iter(proc.stdout.readline, ''):
						if isinstance(line, bytes):
							line = line.decode("utf-8")
						if "Screen" in line:
							match = re.search(r'current\s(\d+) x (\d+)', line)
							if match:
								gv.monitorsWidth =int(match.group(1))
								gv.monitorsHeight = int(match.group(2))
								return
							break
			except:
				pass
			finally:
				if proc:
					proc.stdout.close()
	elif con.IS_MACOS_PC:
		import AppKit
		try:
			width = height = 0
			for screen in AppKit.NSScreen.screens():
				width += screen.frame().size.width
				height += screen.frame().size.height
			gv.monitorsWidth, gv.monitorsHeight = width, height
			return
		except:
			pass

	gv.root.update_idletasks()
	gv.root.attributes('-fullscreen', True)
	gv.root.state('iconic')
	gv.geometry = root.winfo_geometry()
	gv.root.attributes('-fullscreen', False)
	gv.root.state('normal')
	gv.monitorsWidth, gv.monitorsHeight = mu.getAppDimns(geometry)

def fitToMonitors(geom):
	# adjust geometry values to fit monitor resolution
	width, height, xOffset, yOffset = mu.parseGeometry(geom)
	if width > gv.monitorsWidth:
		width, xOffset = gv.monitorsWidth, 0
	elif xOffset + width > gv.monitorsWidth:
		xOffset = max(0, gv.monitorsWidth - width)
	if height > gv.monitorsHeight:
		height, yOffset = gv.monitorsHeight, 0
	elif yOffset + height > gv.monitorsHeight:
		yOffset = max(0, gv.monitorsHeight - height)
	return width, height, xOffset, yOffset

## alias utilities ############################################################

def updateAliasValueWidth():
	gv.root.update_idletasks()
	gv.aliasValueWidth = gv.aliasValueLabel.winfo_width()

# noinspection PyUnusedLocal
def aliasConfig(event=None):
	updateAliasValueWidth()
	if con.ALIAS_PANED == 'ttk':
		gv.sashPosns['AliasSashOffset'] = gv.aliasPaned.sashpos(0)
	else:
		gv.sashPosns['AliasSashOffset'] = gv.aliasPaned.sash_coord(0)
	gv.root.update_idletasks()
	return 'break'

def initAliasSash():					# delayed init to allow Tk to catch up
	gv.root.update_idletasks()
	_, sashOffset = _aliasListWidth()
	if con.ALIAS_PANED == 'ttk':
		padx = 2 # cannot query
	else:
		padx = gv.aliasPaned.panecget(gv.aliasListBox.lbFrame, 'padx')
	sashOffset += 2 * padx
	for lbox in gv.aliasListBoxes:
		# aliasListBox's reqwidth is too big, not sure why
		if lbox is not gv.aliasListBox:
			sashOffset += lbox.winfo_reqwidth()
	sashOffset += gv.aliasListBox.scrollbar.winfo_reqwidth()
	sashOffset += gv.zeroLen # whitespace after widest entry
	positionAliasSash(sashOffset)

def _aliasListWidth():
	# calculate max width of list for setting its width & sash placement
	widestC, widestL = con.MIN_ALIAS_CHAR, con.MIN_ALIAS_CHAR * gv.zeroLen
	if len(gv.aliases) > 0:
		font = gv.OoFonts['default']
		widest = [(a, len(a), font.measure(a)) for a in gv.aliases.keys()]
		widestC = max(widestC, max(widest, key=itemgetter(1))[1])
		widestL = max(widestL, max(widest, key=itemgetter(2))[2])
	# return alias list width in char, pixels
	return widestC, widestL

def positionAliasSash(xOffset=None):
	if xOffset is None:
		posn = gv.sashPosns['AliasSashOffset']
		if posn is None:
			posn = gv.CurrentOptions['History'].get('AliasSashOffset')
	else:
		posn = xOffset
	if posn:
		# suspend '<Configure>' events as sashpos will generate some
		binding = gv.aliasDefn.bind('<Configure>')
		gv.aliasDefn.bind('<Configure>', '')
		# update_idletasks required for 'vertical' sashpos to work correctly
		gv.root.update_idletasks()
		if con.ALIAS_PANED == 'ttk':
			gv.aliasPaned.sashpos(0, posn)
		else:
			gv.aliasPaned.sash_place(0, posn, 0)
		gv.root.update_idletasks()
		gv.aliasDefn.bind('<Configure>', binding)

## app utilities ##############################################################
## code required by modules that cannot import the other

def fmtServerAddress(server, port):
	return '{}{}{}'.format(server if server else 'port',
							':' if server else ' ', port)

def setAppTitle(tcp):
	gv.root.title('{} ({})'.format(con.DEBUGGER_TITLE, tcp))

# noinspection PyUnusedLocal
def paneConfig(event=None):
	gv.root.update_idletasks()
	gv.sashPosns['SashOffset'] = gv.appWindow.sashpos(0)
	return 'break'

def positionAppSash(yOffset=None, init=False):
	gv.root.update_idletasks()
	appH = gv.appWindow.winfo_height()
	if not yOffset or yOffset > appH:
		# bodyY = gv.bodyText.winfo_rooty()
		# bodyH = gv.bodyText.winfo_height()
		# cmdY = gv.cmdLine.winfo_rooty()
		# sashH = cmdY - (bodyY + bodyH)
		sashH = 5 # ?fixed in ttk
		btnH = gv.btnRun.winfo_height()
		yOffset = appH - sashH - 2 * btnH
	gv.appWindow.sashpos(0, yOffset)
	gv.root.update_idletasks()
	if not init:
		gv.sashPosns['SashOffset'] = gv.appWindow.sashpos(0)
	return yOffset

def appConfig(event=None):
	width, height = mu.getAppDimns(gv.root)
	if event:
		closeAnyOpenFrames(event)
		if gv.appWidth != width:
			# remove any previous after, set new one
			# - ensures gridMenuButtons not called until resizing stops for
			#   at least gv.tkTiming['slow'] ms
			removeAfter('gridMenuButtons')
			afterLoop(gv.tkTiming['slow'], 'gridMenuButtons',
									gv.gridMenuButtons)
	gv.appWidth, gv.appHeight = width, height
	return 'break'

# noinspection PyUnusedLocal
def liftMainWindow(event=None):
	gv.root.lift()
	gv.root.attributes('-topmost', True)
	gv.root.after_idle(gv.root.attributes, '-topmost', False)

def closeAnyOpenFrames(event=None):
	# a postcommand to pull down menus, closes/lowers any open windows
	# - as using .grid, .lift/.lower only work on siblings, so we
	#   lower by raising the main app's window
	for name, tkEnt in gv.popupWindows.items():
		if name.startswith('Search'):
			box = tkEnt.searchBox
			if box.searchUser is box and box.shared.winfo_ismapped():
				box.closeSearchBox(event)
				# - this sets instance's 'searchXY'
				gv.save20History('SearchTerms', box.searchTarget)
		else: # it's aliasWindow or grepWindow
			if tkEnt.winfo_ismapped():
				# cannot test using event.widget as it may be None
				width, height, xOffset, yOffset = mu.parseGeometry(tkEnt)
				x, y = gv.root.winfo_pointerxy()
				# check if mouse is outside tkEnt
				if xOffset <= x <= xOffset + width \
						and yOffset <= y <= yOffset + height:
					continue
				if (tkEnt is gv.aliasWindow and gv.aliasDefn.edit_modified()) \
						or (tkEnt is gv.grepWindow and gv.searchRunning == 'running'):
					liftMainWindow(event)
					continue

				# rather than adding a close callback to TopWindow...
				gv.root.call(tkEnt.protocol('WM_DELETE_WINDOW'))

	if gv.fontSelect and gv.fontSelect.state() == 'normal':
		# the 'Select Font' window is open
		gv.fontSelect.closeTop()

def queryTimeAcceleration():
	gv.app.queueSilentCmd('timeAccelerationFactor', 'timeAccelQuery',
							gv.debugOptions['timeAccel'])

## font string fns #############################################################

def measurePhrase(phrase, emphasized=False):
	font = gv.OoFonts['emphasis'] if emphasized else gv.OoFonts['default']
	space = gv.eSpaceLen if emphasized else gv.spaceLen
	cache = gv.measuredEWords if emphasized else gv.measuredWords
	words = phrase.split(' ')
	width = (len(words) - 1) * space
	for word in words:
		if word not in cache:
			cache[word] = font.measure(word)
		width += cache[word]
	return width

def largestMeasure(phrases, emphasized=False):
	largest = 0
	for phrase in phrases:
		width = measurePhrase(phrase, emphasized)
		if width > largest:
			largest = width
	return largest

def _fontPad(string, length, where='left'):
	if len(string) == 0:
		return string
	smallest = min(gv.whiteSpaceChrs.values())
	fontLen = measurePhrase(string)
	if length - fontLen < smallest:
		return string
	for uchar, space in gv.whiteSpaceChrs.items():
		while (length - fontLen - space) >= 0:
			if where == 'left':
				string = uchar + string
			else:
				string += uchar
			fontLen += space
	return string

def rightFontPad(string, length):
	return _fontPad(string, length, where='right')

def leftFontPad(string, length):
	return _fontPad(string, length, where='left')

def centerFontPad(string, length):
	fontLen = measurePhrase(string)
	padding = (length - fontLen) / 2
	return leftFontPad(string, padding + fontLen)
