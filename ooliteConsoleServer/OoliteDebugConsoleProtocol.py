#
#  OoliteDebugConsoleP.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#

from .PropertyListPacketProtocol import PropertyListPacketProtocol
import ooliteConsoleServer._protocol as P

import logging
consoleLogger = logging.getLogger('DebugConsole.ODCProtocol')


class OoliteDebugConsoleProtocol (PropertyListPacketProtocol):
	"""
	Class handling a debug console connection.
	Each instance has a delegate, to which high-level behaviour is dispatched.
	If the delegate is None, the connection will be cleanly rejected.
	
	Pubic methods:
		isOpen()
		sendCommand(commandString)
		closeConnection()
		configurationValue(key)
		hasConfigurationValue(key)
		setConfigurationValue(key, value)  -- the effect is not immediate, and does nothing if connection is not oepn.
	
	Public properties:
		rejectMessage  -- message used when rejecting connection because there is no delegate.
	
	
	Delegate methods:
		acceptConnection()
		connectionOpened(ooliteVersionString)
		connectionClosed(message)
		writeToConsole(message, colorKey, emphasisRanges)
		clearConsole()
		showConsole()
	
	Delegate properties:
		identityString  -- The name of the console server, sent to Oolite when accepting connection.
	"""
	
	rejectMessage = None
	
	__configuration = {}
	__open = False
	__closed = False
	
	
	def isOpen(self):
		return self.__open
	
	
	def sendCommand(self, commandString):
		if self.__open:
			cmdStr = commandString.decode('utf-8') if isinstance(commandString, bytes) else commandString
			packet = { P.packetTypeKey: P.performCommandPacket, P.messageKey: cmdStr or "" }
			self.sendPlistPacket(packet)
	
	
	def closeConnection(self, message):
		if self.__open:
			self.__open = False
			packet = { P.packetTypeKey: P.closeConnectionPacket }
			if message is not None:
				# msgStr = message.decode('ascii') if isinstance(message, bytes) else message
				msgStr = message.decode('utf-8') if isinstance(message, bytes) else message
				packet[P.messageKey] = msgStr
			self.sendPlistPacket(packet)
			
			self.__closed = True
			self.transport.loseConnection()
			self.delegate.connectionClosed(message)

			
	def configurationValue(self, key):
		if key in self.__configuration:
			return self.__configuration[key]
	
	
	def hasConfigurationValue(self, key):
		return key in self.__configuration


	def setConfigurationValue(self, key, value):
		if self.__open and self.__configuration.get(key) != value:
			packet = {P.packetTypeKey: P.noteConfigurationChangePacket}
			# packet = { P.packetTypeKey: P.noteConfigurationPacket } # these types of packets are receive only
			if value is not None:
				packet[P.configurationKey] = {key: value}
			else:
				packet[P.removedConfigurationKeysKey] = [key]
			self.sendPlistPacket(packet)


	# Internals beyod this point
	def connectionMade(self):
		self.delegate = self.factory.delegateClass(self)

		
	def connectionLost(self, reason):
		if self.__open:
			self.__open = False
			self.delegate.connectionClosed(None)
			return
		elif not self.__closed:
			self.__closed = True
		self.delegate.connectionClosed(reason)

		
	def plistPacketReceived(self, packet):
		# Dispatch based on packet type.
		_type = packet[P.packetTypeKey]
		if _type == P.requestConnectionPacket:
			self.__requestConnectionPacket(packet)
		elif _type == P.closeConnectionPacket:
			self.__closeConnectionPacket(packet)
		elif _type == P.consoleOutputPacket:
			self.__consoleOutputPacket(packet)
		elif _type == P.clearConsolePacket:
			self.__clearConsolePacket(packet)
		elif _type == P.showConsolePacket:
			self.__showConsolePacket(packet)
		elif _type == P.noteConfigurationPacket:
			self.__noteConfigurationPacket(packet)
		elif _type == P.noteConfigurationChangePacket:
			self.__noteConfigurationChangePacket(packet)
		elif _type == P.pingPacket:
			self.__pingPacket(packet)
		elif _type == P.pongPacket:
			self.__pongPacket(packet)
		else:
			self.__unknownPacket(_type, packet)
	
	
	def badPacketReceived(self, data):
		consoleLogger.warning("Received bad packet, ignoring.")
		consoleLogger.debug(data)
	
	
	def badPListSend(self, plist):
		consoleLogger.warning("Attempt to send bad plist: {}".format(plist))
	
	
	def __requestConnectionPacket(self, packet):
		if not P.versionCompatible(P.protocolVersion_1_1_0, packet[P.protocolVersionKey]):
			# Protocol mismatch -> reject connection.
			response = { P.packetTypeKey: P.rejectConnectionPacket, P.messageKey: "This console does not support the requested protocol version." }
			self.sendPlistPacket(response)
			self.transport.loseConnection()
			# noinspection PyBroadException
			try:
				self.delegate.connectionClosed("This console does not support the requested protocol version.")
			except:
				consoleLogger.exception("OoliteDebugConsoleProtocol: delegate.connectionClosed failed.")
				# Ignore
		else:
			# Handle connection request
			try:
				if self.delegate.acceptConnection():
					response = {P.packetTypeKey: P.approveConnectionPacket,
								P.consoleIdentityKey: self.delegate.identityString}
					self.sendPlistPacket(response)
					# Pass to delegate
					self.delegate.connectionOpened(packet[P.ooliteVersionKey])
					self.__open = True
			except Exception as inst:
				consoleLogger.exception("Exception in connection set-up: ", inst)
			
			if not self.__open:
				consoleLogger.error("Failed to open connection.")
				# No delegate or delegate failed -> reject connection.
				response = { P.packetTypeKey: P.rejectConnectionPacket, P.messageKey: "This console is not accepting connections." }
				if self.rejectMessage is not None:
					response[P.messageKey] = self.rejectMessage
				self.sendPlistPacket(response)
				self.transport.loseConnection()
	
	
	def __closeConnectionPacket(self, packet):
		if self.__open:
			self.__open = False
			self.__closed = True
			self.transport.loseConnection()
			message = "remote closed connection"
			if P.messageKey in packet:
				message = packet[P.messageKey]
			self.delegate.connectionClosed(message)
	
	
	def __consoleOutputPacket(self, packet):
		if self.__open:
			message = None
			colorKey = None
			emphasisRanges = None
			
			if P.messageKey in packet:
				message = packet[P.messageKey]
			if P.colorKeyKey in packet:
				colorKey = packet[P.colorKeyKey]
			if P.emphasisRangesKey in packet:
				emphasisRanges = packet[P.emphasisRangesKey]
			
			self.delegate.writeToConsole(message, colorKey, emphasisRanges)
	
	
	def __clearConsolePacket(self, packet):
		if self.__open:
			self.delegate.clearConsole()
	
	
	def __showConsolePacket(self, packet):
		if self.__open:
			self.delegate.showConsole()
	
	
	def __noteConfigurationPacket(self, packet):
		if self.__open and P.configurationKey in packet:
			self.__configuration = packet[P.configurationKey]
			if hasattr(self.delegate, 'loadConfig'):
				self.delegate.loadConfig(self.__configuration)
	
	
	def __noteConfigurationChangePacket(self, packet):
		if self.__open:
			if P.configurationKey in packet:
				for k, v in packet[P.configurationKey].items():
					self.__configuration[k] = v
			if P.removedConfigurationKeysKey in packet:
				for k in packet[P.removedConfigurationKeysKey]:
					try:
						del self.__configuration[k]
					except Exception as exc:
						if isinstance(exc, KeyError):
							print('key {!r} not found in __configuration'.format(k),
								  file=sys.stderr)

	
	def __pingPacket(self, packet):
		# Respond to ping packet by sending back pong packet with same message (if any).
		response = { P.packetTypeKey: P.pongPacket }
		if P.messageKey in packet:
			response[P.messageKey] = packet[P.messageKey]
		self.sendPlistPacket(response)
	
	
	def __pongPacket(self, packet):
		# Nothing to do, since we don't send pings.
		pass
	
	
	def __unknownPacket(self, _type, packet):
		#unknown packet, complain.
		consoleLogger.error('Unkown packet type "{}", ignoring.'.format(_type))
		consoleLogger.debug(packet)
