#! /usr/bin/python
#
#  DebugConsole.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#

#  GUI I/O stuff (c) 2008-2011 Kaks. CC-by-NC-SA 3
#

"""
A gui implementation of the Oolite JavaScript debug console interface.

"""

__author__	= "Jens Ayton <jens@ayton.se>, Kaks"
__version__	= "1.2"


from ooliteConsoleServer import *
from twisted.internet.protocol import Factory
from twisted.internet import stdio, reactor, tksupport
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol

from Tkinter import *
import string, os

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
		if message != None and len(message) > 0:
			app.Print ("Connection closed with message: "+ message)
		else:
			app.Print ("Connection closed with no message.")
		if self.__active:
			self.protocol.factory.activeCount -= 1
			self.__active = self.Active = False
	
	def writeToConsole(self, message, colorKey, emphasisRanges):
		#assuming the first 2 lines are the command echo
		app.mPrint(message)
	
	def clearConsole(self):
		pass
		
	def showConsole(self):
		pass
	
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

		self.BodyText = Text(self.frame, bg="#cacdcd", bd=0, font=('arial', 10, 'normal'), wrap=WORD,yscrollcommand=self.yScroll.set)

		self.BodyText.tag_config('input', font=('arial', 10, 'bold'), background='#e0e2e2')
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
			reactor.stop()
		else:
			self.historyIdx = None
			self.CMD = self.cli.get( '1.0', END)
			idx = len(self.history) - 1;
			if string.strip(self.CMD) and (idx < 0 or self.CMD != self.history[idx]):
				self.history.append(self.CMD)		
			if hasattr (cliHandler.inputReceiver,'receiveUserInput') and cliHandler.inputReceiver.Active:
				self.tried = 0
				self.BodyText.config(state=NORMAL)
				cliHandler.inputReceiver.receiveUserInput (self.CMD)
				self.CMD='> '+self.CMD
				self.BodyText.insert(END,self.CMD,'input')
				self.cli.delete( '1.0', END) 
				self.BodyText.config(state=DISABLED)
				self.BodyText.see(END)
			else:
				if self.tried == 0:
					self.Print("\nPlease (re)start Oolite in order to connect.\nYou can only use the console after you're connected.")
				elif self.tried == 1:
					self.Print(' * Please connect to Oolite first! * ')
				self.tried=self.tried+1

	def mPrint (self,str):
		if not hasattr(self,'CMD'):
			self.Print(str)
		else:
			if str[:len(self.CMD)] == self.CMD:
				str=string.strip(str[len(self.CMD):])
			self.Print(str)

	def Print(self,str):
		self.BodyText.config(state=NORMAL)
		self.BodyText.insert(END,str+'\n')
		self.BodyText.config(state=DISABLED)
		self.BodyText.see(END)

	def cClear(self):
		self.tried = 0
		self.BodyText.config(state=NORMAL)
		self.BodyText.delete('1.0', END)
		self.BodyText.config(state=DISABLED)

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


root = Tk()
app = Window(root)
root.minsize(320, 300)

try:
#	windows compiled runtime (pyInstall)
	root.iconbitmap(os.path.join(os.environ['_MEIPASS2'], "OoJSC.ico"))
except Exception:
	try: 
# 	normal windows runtime
		root.iconbitmap("OoJSC.ico")
	except Exception:
#	other runtimes, don't use the tk icon!
		root.iconbitmap('@block.xbm')
root.title("Oolite - Javascript Debug Console")

root.resizable(YES, YES)
root.protocol("WM_DELETE_WINDOW", reactor.stop)


app.Print ("Use Up and Down arrows to scroll through the command history.")
app.Print ("Type /quit to quit.")
app.Print ("Waiting for connection...")

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
app.listener=reactor.listenTCP(defaultOoliteConsolePort, factory)
reactor.run()
