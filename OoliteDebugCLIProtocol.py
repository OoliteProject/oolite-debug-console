#
#  OoliteDebugCLIProtocol.py
#  pythonDebugConsole
#
#  Created by Jens Ayton on 2007-12-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#

from twisted.internet import reactor
from twisted.protocols import basic
import sys

import logging
cmdLogger = logging.getLogger('DebugConsole.CLIProtocol')


class OoliteDebugCLIProtocol(basic.LineOnlyReceiver):
# "... a speed optimisation over LineReceiver, for the
# 	cases that raw mode is known to be unnecessary..."
# MAX_LENGTH: Default is 16384. 
# If a sent line is longer than this, the connection is dropped!

# class OoliteDebugCLIProtocol(basic.LineReceiver):
					 
	
	delimiter = "\n" if sys.version_info[0] == 2 else b"\n"
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
				errmsg = "No client connected."
				cmdLogger.warning(errmsg)
				print(errmsg)
		except:
			errmsg = "Exception in input handler."
			cmdLogger.exception(errmsg)
			# no simple way to redirect output for both Python 2 & 3
			saved_stdout = sys.stdout
			sys.stdout = sys.stderr
			print(errmsg)
			sys.stdout = saved_stdout
	
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
				errmsg = "No client connected."
				cmdLogger.warning(errmsg)
				print(errmsg)
		else:
			errmsg = "Unknown console command: " + line
			cmdLogger.error(errmsg)
			# no simple way to redirect output for both Python 2 & 3
			saved_stdout = sys.stdout
			sys.stdout = sys.stderr
			print(errmsg)
			sys.stdout = saved_stdout
