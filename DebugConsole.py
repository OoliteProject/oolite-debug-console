#! /usr/bin/python
#
#  DebugConsole.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#
#  GUI I/O  & Windows hackery by Kaks (2008-02-25)
#

"""
A gui implementation of the Oolite JavaScript debug console interface.
Tested on Windows, should be Linux compatible.
"""

__author__	= "Jens Ayton <jens@ayton.se>, Kaks"
__version__	= "1.0"


from ooliteConsoleServer import *
from twisted.internet.protocol import Factory
from twisted.internet import stdio, reactor,tksupport
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol

from Tkinter import *
import tkFileDialog,string

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
		frame = Frame(master)
		frame.place(width=500, height=320)

		self.yScroll = Scrollbar ( frame, orient=VERTICAL )
		self.yScroll.place ( x=0,y=488, )

		self.BodyText = Text(frame,bg="#abb",bd=0,font=('arial', 10, 'normal'),wrap=WORD,yscrollcommand=self.yScroll.set)
		self.BodyText.place(x=0, y=0, width=490,height=320)
		self.BodyText.tag_config('input',font=('arial', 10, 'bold'),background='#e2e2e2',bgstipple='gray25')
		self.yScroll.config(command=self.BodyText.yview)
		self.yScroll.pack(side=RIGHT, fill=Y)
		self.BodyText.pack(side=LEFT, fill=BOTH, expand=1)

		self.lineContainer = Frame(master,bg="#ddd")
		self.lineContainer.place(x=0,y=320,width=500,height=60)

		self.cline = Text(self.lineContainer,bd=0, bg="#fff",font=('arial', 10, 'normal'))
		self.cline.place(x=2, y=0, width=448,height=60)
		self.cline.bind('<Return>', self.cRet)
		self.btnRun = Button(self.lineContainer, text="Run", command=self.cRun)
		self.btnRun.place(x=450,y=0, height=40, width=50)

		self.btnExit = Button(self.lineContainer, text="Clear", command=self.cClear)
		self.btnExit.place(x=450,y=40, height=20, width=50)
		self.cline.focus_set()

	def cRet(self,event):
		self.cRun()
		return 'break'

	def cRun(self):
		if '/quit' == self.cline.get( '1.0', END)[:5]:
			reactor.stop()
		if hasattr (cliHandler.inputReceiver,'receiveUserInput') and cliHandler.inputReceiver.Active:
			self.tried = 0
			self.BodyText.config(state=NORMAL)
			self.CMD=self.cline.get( '1.0', END)
			cliHandler.inputReceiver.receiveUserInput (self.CMD)
			self.CMD='> '+self.CMD
			self.BodyText.insert(END,self.CMD,'input')
			self.cline.delete( '1.0', END) 
			self.BodyText.config(state=DISABLED)
			self.BodyText.see(END)
		else:
			if self.tried == 0:
				self.Print("\nPlease (re)start Oolite in order to connect.\nYou can only use the console once you're connected.")
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
		self.BodyText.config(state=NORMAL)
		self.BodyText.delete('1.0', END)
		self.BodyText.config(state=DISABLED)


		
root = Tk()
root.title("Oolite - Javascript Debug Console")
root.geometry("500x380")
root.resizable(0,0)
root.protocol("WM_DELETE_WINDOW", reactor.stop)
app = Window(root)

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
