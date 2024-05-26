#
#  PropertyListPacketProtocol.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#

from twisted.internet.protocol import Protocol

from sys import version_info
_Python2 = version_info[0] == 2
if _Python2:
	from plistlib import readPlistFromString as readPlist
	from plistlib import writePlistToString as writePlist
else:
	from plistlib import loads, dumps


def readPlistFromString(data):
	"""Read a plist data from a string. Return the root object.
	"""
	if _Python2:
		# return readPlist(StringIO(data))
		return readPlist(data)
	else:
		return loads(data)


def writePlistToString(rootObject):
	"""Return 'rootObject' as a plist-formatted string.
	"""
	if _Python2:
		# f = StringIO()
		# writePlist(rootObject, f)
		# return f.getvalue()
		return writePlist(rootObject)
	else:
		return dumps(rootObject)


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
	
	
###################################################################################################
	
	# """
	# cag: to debug badPacketReceived messages, ignoring header and grabbing data 
	     # by searching for its head and tail
		 # - it's about 10% slower, with average of 0.22 ms, ie. extra 0.02 ms/call
		 # - can induce bad backet by mashing 'c' key fast
	# """
	
	# # debug utils #####################
	
# 	PACKET_BEGIN = b'<?xml'
# 	PLIST_BEGIN = b'<?xml version'
# 	PLIST_END = b'</plist>'
# 	PL_END_LEN = len(PLIST_END)
# 	DICT_BEGIN = b'<dict>'
# 	MAX_WIDTH = 200
#
# 	def head(self, array, begin=0, stop=None):
# 		length = len(array)
# 		if stop is None: stop = length
# 		else:			 stop = min(stop, length)
# 		return array[begin : min(begin + self.MAX_WIDTH, stop)]
#
# 	def tail(self, array, begin=0, stop=None):
# 		length = len(array)
# 		if stop is None: stop = length
# 		else:			 stop = min(stop, length)
# 		if stop <= begin + self.MAX_WIDTH:
# 			return ''
# 		return array[max(stop - self.MAX_WIDTH, stop - (begin + self.MAX_WIDTH)) : stop]
#
# 	def bothEnds(self, array, begin=0, stop=None):
#
# 		def skipHeader(dirn=1):
# 			view = array[begin:stop]
# 			if dirn > 0:
# 				packet = view.find(self.PACKET_BEGIN)
# 				dictBegin = view.find(self.DICT_BEGIN)
# 			else:
# 				packet = view.rfind(self.PACKET_BEGIN)
# 				dictBegin = view.rfind(self.DICT_BEGIN)
#
# 			# skip irrelevant info (plist version, comment)
# 			if -1 < packet < dictBegin:
# 				return dictBegin
# 			return begin
#
# 		length = len(array)
# 		if stop is None: stop = length
# 		else:			 stop = min(stop, length)
# 		leading = self.head(array, skipHeader(), stop)
# 		if len(leading) <= self.MAX_WIDTH:	# it all fit
# 			return leading
# 		lagging = self.tail(array, skipHeader(dirn=-1), stop)
# 		return '{}\n ... \n{}'.format(leading, lagging)
#
# 	def pListTags(self, msg):
# 		start = msg.find(self.PLIST_BEGIN)
# 		end = msg.find(self.PLIST_END, start if -1 < start else 0)
# 		tagEnd = -1 if end < 0 else end + self.PL_END_LEN
# 		return start, end, tagEnd
#
# 	def dbgPrint(self, msg):
# 		if len(msg):
# 			# noinspection PyBroadException
# 			try:
# 				print(msg)
# 			except:			# IOError: [Errno 28] No space left on device
# 				print('{}\n...\n{}'.format(self.head(msg), self.tail(msg)))
#
# 	# end debug utils #################
#
# 	if _Python2:
# 		__buffer = ""
# 		__received = None
# 	else:
# 		__buffer = bytearray()
# 		__received = None
#
# 	def dataReceived(self, data):
# 		"""
# 		Receive data from the network. This is called by Twisted.
#
# 		This method handles the decoding of incoming packets and dispatches
# 		them to be handled by the subclass implementation.
# 		"""
#
# 		import pdb, traceback
# 		debug = False  #  or True
#
# #### self._PropertyListPacketProtocol__received
# #### self._PropertyListPacketProtocol__buffer
#
# 		def bufferHasData():
# 			try:
# 				while True:
# 					bufLen = len(self.__buffer)
# 					start, end, tagEnd = self.pListTags(self.__buffer)
#
# 					if debug:
# 						msg = '\nbufferHasData, bufLen {}, start {}, end {}'.format(bufLen, start, end)
# 					else:
# 						msg = ''
#
# 					# any data previously __received is prepended to data upon entry
# 					if -1 < start < end:			# found a plist
#
# 						if debug and start > 4:		# start preceded by 4 bytes of packet's length
# 							msg += '; \n  tossing leading fragment of len {}: {!r}'.format(
# 									start, self.head(self.__buffer, stop=start))
#
# 						if tagEnd < bufLen:			# contains start of next one
# 							self.__received = self.__buffer[tagEnd:]
#
# 							if debug: #   and False
# 								msg += '; contains start of next one, length {}\n  {!r}'.format(
# 										bufLen - tagEnd, self.bothEnds(self.__received))
#
# 						elif debug and 'tossing' not in msg:
# 							msg = ''
#
# 						self.__buffer = self.__buffer[start:tagEnd]
# 						self.dbgPrint(msg)
# 						return True					# buffer has a complete plist
#
# 					elif -1 < end < start:			# end fragment & start of next, flush fragment
#
# 						if debug:
# 							msg += ';  tossing end fragment of len {}, & start of next \n  {!r}'.format(
# 									tagEnd, self.bothEnds(self.__buffer, stop=tagEnd))
#
# 						self.__buffer = self.__buffer[start:]
# 						continue					# recalculate indices
#
# 					elif -1 == end < start:			# incomplete plist, wait for more
#
# 						if debug:
# 							msg += ';  incomplete plist \n  {!r}{}'.format(
# 									self.head(self.__buffer),
# 									'' if bufLen <= self.MAX_WIDTH else '\n ... {!r}'.format(
# 										self.tail(self.__buffer)))
# 						if debug and start > 0:
# 							msg += ', has leading junk \n  {!r}{}'.format(
# 									self.head(self.__buffer, stop=start),
# 									'' if start <= self.MAX_WIDTH else '\n ... {!r}'.format(
# 										self.tail(self.__buffer, stop=start)) )
#
# 						self.__received = self.__buffer if start == 0 else self.__buffer[start:]
#
# 					elif -1 == start < end:			# end fragment, flush it
# 						self.__received = self.__buffer[tagEnd:]
#
# 						if debug:
# 							msg += '; end fragment, tossing\n  {!r}{}'.format(
# 									self.head(self.__buffer, stop=tagEnd),
# 									'' if tagEnd <= self.MAX_WIDTH else '\n ... {!r}'.format(
# 										self.tail(self.__buffer, stop=tagEnd) ))
#
# 					elif -1 == start == end:		# partial plist, flush it
# 						# noinspection PyChainedComparisons
# 						if 0 < bufLen <= 4 and self.__buffer[0] == 0:
# 							msg = ''				# don't report packet lengths
# 						elif debug:
# 							msg = 'no plist markers, tossing {}\n  {!r}{}'.format(
# 									bufLen, self.head(self.__buffer),
# 									'' if bufLen <= self.MAX_WIDTH else '\n ... {!r}'.format(
# 										self.tail(self.__buffer)))
#
# 					self.__reset()	# zeros counters (not used), wipes __buffer
# 					break
# 				self.dbgPrint(msg)
# 				return False
# 			except Exception as exc:
# 				traceback.print_exc()
# 				print(exc)
# 				pdb.set_trace()
#
#
# 		if self.__received:
# 			self.__buffer = self.__received
# 			self.__received = None
# 			if debug:
# 				bufLen = len(self.__buffer)
# 				print('dataReceived, entry, prepending {} char from previous call, giving {}'.format(
# 					bufLen, bufLen + len(data) ))
# 		self.__buffer += data
#
# 		while True:
# 			if bufferHasData():
# 				if debug:
# 					msg = '\ndataReceived, dispatching len {}: \n  {!r}'.format(
# 							len(self.__buffer), self.__buffer)
# 					self.dbgPrint(msg)
# 				try:
# 					self.__dispatchPacket()
# 				finally:
# 					self.__reset()
# 				if self.__received:				# try again with remnant
# 					# in pdb, self._PropertyListPacketProtocol__received
# 					# 		  self._PropertyListPacketProtocol__buffer
# 					self.__buffer = self.__received
# 					self.__received = None
#
# 					if debug and False:	#
# 						bufLen = len(self.__buffer)
# 						start, end, tagEnd = self.pListTags(self.__buffer)
# 						if -1 < start < end:
# 							if bufLen - tagEnd > 0:
# 								print('dataReceived, 2nd plist, len {}{}'.format(tagEnd,
# 									'' if tagEnd == bufLen - 1 else ', len {} remnant: \n  {!r}'.format(
# 											bufLen - tagEnd, self.bothEnds(self.__buffer))))
# 						elif -1 == start < end:
# 							print('dataReceived, remainder of plist, len {}{}'.format(tagEnd,
# 								'' if tagEnd == bufLen - 1 else ', len {} remnant: \n  {!r}'.format(
# 										bufLen - tagEnd, self.bothEnds(self.__buffer))))
# 						else:
# 							print('dataReceived, trying len {} remnant: \n  {!r}'.format(
# 									bufLen, self.__buffer))
# 				else:
# 					break
# 			else:
# 				break
# 		return
		
###################################################################################################
	
	if _Python2:
		__buffer = ""
		__received = ""
	else: # in pdb, prepend to property: _PropertyListPacketProtocol, eg. self._PropertyListPacketProtocol__received
		__buffer = bytearray()
		__received = bytearray()
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
				if _Python2:
					self.__expect = (self.__expect << 8) + ord(self.__received[0])
				else:
					self.__expect = (self.__expect << 8) + self.__received[0]
				self.__received = self.__received[1:]
				self.__sizeCount += 1
			else:
				# Receiving data
				if len(self.__received) < self.__expect:
					# This is not the end of the data
					self.__buffer += self.__received
					self.__expect -= len(self.__received)
					self.__received = "" if _Python2 else bytearray()
				else:
					self.__buffer += self.__received[:self.__expect]
					self.__received = self.__received[self.__expect:]
					try:
						self.__dispatchPacket()
					finally:
						# Expect new packet
						self.__reset()
							
###################################################################################################	
	
	def sendPlistPacket(self, packet):
		"""
		Send a packet (property list). Called by subclass or client objects.
		
		This encodes an XML plist, adds the header and sends it over the
		network connection.
		"""
		data = None
		# noinspection PyBroadException
		try:
			if packet:
				data = writePlistToString(packet)
		except:
			data = None
		if data:
			length = len(data)
			if _Python2:
				self.transport.write(chr((length >> 24) & 0xFF))
				self.transport.write(chr((length >> 16) & 0xFF))
				self.transport.write(chr((length >> 8) & 0xFF))
				self.transport.write(chr(length & 0xFF))
			else:
				hdr = bytearray( ((length >> 24) & 0xFF, (length >> 16) & 0xFF, (length >> 8) & 0xFF, length & 0xFF) )
				self.transport.write(hdr)
			self.transport.write(data)
		else:
			self.badPListSend(packet)

	def __dispatchPacket(self):
		# Decode plist and send to subclass method
		# noinspection PyBroadException
		try:
			plist = readPlistFromString(self.__buffer)
		except:
			plist = None

		if plist:
			self.plistPacketReceived(plist)
		else:  
			self.badPacketReceived(self.__buffer)
	
	
	def __reset(self):
		# Reset to waiting-for-beginning-of-packet state.
		self.__expect = 0
		self.__sizeCount = 0
		if _Python2:
			self.__buffer = "" 
		else:
			del self.__buffer[:]
		
	def plistPacketReceived(self, plist):
		# Doing something useful with the plist is a subclass responsibilitiy.
		pass
	
	def badPacketReceived(self, data):
		# Called for bad (non-plist) packets; subclasses may override.
		pass
	
	def badPListSend(self, plist):
		# Called for invalid (non-plist) objects sent to sendPListPacket(); subclasses may override.
		pass
