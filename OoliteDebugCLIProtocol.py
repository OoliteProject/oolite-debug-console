#
#  OoliteDebugCLIProtocol.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-12-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#

from twisted.internet import stdio, reactor
from twisted.protocols import basic
# import sys
from sys import version_info as version_info
from sys import stderr as stderr

import logging
cmdLogger = logging.getLogger('DebugConsole.CLIProtocol')


class OoliteDebugCLIProtocol(basic.LineReceiver):
	delimiter = "\n" if version_info[0] == 2 else b"\n"
	inputReceiver = None
	
	
	def connectionMade(self):
		pass
	
	def lineReceived(self, bsline):
		if not bsline:  return
		try:
			if isinstance(bsline, bytes):
				line = bsline.decode('ascii') 
			else:
				line = bsline
			if line[0] == "/":  
				self.__internalCommand(line)
			elif self.inputReceiver:
				self.inputReceiver.receiveUserInput(bsline)
			else:
				cmdLogger.warning("No client connected.")
		except:
			cmdLogger.exception("Exception in input handler.")
	
	
	def __internalCommand(self, line):
		parts = line[1:].split()
		command = parts[0]
		args = parts[1:]
		argMsg = str.join(" ", args)
		
		# cmdLogger.debug('Internal command "' + command  + '" with arguments "' + argMsg + '".')
		
		if command == "quit":  
			reactor.stop()
		elif command == "close":
			# Note: I don't recommend using the /close command, as it crashes Oolite.
			if self.inputReceiver:  
				self.inputReceiver.closeConnection(argMsg)
			else:  
				cmdLogger.warning("No client connected.")
		else:
			cmdLogger.error("Unknown console command: " + line, file=stderr)
