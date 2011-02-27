#
#  PropertyListPacketProtocol.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


from twisted.internet.protocol import Protocol
from plistlib import readPlist, writePlist
from cStringIO import StringIO


# These are part of plistlib.py on Mac OS X, but not in the files easily
# available on the web.
def readPlistFromString(data):
    """Read a plist data from a string. Return the root object.
    """
    return readPlist(StringIO(data))


def writePlistToString(rootObject):
    """Return 'rootObject' as a plist-formatted string.
    """
    f = StringIO()
    writePlist(rootObject, f)
    return f.getvalue()


class PropertyListPacketProtocol(Protocol):
	"""
	Class handling a property list packet stream.
	
	Oolite's debug console is based on property lists. Each property list is a
	self-contained entity, or packet. Since TCP is stream-oriented, it is
	necessary to have a packet framing protocol on top of it.
	
	The framing protocol used for the debug console is just about the simplest
	possible: each frame has a header, which consists of four eight-bit bytes.
	These form a 32-bit network-endian integer, specifying the length of the
	packet data. This is followed by packet data. The packet data is an XML
	property list.
	
	This class is a Twisted protocol implementing the packet framing and XML
	property list decoding (using plistlib to handle the details of that). It
	is implemented as an implicit state machine, with two states: receiving
	header (identified by a __sizeCount less than 4) and receiving data. When
	a full data packet is received, it is decoded as a plist and dispatched
	to a subclass's plistPacketReceived() method.
	"""
	
	__buffer = ""
	__received = ""
	__expect = 0
	__sizeCount = 0
	
	def dataReceived(self, data):
		"""
		Receive data from the network. This is called by Twisted.
		
		This method handles the decoding of incoming packets and dispatches
		them to be handled by the subclass implementation.
		"""
		
		# Append data to incoming buffer
		self.__received += data
		
		# Loop over buffer
		while len(self.__received) > 0:
			if self.__sizeCount < 4:
				# Receiving header (size)
				# Decode as big-endian 32-bit integer
				self.__expect = (self.__expect << 8) + ord(self.__received[0])
				self.__received = self.__received[1:]
				self.__sizeCount += 1
			else:
				# Receiving data
				if len(self.__received) < self.__expect:
					# This is not the end of the data
					self.__buffer += self.__received
					self.__expect -= len(self.__received)
					self.__received = ""
				else:
					# End of packet reached
					self.__buffer += self.__received[:self.__expect]
					self.__received = self.__received[self.__expect:]
					try:
						self.__dispatchPacket()
					finally:
						# Expect new packet
						self.__reset()
	
	
	def sendPlistPacket(self, packet):
		"""
		Send a packet (property list). Called by subclass or client objects.
		
		This encodes an XML plist, adds the header and sends it over the
		network connection.
		"""
		data = None
		try:
			if packet:
				data = writePlistToString(packet)
		except:
			data = None
		if data:
			length = len(data)
			self.transport.write(chr((length >> 24) & 0xFF))
			self.transport.write(chr((length >> 16) & 0xFF))
			self.transport.write(chr((length >> 8) & 0xFF))
			self.transport.write(chr(length & 0xFF))
			self.transport.write(data)
		else:
			self.badPListSend(packet)
	
	
	def __dispatchPacket(self):
		# Decode plist and send to subclass method
		plist = None
		try:
			plist = readPlistFromString(self.__buffer)
		except:
			plist = None
		
		if plist:  self.plistPacketReceived(plist)
		else:  self.badPacketReceived(self.__buffer)
	
	
	def __reset(self):
		# Reset to waiting-for-beginning-of-packet state.
		self.__expect = 0
		self.__sizeCount = 0
		self.__buffer = ""
	
	def plistPacketReceived(self, plist):
		# Doing something useful with the plist is a subclass responsibilitiy.
		pass
	
	def badPacketReceived(self, data):
		# Called for bad (non-plist) packets; subclasses may override.
		pass
	
	def badPListSend(self, plist):
		# Called for invalid (non-plist) objects sent to sendPListPacket(); subclasses may override.
		pass
