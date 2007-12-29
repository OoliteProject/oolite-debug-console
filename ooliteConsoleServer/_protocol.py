#
#  _protocol.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


"""
Definitions used to implement Oolite debug console protocol.
"""
# See OODebugTCPConsoleProtocol.h for reference.


# Default TCP port
defaultPort				= 8563


# Packet types
requestConnectionPacket			= "Request Connection"
approveConnectionPacket			= "Approve Connection"
rejectConnectionPacket			= "Reject Connection"
closeConnectionPacket			= "Close Connection"
consoleOutputPacket				= "Console Output"
clearConsolePacket				= "Clear Console"
showConsolePacket				= "Show Console"
noteConfigurationPacket			= "Note Configuration"
noteConfigurationChangePacket	= "Note Configuration Change"
performCommandPacket			= "Perform Command"
requestConfigurationValuePacket	= "Request Configuration Packet"
pingPacket						= "Ping"
pongPacket						= "Pong"


# Value keys
packetTypeKey					= "packet type"
protocolVersionKey				= "protocol version"
ooliteVersionKey				= "Oolite version"
messageKey						= "message"
consoleIdentityKey				= "console identity"
colorKeyKey						= "color key"
emphasisRangesKey				= "emphasis ranges"
configurationKey				= "configuration"
removedConfigurationKeysKey		= "removed configuration keys"
configurationKeyKey				= "configuration key"


# Version encoding
def version(fmt, maj, min):
	""" Encode a protocol version """
	return 65536 * fmt + 256 * maj + min

def versionFormat(vers):
	""" return the format component of a protocol version """
	return (vers / 65536) % 256

def versionMajor(vers):
	""" return the major component of a protocol version """
	return (vers / 256) % 256

def versionMinor(vers):
	""" return the minor component of a protocol version """
	return vers % 256

def versionCompatible(myVersion, remoteVersion):
	return versionFormat(remoteVersion) == versionFormat(myVersion) and versionMajor(remoteVersion) <= versionMajor(myVersion)

# Version constants
protocolVersion_1_1_0			= version(1, 1, 0)
