# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, io, errno

_Python2 = sys.version_info[0] == 2
if _Python2:
	import cPickle as pickle
else:
	import pickle

import debugGUI.constants as con
import debugGUI.config as cfg
import debugGUI.globalVars as gv

_cmdHistory = []						# list of all commands in history
_cmdHistoryIdx = -1						# current position in _cmdHistory array
_differsFromDisk = False				# flag to prevent writing identical file  (preserve versions)
_cmdSearchStr = None					# current search string, None when not searching
_historyWidget = None					# Text widget using these functions

## widget event handlers  #####################################################

# noinspection PyUnusedLocal
def cmdHistoryBack(event=None):			# handler for scrolling backward through history
	# user can scroll back using Tab or (optionally) the mouse wheel
	_scrollHistory(-1)
	return 'break'
	
# noinspection PyUnusedLocal
def cmdHistoryForward(event=None):		# handler for scrolling forward through history
	# user can scroll forward using Shift-Tab or (optionally) the mouse wheel
	_scrollHistory(1)
	return 'break'

# noinspection PyUnusedLocal
def deleteCurrentCmd(event=None):		# handler for deleting cmd from history
	# user can remove commands from history (esp. large pastes) using
	# Ctrl-Del, Ctrl-BackSpace or the Text widget's popup menu
	global _cmdHistoryIdx, _differsFromDisk
	histLen = len(_cmdHistory)
	if histLen > 0:
		# noinspection PyUnresolvedReferences
		cmd = _historyWidget.get('1.0', 'end').rstrip()
		if len(cmd):
			if cmd in _cmdHistory:
				_cmdHistory.remove(cmd)
				# NB: not dependent on _cmdHistoryIdx; cmd deleted from history
				#     if input matches (no search required)
				histLen = len(_cmdHistory)
				_differsFromDisk = True
			if not(-1 < _cmdHistoryIdx <  histLen):
				_cmdHistoryIdx = histLen - 1
			_cmdHistoryShow()
	return 'break'

## externally accessed functions ##############################################

def setHistoryBindings(widget):
	# register the Text widget that uses cmd history, set key bindings
	global _historyWidget
	_historyWidget = widget
	widget.bind('<Up>', cmdHistoryBack)
	widget.bind('<Down>', cmdHistoryForward)
	widget.bind('<Tab>', lambda e: _cmdSearchHistory(-1))
	widget.bind('<Shift-Tab>', lambda e: _cmdSearchHistory(1))
	widget.bind('<Control-Delete>', deleteCurrentCmd)
	widget.bind('<Control-BackSpace>', deleteCurrentCmd)
	
def loadCmdHistory(): 					# Restore CLI history from its save file
	global _differsFromDisk
	try:
		with io.open(con.HISTFILE, 'rb') as hfile:
			history = pickle.load(hfile)
	except IOError as exc:
		if exc.errno == errno.ENOENT:
			errmsg = 'No command history file found'
			gv.debugLogger.debug(errmsg)
		else:
			errmsg = 'IOError loading command history: {!r}'.format(exc)
			gv.debugLogger.exception(errmsg)
		gv.startUpInfo['setup'].append(errmsg)
	except Exception as exc:
		errmsg = 'Error loading command history: {!r}'.format(exc)
		gv.debugLogger.exception(errmsg)
		gv.startUpInfo['setup'].append(errmsg)
	else:
		_cmdHistory[:] = history
		_differsFromDisk = _trimHistory()

def saveCmdHistory(): 					# write CLI history to its save file
	global _differsFromDisk
	try:
		if not _differsFromDisk:
			# with file versioning, only write when there has been changes
			return
		_trimHistory()
		fname = cfg.nextVersion(con.BASE_FNAME, con.HIST_EXT, 
								con.MAX_HIST_VERSION)
		if not fname:
			fname = con.BASE_FNAME + con.HIST_EXT
			errmsg = 'File versioning failed, overwriting {!r}'.format(fname)
		if fname:
			with io.open(fname, 'wb') as hfile:
				pickle.dump(_cmdHistory, hfile, protocol=0)
				# pickle.dump(_cmdHistory, hfile, protocol=2)
				# - protocol 0 is just text, so manual recovery is easier
			_differsFromDisk = False
		else:
			_differsFromDisk = True
			gv.debugLogger.error('Unable to save command history')
	except Exception as exc:
		errmsg = 'failed to save command history file: {!r}'.format(exc)
		gv.debugLogger.exception(errmsg)

def cmdSearchClear():					# see runCmd and cmdClear
	global _cmdHistoryIdx, _cmdSearchStr
	_cmdSearchStr = None
	_cmdHistoryIdx = -1

def addCmdToHistory(cmd):				# see runCmd
	global _differsFromDisk
	cmd = cmd.rstrip()
	if cmd in _cmdHistory:				# move to end of list
		_cmdHistory.remove(cmd)
		_differsFromDisk = False
	else:
		_differsFromDisk = True
	_cmdHistory.append(cmd)

## internal functions #########################################################

def _scrollHistory(direction):
	global _cmdHistoryIdx
	histLen = len(_cmdHistory)
	if histLen > 0:
		if _cmdHistoryIdx == -1:		# just reset or ran a cmd (ie. cmdSearchClear)
			_cmdHistoryIdx = histLen - 1
		elif (direction < 0 < _cmdHistoryIdx < histLen) \
			or (direction > 0 and -1 < _cmdHistoryIdx < histLen - 1):
			# valid range for a step in direction		
			_cmdHistoryIdx += direction
		else:							# scrolling does not wrap
			_cmdHistoryIdx = 0 if direction < 0 else histLen - 1
		_cmdHistoryShow()

# noinspection PyUnresolvedReferences
def _cmdHistoryShow():					# display cmd from history in registered Text widget
	histLen = len(_cmdHistory)
	_historyWidget.delete('1.0', 'end')
	if histLen > 0:
		if -1 < _cmdHistoryIdx < histLen:
			cmd = _cmdHistory[_cmdHistoryIdx]
			_historyWidget.insert('end', cmd, 'command')
	else:
		cmdSearchClear()

def _cmdSearchHistory(direction):		# find/show next cmd in history search
	global _cmdHistoryIdx, _cmdSearchStr
	histLen, cmd, idx = len(_cmdHistory), _cmdSearchStr, _cmdHistoryIdx
	if histLen > 0:
		if not(-1 < idx < histLen):		# just ran a cmd or 'Clear'd widget
			idx = histLen - 1
		if cmd is None:					# starting new search
			# noinspection PyUnresolvedReferences
			cmd = _historyWidget.get('1.0', '1.end').strip()
			idx = idx if -1 < idx < histLen else histLen - 1
			_cmdSearchStr, _cmdHistoryIdx = cmd, idx
		else:							# continuing search
			idx += direction
		while -1 < idx < histLen:
			if _cmdHistory[idx].startswith(cmd):
				_cmdHistoryIdx = idx
				_cmdHistoryShow()
				break
			idx += direction
	return 'break'

def _trimHistory():						# shrink history to keep within limits
	settings = gv.CurrentOptions['Settings']
	trimmed = False
	maxCmds = settings.get('MaxHistoryCmds', con.MAX_HIST_CMDS)
	if len(_cmdHistory) > maxCmds:		# toss oldest commands
		del _cmdHistory[:-maxCmds]
		trimmed = True
	histSize = sum(len(cmd) for cmd in _cmdHistory)
	maxSize = settings.get('MaxBufferSize', con.MAX_HIST_SIZE)
	while histSize > maxSize and len(_cmdHistory):
		# keep tossing oldest until fits
		histSize -= len(_cmdHistory.pop(0))
		trimmed = True
	cmdSearchClear()
	return trimmed
