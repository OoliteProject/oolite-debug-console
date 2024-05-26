# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys
from collections import OrderedDict
import pdb, traceback

import win32con

_Python2 = sys.version_info[0] == 2
if _Python2:
	import Tkinter as tk
	import tkFont
	import ttk
else:
	import tkinter as tk
	import tkinter.font as tkFont
	import tkinter.ttk as ttk
	
import debugGUI.appUtils as au
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.stringUtils as su

class TopWindow(tk.Toplevel):
	def __init__(self, master, title='', enduring=False, 
								showNow=True, **kwargs):
		tk.Toplevel.__init__(self, master, **kwargs)
		self.transient(master)
		self.setTitle(title)
		self.enduring = enduring
		if enduring: 					
			# override the 'X' from destroying window
			self.protocol('WM_DELETE_WINDOW', self.closeTop)
		self.resizable(width=False, height=False)
		self.twFrame = ttk.Frame(self, name=mu.TkName('twFrame'))
		self.twFrame.grid(sticky='news')
		if showNow:
			self.focus_set()
		else:
			self.withdraw()
		self.mouseXY = None

	def savePosition(self):
		_, _, Xoff, Yoff = mu.parseGeometry(self)
		if Xoff == 0 and Yoff == 0:	
			# newly minted widget, ie. never mapped
			# don't clobber any existing saved values
			return					
		self.mouseXY = [Xoff, Yoff]

	def center(self):
		toplevel = self.master.winfo_toplevel()
		width, depth, Xoff, Yoff = mu.parseGeometry(toplevel)
		winWidth, winDepth, _, _ = mu.parseGeometry(self)
		winXoff = Xoff + (width>>1) - (winWidth>>1)
		winYoff = Yoff + (depth>>1) - (winDepth>>1)
		self.geometry('{}x{}+{}+{}'.format(winWidth, winDepth, winXoff, winYoff))
		self.mouseXY = [winXoff, winYoff]
		self.restoreTop()

	def showAtMouse(self, coords=None, offsetX=0, offsetY=0):
		if self.mouseXY is None and coords is None:
			self.mouseXY = self.winfo_pointerxy()
		x, y = self.mouseXY if coords is None else coords
		self.mouseXY = [x + offsetX, y + offsetY]
		self.restoreTop()

	def setTitle(self, name):
		if name and len(name) > 0:
			self.title(name)

	def openTop(self):
		if self.mouseXY is None:
			self.showAtMouse()
		else:
			self.restoreTop()

	def restoreTop(self):
		if self.mouseXY is not None:
			self.geometry('+{}+{}'.format(*self.mouseXY))
		self.deiconify()
		# lift required in pyinstaller version else 
		# fontSelectTop won't show (anywhere!)
		self.lift()						
		self.focus_set()

	# noinspection PyUnusedLocal
	def closeTop(self, event=None):
		if self.enduring:
			# creation delayed until opened 
			# (closeTop may precede; see closeAnyOpenFrames)
			if self.mouseXY:
				self.savePosition()		# preserve user's positioning of window
			self.withdraw()
		else:
			self.destroy()
		return 'break'
# end class TopWindow

class OoInfoBox(TopWindow):
	infoBox = None
	font = None
	destruct = None

	# noinspection PyMissingConstructor
	def __init__(self, master, msg, label=False, font=None,
								destruct=None, error=False):
		cls = self.__class__
		cls.focusOnInit = master.focus_get()
		cls.destruct = destruct

		if font is None:
			font = gv.OoFonts.get('default', None)
		if font is None:
			defFont = con.defaultConfig['Font']
			font = tkFont.Font(family=defFont.get('Family', 'Arial'),
								size=defFont.get('Size',   '10'))
		cls.font = font

		if cls.infoBox is None: # only one instance created; gets recycled
			self.makeWidgets(master)
		# cannot be .transient as will lift its master when gridded
		cls.infoBox.transient('')

		if con.NL in msg:
			widest = max((len(line), line) for line in msg.split(con.NL))
			width, maxLine = widest
			msgLen = font.measure(maxLine)
			width = (msgLen // font.measure('0')) + 1
		else:
			width = len(msg)
		width = max(width + 4, 40)		# 2 blank chars each side
		boxLen = width * font.measure('0')
		msg = '\n{}\n'.format(msg)		# vertical whitespace

		title = label if label and len(label) \
					else ('Error' if error else 'Message')
		cls.infoBox.setTitle(title)
		# cls.msgBoxLabel.config(text=msg, width=width)
		lines = [au.centerFontPad(line, boxLen) for line in  msg.split(con.NL)]
		txt = cls.msgBoxText
		txt.config(width=width, height=msg.count(con.NL) + 1)
		txt.tag_remove('sel', '1.0', 'end')
		txt.delete('1.0', 'end')
		txt.insert('end', con.NL.join(lines))

		infoBoxFrame = cls.infoBox.twFrame

		if destruct is None:
			cls.msgBoxSpinFrame.grid_remove()
			infoBoxFrame.columnconfigure(0, weight=1)
			infoBoxFrame.columnconfigure(1, weight=1)
			cls.msgBoxOK.grid(row=1, column=0, sticky='s',
							  padx=4, pady=4, columnspan=3)
		else:
			# Spinbox uses a StringVar
			cls.msgBoxSpinVar.set(str(cls.destruct))
			cls.destructID = cls.infoBox.after(1000, cls.destructMessage)
			# to center OK button (almost)
			infoBoxFrame.columnconfigure(0, weight=1)
			infoBoxFrame.columnconfigure(1, weight=3)
			cls.msgBoxOK.grid(row=1, column=1, sticky='w', padx=4, pady=4)
			cls.msgBoxSpinFrame.grid(row=1, column=0, sticky='w',
									 padx=4, pady=4)

		_, noTitleHeight = mu.getWidgetWH(master)
		mWidth, mHeight, xRoot, yRoot = mu.parseGeometry(master)
		titleH = mHeight - noTitleHeight
		iWidth, iHeight = mu.getWidgetWH(infoBoxFrame)
		iHeight += titleH
		cls.infoBox.mouseXY[0] = xRoot + (mWidth - iWidth) // 2
		cls.infoBox.mouseXY[1] = yRoot + (mHeight - iHeight) // 2
		cls.infoBox.restoreTop()

		cls.msgBoxOK.focus_set()
		if destruct is None:
			# 'Toplevel' object has no attribute 'grab' 
			# => master should be/inherit Frame
			infoBoxFrame.grab_set()

	@classmethod
	def makeWidgets(cls, master):
		cls.master = master
		cls.infoBox = TopWindow(master, name=mu.TkName('ooInfoBox'),
							enduring=True, showNow=False)
		cls.infoBox.bind('<Escape>', cls.closeMessageBox)
		cls.infoBox.protocol('WM_DELETE_WINDOW', cls.closeMessageBox)
		cls.infoBox.mouseXY = [-1, -1]
		infoBoxFrame = cls.infoBox.twFrame

		# cls.msgBoxLabel = ttk.Label(infoBoxFrame, font=cls.font,
		# 							name=mu.TkName('msgBoxLabel'),
		# 							anchor='center', justify='center')

		cls.msgBoxText = tk.Text(infoBoxFrame, font=cls.font,
									name=mu.TkName('msgBoxText'))
		cls.msgBoxText.editable = False
		cls.msgBoxText.popup = TextPopup(cls.msgBoxText, font=cls.font,
										 disabledFont=cls.font,
										 searchPrefix='OoInfoBox')

		cls.msgBoxOK = ttk.Button(infoBoxFrame, text='OK',
								   name=mu.TkName('msgBoxOK'), width=6,
								   command=cls.closeMessageBox)
		cls.msgBoxOK.bind('<Escape>', cls.closeMessageBox)
		cls.msgBoxOK.bind('<Return>', cls.closeMessageBox)
		# cls.msgBoxLabel.grid(row=0, column=0, sticky='n',
		# 					columnspan=3, padx=8)
		cls.msgBoxText.grid(row=0, column=0, sticky='n',
							columnspan=3, ipadx=8)
		# msgBoxOK gridded in __init__ depending on destruct

		# for askYesNo
		cls.askingVar = tk.IntVar(name=mu.TkName('ooInfoBox', 'askingVar'),
								   value=-1)
		cls.msgBoxNo = ttk.Button(infoBoxFrame,
								name=mu.TkName('msgBoxNo'), 
								text='No', width=6,
								command=cls.negativeReply)

		# for self destructing msg
		cls.msgBoxSpinFrame = ttk.Frame(infoBoxFrame,
										 name=mu.TkName('msgBoxSpinFrame'))
		cls.msgBoxSpinVar = tk.StringVar(value=str(cls.destruct),
										  name=mu.TkName('msgBoxSpinVar'))
		cls.msgBoxSpinLabel = ttk.Label(cls.msgBoxSpinFrame,
										name=mu.TkName('msgBoxSpinLabel'),
										text='closing in:',
										font=cls.font, anchor='w')	# , padx=10
		cls.msgBoxSpinbox = tk.Spinbox(cls.msgBoxSpinFrame,
										name=mu.TkName('msgBoxSpinbox'),
										exportselection=0, from_=0, to=10,
										increment=1, font=cls.font, width=2,
										textvariable=cls.msgBoxSpinVar)
		cls.msgBoxSpinbox.bind('<Enter>', cls.haltDestruct)
		# in msgBoxSpinFrame
		cls.msgBoxSpinLabel.grid(row=0, column=0, sticky='e')
		cls.msgBoxSpinbox.grid(row=0, column=1, sticky='w')

	destructID = None
	@classmethod
	def destructMessage(cls):
		cls.destructID = None
		cls.msgBoxSpinbox.invoke('buttondown')
		count = int(cls.msgBoxSpinVar.get())
		if count > 0:
			cls.destructID = cls.infoBox.after(1000, cls.destructMessage)
		elif cls.msgBoxNo.winfo_ismapped():
			cls.negativeReply()
		else:
			cls.closeMessageBox()

	# noinspection PyUnusedLocal
	@classmethod
	def haltDestruct(cls, event=None):
		if cls.destructID is not None:
			cls.infoBox.after_cancel(cls.destructID)
			cls.destructID = None

	@classmethod
	def askYesNo(cls):
		cls.msgBoxOK['text'] = 'Yes'	# repurpose existing button
		cls.msgBoxOK['command'] = cls.positiveReply
		noCol = 1 if cls.destruct else 0
		cls.msgBoxNo.grid(row=1, column=noCol, sticky='w',
							padx=4, pady=4)
		cls.msgBoxOK.grid(row=1, column=2, sticky='w',
							padx=4, pady=4, columnspan=2)
		cls.msgBoxNo.bind('<Return>', cls.negativeReply)
		cls.msgBoxOK.bind('<Return>', cls.positiveReply)
		cls.msgBoxNo.focus_set()
		cls.infoBox.twFrame.wait_variable(cls.askingVar)
		return cls.askingVar.get() == 1

	@classmethod
	def resetAfterYesNo(cls):
		# reverse effect from askYesNo
		cls.msgBoxOK['text'] = 'OK'	# restore existing button
		cls.msgBoxOK['command'] = cls.closeMessageBox
		cls.msgBoxNo.grid_remove()
		# msgBoxOK gridded in __init__ depending on destruct
		cls.msgBoxNo.unbind('<Return>')
		cls.msgBoxOK.bind('<Return>', cls.closeMessageBox)

	# noinspection PyUnusedLocal
	@classmethod
	def negativeReply(cls, event=None):
		cls.askingVar.set(0)
		cls.closeMessageBox()
		cls.resetAfterYesNo()
		return 'break'

	# noinspection PyUnusedLocal
	@classmethod
	def positiveReply(cls, event=None):
		cls.askingVar.set(1)
		cls.closeMessageBox()
		cls.resetAfterYesNo()
		return 'break'

	# noinspection PyUnusedLocal
	@classmethod
	def closeMessageBox(cls, event=None):
		cls.msgBoxNo.unbind('<Return>')
		cls.msgBoxOK.unbind('<Return>')
		
		if cls.destructID is not None:
			cls.infoBox.after_cancel(cls.destructID)
			cls.destructID = None
		cls.infoBox.closeTop()
		cls.infoBox.twFrame.grab_release()
		if cls.focusOnInit:
			cls.infoBox.after_idle(cls.focusOnInit.focus_force)
		return 'break'
# end class OoInfoBox

class OoBarMenu(tk.Menu):				# for menubar that support fonts!
	menus = []							
	buttons = []
	def __init__(self, master, label, font, disabledFont=None, 
										style=None, **kwargs):
		self.label = label
		self.font = font
		self.disabledFont = disabledFont
		self.menuButton = ttk.Menubutton(master,
										name=mu.TkName(label, 'menuButton'),
										text=self.label, style=style)
		OoBarMenu.buttons.append(self.menuButton)
		self.menuButton.bind('<FocusOut>', self.closeMenu)
		# if con.IS_WINDOWS_PC and False:
		# 	self.menuButton.bind('<Leave>', self.closeMenu)
		# 	# only the OS can close a menu (?),
		# 	# so this at least keeps their 'open' flags in sync
		tk.Menu.__init__(self, master, tearoff=0, font=font, **kwargs)
		
		self.menuButton['menu'] = self ###
		self._index = len(OoBarMenu.menus)
		OoBarMenu.menus.append(self)
		self.menuButton.grid(row=0, column=self._index, sticky='w')
		self.menuIndices = {}				# indices of sub-menu items
		self.statesVary = {}
		self.isOpen = False

	# noinspection PyUnusedLocal
	def closeMenu(self, event=None):
		if self.isOpen and con.IS_LINUX_PC:
			self.unpost()
			# This subcommand does not work on Windows and the Macintosh, as
			# those platforms have their own way of un-posting menus. (tcl8.5)
		self.isOpen = False

	# def toggleMenu(self, event=None):
		# if not self.isOpen:
			# openXY = [self.master.winfo_rootx() + self.menuButton.winfo_x(),
					  # self.master.winfo_rooty() + self.menuButton.winfo_y() \
						# + self.menuButton.winfo_height()]
			# for menu in OoBarMenu.menus:
				# if isinstance(menu, ttk.Button):# is an alias button
					# continue
				# if menu != self:		# prevent flashing on Linux??
					# menu.closeMenu()
			# self.isOpen = True
			# self.post(*openXY)			# we wait for the menu to close
		# else:
			# self.closeMenu()

	def _add(self, kind, **kwargs):
		label = kwargs.get('label', None)
		if not label: 
			return
		stateChange = kwargs.pop('stateChange', None)
		if stateChange:
			self.statesVary[label] = stateChange
		font, disabled = self.font, self.disabledFont
		state = kwargs.get('state', None)
		if state and disabled:
			font = disabled if state == 'disabled' else font
		self.add(kind, font=font, **kwargs)
		self.menuIndices[label] = self.index('end')

	def add_cascade(self, **kwargs):
		self._add('cascade', **kwargs)

	def add_checkbutton(self, **kwargs):
		self._add('checkbutton', **kwargs)

	def add_command(self, **kwargs):
		self._add('command', **kwargs)

	def add_radiobutton(self, **kwargs):
		self._add('radiobutton', **kwargs)

	def add_separator(self, **kwargs):
		# bypass _add as never change state, color
		self.add('separator', **kwargs)	
				
	def changeAllStates(self, newState):
		font = self.disabledFont if newState == 'disabled' else self.font
		for label in self.statesVary:
			index = self.menuIndices.get(label, None)
			if index is not None:
				self.entryconfigure(index, font=font, state=newState)
		
	def removeOnesSelf(self):
		if self.menuButton in OoBarMenu.buttons:
			OoBarMenu.buttons.remove(self.menuButton)
		if self in OoBarMenu.menus:
			OoBarMenu.menus.remove(self)
		self.menuButton.destroy()
		self.destroy()
# end class OoBarMenu

class ToolTip(tk.Toplevel):
	# singleton widget used for all tool tips
	_tip = None
	# references to all instances (may not be saved by caller)
	# - values are list of instances as some tips are repeated among widgets
	_tip_instances = {}

	def __new__(cls, master, msg, delay=400, group=None,
				allowFunc=None, allowHide=True):
		if len(msg.strip()) == 0 or delay == 0:
			return
		return object.__new__(cls)

	# noinspection PyMissingConstructor
	def __init__(self, master, msg, delay=400, group=None,
				 allowFunc=None, allowHide=True):
		self.master = master
		self.msg = msg
		self.delay = delay # in ms
		self.group = group
		self.allowFunc = allowFunc
		self.allowHide = allowHide

		# widget is re-used for all tool tips
		cls = self.__class__
		if cls._tip is None:
			cls._tip = tk.Toplevel(self.master, name=mu.TkName('ToolTip'))
			cls._tip.withdraw()
			cls._w = cls._tip._w
			cls._tip.wm_overrideredirect(True)
			# cls._tip.resizable(width=False, height=False)
			cls.frame = ttk.Frame(cls._tip, borderwidth=2, relief='groove',
								  name=mu.TkName('ToolTip', 'frame'))
			cls.frame.grid(sticky='news')
			cls.labelVar = tk.StringVar(name=mu.TkName('ToolTip', 'labelVar'))
			cls.label = ttk.Label(cls.frame, textvariable = cls.labelVar,
								  name=mu.TkName('ToolTip', 'label'),
								  style='toolTip.TLabel')
			cls.label.grid(row=0, column=0, ipadx=2, ipady=2)
			cls.hideTip = ttk.Button(cls.frame, text='(don\'t show this tip)',
									 name=mu.TkName('ToolTip', 'hideTip'),
									 style = 'toolTip.TButton')
			cls.hideTip.grid(row=1, column=0, sticky='w')
			cls.frame.columnconfigure(0, weight=1)
		self.tk = cls._tip.tk
		self.placed = 0
		self._resetTip()

		# tips can be grouped when there is more than 1 instance of master
		# - when a tip is quieted by user, this will apply to all in group
		# noinspection PyProtectedMember
		cls._tip_instances.setdefault(self.instanceName(), []).append(self)

		self.funcIDs = {}
		for sequence, func in [('<Enter>', self._enterWidget),
							   ('<Leave>', self._leaveWidget),
							   ('<ButtonPress>', self._leaveWidget)]:
			self.funcIDs[sequence] \
				= (master, master.bind(sequence, func, add=True))

	# noinspection PyUnusedLocal
	def _enterWidget(self, event=None): # master's <Enter> handler
		# have entered the master widget
		self._resetTip()
		if self.allowFunc and callable(self.allowFunc):
			permission = self.allowFunc()
			if not permission:
				return 'continue'
		self.lastMsY = self.winfo_pointery()
		self._bindEvent('<Motion>', self._mouseMoved)
		# tk widgets are shared
		self.labelVar.set(self.msg)
		self.hideTip.configure(command=self.suppressTip)
		# start countdown
		self._setAfter()
		return 'continue'

	# noinspection PyUnusedLocal
	def _leaveWidget(self, event=None): # master's <Leave> handler
		# have left the master widget
		if '<Motion>' in self.funcIDs:
			# will be on initial entry but not if returning from
			# tip or from outside app
			self._unbindEvent('<Motion>')
		_, _, overTip = self._mouseOverTip()
		if overTip:
			self._enterTip(event)
		else:
			self._resetTip()
		self._cancelAfter()
		return 'continue'

	def _resetTip(self, reset=True):
		if self.placed != 0:
			self._tip.withdraw()
		# placed: -1 for above master, +1 for below, 0 for withdrawn
		self.placed = 0
		self.lastMsY = None
		self.currGeometry = None
		# allow tip if entering widget but not if coming from tip
		if reset:
			self.tipShown = None

	# noinspection PyUnusedLocal
	def _enterTip(self, event=None): # toolTip's <Enter> handler
		# remove <Enter> so tip doesn't show if return to master
		self._unbindEvent('<Enter>')
		# move <Leave> binding to hide tip when leave tip
		self._unbindEvent('<Leave>')
		self._bindEvent('<Leave>', self._leaveTip, widget=self._tip)

	# noinspection PyUnusedLocal
	def _leaveTip(self, event=None): # toolTip's <Leave> handler
		msX, msY = self.winfo_pointerxy()
		widget = event.widget if event and hasattr(event, 'widget') else None
		self._resetTip(False)
		# re-entered master from tip, restore bindings
		self._unbindEvent('<Leave>')
		self._bindEvent('<Leave>', self._leaveWidget)
		# delay rebinding of <Enter> so the tip doesn't reappear
		# if we've returned to widget
		self.after(self.delay, self._bindEnterWidget)

	def _bindEnterWidget(self):
		# delayed restoration of widget's <Enter> binding
		self._bindEvent('<Enter>', self._enterWidget)

	def _mouseOverTip(self):
		msX, msY = self.winfo_pointerxy()
		if self.placed == 0:
			# for case when returning to app, both _enterWidget
			# and _leaveWidget are immediately invoked
			return msX, msY, False
		if self.currGeometry is None:
			self.currGeometry = mu.parseGeometry(self._tip)
		width, height, rootX, rootY = self.currGeometry
		return msX, msY, (rootX < msX < (rootX + width)
						  and rootY < msY < (rootY + height))

	lastMsY = None
	# noinspection PyUnusedLocal
	def _mouseMoved(self, event=None):
		if self.tipShown is None:
			# not shown on this <Enter>, (re)set countdown timer
			self._setAfter()
			self.lastMsY = self.winfo_pointery()
		elif self.placed != 0:
			# remove showing tip if motion exceeds delta
			msX, msY, overTip = self._mouseOverTip()
			tipX, tipY = self.tipShown
			deltaX, deltaY = abs(msX - tipX), abs(msY - tipY)
			towardsTip = (msY <= self.lastMsY and self.placed < 0) \
						 or (msY >= self.lastMsY and self.placed > 0)
			if not towardsTip and not overTip and deltaX + deltaY > 8:
				self._resetTip()
				self._cancelAfter()
			self.lastMsY = msY
		return 'continue'

	afterId = None
	def _setAfter(self):
		self._cancelAfter()
		self.afterId = self.after(self.delay, self._showTip)

	def _cancelAfter(self):
		if self.afterId:
			self.after_cancel(self.afterId)
			self.afterId = None

	@classmethod
	def cancelAnyAfters(cls):
		for instList in cls._tip_instances.values():
			for inst in instList:
				# noinspection PyProtectedMember
				inst._cancelAfter()

	def _showTip(self):
		if self.allowHide:
			self.__class__.hideTip.grid()
		else:
			self.__class__.hideTip.grid_forget()
		self.master.update_idletasks()
		# parseGeometry calls update_idletasks
		hostW, _, hostX, _ = mu.parseGeometry(self.master.winfo_toplevel())
		labelW = max(self.label.winfo_width(), self.hideTip.winfo_width())
		labelH = self.label.winfo_height()
		if self.allowHide:
			labelH += self.hideTip.winfo_height()
		# self._tip.minsize(width=labelW, height=labelH) # auto forms to text
		destX, destY = self.master.winfo_rootx(), self.master.winfo_rooty()

		# place toolTip above master if possible else below
		# NB: - 1 pixel to ensure overlap and allow mouse traversal
		if destY - labelH >= 0:
			destY -= labelH - 1
			self.placed = -1
		else:
			destY += self.master.winfo_height() - 1
			self.placed = 1
		# right justify if will run off edge of widget
		if destX + labelW > hostX + hostW:
			destX = hostX + hostW - labelW
		self._tip.geometry('+{}+{}'.format(destX, destY))
		self._tip.transient(self.master)
		self._tip.deiconify()
		self._tip.lift()
		self.tipShown = self.winfo_pointerxy()

	def _bindEvent(self, sequence, func, widget=None):
		target = widget if widget else self.master
		self.funcIDs[sequence]\
			= (target, target.bind(sequence, func, add=True))

	# noinspection PyProtectedMember
	def _unbindEvent(self, sequence):
		widget, funcID = self.funcIDs.pop(sequence, (None, None))
		if widget and funcID:
			mu.unbindAdded(sequence, widget, funcID)

	def _clear(self):
		for sequence, callback in self.funcIDs.items():
			mu.unbindAdded(sequence, *callback)
		self.funcIDs.clear()
		# noinspection PyProtectedMember
		self._tip_instances.pop(self.instanceName(), None)

	def instanceName(self):
		# noinspection PyProtectedMember
		return self.group if self.group else self.master._name

	# noinspection PyProtectedMember
	def suppressTip(self): # allow caller to prevent tip
		self._resetTip(True)
		for instance in reversed(
				self._tip_instances[self.instanceName()]):
			instance._clear()

	@classmethod
	def limitToolTips(cls, names):
		for tip in cls.allToolTipNames():
			if tip not in names:
				for instance in cls._tip_instances[tip]:
					# noinspection PyProtectedMember
					instance._clear()

	@classmethod
	def allToolTipNames(cls):
		return list(cls._tip_instances.keys())
# end class ToolTip

class OoCombobox(ttk.Entry):
	""" re-implementation of combobox.tcl for better access/control
	"""
	_toolTip = None		# singleton for use by all instances
	instances = []		# list for manually applying style
	_BOX_HEIGHT = 10	# max depth of drop down list (less room for buttons)
	_BOX_PAD = 2		# for padx & pady

	def __init__(self, master, name, *args, **kwargs):
		self.width = kwargs.pop('width', 20)
		self.postcommand = kwargs.pop('postcommand', self.adjustEntry)
		self.preProcessFn = kwargs.pop('preProcessFn', None)
		## - button image set as part of style
		self.selectors = 0

		# frame stands in for combobox; gridded by caller
		# (see grid method overrides below)
		self.combo = ttk.Frame(master, name=mu.TkName(name, 'combo'),
							   style='ComboboxPopdownFrame')

		self.entryValue = tk.StringVar(name=mu.TkName(name, 'entryValue'))
		entryOptions = kwargs.copy()
		entryOptions.update(con.ENTRY_OPTIONS)
		ttk.Entry.__init__(self, self.combo, width=self.width, name=name,
						   textvariable=self.entryValue, **entryOptions)
		# Entry widget is less deep so expand to fit
		# (frame is colored and would show through)
		ttk.Entry.grid(self, row=0, column=0, sticky='ns')
		self.__class__.instances.append(self)

		# remove ttk.Entry specific keys
		for key in ['validate', 'validatecommand', 'name']:
			kwargs.pop(key, None)
		self.toggle = ttk.Button(self.combo, name=mu.TkName(name, 'toggle'),
								 style='history.TCheckbutton',
								 command=self.toggleList, **kwargs)
		self.toggle.grid(row=0, column=1, sticky='e',
						 padx=(self._BOX_PAD // 2, self._BOX_PAD),
						 pady=self._BOX_PAD)

		self.toplevel = self.popdownTopLevel()
		self.listboxes = None
		self.popdown = self.popdownWindow()
		self.tk_lbHover = self.register(self.lbHover)
		self.tk_showTip = self.register(self._showTip)
		self.tk_bindTip = self.register(self.bindTip)
		self.tk_unbindTip = self.register(self.unbindTip)
		self.setBindings()
		self.checkboxes = OrderedDict()

		cls = self.__class__
		# singleton internal toolTip for long entries
		# not to be confused w/ singleton class ToolTip
		if cls._toolTip is None:
			cls._toolTip = tk.Toplevel(self,
								name=mu.TkName('OoCombobox', 'toolTip'))
			cls._toolTip.wm_overrideredirect(True)
			cls._toolTip.resizable(width=False, height=False)
			cls._toolTipLabel = ttk.Label(self._toolTip, style='toolTip.TLabel',
								name=mu.TkName('OoCombobox', 'toolTipLabel'))
			cls._toolTipLabel.grid()
			cls._toolTip.withdraw()

	# grid manager overrides ##################################################

	def grid_configure(self, *args, **kw):
		self.combo.grid_configure(*args, **kw)
	grid = grid_configure

	def grid_forget(self):
		self.combo.grid_forget()

	def grid_remove(self):
		self.combo.grid_remove()

	# tooltip methods #########################################################

	# noinspection PyUnusedLocal,PyAttributeOutsideInit
	def enterEntry(self, event=None):
		# '<Enter>' handler for Entry widget
		self.font = tkFont.nametofont(str(self.cget('font')))
		if not self._entryTextFits(self.get()):
			x = self.winfo_rootx()
			y = self.winfo_rooty() + self.winfo_height()
			self._raiseTip(x, y)
		else:
			self._toolTipLabel.grid_remove()
		return 'continue'

	# noinspection PyUnusedLocal
	def leaveEntry(self, event=None):
		# '<Leave>' handler for Entry widget
		if self._toolTip.state() == 'normal':
			self._toolTip.withdraw()
		# do not return 'break' as it will kill scrolling
		return 'continue'

	# noinspection PyUnusedLocal,PyAttributeOutsideInit
	def bindTip(self, event=None):
		# '<Enter>' handler for Listbox item
		# event binder for listbox items too long to display
		self.font = tkFont.nametofont(str(self.cget('font')))
		self._lastListItemFit = False
		self._lastListItemIdx = -1
		self._showTip()
		for box in self.listboxes:
			box.unbind('<Motion>')
			box.bind('<Motion>', self.tk_showTip, add=True)
		return 'break'

	# noinspection PyUnusedLocal
	def unbindTip(self, event=None):
		# '<Leave>' handler for Listbox item
		# remove bindings for listbox items
		for box in self.listboxes:
			box.unbind('<Motion>')
			box.bind('<Motion>', self.tk_lbHover, add=True)
		self._toolTip.withdraw()
		return 'break'

	# noinspection PyUnusedLocal
	def _showTip(self, event=None):
		# display internal tooltip if item too long to display
		if self.pdList.size() == 0:
			return
		boxTop, index = self._itemUnderMouse()
		self.highlightRow(index)
		if self._toolTip.state() == 'normal' \
				and self._lastListItemIdx == index:
			return
		if self._listboxTextFits(index):
			self._toolTip.withdraw()
			return
		bbox = self.pdList.bbox(index)
		if isinstance(bbox, (list, tuple)):
			_, lbY, _, lbHeight = bbox
			# NB: tip can be deeper than listbox item
			x = self.pdList.winfo_rootx()
			y = boxTop + lbY + lbHeight
			# never show tooltip under mouse as will generate <Leave> event
			labelH = self._toolTipLabel.winfo_height()
			msY = self.winfo_pointery()
			if y <= msY <= y + labelH:
				self._toolTip.withdraw()
			else:
				self._raiseTip(x, y)

	_lastListItemFit = False
	_lastListItemIdx = -1
	def _listboxTextFits(self, idx):
		# decide if a tooltip is needed
		# - measure results cached as bound to mouse movement
		if idx == self._lastListItemIdx:
			return self._lastListItemFit
		text = self.pdList.get(idx)
		measured = self.font.measure(text)
		self._toolTipLabel.config(text=text)
		self._toolTipLabel.grid()
		self.update_idletasks()
		lbWidth = self.pdList.winfo_width()
		self._lastListItemFit = measured < lbWidth
		self._lastListItemIdx = idx
		return self._lastListItemFit

	def _raiseTip(self, x, y):
		# shows internal tooltip for long items
		# used for both Entry widget and Listbox items
		self._toolTip.geometry('+{}+{}'.format(x, y))
		self._toolTip.transient(self.pdList)
		self._toolTip.deiconify()
		self._toolTip.lift(aboveThis=self.pdList)

	def _entryTextFits(self, text):
		measured = self.font.measure(text)
		self._toolTipLabel.config(text=text)
		self._toolTipLabel.grid()
		self.update_idletasks()
		return measured < self.winfo_width()

	def _itemUnderMouse(self):
		self.update_idletasks()
		boxTop = self.pdList.winfo_rooty()
		nearest = self.pdList.nearest(self.winfo_pointery() - boxTop)
		return boxTop, nearest

	# functions from combobox.tcl #############################################

	# noinspection PyUnusedLocal
	def traverseIn(self, event=None):
		# proc ttk::combobox::TraverseIn {w}
		# receive focus due to keyboard navigation
		# For editable comboboxes, set the selection and insert cursor.
		if self.instate(['!readonly', '!disabled']):
			self.selection_range(0, 'end')
			self.icursor('end')
		return 'break'

	def selectEntry(self, index):
		# proc ttk::combobox::SelectEntry {cb index}
		# Set the combobox selection in response to a user action.
		items = self.getList()
		if -1 < index < len(items):
			self.set(items[index])
			# self.select_range(0, 'end')
			self.icursor('end')
			self.event_generate('<<ComboboxSelected>>', when='mark')
		return 'break'

	# noinspection PyUnusedLocal
	def lbSelected(self, box, event=None):
		# proc ttk::combobox::LBSelected {lb}
		# Activation binding for listbox
		# Set the combobox value to the currently-selected listbox value
		# and unpost the listbox.
		self.lbSelect(box)
		if box is self.pdList:
			self.unpost()
			self.focus_set()
		return 'break'

	# noinspection PyUnusedLocal
	def lbCancel(self, event=None):
		# proc ttk::combobox::LBCancel {lb}
		# Unpost the listbox.

		# focus is None when user leaves application
		focus = self.focus_get()
		if focus and focus is self.toggle:
			# do not disturb toggle state (toplevel's binding is for
			# trapping events outside toplevel)
			return 'break'
		self.unpost()
		return 'break'

	# noinspection PyUnusedLocal
	def lbTab(self, box, dirn, event=None):
		# ttk::combobox::LBTab {lb dir}
		# Tab key binding for combobox listbox.
		# Set the selection, and navigate to next/prev widget.
		newFocus = None
		if dirn == 'next':
			if self.selectors == 0 or box is self.listboxes[-1]:
				newFocus = self.combo.tk_focusNext()
			else:
				newFocus = self.listboxes[self.listboxes.index(box) + 1]
		elif dirn == 'prev':
			if self.selectors == 0 or box is self.listboxes[0]:
				newFocus = self.combo.tk_focusPrev()
			else:
				newFocus = self.listboxes[self.listboxes.index(box) - 1]
		if box is self.pdList:
			self.lbSelect(box)
		if newFocus:
			self.unpost()
			self.after_idle(newFocus.focus_set)
		return 'break'

	# noinspection PyUnusedLocal
	def lbHover(self, event=None):
		# proc ttk::combobox::LBHover {w x y}
		# <Motion> binding for combobox listbox.
		# Follow selection on mouseover.
		if event and hasattr(event, 'widget'):
			box = event.widget
			if box in self.listboxes:
				x, y = box.winfo_pointerxy()
				rooty = box.winfo_rooty()
				index = box.index('@{},{}'.format(x, y - rooty))
				self.highlightRow(index)
		return 'break'

	# noinspection PyUnusedLocal
	def mapPopdown(self, event=None):
		# proc ttk::combobox::MapPopdown {w}
		# <Map> binding for ComboboxPopdown
		if event and hasattr(event, 'widget') \
				and event.widget is self.toplevel:
			self.popdown.state(['pressed'])
			self.toplevel.focus_set()
		# self.toplevel.grab_set()
		# - prevents detection of FocusOut!
		return 'break'

	# noinspection PyUnusedLocal
	def unmapPopdown(self, event=None):
		# proc ttk::combobox::UnmapPopdown {w}
		# <Unmap> binding for ComboboxPopdown
		if event and hasattr(event, 'widget') and event.widget is self.toplevel:
			self.popdown.state(['!pressed'])
			self.toplevel.grab_release()
		return 'break'

	# noinspection PyAttributeOutsideInit
	def popdownWindow(self):
		# proc ttk::combobox::PopdownWindow {cb}
		# Returns the popdown widget associated with a combobox,
		# creating it if necessary.
		if not hasattr(self, 'popdown'):
			popdown = ttk.Frame(self.toplevel, style='ComboboxPopdownFrame',
								name=mu.TkName(self._name, 'popdown'))

			self.lbScroll = ttk.Scrollbar(popdown, orient='vertical',
										 name=mu.TkName(self._name, 'lbScroll'),
										 command=self.scrollAllBoxes)
			# foregoing listvariable, using listbox for storage
			self.pdList = tk.Listbox(popdown, yscrollcommand=self.setScroller,
									 name=mu.TkName(self._name, 'pdList'),
									 **con.LISTBOX_OPTIONS)
			self.pdList.bindtags([self.pdList._w, 'Listbox', popdown._w, 'all'])
			self.listboxes = [self.pdList]

			popdown.columnconfigure(0, weight=1)
			popdown.rowconfigure(0, weight=1)
			self.pdList.grid(row=0, column=0, sticky='news',
							 padx=(self._BOX_PAD, 0), pady=self._BOX_PAD)
			self.lbScroll.grid(row=0, column=1, sticky='ns',
							   padx=(0, self._BOX_PAD), pady=self._BOX_PAD)

			self.toplevel.columnconfigure(0, weight=1)
			self.toplevel.rowconfigure(0, weight=1)
			popdown.grid(row=0, column=0, padx=0, pady=0, sticky='news')
			return popdown
		else:
			return self.popdown

	# noinspection PyShadowingNames
	def setBindings(self):
		# Combobox bindings.
		self.bind('<KeyPress-Down>', self.post)
		self.toplevel.bind('<KeyPress-Escape>', self.unpost)
		self.bind('<<TraverseIn>>', self.traverseIn)

		self.bind('<Control-Delete>', self.removeFromList)
		self.bind('<Control-BackSpace>', self.removeFromList)

		self.bind('<<ComboboxSelected>>', self.adjustEntry)
		self.bind('<Enter>', self.enterEntry, add=True)
		self.bind('<Leave>', self.leaveEntry, add=True)

		self.setBoxBindings()
		if self._windowingsystem == 'win32':
			# Dismiss listbox when user switches to a different application.
			# NB: *only* do this on Windows (see #1814778)
			# self.popdown.bind('<FocusOut>', self.lbCancel)
			self.toplevel.bind('<FocusOut>', self.lbCancel)

		# Combobox popdown window bindings.
		self.toplevel.bind('<Map>', self.mapPopdown)
		self.toplevel.bind('<Unmap>', self.unmapPopdown)

		self.master.winfo_toplevel().bind('<Configure>', self.unpost, add=True)
		self.bind('<Destroy>', self.cleanup)

	def popdownTopLevel(self):
		# proc ttk::combobox::PopdownToplevel {w}
		# Create toplevel window for the combobox popdown
		toplevel = tk.Toplevel(class_='ComboboxPopdown',
							   name=mu.TkName(self._name, 'toplevel'))
		toplevel.withdraw()
		winSys = toplevel._windowingsystem
		if winSys == 'x11':
			toplevel.configure(relief='flat', borderwidth=0)
			toplevel.wm_attributes('-type', 'combo')
			toplevel.overrideredirect(True)
		elif winSys == 'win32':
			toplevel.configure(relief='flat', borderwidth=0)
			toplevel.overrideredirect(True)
			toplevel.wm_attributes('-topmost', 1)
		elif winSys == 'aqua':
			toplevel.configure(relief='solid', borderwidth=0)
			# On OSX: [wm transient] does utterly the wrong thing
			# and not called in post(). Instead, handled via an unsupported style
			# (see combobox.tcl)
			# tk::unsupported::MacWindowStyle style $w help {noActivates hideOnSuspend}
			toplevel.tk.call("::tk::unsupported::MacWindowStyle", "style",
							 toplevel._w, 'help', 'noActivates hideOnSuspend')
			toplevel.resizable(width=False, height=False)
		return toplevel

	def configureListbox(self):
		# proc ttk::combobox::ConfigureListbox {cb}
		# Set listbox values, selection, height, and scrollbar visibility
		# from current combobox values.
		current = self.current()
		if current < 0:
			current = 0		# no current entry, highlight first one
		self.highlightRow(current)

		self.update_idletasks()
		boxH = self.pdList.winfo_height() - 2 * self._BOX_PAD
		bbox = self.pdList.bbox(self.pdList.nearest(0))
		if bbox is None: # not yet opened
			return self.popdown.winfo_reqheight()
		_, _, _, itemH = bbox
		topH = self.toplevel.winfo_height()
		buttonH = topH - boxH
		# number of listbox items sacrificed for buttons
		blocked = round(0.5 + (topH - boxH) / itemH)
		maxItems = self._BOX_HEIGHT - blocked

		count = self.pdList.size()
		if count > maxItems:
			self.lbScroll.grid()
			self.pdList.grid_configure(padx=(self._BOX_PAD, 0))
			height = maxItems
		else:
			self.lbScroll.grid_remove()
			self.pdList.grid_configure(padx=self._BOX_PAD)
			height = max(1, count)
		for box in self.listboxes:
			box.configure(height=height)
		return height * itemH + buttonH + 2 * self._BOX_PAD

	def placePopdown(self, reqH):
		# proc ttk::combobox::PlacePopdown {cb popdown}
		# Set popdown window geometry.
		self.update_idletasks()
		x = self.combo.winfo_rootx()
		y = self.combo.winfo_rooty()
		w = self.combo.winfo_width()
		h = self.combo.winfo_height()

		delta = ttk.Style().lookup('TCombobox', 'postoffset')
		# - 'postoffset' only in aqua style
		if len(delta) == 4:
			x += delta[0]
			y += delta[1]
			w += delta[2]
			h += delta[3]

		# reqH = self.popdown.winfo_reqheight()
		if y + h + reqH > self.popdown.winfo_screenheight():
			geomY = y - reqH
		else:
			geomY = y + h
		self.toplevel.wm_geometry('{}x{}+{}+{}'.format(w, reqH, x, geomY))

	# noinspection PyUnusedLocal
	def post(self, event=None):
		# proc ttk::combobox::Post {cb}
		# Pop down the associated listbox.

		# Don't do anything if disabled:
		if self.combo.instate(['disabled']):
			return 'break'

		# Run -postcommand callback:
		if self.postcommand and callable(self.postcommand):
			self.postcommand()

		height = self.configureListbox()
		self.placePopdown(height)

		if self.toplevel._windowingsystem in ['win32', 'x11']:
			#	On Windows: setting [wm transient] prevents the parent
			#	toplevel from becoming inactive when the popdown is posted
			#	(Tk 8.4.8+)
			#
			#	On X11: WM_TRANSIENT_FOR on override-redirect windows
			#	may be used by compositing managers and by EWMH-aware
			#	window managers (even though the older ICCCM spec says
			#	it's meaningless).
			self.toplevel.transient(self.combo.winfo_toplevel())

		# Post the listbox:
		self.toplevel.wm_attributes('-topmost', 1)
		self.toplevel.deiconify()
		self.toplevel.tkraise()
		return 'break'

	# noinspection PyUnusedLocal
	def unpost(self, event=None):
		# proc ttk::combobox::Unpost {cb}
		# Unpost the listbox.
		if self.toplevel.state() == 'normal':
			self.toplevel.withdraw()
		self.popdown.grab_release()  # in case of stuck/unexpected grab
		return 'continue'

	def lbSelect(self, box):
		# proc ttk::combobox::LBSelect {lb}
		# Transfer listbox selection to combobox value.
		if box is self.pdList:
			selection = box.curselection()
			if len(selection) == 1:
				self.selectEntry(selection[0])
		else:
			self.toggleSelect(box)

	# noinspection PyUnusedLocal
	def cleanup(self, event=None):
		# combobox widgets
		self.toggle.destroy()
		self.destroy()
		self.combo.destroy() # Frame for combobox widgets
		self._toolTip.destroy()
		return 'break'

	# noinspection PyUnusedLocal
	def lbCleanup(self, event=None):
		# proc ttk::combobox::LBCleanup {lb}
		# <Destroy> binding for combobox listboxes.
		for box in self.listboxes:
			box.destroy()
		del self.listboxes[:]
		self.lbScroll.destroy()
		self.popdown.destroy() # Frame for popdown widgets
		self.toplevel.destroy()
		return 'break'

	# customizations from combobox ############################################

	def setBoxBindings(self):
		# Combobox listbox bindings.
		for box in self.listboxes:
			box.bind('<ButtonRelease-1>',
					 lambda ev, widget=box: self.lbSelected(widget, ev))
			box.bind('<KeyPress-Return>',
					 lambda ev, widget=box: self.lbSelected(widget, ev))
			box.bind('<KeyPress-Escape>', self.lbCancel)
			box.bind('<KeyPress-Tab>',
					 lambda ev, widget=box: self.lbTab(widget, 'next', ev))
			box.bind('<<PrevWindow>>',
					 lambda ev, widget=box: self.lbTab(widget, 'prev', ev))
			box.bind('<Destroy>', self.lbCleanup)
			# for _toolTip
			box.bind('<Enter>', self.tk_bindTip)
			box.bind('<Leave>', self.tk_unbindTip)
			box.bind('<ButtonPress>', self.tk_unbindTip)
			# box.bind('<Motion>', self.lbHover, add=True)
			box.bind('<Motion>', self.tk_lbHover, add=True)

	def addSelectColumn(self, column=0, choices=None):
		if choices is None:
			choices = [con.UNCHECKED, con.CHECKED]
		font = gv.OoFonts['default']
		maxLen = max(round((font.measure(ch)/gv.zeroLen) + 0.5)
					 for ch in choices)
		select = tk.Listbox(self.popdown, width=maxLen,
						name=mu.TkName(self._name, 'pdSelect', self.selectors),
						yscrollcommand=self.setScroller, **con.LISTBOX_OPTIONS)
		select.grid(padx=(2, 0), pady=2)
		self.listboxes.insert(column, select)
		self.checkboxes[select] = choices
		self.selectors = len(self.listboxes) - 1
		for x, box in enumerate(self.listboxes):
			if box is self.pdList:
				box.grid(row=0, column=x, sticky='news')
				self.popdown.columnconfigure(x, weight=1)
			else:
				box.grid(row=0, column=x, sticky='ns')
				self.popdown.columnconfigure(x, weight=0)
		self.lbScroll.grid(row=0, column=len(self.listboxes), sticky='ns')
		self.setBoxBindings()

	def toggleList(self):
		# handler for Listbox toggle button
		if self.toplevel.state() == 'normal':
			self.unpost()
		else:
			self.post()

	# noinspection PyUnusedLocal
	def toggleSelect(self, box, event=None):
		# handler for Listbox selector column
		selected = box.curselection()
		if len(selected):
			index = selected[0]
			value = box.get(index)
			choices= self.checkboxes[box]
			chIdx = choices.index(value)
			nextCh = (chIdx + 1) % len(choices)
			box.insert(index, choices[nextCh])
			box.delete(index + 1)
			box.xview_moveto(0.0)
			self.highlightRow(index)
			self.event_generate('<<ComboboxChecked>>')
		return 'break'

	def scrollAllBoxes(self, *args):  # Scrollbar's 'command'
		for box in self.listboxes:
			box.yview(*args)

	def setScroller(self, lo, hi):  # Listbox's 'yscrollcommand'
		# set positions of associated widgets
		for box in self.listboxes:
			box.yview_moveto(lo)
		# set scrollbar position
		self.lbScroll.set(lo, hi)

	def highlightRow(self, index):
		for box in self.listboxes:
			box.selection_clear(0, 'end')
			box.activate(index)
			box.selection_set(index)
			box.see(index)

	def addEntry(self, value):
		if self.preProcessFn and callable(self.preProcessFn):
			value = self.preProcessFn(value)
		self.set(value)
		self.adjustEntry(value=value)

	# noinspection PyUnusedLocal
	def adjustEntry(self, event=None, value=None):
		# default listbox postcommand
		# - ensure at left edge: if you drag mouse across a log entry, the box
		#   will scroll but only returns if it's dragged back
		for box in self.listboxes:
			box.xview_moveto(0.0)
		# - ensure list order is LIFO.
		if value is None:
			value = self.get()
		if len(value):
			self.updateList(value)
			self.current(0)

	def getList(self):
		# Listbox .get returns a tuple
		return list(self.pdList.get(0, 'end'))

	def setList(self, items, selections=None):
		if selections is None:
			# get a parallel list of selections
			selections = self.getAllSelections(items)
		try:
			# selections is parallel list of checks
			num = 0
			for box in self.listboxes:
				box.delete(0, 'end')
				if box is self.pdList and items is not None:
					box.insert('end', *items)
				elif selections is not None:
					selected = [sel[num] for sel in selections]
					box.insert('end', *selected)
					num += 1

		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	def updateList(self, value):
		# add to start of list and remove duplicate if present
		if len(value) == 0:
			return
		selections = self.getSelections(value=value)
		self.removeFromList(value=value, clear=False)
		num = 0
		for box in self.listboxes:
			if box is self.pdList:
				box.insert(0, value)
			elif selections is not None:
				box.insert(0, con.UNCHECKED if selections is None
									   else selections[num])
				num += 1

	# noinspection PyUnusedLocal
	def removeFromList(self, event=None, value=None, clear=True):
		# remove value from pdList and any associated selections
		if value is None:
			value = self.get()
		if len(value):
			items = self.getList()
			if value in items:
				index = items.index(value)
				for box in self.listboxes:
					inBox = items if box is self.pdList \
								else list(box.get(0, 'end'))
					del inBox[index]
					box.delete(0, 'end')
					box.insert('end', *inBox)
			if clear:
				self.set('')

	def defaultRowSelections(self):
		# selections = []
		# for box, choices in self.checkboxes:
		# 	selections.append(choices[0])
		# return selections
		# # return [con.UNCHECKED] * self.selectors
		return [choices[0] for choices in self.checkboxes.values()]

	def defaultSelections(self, count):
		# return [[con.UNCHECKED] * self.selectors for _ in range(count)]
		return [self.defaultRowSelections() for _ in range(count)]

	def getAllSelections(self, items=None):
		# return a parallel list of selections
		try:

			if self.selectors == 0:
				return
			if self.pdList.size() == 0:  # initial load
				if items is None:
					return
				return self.defaultSelections(len(items))
			else:
				if items is None:
					items = self.getList()
				count = len(items)
				return [[box.get(idx) for box in self.checkboxes.keys()]
						for idx in range(count)]

		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	def getSelections(self, index=None, value=None):
		# return list of selection values for given item
		if self.selectors == 0:
			return
		selections = None
		items = self.getList()
		itemIdx = items.index(value) if value and value in items else index
		if itemIdx is not None:
			selections = [box.get(itemIdx) for box in self.checkboxes.keys()]
		if selections is None or len(selections) == 0:
			return self.defaultRowSelections()
		return selections

	# Tk's Combobox methods ###################################################

	def set(self, value):
		# Sets the value of the combobox to value.
		self.entryValue.set(value)

	def get(self):
		# Returns the current value of the combobox.
		return self.entryValue.get()

	def current(self, index=None):
		# If 'index' is supplied, sets the combobox value to the element at
		# that position in the list.
		# Otherwise, returns the index of the current value in the list or -1
		# if the if the current value does not appear in the list.
		items = self.getList()
		if index is not None:
			if -1 < index < len(items):
				self.set(items[index])
				self.icursor('end')
		else:
			if len(items) > 0:
				value = self.entryValue.get()
				if value in items:
					return items.index(value)
			return -1
# end class OoCombobox

class OoSelector(OoCombobox):
	_oosToolTips = {
		'allBox':
			'Select all items in the pull down list \n'
			+ 'instead of the one in the text window',
		'checkedBox':
			'Select the checked items in the pull down list \n'
			+ 'instead of the one in the text window',
		'clearAll':
			'Removes all check marks from the pull down list',
		'setAll':
			'Set all check marks in the pull down list',
		'deleteChecked':
			'Removes from the pull down list all that are checked',
	}

	_buttonStr = {'set': 'Select all', # 'Set all checks'
				  'clear': 'Clear all', # 'Clear all checks'
				  'delete': 'Delete selected'} # 'Delete checked'

	# references to all instances (for checking overlap)
	_sel_instances = []

	def __init__(self, master, tag, label, tipDelay,
						selectors=0, choiceList=None):
		self.selectors = selectors
		self.__class__._sel_instances.append(self)
		self.rowsSelected = 0
		self.oosFrame = ttk.Frame(master,
								  name=mu.TkName(tag, 'Frame'))

		self.oosLabel = ttk.Label(self.oosFrame, text=label, anchor='w',
								  name=mu.TkName(tag, 'Label'))
		OoCombobox.__init__(self, self.oosFrame, width=25,
							name=mu.TkName(tag, 'Entry'))
		# choiceList == None => using default choices, eg. [[' ', ' X']]
		# see addSelectColumn: [[con.UNCHECKED, con.CHECKED]]
		if selectors > 0 and choiceList is not None:
			if not isinstance(choiceList, (tuple, list)) \
					or len(choiceList) != selectors \
					or not all(isinstance(chList, (tuple, list)) 
							   and all(isinstance(ch, (bytes, str)) 
									   for ch in chList) 
							   for chList in choiceList):
				msg = '''Invalid choiceList parameter: {}
	expecting list of len {} (selectors) of lists of strings 
	(values to cycle through for each selector column)'''.format(choiceList, selectors)
				raise ValueError(msg)

		for num in range(selectors):
			self.addSelectColumn(num, None if choiceList is None
											else choiceList[num])

		if selectors > 0:
			self.checkFrame = ttk.Frame(self.oosFrame,
										name=mu.TkName(tag, 'checkFrame'))

			self.useAll = tk.IntVar(name=mu.TkName(tag, 'useAll'))
			self.allButton = ttk.Checkbutton(self.checkFrame,
										name=mu.TkName(tag, 'allButton'),
										variable=self.useAll,
										command=self._resetUseChecked,
										text=' All',
										**con.CHECKBUTTON_OPTIONS)

			self.useChecked = tk.IntVar(name=mu.TkName(tag, 'useChecked'))
			self.checkedButton = ttk.Checkbutton(self.checkFrame,
										name=mu.TkName(tag, 'checkedButton'),
										variable=self.useChecked,
										command=self._resetUseAll,
										text=' Checked',
										**con.CHECKBUTTON_OPTIONS)

			self.buttonFrame = ttk.Frame(self.toplevel,
										 name=mu.TkName(tag, 'buttonFrame'))

			self.checkStr = tk.StringVar(name=mu.TkName(tag, 'checkStr'),
										 value=self._buttonStr['set'])
			self.checkActions = ttk.Button(self.buttonFrame, # self.oosFrame,
										   name=mu.TkName(tag, 'checkActions'),
										   textvariable=self.checkStr,
										   command=self._toggleChecked)

			self.delChecked = ttk.Button(self.buttonFrame, # self.oosFrame,
										 name=mu.TkName(tag, 'deleteChecked'),
										 text=self._buttonStr['delete'],
										 command=self._deleteChecked)

			ToolTip(self.allButton, self._oosToolTips['allBox'],
					tipDelay, 'allBox', allowFunc=self.allowToolTip)
			ToolTip(self.checkedButton, self._oosToolTips['checkedBox'],
					tipDelay, 'checkedBox', allowFunc=self.allowToolTip)
			# these appear below the drop down, so we limit when tip is shown
			self.checkTip = ToolTip(self.checkActions, self._oosToolTips['setAll'],
					tipDelay, 'clearChecked', allowFunc=self.allowToolTip)
			ToolTip(self.delChecked, self._oosToolTips['deleteChecked'],
					tipDelay, 'deleteChecked', allowFunc=self.allowToolTip)
			self.bind('<<ComboboxChecked>>', self._setUseChecked)

		_pad4 = {'padx': 4, 'pady': 4}
		# in oosFrame (which is gridded by caller)
		self.oosLabel.grid(row=0, column=0, sticky='w', **_pad4)
		self.grid(row=1, column=0, sticky='we', columnspan=5, **_pad4)
		if selectors > 0:
			# in oosFrame
			self.checkFrame.grid(row=0, column=1, sticky='e', columnspan=4, **_pad4)
			# in checkFrame
			self.allButton.grid(row=0, column=0, sticky='e', **_pad4)
			self.checkedButton.grid(row=0, column=1, sticky='e', **_pad4)
			# in self.toplevel (ie. pull down list)
			self.buttonFrame.grid(row=1, column=0, sticky='we', columnspan=100)

			# weighted so buttons split apart
			self.buttonFrame.columnconfigure(1, weight=1)

			# in buttonFrame
			self.checkActions.grid(row=0, column=0, sticky='w')
			self.delChecked.grid(row=0, column=1, sticky='e')

		msg = con.toolTips.get(tag, '').strip()
		self.tooltip = ToolTip(self, msg, tipDelay, allowFunc=self.allowToolTip)

	def allowToolTip(self):
		# suppress tooltips when a drop down list is open
		# (assuming instances are vertically aligned and an open list overlaps)
		# removed 'self.focus_get() is not self' test as it seemed unintuitive
		# return self.focus_get() is not self \
		return not any(inst.pdList.winfo_toplevel().state() == 'normal'
					   for inst in self._sel_instances)

	def unpost(self, event=None):
		if self.toplevel.state() != 'normal':
			return 'continue'
		# when altering checks in pdList, a config change in outer buttons
		# (ie. updating their state) will generate a <Configure> event,
		# which comes here
		if self.selectors > 0 and event and hasattr(event, 'widget') \
				and event.widget in [self.checkedButton, self.checkActions,
									 self.delChecked]:
			# intercept & deny the unpost request, user may not be finished
			return 'continue'
		super(OoSelector, self).unpost()
		return 'continue'

	def removeFromList(self, event=None, value=None, clear=True):
		super(OoSelector, self).removeFromList(event, value)
		if self.selectors > 0:
			self.checkSelectionCount()

	def addEntry(self, value):
		super(OoSelector, self).addEntry(value)
		if self.selectors > 0:
			self.checkSelectionCount()

	def _resetUseAll(self):
		# command for 'useChecked' as mutually exclusive
		self.useAll.set(0)
		self.checkSelectionCount()

	def _resetUseChecked(self):
		# command for 'useAll' as mutually exclusive
		self.useChecked.set(0)
		self.checkSelectionCount()

	def _checkValues(self, boxNum=0):
		# the leftmost box (ie. [0]) is default for selection, ie. not
		count = 0
		for box, choices in self.checkboxes.items():
			if count == boxNum:
				return box, choices
			count += 1

	# noinspection PyUnusedLocal
	def _setUseChecked(self, event=None):
		# handler for <<ComboboxChecked>> event
		selections = self.getAllSelections()
		if selections is None:
			return
		box, choices = self._checkValues()
		# choices[0] is the unselected value
		numSet = sum(1 for select in selections
					 if any(sel != choices[0] for sel in select))
		self._updateCheckButtons(numSet)
		if self.useAll.get() == 0:
			useChecked = self.useChecked.get()
			if useChecked == 0:
				if self.rowsSelected == 0 and numSet == 1:
					# only be *helpful* turning on useChecked with first one
					self.useChecked.set(1)
		self.rowsSelected = numSet

	def _updateCheckButtons(self, numSet):
		self.allButton.state(['!disabled'])
		self.checkActions.state(['!disabled'])
		# alter state based on # of selections
		if numSet == 0:
			# alter state based on # of items
			if self.pdList.size() == 0:
				self.useAll.set(0)
				self.allButton.state(['disabled'])
				self.checkActions.state(['disabled'])
			self.useChecked.set(0)
			self.checkedButton.state(['disabled'])
			self.delChecked.state(['disabled'])
			self.checkTip.msg = self._oosToolTips['setAll']
			self.checkStr.set(self._buttonStr['set'])
		else:
			self.checkedButton.state(['!disabled'])
			self.delChecked.state(['!disabled'])
			self.checkTip.msg = self._oosToolTips['clearAll']
			self.checkStr.set(self._buttonStr['clear'])

	def _toggleChecked(self): # handler for the Set/Clear all checks button
		toggle = 'set' if self.checkStr.get() \
						   == self._buttonStr['clear'] else 'clear'
		box, choices = self._checkValues()
		items = self.getList()
		selections = [choices[-1] if toggle == 'clear' else choices[0]
						for _ in items]
		self.setList(items, selections)
		self.checkSelectionCount(selections=selections)

	def _deleteChecked(self):
		try:
			inList = self.getList()
			checked = self.getAllSelections(inList)
			if checked is None:
				return
			box, choices = self._checkValues()
			# choices[0] is the unselected value
			keepers = [index for index, checks in enumerate(checked)
						if checks[0] == choices[0]]
			items = [inList[index] for index in keepers]
			selections = [checked[index] for index in keepers]
			inEntry = self.get()
			if inEntry not in items:
				# item in Entry selected for deletion
				self.set('')
			self.setList(items, selections)
			self.checkSelectionCount(selections=selections)
		except Exception as exc:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

	def checkSelectionCount(self, boxNum=0, selections=None):
		if selections is None:
			selections = self.getAllSelections()
		if selections is None:
			numSet = 0
		else:
			# the leftmost box (ie. #0) is default for selection
			box, choices = self._checkValues(boxNum)
			# choices[0] is the unselected value
			numSet = sum(1 for select in selections
							if select[boxNum] != choices[0])
		self._updateCheckButtons(numSet)

	def getValues(self):
		if self.useAll.get():
			return self.getList()
		elif not self.useChecked.get():
			return [self.get()]
		allInList = self.getList()
		selections = self.getAllSelections(allInList)
		if selections is None:
			return []
		box, choices = self._checkValues()
		# choices[0] is the unselected value
		return [allInList[index] for index, select in enumerate(selections)
								if select[0] != choices[0]]

# end class OoSelector

# noinspection PyUnresolvedReferences
class SearchBox(TopWindow):
	searchWidth = searchHeight = -1
	# searchTitleBar = -1
	shared = None		# class level shared widget set
	searchUser = None	# instance currently using shared widgets
	def __init__(self, master, font, searchPrefix='',):
		self.initInstance(master, searchPrefix)
		# widgets only created once, shared by ScrollingText's
		cls = self.__class__
		if cls.shared:
			return
		cls.font = font	
		# use topmost master for a short _w in self.top
		TopWindow.__init__(self, master.winfo_toplevel(), label=None, 
							name=mu.TkName('SearchBox_shared'),
							enduring=True, showNow=False)
		cls.shared = self
		# cannot be .transient as will lift its master when gridded
		cls.shared.transient('')
		cls.shared.bind('<Configure>', au.dragSearchbox)
		searchFrame = cls.shared.twFrame

		cls.searchDirn = tk.IntVar(value=1, name=mu.TkName('searchDirn'))
		# - default backwards=1 (.search also accepts forwards=0)
		cls.searchResultLen = tk.IntVar(name=mu.TkName('searchResultLen'))
		# - search stores # of char.s if pattern found

		_radioButtonKWs = {	'variable': cls.searchDirn,
							'command': self.startSearch, }

		cls.searchDirnBck = ttk.Radiobutton(searchFrame, value=1, 
								style= 'searchUp.TRadiobutton',
								name=mu.TkName('searchDirnBck'), 
								**_radioButtonKWs)

		cls.searchDirnFwd = ttk.Radiobutton(searchFrame, value=0,
											style='searchDown.TRadiobutton',
											name=mu.TkName('searchDirnFwd'),
											**_radioButtonKWs)

		tipDelay = gv.CurrentOptions['Settings'].get('SearchToolTipDelayMS', 0)
		entryWidth = len(con.REGEX_TEXT)
		# entryHeight = max(int(gi['row'], 10) \
						# for gi in cls.searchGridInfo.values()) + 1 # 0-based
		setBtns = (cls.shared.register(cls.buttonState), '%P')
		cls.searchTarget = OoCombobox(searchFrame,
								name=mu.TkName('SearchTarget'),
								width=entryWidth, validate='key', #'focus', #
								validatecommand=setBtns)
		msg = con.toolTips.get('searchTargetEntry', '').strip()
		ToolTip(cls.searchTarget, msg, tipDelay)

		cls.searchTargetClear = ttk.Button(searchFrame, text='Clear',
								name=mu.TkName('searchTargetClear'),
								state='disabled', 
								command=self.clearSearchTarget)
		msg = con.toolTips.get('searchTargetClear', '').strip()
		ToolTip(cls.searchTargetClear, msg, tipDelay)

		cls.searchAuxFrame = ttk.Frame(searchFrame, 
										name=mu.TkName('searchAuxFrame'))
		
		cls.searchCountBtn = ttk.Button(cls.searchAuxFrame, text='Count',
								name=mu.TkName('searchCountBtn'),
								state='disabled', 
								command=lambda: self.startSearch(counting=True))
		msg = con.toolTips.get('searchCountBtn', '').strip()
		ToolTip(cls.searchCountBtn, msg, tipDelay)

		cls.searchMarkall = ttk.Button(cls.searchAuxFrame, text='Mark all',
								name=mu.TkName('searchMarkall'),
								state='disabled', 
								command=lambda: self.startSearch(marking=True))
		msg = con.toolTips.get('searchMarkall', '').strip()
		ToolTip(cls.searchMarkall, msg, tipDelay)

		cls.searchBackwards = tk.IntVar(value=1,
										name=mu.TkName('searchBackwards'))
		# - default search up, backwards=1
		cls.searchBackwardsBtn = ttk.Checkbutton(searchFrame, 
								variable=cls.searchBackwards,
								name=mu.TkName('searchBackwardsBtn'),
								text=' Backwards',
								**con.CHECKBUTTON_OPTIONS)
		msg = con.toolTips.get('searchBackwards', '').strip()
		ToolTip(cls.searchBackwardsBtn, msg, tipDelay)

		cls.searchWordsOnly = tk.IntVar(name=mu.TkName('searchWordsOnly'))
		# - default any match, word boundary not detected by tk.search
		cls.searchWordsOnlyBtn = ttk.Checkbutton(searchFrame, 
								variable=cls.searchWordsOnly,
								name=mu.TkName('searchWordsOnlyBtn'),
								text=' Words only',
								**con.CHECKBUTTON_OPTIONS)
		msg = con.toolTips.get('searchWordsOnly', '').strip()
		ToolTip(cls.searchWordsOnlyBtn, msg, tipDelay)

		cls.searchWrap = tk.IntVar(name=mu.TkName('searchWrap'))
		# - default off, stopindex='1.0' or 'end'; search will wrap if not set
		cls.searchWrapBtn = ttk.Checkbutton(searchFrame, 
								variable=cls.searchWrap,
								name=mu.TkName('searchWrapBtn'),
								text=' Wrap search',
								**con.CHECKBUTTON_OPTIONS)
		msg = con.toolTips.get('searchWrap', '').strip()
		ToolTip(cls.searchWrapBtn, msg, tipDelay)

		cls.searchCase = tk.IntVar(value=1, name=mu.TkName('searchCase'))
		# - default insensitive, nocase=1
		cls.searchCaseBtn = ttk.Checkbutton(searchFrame, 
								variable=cls.searchCase,
								name=mu.TkName('searchCaseBtn'),
								text=' Ignore case',
								**con.CHECKBUTTON_OPTIONS)

		# default off, regexp=0 or exact=1; 
		# (subset of Py's regexs: . ^ [c 1 …] (…) * + ? e1|e2)
		cls.searchRegex = tk.IntVar(name=mu.TkName('searchRegex'))
		cls.searchRegexBtn = ttk.Checkbutton(searchFrame, 
								variable=cls.searchRegex,
								name=mu.TkName('searchRegexBtn'),
								text=con.REGEX_TEXT,
								**con.CHECKBUTTON_OPTIONS)
		msg = con.toolTips.get('searchRegex', '').strip()
		ToolTip(cls.searchRegexBtn, msg, tipDelay)

		cls.searchLabelStr = tk.StringVar(name=mu.TkName('searchLabelStr'))
		cls.searchLabel = ttk.Label(searchFrame, relief='flat',
								textvariable=cls.searchLabelStr,
								name=mu.TkName('searchLabel'))

		gI = cls.searchGridInfo
		cls.searchDirnBck.grid(gI['DirnBck'])
		cls.searchTarget.grid(gI['History'])
		cls.searchTargetClear.grid(gI['Clear'])
		cls.searchDirnFwd.grid(gI['DirnFwd'])
		cls.searchBackwardsBtn.grid(gI['Backwards'])
		cls.searchWordsOnlyBtn.grid(gI['WordsOnly'])
		cls.searchWrapBtn.grid(gI['Wrap'])
		cls.searchCaseBtn.grid(gI['Case'])
		cls.searchRegexBtn.grid(gI['Regex'])
		cls.searchLabel.grid(gI['Label'])
		# inner frame
		cls.searchAuxFrame.grid(gI['AuxFrame'])
		cls.searchCountBtn.grid(gI['Count'])
		cls.searchMarkall.grid(gI['Markall'])

	searchGridInfo = {
		'DirnBck':   {'row': 0, 'column': 0, 'sticky': 'nw', 'padx': 4,  'pady': 4, 'columnspan': 1, 'rowspan': 1},
		'History':   {'row': 0, 'column': 1, 'sticky': 'w',  'padx': 4,  'pady': 4, 'columnspan': 2, 'rowspan': 1},
		'Clear':     {'row': 0, 'column': 4, 'sticky': 'e',  'padx': 4,  'pady': 4, 'columnspan': 1, 'rowspan': 1},
		'DirnFwd':   {'row': 1, 'column': 0, 'sticky': 'nw', 'padx': 4,  'pady': 4, 'columnspan': 1, 'rowspan': 1}, # ipady to align w/ buttons
		'Backwards': {'row': 1, 'column': 1, 'sticky': 'nw', 'padx': '12', 'pady': 4, 'columnspan': 1, 'rowspan': 1, 'ipady': 4},
		'WordsOnly': {'row': 1, 'column': 2, 'sticky': 'nw', 'padx': '12', 'pady': 4, 'columnspan': 1, 'rowspan': 1, 'ipady': 4},
		'Wrap':      {'row': 2, 'column': 1, 'sticky': 'nw', 'padx': '12', 'pady': 4, 'columnspan': 1, 'rowspan': 1, 'ipady': 4},
		'Case':      {'row': 2, 'column': 2, 'sticky': 'nw', 'padx': '12', 'pady': 4, 'columnspan': 1, 'rowspan': 1, 'ipady': 4},
		'Regex':     {'row': 3, 'column': 1, 'sticky': 'sw', 'padx': '12', 'pady': 4, 'columnspan': 3, 'rowspan': 1, 'ipady': 4},
		'Label':     {'row': 4, 'column': 0, 'sticky': 'nw', 'padx': 4,  'pady': 4, 'columnspan': '5', 'rowspan': 1},
		# searchAuxFrame is in_ searchBoxFrame, for alignment
		'AuxFrame':  {'row': 1, 'column': 3, 'sticky': 'ne', 'padx': 4,  'pady': 0, 'columnspan': 2, 'rowspan': 2},
		'Count':     {'row': 0, 'column': 0, 'sticky': 'ne', 'padx': 0,  'pady': 4, 'columnspan': 2, 'rowspan': 1},
		'Markall':   {'row': 1, 'column': 0, 'sticky': 'se', 'padx': 0,  'pady': 4, 'columnspan': 2, 'rowspan': 1},
	}

	@classmethod
	def clearSearchTarget(cls):
		cls.searchTarget.set('')
		cls.buttonState('')
		cls.searchTarget.focus_set()

	@classmethod
	def buttonState(cls, contents):	# Entry validator to set button's state
		state = 'disabled' if len(contents) == 0 else 'normal'
		cls.searchTargetClear.config(state=state)	
		cls.searchCountBtn.config(state=state)
		cls.searchMarkall.config(state=state)
		# allow all changes (validate requires boolean return)
		return True

	# noinspection PyUnusedLocal
	@classmethod
	def handleCR(cls, event=None):
		cls.startSearch()
		return 'break'

	# noinspection PyAttributeOutsideInit
	def initInstance(self, master, searchPrefix):
		self.master = self.hostWidget = master
		# noinspection PyProtectedMember
		self._w = master._w
		self.tk = master.tk

		self.searchPrefix = searchPrefix
		# establish instance specific vars else will use class's
		self.searchOpenXY = None	# position to open searchBox
		self.searchXY = None		# position when closed, saved to CFGFILE
		self.lastSearchIdx = ''		# starting position of last on a subsequent
									#   search on same pattern
		self.lastPattern = ''		# last pattern searched
		self.lastFoundLen = 0		# length of last successful match
		self.patternMatched = False
		self.lastPatternFound = True

	@classmethod
	def startSearch(cls, counting=False, marking=False):
		# arrow buttons; for consistency, 1 => backwards
		backwards = cls.searchDirn.get()
		if backwards == 0 or backwards == 1:
			# came in via a button, they override searchBackwards
			# - reset button (ie. neither radiobutton)
			cls.searchDirn.set(2)
		else:
			# started w/ Return
			backwards = cls.searchBackwards.get()
		pattern = cls.searchTarget.get()
		if len(pattern) == 0:
			cls.searchLabelStr.set('enter a target')
			return
		cls.searchTarget.updateList(pattern)

		# fetch instance specific values from current 'user'
		user = cls.searchUser
		txt = user.hostWidget
		wordsOnly = cls.searchWordsOnly.get() == 1
		wrapping = cls.searchWrap.get() == 1
		nocase = cls.searchCase.get() == 1
		regexp = cls.searchRegex.get() == 1
		haveMarks = len(txt.tag_ranges('searchMark')) > 0
		user.patternMatched = pattern == user.lastPattern \
										and user.lastPatternFound
		if not user.lastPattern or (marking and haveMarks):
			txt.tag_remove('searchMark', '1.0', 'end')
			cls.searchMarkall.config(text='Mark all')
			if marking and haveMarks: 	# button acts as a toggle
				cls.searchLabelStr.set('')
				return
		user.lastPattern = pattern
		if user.lastSearchIdx == '':	# first time visit
			searchFrom = user.lastSearchIdx \
					   = mu.formatMouseIndex(user.hostWidget, *user.searchOpenXY)
		else:
			searchFrom = user.lastSearchIdx if backwards \
										else '{} +1c'.format(user.lastSearchIdx)
		idx = searchFrom if backwards else '{} -1c'.format(searchFrom)
		stopindex = None if wrapping or counting or marking \
						else ('1.0' if backwards else 'end')
		findings = []
		found = wrapped = False
		endIdx = ''
		foundLength = 0
		while not found or counting or marking:
			searchFrom = idx if backwards else '{} +1c'.format(idx)
			idx = ''
			try:
				# print('startSearch, pattern: {}, searchFrom: {}, backwards: {}, stopindex: {}, nocase: {}, regexp: {}'.format(
					# pattern, searchFrom, backwards, stopindex, nocase, regexp))
				idx = txt.search(pattern, searchFrom, backwards=backwards,
								stopindex=stopindex, count=cls.searchResultLen,
								nocase=nocase, elide=1, regexp=regexp)
			except tk.TclError as exc:
				errmsg = 'TclError: \n{}\n'.format(exc.message.replace(':', con.NL))
				errmsg += '\n(www.tcl.tk/man/tcl8.5/TclCmd/re_syntax.htm)'
				OoInfoBox(cls.top, errmsg, font=cls.font)
				gv.debugLogger.error(errmsg)
			except Exception as exc:
				errmsg = 'startSearch, Exception: {!r}'.format(exc)
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.exception(errmsg)

			found = idx != ''
			if not found: break
			foundLength = cls.searchResultLen.get()
			if foundLength == 0: break	# degenerate case for re's
			endIdx = txt.index('{}+{}c'.format(idx, foundLength))
			if wordsOnly:
				if txt.compare(idx, '!=', '{} wordstart'.format(idx)) \
						or txt.compare('{} +1c'.format(endIdx), '!=',
										'{} wordend'.format(endIdx)):
					found = False		# it's not a word
					continue
			if not found and not (counting or marking):
				break					# quit on 1st match in normal search
			if idx in findings:
				break					# we've wrapped around
			elif found:
				findings.append(idx)
				if marking:
					txt.tag_add('searchMark', idx, endIdx)
		# endwhile
		cls.updateMarkButton()
		if counting or marking:
			count = len(findings)
			cls.searchLabelStr.set('{} matches {}'.format(
								('no' if count == 0 else count),
								('found' if counting else 'marked')))
			return
		# check if we wrapped
		if stopindex is None and found and user.lastPatternFound:
			wrapped = txt.compare(idx, '>=' if backwards else '<=',
									user.lastSearchIdx)
		if found: 						# "line.char" of start of match
			txt.tag_remove('sel', '1.0', 'end')
			txt.tag_add('sel', idx, endIdx)
			txt.see(idx)
			user.patternMatched = True
			if wrapped:
				cls.searchLabelStr.set('wrapped to {} of window'.format(
										'end' if backwards else 'start'))
			else:
				cls.searchLabelStr.set('')
			user.lastSearchIdx = idx
			user.lastFoundLen = foundLength
		else: 					# search failed
			cls.searchLabelStr.set('no {}matches found'.format(
										'more ' if user.patternMatched else ''))
			if user.lastPatternFound:	# clear selection when reach last match
				txt.tag_remove('sel', '1.0', 'end')
				if backwards:
					user.lastSearchIdx = txt.index('{}-1c'.format(
										user.lastSearchIdx))
				else:
					user.lastSearchIdx = txt.index('{}+{}c'.format(
										user.lastSearchIdx, user.lastFoundLen))
			else:
				user.lastSearchIdx = '1.0' if backwards else 'end'
		user.lastPatternFound = True if user.patternMatched else found

	@classmethod
	def setupDimns(cls):
		cls.shared.deiconify()
		cls.shared.lift()
		cls.shared.update_idletasks()
		cls.searchWidth, cls.searchHeight = mu.getWidgetReqWH(cls.shared)
		rootX, rootY = mu.getWidgetRoot(cls.shared)
		cls.searchWidth += rootX
		cls.searchHeight += rootY
		# cls.searchTitleBar = rootY - cls.shared.winfo_y()

		yForBtns = cls.searchLabel.winfo_y() \
					- cls.searchWordsOnlyBtn.winfo_y()
		dyHist = int((yForBtns - cls.searchTarget.winfo_height()) / 2)
		cls.searchGridInfo['History']['pady'] = dyHist

	@classmethod
	def updateMarkButton(cls):
		# reset 'Mark all' button as window contents may changed
		txt = cls.searchUser.hostWidget
		haveMarks = len(txt.tag_ranges('searchMark')) > 0
		cls.searchMarkall.config(text='Clear marks' if haveMarks else 'Mark all')

	@classmethod
	def openSearchBox(cls, centered=False):		# command for popup 'Search ...'
		def searchInWindow(newX, newY):
			return txtX < newX < newX + cls.searchWidth < txtX + txtW \
				and txtY < newY < newY + cls.searchHeight < txtY + txtH

		# make transparent to prevent flashing at previous location as it is
		# shared by 4 widgets (bodyText, cmdLine, aliasDefn & contextText)
		cls.shared.attributes('-alpha', 0.0)
		if cls.searchWidth < 0:
			# first time opened, calculate searchWidth, searchHeight
			cls.setupDimns()
		# fetch instance specific values from current 'user'
		user = cls.searchUser
		searchTitle = 'Search:'
		if len(user.searchPrefix):
			searchTitle = '{} search'.format(user.searchPrefix)
		cls.shared.setTitle(searchTitle)
		# link shared to current user's master
		cls.shared.transient(user.hostWidget)
		cls.updateMarkButton()
		openedBefore = user.searchXY is not None
		# opened before, restore this instance's coords to shared widget
		if openedBefore:
			cls.shared.mouseXY = user.searchXY
			cls.shared.geometry('+{}+{}'.format(*user.searchXY))

		# set IntVar so neither button is on
		cls.searchDirn.set(2)

		cls.searchLabelStr.set('')
		user.lastPatternFound = True
		user.patternMatched = False
		txt = user.hostWidget
		txtW = txtH = txtoffX = txtoffY = txtX = txtY = None
		openAbove = haveSelection = False
		selection = txt.tag_ranges('sel')
		if len(selection) == 0:
			cls.searchTarget.focus_set()
		elif len(selection) == 2: 		
			# auto-add selection to Entry, set starting index
			selIdx = user.lastSearchIdx = txt.index('sel.first')
			selEndIdx = txt.index('sel.last')
			searchStr = txt.get(selIdx, selEndIdx)
			cls.searchTarget.set(searchStr)
			cls.searchTarget.updateList(searchStr)
			# check selection is visible so tkinter doesn't go BOOM
			selBbox = txt.bbox(selIdx)
			selEndBbox = txt.bbox(selEndIdx)
			if selBbox is not None and selEndBbox is not None:
				haveSelection = True
				# create Rectangle's for txt, 'sel' & searchBox 
				# to check if there's an overlap
				txtW, txtH, txtoffX, txtoffY = mu.parseGeometry(txt)
				# - calls update_idletasks
				txtX, txtY = mu.getWidgetRoot(txt)
				selULx, selULy, _, _ = selBbox 				# relative to txt
				selLRx, selLRy, width, height = selEndBbox	#   "
				# bbox returns very large width (>1000) for some char's, eg NL
				if width > height:				
					width = height//2
				# spans multiple lines; ensure Rectangle is as wide as txt
				selFullWidth = selLRy != selULy 
				if not selFullWidth:
					selULx += txtX				# absolute for Upper Left
					selULy += txtY
					selLRx += width + txtX 		# absolute for Lower Right
					selLRy += height + txtY
					searchULx, searchULy = user.searchXY \
												if openedBefore \
												else user.searchOpenXY
					searchLRx = searchULx + cls.searchWidth
					searchLRy = searchULy + cls.searchHeight
					if 	(searchULx < selULx < searchLRx
						   and searchULy < selULy < searchLRy) \
						or (searchULx < selLRx < searchLRx
							and searchULy < selLRy < searchLRy) \
						or selULx < searchULx < searchLRx < selLRx:
						# searchBox will overlap/cover selection
						openedBefore = False # force initial position check below
						if searchInWindow(searchULx, selLRy): 
							# open window below
							user.searchOpenXY = [searchULx, selLRy]
						elif searchInWindow(searchULx, selULy - cls.searchHeight): 
							# open window above
							user.searchOpenXY = [searchULx, selULy - cls.searchHeight]
							openAbove = True
						else:				
							# abort movement
							openedBefore = user.searchXY is not None
		if openedBefore and not centered:
			cls.shared.restoreTop()
		else:							
			# ensure initial search box stays inside app
			if txtW is None:			# no selection, so not set above
				txtW, txtH, txtoffX, txtoffY = mu.parseGeometry(txt)
				# - calls update_idletasks
				txtX, txtY = mu.getWidgetRoot(txt)
			appMinX, appMinY = txtX + txtoffX, txtY + txtoffY
			appMaxX, appMaxY = appMinX + txtW, appMinY + txtH
			if centered:
				searchOpenX = txtX + (appMaxX - appMinX) // 2 \
							  - cls.searchWidth // 2
				searchOpenY = txtY + (appMaxY - appMinY) // 2 \
							  - cls.searchHeight // 2
			else:
				searchOpenX, searchOpenY = user.searchOpenXY

			if searchOpenX + cls.searchWidth > appMaxX:
				# exceeds right edge, right justify
				searchOpenX = appMaxX - cls.searchWidth

			if haveSelection and not centered:
				# ensure some space between selection and searchBox
				lineSpace = gv.lineSpace
				if searchOpenY > txtH / 2:
					searchOpenY -= (0 if openAbove
									else cls.searchHeight)+ 2 * lineSpace
				else:
					searchOpenY += 2 * lineSpace

			if searchOpenY < appMinY:
				# exceeds top edge, top justify
				searchOpenY = appMinY
			if searchOpenY + cls.searchHeight > appMaxY:
				# exceeds bottom edge, bottom justify
				searchOpenY = appMaxY - cls.searchHeight
			cls.shared.showAtMouse([searchOpenX, searchOpenY])

		cls.buttonState(cls.searchTarget.get())
		# as SearchBox is shared, binding must be reset on every open
		cls.shared.bind('<Escape>', cls.closeSearchBox)
		cls.shared.bind('<Return>', cls.handleCR)
		# override the 'X' from destroying window
		cls.shared.protocol('WM_DELETE_WINDOW', cls.closeSearchBox)
		cls.shared.attributes('-alpha', 1.0)

	# noinspection PyUnusedLocal
	@classmethod
	def closeSearchBox(cls, event=None):
		cls.searchTarget.lbCancel()
		cls.shared.closeTop()
		# unlink shared from current user's master
		cls.shared.transient('')
		# # make copy of coords in ScrollingText instance as
		# #   next 'user' will clobber mouseXY
		# cls.searchUser.searchXY = cls.shared.mouseXY[:]
		cls.searchUser = None
# end class SearchBox
			
class TextPopup(tk.Menu):
	# searchStrings = []	# search strings history, common for all Text windows
	# searchTop = None	# search window shared between ScrollingText widgets
	# searchUser = None	# ScrollingText instance curr. using searchTop (if any)
	def __init__(self, master, font, disabledFont, searchPrefix, histCmd=None):
		self.font = font
		self.disabledFont = disabledFont
		self.histCmd = histCmd
		self.searchBox = SearchBox(master, font=font, searchPrefix=searchPrefix)
		self.delUndoStack = []			# undo's include selections for undo
		self.rightMouseXY = None
		self.searchOpenXY = None
		self.leftMouseXY = None
		tk.Menu.__init__(self, master, font=font, tearoff=0,
							name=mu.TkName('TextPopup', searchPrefix))
		self.add_command(label='Select all', command=self.selectAll)
		self.add_command(label='Begin Select', command=self.beginSelect)
		self.add_command(label='End Select', command=self.endSelect)
		self.add_separator()
		self.add_command(label='Search ...', command=self.openSearchBox)
		# self.add_command(label='Center Search',
		# 				 command=lambda :self.openSearchBox(True))
		self.add_separator()
		self.add_command(label='Cut', command=self.cutText)
		self.add_command(label='Copy', command=self.copyText)
		self.add_command(label='Copy All', command=self.copyAllText)
		self.add_command(label='Paste', command=self.pasteText)
		self.add_separator()
		self.add_command(label='Delete', command=self.deleteText)
		self.add_command(label='Delete All', command=self.deleteAllText)
		self.add_separator()
		self.add_command(label='Undo delete', command=self.deleteUndo)
		if histCmd:
			self.add_separator()
			self.add_command(label='Remove command', command=histCmd)

		self.master.bind('<Button-1>', self.recordTextPosn)
		self.master.bind('<Button-3>', self.openPopUpMenu)

		self.master.bind('<<Clear>>', self.deleteText)
		self.master.bind('<BackSpace>', self.deleteText)
		self.master.bind('<Delete>', self.deleteText)

		self.master.bind('<<Cut>>', self.cutText)
		self.master.bind('<Control-X>', self.cutText)
		self.master.bind('<<Copy>>', self.copyText)
		self.master.bind('<Control-C>', self.copyText)
		self.master.bind('<<Paste>>', self.pasteText)
		self.master.bind('<Control-V>', self.pasteText)
		self.master.bind('<<Undo>>', self.deleteUndo)
		self.master.bind('<Control-Z>', self.deleteUndo)

	def selectAll(self):
		txt = self.master
		txt.tag_remove('sel', '1.0', 'end')
		txt.tag_add('sel', '1.0', 'end')
		txt.tag_raise('sel')
		self.selStart = '1.0'
		self.selEnd = 'end'
		txt.focus_set()

	def beginSelect(self):
		txt = self.master
		txt.tag_remove('sel', '1.0', 'end')
		selStart = mu.formatMouseIndex(self.master, *self.rightMouseXY)
		# txt.tag_add('sel', selStart + ' +1c') # this sets selection of current char
		self.selStart = selStart
		self.selEnd = None

	def endSelect(self):
		txt = self.master
		selStart = self.selStart
		selEnd = mu.formatMouseIndex(self.master, *self.rightMouseXY)
		if txt.compare(selStart, '>', selEnd): # backwards
			selStart, selEnd = selEnd, selStart
		if txt.compare(selEnd, "!=", txt.index(selEnd) + " linestart"):
			# ensure current character included
			selEnd = '{} +1c'.format(selEnd)
		if txt.compare(selEnd, '>', 'end'):
			selEnd = txt.index('end')
		selEnd = txt.index(selEnd)
		txt.tag_remove('sel', '1.0', 'end')
		txt.tag_add('sel', selStart, selEnd)
		if len(txt.tag_ranges('sel')) > 0:
			txt.tag_raise('sel')
			self.selEnd = txt.index('sel.last')

	# noinspection PyUnusedLocal
	def cutText(self, event=None):
		self.copyText()
		self.deleteText()

	# noinspection PyUnusedLocal
	def copyText(self, event=None):
		txt = self.master				
		# only executes if there's a selection
		if len(txt.tag_ranges('sel')) > 0:
			text = txt.get('sel.first', 'sel.last')
			self.clipboard_clear()
			self.clipboard_append(text)

	# noinspection PyUnusedLocal
	def copyAllText(self):
		txt = self.master
		text = txt.get('1.0', 'end')
		if len(text) > 1: 				# empty Text always has a NL char
			self.clipboard_clear()
			self.clipboard_append(text)

	# noinspection PyUnusedLocal
	def pasteText(self, event=None):
		txt = self.master
		text = self.clipboard_get()
		if txt.editable and len(text) > 0:
			if len(txt.tag_ranges('sel')) > 0:
				index = txt.index('sel.first')
				txt.delete('sel.first', 'sel.last')
				txt.tag_remove('sel', '1.0', 'end')
				self.clearSelection()
			elif self.focus_get() == txt:
				index = txt.index('insert')
			else:
				rootX, rootY = mu.getWidgetRoot(txt)
				index = txt.index('@{},{}'.format(
							self.rightMouseXY[0] - rootX,
							self.rightMouseXY[1] - rootY))
				txt.mark_set('insert', index)
			txt.insert(index, text)
			txt.update_idletasks()
			txt.focus_set()
		return 'break'

	# noinspection PyUnusedLocal
	def deleteUndo(self, event=None):
		txt = self.master
		if len(self.delUndoStack):
			if not txt.editable:
				txt.config(state='normal')
			self.undoDelWithTags()
			if not txt.editable:
				txt.config(state='disabled')
			txt.update_idletasks()
		return 'break'

	def undoDelWithTags(self):
		txt = self.master
		txt.tag_remove('sel', '1.0', 'end')
		tags = []
		undo = self.delUndoStack.pop()
		for key, value, index in undo:
			if key == 'tagon':
				if value not in tags:
					tags.append(value)
			elif key == 'tagoff':
				if value in tags:
					tags.remove(value)
			elif key == 'text':
				txt.mark_set('insert', index)
				txt.insert(index, value, tuple(tags))
				# - tkinter insists tags be a tuple 
				# (will silently fail otherwise)
			else:
				errmsg = 'unknown key "{}" in delUndoStack'.format(key)
				if con.CAGSPC:
					print(errmsg)
					traceback.print_exc()
					pdb.set_trace()
				else:
					gv.debugLogger.error(errmsg)

	def deleteWithTags(self, start, stop):
		txt, stack = self.master, self.delUndoStack
		stack.append(txt.dump(start, stop, tag=True, text=True))
		txt.delete(start, stop)
		txt.tag_remove('sel', '1.0', 'end')
		if len(stack) > con.MAX_UNDOS:
			stack.pop(0)

	# noinspection PyUnusedLocal
	def deleteText(self, event=None):	# only executes if there's a selection
		txt = self.master
		if len(txt.tag_ranges('sel')) > 0:
			self.master.unbind('<<Modified>>')
			if not txt.editable:
				txt.config(state='normal')
			self.deleteWithTags('sel.first', 'sel.last')
			if not txt.editable:
				txt.config(state='disabled')
			self.clearSelection()
			self.master.bind('<<Modified>>', self.resetUndoStack)
			return 'break'	# if there's no selection, let cmd pass through

	def deleteAllText(self):
		txt = self.master
		if len(txt.get('1.0', 'end')) > 1:# empty Text always has a NL char
			self.master.unbind('<<Modified>>')
			if not txt.editable:
				txt.config(state='normal')
			self.deleteWithTags('1.0', 'end')
			if not txt.editable:
				txt.config(state='disabled')
			self.clearSelection()
			if hasattr(txt, 'vScrollbar') and txt.vScrollbar.winfo_ismapped():
				txt.setVscroll(0.0, 1.0)
			self.master.bind('<<Modified>>', self.resetUndoStack)

	def openSearchBox(self, centered=False):
		self.searchBox.searchOpenXY = self.searchOpenXY
		# SearchBox is a shared widget, set this instance as 'user'
		self.searchBox.__class__.searchUser = self.searchBox
		self.searchBox.openSearchBox(centered)
		return 'break'
		
	selStart = None
	selEnd = None
	def openPopUpMenu(self, event):
		txt = self.master
		txt.event_generate('<<closeAnyOpenFrames>>')
		self.rightMouseXY = [event.x_root, event.y_root]
		if self.leftMouseXY:
			self.searchOpenXY = self.leftMouseXY
			self.leftMouseXY = None
		else:
			self.searchOpenXY = self.rightMouseXY[:]
		noSel = len(txt.tag_ranges('sel')) == 0
		empty = txt.compare('end', '<=', '2.0') \
				and len(txt.get('1.0', 'end')) == 1
		norm = ('normal', self.font)
		grey = ('disabled', self.disabledFont)
		index = self.index('end')
		if index == 0:
			return
		index += 1
		while index > 0:
			index -= 1
			# can also be 'cascade', 'checkbutton', 'command', 'radiobutton'
			if self.type(index) in ['separator', 'tearoff']: 
				continue
			label = self.entrycget(index, 'label')
			if label == 'Select all':
				state, font = norm if noSel and not empty else grey
			elif label == 'Begin Select':
				state, font = norm if self.selStart is None \
										and not empty else grey
			elif label == 'End Select':
				state, font = norm if self.selStart is not None \
										and self.selEnd is None else grey
			elif label in ['Search ...', 'Copy All', 
							'Delete All', 'Remove command']:
				state, font = grey if empty else norm
			elif label in ['Cut', 'Copy', 'Delete']:
				state, font  = grey if noSel else norm
			elif label == 'Paste':
				clipLen = 0
				# noinspection PyBroadException
				try:
					clipped = self.clipboard_get()
					clipLen = len(clipped)
				except:
					# _tkinter.TclError: CLIPBOARD selection doesn't exist or form "STRING" not defined
					pass
				state, font = norm if txt.editable and clipLen > 0 \
									else grey
			elif label == 'Undo delete':
				state, font = norm if len(self.delUndoStack) else grey
			else:						# nothing to config
				continue
			self.entryconfigure(index, state=state, font=font)
		self.post(*self.rightMouseXY)
		return 'break'

	# noinspection PyUnusedLocal
	def resetUndoStack(self, event=None):
		del self.delUndoStack[:]

	def recordTextPosn(self, event):
		self.leftMouseXY = [event.x_root, event.y_root]
		self.clearSelection()
		self.searchBox.lastSearchIdx = ''

	def clearSelection(self):
		if self.selEnd is not None:		
			# only clear outside begin/end select cycle
			self.selStart = None
			self.selEnd = None
# end class TextPopup

class ScrollbarPopup(ttk.Scrollbar):
	def __init__(self, master, associate, horizontal=False, 
						name=None, font=None, disabledFont=None):
		self.font = font
		self.disabledFont = disabledFont
		self.horizontal = horizontal
		if horizontal:
			sName = mu.TkName(name if name else 'hScrollPopup')
			ttk.Scrollbar.__init__(self, master, orient='horizontal',
									name=sName, command=self.setAssociates)
		else:
			sName = mu.TkName(name if name else 'vScrollPopup')
			ttk.Scrollbar.__init__(self, master, orient='vertical',
									name=sName, command=self.setAssociates)
		self.rightMouseXY = None
		self.associate = None
		self.associatedGroup = None
		self.singleAssociate(associate)
		self.popup = tk.Menu(self, tearoff=0, font=font, 
							name=mu.TkName('popup'))
		if horizontal:
			self.popup.add_command(label='Scroll Here', 
									command=self.scrollBodyHere)
			self.popup.add_separator()
			self.popup.add_command(label='Left Edge', 
									command=self.scrollTop)
			self.popup.add_command(label='Right Edge', 
									command=self.scrollBottom)
			self.popup.add_separator()
			self.popup.add_command(label='Page Left', 
									command=self.scrollPageUp)
			self.popup.add_command(label='Page Right', 
									command=self.scrollPageDown)
			self.popup.add_separator()
			self.popup.add_command(label='Scroll Left', 
									command=self.scrollScrollUp)
			self.popup.add_command(label='Scroll Right', 
									command=self.scrollScrollDown)
		else:
			self.popup.add_command(label='Scroll Here', 
									command=self.scrollBodyHere)
			self.popup.add_separator()
			self.popup.add_command(label='Top', 
									command=self.scrollTop)
			self.popup.add_command(label='Bottom', 
									command=self.scrollBottom)
			self.popup.add_separator()
			self.popup.add_command(label='Page Up', 
									command=self.scrollPageUp)
			self.popup.add_command(label='Page Down', 
									command=self.scrollPageDown)
			self.popup.add_separator()
			self.popup.add_command(label='Scroll Up', 
									command=self.scrollScrollUp)
			self.popup.add_command(label='Scroll Down', 
									command=self.scrollScrollDown)

		self.bind('<Button-3>', self.openScrollPopUp, add='+')
		if not self.horizontal:
			self.master.bind('<Enter>', self._bindMouseWheel)
			self.master.bind('<Leave>', self._unbindMouseWheel)

	def singleAssociate(self, associate):
		self.associate = associate
		self.associatedGroup = None

	def groupAssociates(self, group):
		self.associatedGroup = group
		self.associate = None

	# noinspection PyUnusedLocal
	def _bindMouseWheel(self, event):
		if not self.horizontal:
			if self.associate:
				self.associate.master.bind('<MouseWheel>',
											self._mouseWheel)
			else:
				for associate in self.associatedGroup:
					associate.master.bind('<MouseWheel>', 
											self._mouseWheel)

	# noinspection PyUnusedLocal
	def _unbindMouseWheel(self, event):
		if not self.horizontal:
			if self.associate:
				self.associate.master.unbind('<MouseWheel>')
			else:
				for associate in self.associatedGroup:
					associate.master.unbind('<MouseWheel>')

	def _mouseWheel(self, event):
		if con.IS_LINUX_PC:
			# event.num: 4 => scroll fwd, 5 => scroll back
			if 3 < event.num < 6:
				delta = -1 if event.num == 4 else 5
			else:
				return
		else:							
			# on Windows, event.delta is +- 120
			delta = -1 if event.delta > 0 else 1
		self.setAssociates('scroll', delta, 'units')
		# prevent default binding from scrolling 2nd time
		return 'break'

	# A scrollbar 'command' is usually set to the widget's 'xview' or 'yview'
	# and the widget's 'xscrollcommand' or 'yscrollcommand' is set to the 
	# scrollbar's 'set'
	# Here we support both single and groups of associated widgets, so
	# the scrollbar's 'command' is replaced by 'setAssociates'
	# The associated widget still uses 'set', which we override

	def set(self, lo, hi):		# move associates in lock step
		# set scrollbar position
		# super(ScrollbarPopup, self).set(lo, hi)
		# - Tk are not 'new-style classes', can't user super
		ttk.Scrollbar.set(self, lo, hi)
		# set positions of associated widgets 
		self.setAssociates('moveto', lo)

	def setAssociates(self, *args):
		if self.associate:
			self.viewAssociate(self.associate, *args)
		else:
			for associate in self.associatedGroup:
				self.viewAssociate(associate, *args)

	def viewAssociate(self, associate, *args):
		if self.horizontal:
			associate.xview(*args)
		else:
			associate.yview(*args)

	def scrollTop(self):
		self.setAssociates('moveto', 0)

	def scrollBottom(self):
		self.setAssociates('moveto', 1)

	def scrollPageUp(self):
		self.setAssociates('scroll', '-1', 'pages')

	def scrollPageDown(self):
		self.setAssociates('scroll', '1', 'pages')

	def scrollScrollUp(self):
		self.setAssociates('scroll', '-1', 'units')

	def scrollScrollDown(self):
		self.setAssociates('scroll', '1', 'units')

	def scrollBodyHere(self):
		barX, barY = mu.getWidgetRoot(self)
		mouseX, mouseY = self.rightMouseXY
		# args to fraction() must be pixel coordinates 
		# relative to the scrollbar widget
		spot = self.fraction(mouseX - barX, mouseY - barY)
		# relative positions (0.0...1.0) of slider
		top, bottom = self.get()		
		# offset to midpoint of the slider
		middle = (bottom - top)/2		
		self.setAssociates('moveto', spot - middle)

	def openScrollPopUp(self, event):
		if self != event.widget:
			# wrong instance, ignore event
			return						
		if self.winfo_class() == 'TScrollbar': 
			# filter <Button-3> events
			self.rightMouseXY = [event.x_root, event.y_root]
			top, bottom = self.get()
			menu = self.popup
			index = menu.index('end')
			if index == 0: 
				return
			lo, hi = self.get()
			fixed = lo == 0.0 and hi == 1.0
			norm = ('normal', self.font)
			grey = ('disabled', self.disabledFont)
			index += 1
			while index > 0:
				index -= 1
				# can also be 'cascade', 'checkbutton', 'command', 'radiobutton'
				if menu.type(index) in ['separator', 'tearoff']:
					continue
				label = menu.entrycget(index, 'label')
				if label in ['Top', 'Page Up', 'Scroll Up', 'Left Edge', 
							'Page Left', 'Scroll Left']:
					state, font = norm if top > 0 else grey
				elif label in ['Bottom', 'Page Down', 'Scroll Down', 
							'Right Edge', 'Page Right', 'Scroll Right']:
					state, font = norm if bottom < 1 else grey
				elif label == 'Scroll Here':
					state, font = grey if fixed else norm
				else:						# nothing to config
					continue
				menu.entryconfigure(index, state=state, font=font)
			menu.post(*self.rightMouseXY)
			return 'break'
# end class ScrollbarPopup

class ScrolledWindow(ttk.Frame):
	"""
	adapted from solution by Bryan Oakley
	https://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-group-of-widgets-in-tkinter
	
	Master widget parents a Scrollbar & Frame which parents a canvas which 
	parents another Frame.

	The inner Frame, .cvFrame is parent to any widgets installed. 
	"""


	def __init__(self, parent, *args, **kwargs):
		name = kwargs.pop('name', 'ScrWinInnerFrame')
		ttk.Frame.__init__(self, parent, borderwidth=0,
									name=mu.TkName('ScrWinOuterFrame'))
									
		self.canvas = tk.Canvas(self, name=mu.TkName('ScrWinCanvas'),
									borderwidth=0, highlightthickness=0,
									*args, **kwargs)
		self.scrollbar = ttk.Scrollbar(self, orient='vertical', 
									name=mu.TkName('ScrWinScrollbar'),
									command=self.canvas.yview)
		self.canvas.configure(yscrollcommand=self.scrollbar.set)

		self.cvFrame = ttk.Frame(self.canvas, name=name, borderwidth=0)
		self.frameID = self.canvas.create_window(0, 0, window=self.cvFrame, 
												anchor='nw', tags='cvFrame')

		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)
		self.canvas.grid(row=0, column=0, sticky='news')
		self.scrollbar.grid(row=0, column=1, sticky='news')
		# self.scrollbar.pack(side="right", fill="y")
		# self.canvas.pack(side="left", fill="both", expand=True)

		self.cvFrame.bind('<Configure>', self.onFrameConfigure, add=True)
		self.cvFrame.bind('<Enter>', self.bindMousewheel)
		self.cvFrame.bind('<Leave>', self.unbindMousewheel)

	# noinspection PyUnusedLocal
	def bindMousewheel(self, event):
		self.canvas.bind_all('<MouseWheel>', self.onMousewheel) 

	# noinspection PyUnusedLocal
	def unbindMousewheel(self, event):
		self.canvas.unbind_all('<MouseWheel>') 

	def onMousewheel(self, event):			
		self.canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')  
		
	# noinspection PyUnusedLocal
	def onFrameConfigure(self, event=None):
		self.canvas.configure(scrollregion=self.canvas.bbox('cvFrame'))
		return 'break'
# end class ScrolledWindow

class ScrollingText(tk.Text):
	# fonts are required as using TextPopup & ScrollbarPopup
	def __init__(self, master, font, disabledFont, 
					   searchPrefix='', editable=False,
					   hScroll=False, histCmd=None, **kwargs):
		self.font = font
		self.editable = editable
		self.hScroll = hScroll

		vName = mu.TkName(kwargs.get('name', 'scrollText'), 'Frame')
		self.frame = ttk.Frame(master, name=vName)
		# make frame stretchable
		self.frame.rowconfigure(0, weight=1)
		self.frame.columnconfigure(0, weight=1)
		# - frame is .grid() by caller

		tk.Text.__init__(self, self.frame, **kwargs)
		self.config(state='normal' if editable else 'disabled')
		self.popup = TextPopup(self, histCmd=histCmd, font=font, 
									 disabledFont=disabledFont,
									 searchPrefix=searchPrefix)
		self.bind('<<Modified>>', self.popup.resetUndoStack)

		self.vScrollbar = ScrollbarPopup(self.frame, self, 
										 name=mu.TkName('vScrollbar'),
										 disabledFont=disabledFont, font=font)
		self['yscrollcommand'] = self.setVscroll

		self.stopper = ttk.Frame(self.frame, name=mu.TkName('stopper'),
											 width=con.SCROLL_WIDTH,
											 height=con.SCROLL_HEIGHT)

		self.grid(row=0, column=0, sticky='news')
		self.stopper.grid(row=1, column=1, sticky='se')
		# vanishing scrollbars disable for users until sure endless
		# recursion bug fixed (see checkStopper & needsScrollbars too)
		if con.CAGSPC:
			self.stopper.grid_remove()
		self.stopper.grid_propagate(0)
		self.vScrollbar.grid(row=0, column=1, sticky='ns')
		self.vScrollbar.grid_remove()

		if hScroll:
			self.hScrollbar = ScrollbarPopup(self.frame, self, font=font, 
											 name=mu.TkName('hScrollbar'),
											 horizontal=True,
											 disabledFont=disabledFont)
			self['xscrollcommand'] = self.setHscroll
			self.hScrollbar.grid(row=1, column=0, sticky='ew')
			self.hScrollbar.grid_remove()

	def setVscroll(self, lo, hi):
		self.setScrollbars('vertical', lo, hi)

	def setHscroll(self, lo, hi):
		self.setScrollbars('horizontal', lo, hi)

	vIsMapped = hIsMapped = False
	def setScrollbars(self, caller, lo, hi):
		# Tk calculates lo & hi, based on what's currently
		# visible, not the widest line overall; if you scroll down
		# to a line that's too wide, only then is 'hi' a value < 1.0 sent
		# thus, it can happen that one scrollbar drives the other and an
		# endless loop of griding/removing occurs
		# - stopper frame ensures they never overlap
		# - scrollbar's .set must only be called on function exit otherwise the
		#   other scrollbar will execute this handler before the currently
		#   executing one is finished; even still, griding/removing can result
		#   in a 2nd call (same 'caller' orientation) before we're finished!
		# - if need to call update_idletasks(), do so before griding/removing
		#   as it will generate events, like .set
		# - any change in griding of any of these will generate events so it's
		#   quite fine (and simpler) to bail after any such change

		def needsRemoval(low, high):
			return (low is not None and low <= 0.0
					and high is not None and high >= 1.0)

		def needsMapping(low, high):
			return ((low is not None and low > 0.0)
					or (high is not None and high < 1.0))

		def checkStopper():
			if self.vIsMapped and self.hIsMapped:
				if not self.stopper.winfo_ismapped():
					self.stopper.grid()
					if self._dbg:
						print('    stopper.grid()')
			elif self.stopper.winfo_ismapped():
				self.stopper.grid_remove()
				if self._dbg:
					print('    stopper.grid_remove()')

		if not self.winfo_ismapped():
			return

		if not self.hScroll:
			# widget with a single, vertical scrollbar, no need
			# to call needsHorizontal()
			lowV, highV = float(lo), float(hi)
			if self.vIsMapped and needsRemoval(lowV, highV):
				self.vScrollbar.grid_remove()
				self.vIsMapped = False
				checkStopper()
			elif not self.vIsMapped and needsMapping(lowV, highV):
				self.vScrollbar.grid()
				self.vIsMapped = True
				checkStopper()
			return
		self.update_idletasks()

		if self._dbg:
			print('.\nsetScrollbars, {!r}, {!r}, vIsMapped: {}, hIsMapped: {}'.format(
					self._name, caller, self.vIsMapped, self.hIsMapped))

		# needsVertical, needsHorizontal = self.needsScrollbars()
		needsVertical, needsHorizontal = self.needsScrollbars()

		if self._dbg:
			print('  needsV: == {} ==, needsH: ** {} **, lo: {:.3}, hi: {:.3}'.format(
					needsVertical, needsHorizontal, float(lo), float(hi)))

		altered = False
		if needsVertical and not self.vIsMapped:
			self.vScrollbar.grid()
			self.vIsMapped = True
			altered = True
			if self._dbg:
				print('  vScrollbar.grid()')
		elif not needsVertical and self.vIsMapped:
			self.vScrollbar.grid_remove()
			self.vIsMapped = False
			altered = True
			if self._dbg:
				print('  vScrollbar.grid_remove()')

		if needsHorizontal and not self.hIsMapped:
			self.hScrollbar.grid()
			self.hIsMapped = True
			altered = True
			if self._dbg:
				print('  hScrollbar.grid()')
			# initially, hScrollbar will display % of hidden line
			self.update_idletasks()
		elif not needsHorizontal and self.hIsMapped:
			self.hScrollbar.grid_remove()
			self.hIsMapped = False
			altered = True
			if self._dbg:
				print('  hScrollbar.grid_remove()')

		if altered and con.CAGSPC:
			# unsure this is wise
			checkStopper()
			return
		elif caller == 'vertical':
			self.vScrollbar.set(lo, hi)
			if self._dbg:
				print('  vScrollbar.set', lo, hi)
			return # .set must be last call
		elif caller == 'horizontal':
			self.hScrollbar.set(lo, hi)
			if self._dbg:
				print('  hScrollbar.set', lo, hi)
			return  # .set must be last call

	_dbg = True and False  #
	def needsScrollbars(self):

		def lineWidth(index):
			return self.tk.call(self._w, 'count', '-xpixels',
								self.index(index + ' linestart'),
								self.index(index + ' lineend'))

		def widthExceeded(index, count, direction):
			exceeds = False
			checking = index
			while count > 0:
				_Width = lineWidth(checking)
				exceeds = exceeds or _Width > width
				if direction < 0 and self.compare(checking, '<=', '1.0'):
					break
				if direction > 0 and self.compare(checking, '>=', lastLine):
					break
				checking = self.index(checking + ' {} 1 lines lineend'.format(
												'-' if direction < 0 else '+'))
				count -= 1
			return exceeds

		if not con.CAGSPC:
			return True, True
		# these exclude scrollbars if present
		width, height = self.winfo_width(), self.winfo_height()
		vScrollMapped = self.vScrollbar.winfo_ismapped()
		hScrollMapped = self.hScrollbar.winfo_ismapped()
		vScrollWidth = self.vScrollbar.winfo_width() if vScrollMapped else 0
		start = self.index('@0, 0')
		lastLine = self.index('end - 1 lines lineend') # Text always ends w/ blank line
		needsVertical = self.compare(start, '>', '1.0') \
						or self.compare(self.index('@0,{}'.format(height)),
										'<', lastLine)
		if vScrollMapped or needsVertical:
			width -= vScrollWidth
		# stop can be off by depending on how much of a partial line is visible
		# ie. with scrollbar visibility unchanged, scrolling by pixels, stop will
		#     increase to next line while start does not change
		stop = self.index('@{}, {} lineend'.format(width, height))		# the last visible line
		if self.compare(start, '==', stop):
			return needsVertical, False
		hScrollHeight = self.hScrollbar.winfo_height() if hScrollMapped else 0
		covered = 1
		if hScrollMapped:
			# check line under hScrollbar to avoid thrashing it on/off
			dline = self.dlineinfo(start)
			if len(dline) == 5: # [x, y, width, height, baseline]
				covered = hScrollHeight // dline[3] + 1 # ceil
			# .index respects scrollbars, so increase stop to ensure that
			# lines covered by hScrollbar are measured
			stop = self.index(stop + ' + {} lines lineend'.format(covered))
			if self._dbg:
				print('  covered: {} = hScrollHeight: {} // dline[3]: {} (: {}) + 1; stop now {}'.format(
						covered, hScrollHeight, dline[3], (hScrollHeight // dline[3]), stop))
		# check partial lines top & bottom
		chkTop = widthExceeded(start, covered, -1)
		if self._dbg:
			print('needsHscrollbar, widthExceeded({}, {}, -1) is {}'.format(start, covered, chkTop))
		if chkTop:
			return needsVertical, True
		chkBottom = widthExceeded(stop, covered + 1, 1)
		if self._dbg:
			print('needsHscrollbar, widthExceeded({}, {}, 1) is {}'.format(stop, covered, chkBottom))
		if chkBottom:
			return needsVertical, True
		lineIdx = start
		while True:
			lineIdx = self.index(lineIdx + ' + 1 line')
			if self.compare(lineIdx, '>=', stop):
				break
			if lineWidth(lineIdx) > width:
				if self._dbg:
					print('needsScrollbars, lineWidth(lineIdx={}): {} > {} width '.format(
						lineIdx, lineWidth(lineIdx), width))
				return needsVertical, True
		return needsVertical, False

# end class ScrollingText

class ScrollingListBox(tk.Listbox):
	# fonts are required as using ScrollbarPopup
	def __init__(self, master, disabledFont, label=None,
					   suppressHelper=False, lbColumn=None, **kwargs):
		# bg = kwargs.get('background', None)
		# if not bg:
		# 	bg = kwargs.get('bg')
		font = con.LISTBOX_OPTIONS['font']
		# lbColumn is used when griding Listbox;
		# set > 0 if widgets appear to its left
		self.lbColumn = lbColumn
		self.lbFrame = ttk.Frame(master, name=mu.TkName('lbFrame'))
		lbName = kwargs['name'] if 'name' in kwargs else mu.TkName('scrListBox')
		tk.Listbox.__init__(self, self.lbFrame, name=lbName, **con.LISTBOX_OPTIONS)
		self.scrollbar = ScrollbarPopup(self.lbFrame, self, font=font,
										disabledFont=disabledFont)
		# we have work to do before calling self.scrollbar.set
		self['yscrollcommand'] = self.setStopper

		# a frame replaces the scrollbar when not in use to prevent
		# the app's widgets from moving 
		self.stopper = ttk.Frame(self.lbFrame, name=mu.TkName('stopper'),
								 width=con.SCROLL_WIDTH)
		self.stopper.grid_propagate(0)

		if not suppressHelper:
			self.bind('<KeyPress>', self.firstCharHelper)
		self.label = None
		if label:
			font = kwargs.get('font')
			self.label = ttk.Label(self.lbFrame, font=font,
									name=mu.TkName('label'),
									anchor='center', text=label)
			self.label.grid(row=0, column=0, columnspan=2, sticky='ew')
		row = 1 if self.label else 0
		column = 0 if self.lbColumn is None else self.lbColumn
		self.grid(row=row, column=column, sticky='ns')
		self.scrollbar.grid(row=row, column=column + 1, sticky='ns')
		self.stopper.grid(row=row, column=column + 1, sticky='ns')
		self.stopper.grid_remove()

	def setStopper(self, lo, hi):
		low, high = float(lo), float(hi)
		isMapped = self.scrollbar.winfo_ismapped()
		if isMapped and low <= 0.0 and high >= 1.0:
			self.scrollbar.grid_remove()
			self.stopper.grid()
		elif not isMapped and (low > 0.0 or high < 1.0):
			self.stopper.grid_remove()
			self.scrollbar.grid()
		self.scrollbar.set(lo, hi)

	def firstCharHelper(self, event):	
		# move to point in list where items start with key pressed
		keyPressed = event.char.lower()
		selection = self.get(0, 'end')
		if len(selection) == 0: return	# no items
		choices = [sel for sel in selection if sel[0].lower() == keyPressed]
		if len(choices) == 0: return	# no items start with keyPressed
		first, last = selection.index(choices[0]), selection.index(choices[-1])
		top, bottom = self.nearest(0), self.nearest(self.winfo_height())
		selected = self.curselection()
		index = selected[0] if len(selected) > 0 else top
		firstChar = selection[index][0] if len(selection[index]) > 0 else ''
		firstOfNext = selection[index + 1][0] \
						if len(selection) > index \
							and len(selection[index]) > 0 else ''
		if firstChar.lower() == keyPressed \
				and firstOfNext.lower() == keyPressed: 
			# continue along through group
			target = index + 1
		else:							# force scroll so more are visible
			if index <= last and index != first:
				target = last if last > bottom else first
			else:
				target = first if first < top else last
		if target == first and first != last:
			distance = (target - top) if target < top \
									else (target - bottom - len(choices)) \
									if target > bottom else 0
		else:
			distance = (target - bottom) if target > bottom \
									else (target - bottom - len(choices)) \
									if target < top else 0
		self.yview('scroll', distance, 'units')
		self.selection_clear(0, 'end')
		self.selection_set(target)

	def setContents(self, selection):
		self.delete(0, 'end')
		self.insert('end', *selection)

	def closeBox(self):
		self.lbFrame.grid_remove()

	def restoreBox(self, **kwargs):
		self.lbFrame.grid(**kwargs)
# end class ScrollingListBox

class StartUpAbort(tk.Frame):
	def __init__(self, errmsg, title):
		self.root = tk.Tk()
		self.root.title(title)
		self.root.resizable(width=False, height=False)
		titleFont = tkFont.Font(family='Arial', size=16, weight='bold')
		errorFont = tkFont.Font(family='Arial', size=12)

		tk.Frame.__init__(self, self.root)
		self.grid(sticky='news')
		
		fmtMsg = self.formatMsg(errmsg, errorFont)
		self.msgLabel = tk.Label(self, text=fmtMsg, 
								font=errorFont, justify='left')
		self.btnOK = tk.Button(self, text='OK', font=titleFont, padx=10, 
								command=self.destroyStartUpAbort)
		self.msgLabel.grid(	row=0, column=0, padx=10, pady=10)
		self.btnOK.grid(	row=1, column=0, sticky='s')
		self.btnOK.rowconfigure(0, minsize=50)
		self.btnOK.columnconfigure(0, minsize=50)
		
		self.bind_all('<Return>', self.destroyStartUpAbort)
		self.bind_all('<Escape>', self.destroyStartUpAbort)
		self.btnOK.focus_force()

	# noinspection PyUnusedLocal
	def destroyStartUpAbort(self, event=None):
		self.root.destroy()
		
	@staticmethod
	def formatMsg(errmsg, errFont):
		zeroLen = errFont.measure('0')
		msgLines = []
		for line in errmsg.split(con.NL):
			msg = ''
			if errFont.measure(line) > con.MINIMUM_WIDTH:
				prefix = ''
				while line.startswith(' '):
					prefix += ' '
					line = line[1:]
				msg += prefix
				msgLen = errFont.measure(prefix) if len(prefix) else 0
				for word in line.split():
					measured = errFont.measure(word)
					if msgLen + measured + zeroLen > con.MINIMUM_WIDTH:
						msgLines.append(msg)
						msg, msgLen = prefix, 0
					msg += word + ' '
					msgLen += measured + zeroLen
			else:
				msg += line
			msgLines.append(msg)
		msgLines.append('\nThis debug console will close now.\n')
		return '\n'.join(msgLines)

