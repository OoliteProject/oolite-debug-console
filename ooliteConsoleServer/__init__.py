#
#  __init__.py
#  ooliteConsoleServer
#
#  Created by Jens Ayton on 2007-11-29.
#  Copyright (c) 2007 Jens Ayton. All rights reserved.
#


"""
Module to handle details of communicating with Oolite.
"""


try:
	import twisted
except ImportError:
	raise ImportError("ooliteConsoleServer requires Twisted (http://twistedmatrix.com/)")

try:
	import plistlib
except ImportError:
	raise ImportError("ooliteConsoleServer requires plistlib")


from _protocol import defaultPort as defaultOoliteConsolePort
from OoliteDebugConsoleProtocol import OoliteDebugConsoleProtocol


__author__	= "Jens Ayton <jens@ayton.se>"
__version__	= "1.0"


__all__ = ["PropertyListPacketProtocol", "OoliteDebugConsoleProtocol", "defaultOoliteConsolePort"]
