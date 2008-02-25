#
#  OoliteDebugCLIProtocol.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-12-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


from twisted.internet import stdio, reactor
from twisted.protocols import basic
import sys


class OoliteDebugCLIProtocol(basic.LineReceiver):
	delimiter = "\n"
	inputReceiver = None
	
	
	def connectionMade(self):
		pass
	
	
	def lineReceived(self, line):
		if not line:  return
		
		try:
			if line[0] == "/":  self.__internalCommand(line)
			elif self.inputReceiver:
				self.inputReceiver.receiveUserInput(line)
			else:
				print "No client connected."
		except:
			print >> sys.stderr, "Exception in input handler."
	
	
	def __internalCommand(self, line):
		parts = line[1:].split()
		command = parts[0]
		args = parts[1:]
		argMsg = str.join(" ", args)
		
		# print 'Internal command "' + command  + '" with arguments "' + argMsg + '".'
		
		if (command == "quit"):  reactor.stop()
		elif (command == "close"):
			# Note: I don't recommend using the /close command, as it crashes Oolite.
			if self.inputReceiver:  self.inputReceiver.closeConnection(argMsg)
			else:  print "No client connected."
		else:
			print >> sys.stderr, "Unknown console command: " + line
