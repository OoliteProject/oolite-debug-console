#! /usr/bin/python
#
#  pySimpleConsole.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


"""
A simple implementation of the Oolite JavaScript debug console interface.
"""

__author__	= "Jens Ayton <jens@ayton.se>"
__version__	= "1.0"


from ooliteConsoleServer import *
from twisted.internet.protocol import Factory
from twisted.internet import stdio, reactor
from OoliteDebugCLIProtocol import OoliteDebugCLIProtocol


cliHandler = None


class SimpleConsoleDelegate:
	__active = False
	
	def __init__(self, protocol):
		self.protocol = protocol
		self.identityString = "pySimpleConsole"
	
	def __del__(self):
		if self.__active: self.protocol.factory.activeCount -= 1
		if cliHandler.inputReceiver is self:  cliHandler.inputReceiver = None
	
	def acceptConnection(self):
		return self.protocol.factory.activeCount < 1
	
	def connectionOpened(self, ooliteVersionString):
		print "Opened connection to Oolite version", ooliteVersionString
		self.protocol.factory.activeCount += 1
		self.__active = True
		cliHandler.inputReceiver = self
	
	def connectionClosed(self, message):
		if message != None and len(message) > 0:
			print "Connection closed with message:", message
		else:
			print "Connection closed with no message."
		print ""
		if self.__active:
			self.protocol.factory.activeCount -= 1
			self.__active = False
	
	def writeToConsole(self, message, colorKey, emphasisRanges):
		print "  " + message
	
	def clearConsole(self):
		pass
		
	def showConsole(self):
		pass
	
	def receiveUserInput(self, string):
		self.protocol.sendCommand(string)
	
	def closeConnection(self, message):
		self.protocol.closeConnection(message)


def getInputReceiver():
	return currentInputReceiver


# Set up console server protocol
factory = Factory()
factory.delegateClass = SimpleConsoleDelegate
factory.activeCount = 0
factory.protocol = OoliteDebugConsoleProtocol

# Set up command line I/O protocol
cliHandler = OoliteDebugCLIProtocol()
cliHandler.getInputReceiver = getInputReceiver
stdio.StandardIO(cliHandler)

print "Python Oolite debug console"
print "Type /quit to quit."
print "Waiting for connection..."
print ""

reactor.listenTCP(defaultOoliteConsolePort, factory)
reactor.run()
