#! /usr/bin/python
#
#  DebugConsole.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#
#  GUI I/O stuff (c) 2008-2012 Kaks. CC-by-NC-SA 3
#

"""
A gui implementation of the Oolite JavaScript debug console interface.
"""

__author__	= "Jens Ayton <jens@ayton.se>, Kaks"
__version__	= "1.5"


from ooliteConsoleServer import *
from twisted.internet.protocol import Factory
from twisted.internet import stdio, reactor, tksupport
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol
from Tkinter import *

import string, os, ConfigParser, pickle


CFGFILE = 'DebugConsole.cfg'
# if we're using the compiled version, it's OoDebugConsole.cfg rather than DebugConsole.cfg
if hasattr (sys,'frozen'): CFGFILE = 'Oo' + CFGFILE

# use a corresponding cli history file.
HISTFILE = CFGFILE.replace('.cfg','.dat')

class SimpleConsoleDelegate:
	__active = Active = False
	
	def __init__(self, protocol):
		self.protocol = protocol
		self.identityString = "DebugConsole"
	
	def __del__(self):
		if self.__active: self.protocol.factory.activeCount -= 1
		if cliHandler.inputReceiver is self:  cliHandler.inputReceiver = None
	
	def acceptConnection(self):
		return self.protocol.factory.activeCount < 1
	
	def connectionOpened(self, ooliteVersionString):
		app.Print ("Opened connection with Oolite version "+ ooliteVersionString)
		self.protocol.factory.activeCount += 1
		self.__active = self.Active = True
		cliHandler.inputReceiver = self
	
	def connectionClosed(self, message):
		if message is None or isinstance(message, str):
			if message is not None and len(message) > 0:
				app.Print ('Connection closed:"' + message +'"')
			else:
				app.Print ("Connection closed with no message.")
		if self.__active:
			self.protocol.factory.activeCount -= 1
			self.__active = self.Active = False
		app.tried=0
	
	def writeToConsole(self, message, colorKey, emphasisRanges):
		app.colPrint(message, colorKey)
	
	def clearConsole(self):
		app.cClear(True)
		
	def showConsole(self):
		if (ENABLESHOW):
			if root.state() is not 'zoomed' and root.state() is not 'normal': root.state('normal')
			root.wm_attributes("-topmost", 1)
			root.wm_attributes("-topmost", 0)
			app.cli.focus_set()
	
	def send(string):
		receiveUserInput(string)
	
	def receiveUserInput(self, string):
		self.protocol.sendCommand(string)
	
	def closeConnection(self, message):
		self.protocol.closeConnection(message)

def getInputReceiver():
	return currentInputReceiver


class Window:
	def __init__(self,master):
		self.tried=0
		
		self.frame = Frame(master)
		self.frame.place(relwidth=1, relheight=1, height=-60)
		
		self.yScroll = Scrollbar (self.frame, orient=VERTICAL, width=16)
		self.yScroll.pack(side=LEFT, anchor=E, fill=Y, expand=YES)
		
		self.BodyText = Text(self.frame,bg="#dadddd", bd=0, padx=2, font=('arial', 10, 'normal'), wrap=WORD, yscrollcommand=self.yScroll.set)
		
		self.BodyText.tag_config('dbg')
		self.BodyText.place(relwidth=1, relheight=1, width=-16)
		
		self.yScroll.config(command=self.BodyText.yview)
		
		self.cliBox = Frame(master)
		self.cliBox.place(rely=1,anchor=SW, relwidth=1, height=60)
		
		self.cli = Text(self.cliBox, bd=2, relief=FLAT, bg="#fff",font=('arial', 10, 'normal'))
		self.cli.place(relwidth=1,relheight=1,width=-50)
		self.cli.bind('<Return>', self.cRet)
		self.cli.bind("<Up>", self.cHistoryBack)
		self.cli.bind("<Down>", self.cHistoryForward)
		
		self.cli.focus_set()
		
		self.btnRun = Button(self.cliBox, text=" Run", bg='#ccc', command=self.cRun)
		self.btnRun.place(anchor=NE, relx=1, height=38, width=50)
		self.btnExit = Button(self.cliBox, bg='#ddd', text=" Clear", command=self.cClear)
		self.btnExit.place(anchor=NE, relx=1, y=38, height=22, width=50)
		
		# Command history
		
		self.history = []
		self.historyIdx = None
		self.current = ""
		
	def cRet(self,event):
		self.cRun()
		return 'break'
	
	def cRun(self):
		if '/quit' == self.cli.get( '1.0', END)[:5]:
			self.cExit()
		else:
			self.historyIdx = None
			self.CMD = self.cli.get( '1.0', END)
			idx = len(self.history) - 1;
			if string.strip(self.CMD) and (idx < 0 or self.CMD != self.history[idx]):
				self.history.append(self.CMD)		
			if hasattr (cliHandler.inputReceiver,'receiveUserInput') and cliHandler.inputReceiver.Active:
				self.tried = 0
				cliHandler.inputReceiver.receiveUserInput(self.CMD)
				self.cli.delete( '1.0', END) 
			else:
				if self.tried == 0:
					self.Print("\n"+CONNECTINFO+"\nYou can only use the console after you're connected.")
				elif self.tried == 1:
					self.Print(' * Please connect to Oolite first! * ')
				self.tried=self.tried+1
		
	def Print(self,s):
		self.colPrint(s,'dbg')
	
	def colPrint(self,s,colkey):
		colkey = colkey.lower()
		isDbg = True
		if colkey != 'dbg':
			isDbg = False
			s = s.strip(' \t\n\r')
			if len(s) >0: s = s + '\n'
		
		txt = self.BodyText
		try:
			if not isDbg: tmp = COLORS[colkey]
		except Exception:
			if (DEBUGCOLS): s = '['+colkey+'] ' + s
			colkey = 'dbg'
			isDbg = True
		
		txt.config(state=NORMAL)
		txt.insert(END,s,colkey)
		if len(s) < 1 or isDbg: txt.insert(END,'\n','dbg')
		txt.config(state=DISABLED)
		txt.see(END)
		txt.tag_raise('sel')
	
	def cClear(self,body=False):
		if body or OLDCLEAR:
			self.tried = 0
			self.BodyText.config(state=NORMAL)
			self.BodyText.delete('1.0', END)
			self.BodyText.config(state=DISABLED)
		else:
			self.cli.delete('1.0', END)
	
	def cHistoryBack(self, event):
		if self.history:
			if self.historyIdx is None:
				self.current = self.cli.get( '1.0', END)
				self.historyIdx = len(self.history) - 1
			elif self.historyIdx > 0:
				self.historyIdx -= 1
			self.cHistoryShow()
		return 'break'
	
	def cHistoryForward(self, event):
		if self.history and self.historyIdx is not None:
			self.historyIdx += 1
			if self.historyIdx < len(self.history):
				self.cHistoryShow()
			else:
				self.historyIdx = None
				self.cHistoryShow(self.current)
		return 'break'
	
	def cHistoryShow(self, cmd=None):
		if cmd is None:
			cmd = self.history[self.historyIdx]
		self.cli.delete('1.0', END)
		self.cli.insert(END,cmd.rstrip())
	
	def cExit(self_):
		saveConfig = True
		saveHistory = True
		config = ConfigParser.RawConfigParser()
		config.optionxform = str
		try:
			fp = open(CFGFILE)
			config.readfp(fp)
			try:
				saveConfig = config.getboolean('Settings','SaveConfigOnExit')
			except:
				pass
			try:
				saveHistory = config.getboolean('Settings','SaveHistoryOnExit')
			except:
				pass
			fp.close()
		except Exception: 
			pass
		
		if saveConfig:
			try:
				if not config.has_section('Settings'):
					config.add_section('Settings')
				config.set('Settings', 'SaveConfigOnExit', 'Yes')
				config.set('Settings', 'Geometry', root.geometry())
				cfg = open(CFGFILE, 'w')
				config.write(cfg)
				cfg.close()
			except Exception:
				pass
		if saveHistory:
			try:
				hfile = open(HISTFILE, 'wb')
				pickle.dump(app.history[-200:], hfile, -1)
				hfile.close()
			except Exception:
				pass
		
		reactor.stop()


root = Tk()
app = Window(root)
root.minsize(320, 300)
root.resizable(YES, YES)
root.title("Oolite - Javascript Debug Console")
root.protocol("WM_DELETE_WINDOW", app.cExit)


# Load initial settings
consolePort = None
DEBUGCOLS = False
ENABLESHOW = True
OLDCLEAR = False
CONNECTINFO = "Please (re)start Oolite in order to connect."
initConfig = ConfigParser.RawConfigParser()
try:
	fp = open(CFGFILE)
	initConfig.readfp(fp)
	fp.close()
	try:
		settings = initConfig.get('Settings','Geometry')
	except:
		pass
	try:
		consolePort = initConfig.get('Settings','Port')
	except:
		pass
	try:
		DEBUGCOLS = initConfig.getboolean('Settings','DebugColors')
	except:
		pass
	try:
		ENABLESHOW = initConfig.getboolean('Settings','EnableShowConsole')
	except:
		pass
	try:
		OLDCLEAR = initConfig.getboolean('Settings','OldClearBehaviour')
	except:
		pass
	try:
		CONNECTINFO = initConfig.get('Settings','ConnectInfo')
	except:
		pass

except Exception: 
	pass
# if size & position settings are not valid, revert to default
try:
	root.geometry(settings)
except Exception:
	root.geometry("500x380")


# Set up icon if possible
try:
#	windows compiled runtime (pyInstall)
	root.iconbitmap(os.path.join(os.environ['_MEIPASS2'], "OoJSC.ico"))
except Exception:
	try: 
# 	normal windows runtime
		root.iconbitmap("OoJSC.ico")
	except Exception:
#	other runtimes, try not to use the tk icon
		try:
			root.iconbitmap('@block.xbm')
		except Exception:
			pass

# Set up the console's port using the Port setting inside the .cfg file.
# All dynamic, private, or ephemeral ports 'should' be between 49152-65535. However, the default port is 8563.
connectPort = defaultOoliteConsolePort
if consolePort is not None:
	try:
		consolePort = int(consolePort)
	except:
		pass
	if consolePort > 1 and consolePort < 65536:
		connectPort = consolePort
		app.Print ("Listening on port " + str(connectPort) +".")
		root.title("Oolite - Javascript Debug Console:" + str(connectPort))
	else:
		app.Print ("Invalid port specified. Using default port (" + str(connectPort) +").")

# Set up Colors:
COLORS = {'general':'#000','command':'#006','warning':'#660','error':'#800','exception':'#808'}

COLORS['command-result'] = '#050'
COLORS['command-error'] = '#600'

COLORS['macro-expansion'] = '#999'
COLORS['macro-warning'] = '#aa5'
COLORS['macro-list'] = '#5a5'

COLORS['unknown-macro'] = '#aa5'
COLORS['macro-error'] = '#a55'
COLORS['macro-info'] = '#5a5'
COLORS['command-exception'] = '#606'

txt = app.BodyText
txt.tag_configure('sel', foreground ='#dcecf2', background='#5c6070')

if initConfig.has_section('Colors'):
	cols = initConfig.options('Colors')
	for col in cols:
		try:
			tmp = initConfig.get('Colors', col)
			txt.tag_configure('tmp', foreground=tmp)
			COLORS[col.lower()] = tmp
		except:
			if DEBUGCOLS: app.Print(" CFG Error: "+col+" = "+tmp+" -  wrong value '"+tmp+"'")
if float(txt.index(END)) > 2: app.Print('')
			
for col,val in COLORS.items():
	txt.tag_configure(col, foreground=val)
	if col is 'command': txt.tag_configure(col, font=('arial',9,'bold'), background='#e8ebeb')

#app.Print(COLORS)

# Restore CLI history from its savefile
try:
	hfile = open(HISTFILE, 'rb')
	app.history = pickle.load(hfile)
	hfile.close()
	if not isinstance(app.history, list):
		app.history = []
except:
	pass

# Set up console server protocol
factory = Factory()
factory.delegateClass = SimpleConsoleDelegate
factory.activeCount = 0
factory.protocol = OoliteDebugConsoleProtocol

# Set up command line I/O protocol
cliHandler = OoliteDebugCLIProtocol()
cliHandler.getInputReceiver = getInputReceiver
stdio.StandardIO(cliHandler)

# Install the Reactor support
tksupport.install(root)

try:
	app.listener=reactor.listenTCP(connectPort, factory)
	app.Print ("Use Up and Down arrows to scroll through the command history.")
	app.Print ("Type /quit to quit.")
	app.Print ("Waiting for connection...")
except Exception, e:
	oops = str(e)
#	oops = "\nAnother process is already listening on "
#	oops += "\nthe default port." if (connectPort == defaultOoliteConsolePort) else "port " + str(connectPort) +"."
	oops += "\n\nThis debug console will close now."
	root.minsize(1, 1)
	root.resizable(NO, NO)
	root.geometry("320x166")
	root.protocol("WM_DELETE_WINDOW", reactor.stop)
	app.yScroll.pack_forget()
	app.btnOK = Button(app.cliBox, text="OK", bg='#eee', font=('arial', 17, 'bold'), command=reactor.stop)
	app.btnOK.place(relwidth=1,relheight=1)

	txt.place(width=0)
	txt.configure(bg="#fffdfd")
	txt.config(state=NORMAL)
	txt.delete('1.0', END)
	txt.tag_configure('header', justify=CENTER, font=('arial', 11, 'bold'), foreground='#600')
	txt.tag_configure('center', justify=CENTER)
	txt.insert(END,'\nInitialisation Error\n\n','header')
	txt.insert(END,oops,'center')
	root.geometry("320x" + str(int((float(txt.index(END))-5)*16 + 166)))
	txt.config(state=DISABLED)

# Wait for user input.
reactor.run()
