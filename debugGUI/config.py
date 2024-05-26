# -*- coding: utf-8 -*-
#
# (c) 2021 cag CC BY-NC-SA 4.0
#
import sys, os, io, errno, re
import json
from copy import deepcopy
from twisted.internet.error import CannotListenError
from collections import OrderedDict
import pdb, traceback

import debugGUI.colors as cl
import debugGUI.comments as cmt
import debugGUI.constants as con
import debugGUI.globalVars as gv
import debugGUI.miscUtils as mu
import debugGUI.regularExpn as rx
import debugGUI.stringUtils as su
import debugGUI.widgets as wg

# backward compatibility (names changed from previous version's CFGFILE)
_configNameChange = {					
	'Foreground': 'General-foreground', 'Background': 'General-background',
	'Command': 'Command-foreground', 	# there was no command background
	'Selectfg': 'Select-foreground', 'Selectbg': 'Select-background',
	'ConsolePort': 'Port'}

def parseErr(err):
	try:
		name = repr(err)
		name = name[: name.find('(')]
		kind = None
		if hasattr(err, 'args') and len(err.args) > 1:
			if isinstance(err, CannotListenError):
				kind = 'CannotListenError: {}'.format(
								err.socketError.errno)
				msg = '{!r} (port: {})'.format(
								err.socketError.strerror, err.port)
			elif isinstance(err, OSError):
				kind = 'OSError: {}'.format(
						err.winerror if hasattr(err, 'winerror') \
									else err.errno)
				msg = repr(err.strerror)
			else:
				kind = '{}: {}'.format(name, err.args[0])
				msg = repr(err.args[-1][-1] \
								if isinstance(err.args[-1], tuple) \
								else err.args[-1])
		else:
			msg = repr(err)
			# if finds fail, use start of msg
			start = max(msg.find('('), msg.find("'"), msg.find('"'), 0)
			if 0 < len(name) <= start:
				kind = name
			elif 0 < start:
				kind = msg[:start]
			# if rfinds fail, use end of msg
			end = min([msg.rfind(')'), msg.rfind("'"), msg.rfind('"')],
					key=lambda x: x if x > 0 else sys.maxsize )
			msg = msg[start:min(end, len(msg))]
		return msg, kind
	except Exception as exc:
		if con.CAGSPC:
			print(exc)
			traceback.print_exc()
			pdb.set_trace()

def nextVersion(fn, ext, highest=None):
	def fmtVernFn(ver):
		return '{}{}{}'.format(
				fn, '.{}'.format(ver) if ver > 0 else '', ext)

	versToIncr = []
	currVer = nextFn = None
	vern = -1
	maxVerNum = highest if highest else con.MAX_LOG_VERSION
	try:
		for num in range(0, maxVerNum):
			currVer = fmtVernFn(num)
			if os.path.exists(currVer):
				if ext in [con.HIST_EXT, con.LOG_EXT] and \
						os.path.getsize(currVer) == 0:
					os.remove(currVer)
				else:
					versToIncr.append((num, currVer))
			else:	# leave older versions alone
				break
		currVer = None
		for vern, currFn in reversed(versToIncr):
			nextFn = fmtVernFn(vern + 1)
			if vern + 1 == maxVerNum and os.path.exists(nextFn):
				os.remove(nextFn)
			if con.Python2:
				os.rename(currFn, nextFn)
			else:
				os.replace(currFn, nextFn)
		return fmtVernFn(0)
	except Exception as exc:
		errmsg = 'nextVersion, Error '
		if currVer or vern + 1 == maxVerNum:
			errmsg += 'deleting {!r} '.format(currVer)
		else:
			errmsg += 'renaming {!r} '.format(nextFn)
		msg, kind = parseErr(exc)
		if kind:
			errmsg += '  ({})\n  {}'.format(kind, msg)
		else:
			errmsg += '\n  ' + msg
		gv.startUpInfo['error'].append(errmsg)
		if gv.debugLogger:
			gv.debugLogger.exception(errmsg)
		if gv.setupComplete:
			gv.app.colorPrint(errmsg)

## configuration  #############################################################

_writingCfg = False						# flag for need to update CFGFILE
_saveConfigRead = False					# the SaveConfigOnExit when loaded

def initConfig():						# initialize config dict with defaults
	global _writingCfg
	
	try:
		gv.CurrentOptions = OrderedDict((key, OrderedDict()) \
								for key in con.defaultConfig.keys())
		# need Settings, Font & Colors to make widgets if no CFGFILE
		_setDefaultConfig(gv.CurrentOptions)
		gv.aliases = gv.CurrentOptions['Aliases']
			
		if not _readCfgFile():	
			# # fake it, as _getAppsCfg expects CFGFILE
			_setDefaultConfig(gv.ConfigFile, mkObj=True)
			# insert all con.defaultComments
			# - this time only? until first save when read succeeds
			_writingCfg = True
	except IOError as exc:
		if exc.errno == errno.ENOENT:
			errmsg = 'No configuration file found'
			gv.debugLogger.debug(errmsg)
		else:
			errmsg = 'IOError loading configuration: {!r}'.format(exc)
			gv.debugLogger.exception(errmsg)
		gv.startUpInfo['setup'].append(errmsg)
	except Exception as exc:
		errmsg = 'Exception: {!r}'.format(exc)
		gv.debugLogger.exception(errmsg)
		gv.startUpInfo['setup'].append(errmsg)
		raise exc

def _setDefaultConfig(db, mkObj=False):
	try:
		index = 0
		for section in con.defaultSections:
			if mkObj:
				db[section] = gv.Section(section, index + 1) # skip '['
				index += len(section) + 2 # both '[' & ']'
			defaults = con.defaultConfig[section]
			if mkObj:
				for option, value in defaults.items():
					if value is None or (section == 'Settings'
							and option in con.settingsNotRequired):
						continue
					if isinstance(value, bool):
						value = 'yes' if value else 'no'
					optionObj = gv.Option(db[section], option, value,
										  index + 1) # skip '['
					db[section].addOption(option, optionObj)
					index += len(option) + 3 # include ' = '
					index += len(str(value) if isinstance(value, int) else value)
			elif section == 'Settings':
				db[section] = {option:value for option, value in defaults.items()
							   if option not in con.settingsNotRequired}
			elif section == 'Colors':
				# Tk uses lowercase keys, configparser capitalized,
				# kept for backward compatibility
				db[section] = {color.lower():value
							   for color, value in defaults.items()}
			elif section == 'Font':
				db[section] = deepcopy(defaults)
			# else:
				# sections History & Aliases are empty by default

	except Exception as exc:
		msg = repr(exc)
		gv.debugLogger.exception(msg)
		if con.CAGSPC:
			print(msg)
			traceback.print_exc()
			pdb.set_trace()

def _saveComments(obj, string, index):
	# used both for configuration options and aliases
	# - the .addComment 2nd arg is only meaningful for aliases and is ignored
	#   for Section/Option instances
	if string is None:
		return index
	elif len(string.strip()) == 0:
		return index + len(string)
	cmtIdx = 0
	while su.inbounds(cmtIdx, string):
		if string[cmtIdx:].isspace():  # preserve whitespace
			obj.addComment(string[cmtIdx:], index + cmtIdx - obj.location)
			return index + len(string)
		endLine = rx.ENDLINE_CMT_RE.match(string, cmtIdx)
		if endLine:  # captures leading WS and any trailing NLs
			start, cmtIdx = endLine.span('eolCmt')
			obj.addComment(string[start:cmtIdx], index + start - obj.location)
			continue
		inLine = rx.INLINE_CMT_RE.match(string, cmtIdx)
		if inLine:  # captures leading WS and any trailing NLs
			start, cmtIdx = inLine.span('inlineCmt')
			obj.addComment(string[start:cmtIdx], index + start - obj.location)
			continue
		print('_saveComments, failed to parse comment at index {} + {}: {!r} <> {!r}'
			  .format(index, cmtIdx, string[0:cmtIdx], string[cmtIdx:]))
		if con.CAGSPC:
			pdb.set_trace()
		break  # safety valve, should never execute
	return index + cmtIdx

def _coerceValue(name, string, default):
	# type conversion as all values in CFGFILE are str
	if name in con.optionsAreLists:
		if name == 'ToolTips' and string.lower() in \
								['all', 'none', "'all'", "'none'",
				 				'"all"', '"none"', '`all`', '`none`']:
			return string.strip("""`"'""").lower()
		else:
			return None if string.lower() in con.NIL_STRS or string == [] \
					else list(json.loads(string))
	elif isinstance(default, bool):
		return True if str(string).lower() in con.TRUE_STRS else False
	elif name in con.optionsAreInts:
		return None if str(string).lower() in con.NIL_STRS else int(string)
	elif isinstance(default, int):
		return string if isinstance(string, int) else int(string)
	return string

def readOptions(sectionObj, string, index):
	try:
		sectionDict = gv.CurrentOptions[sectionObj.name]
		while su.inbounds(index, string):
			option = rx.OPTION_RE.match(string, index)
			if option:
				optionName = _configNameChange.get(option['name'], option['name'])
				if optionName in sectionObj:
					msg = 'option {!r} duplicated {}'.format(optionName,
							'(was {!r}) '.format(option['name'])
							if option['name'] in _configNameChange else '')
					msg += 'in {!r}, keeping first value: {}'.format(
							con.CFGFILE, sectionObj[optionName])
					if gv.debugLogger:
						gv.debugLogger.warning(msg)
					index = option.end('option')
					index = _saveComments(sectionObj.options[optionName],
										 option['optionTail'], index)
				else:
					optionObj = gv.Option(sectionObj, optionName, option['value'],
										  option.start('name'))
					sectionObj.addOption(optionName, optionObj)
					key, value = optionName, option['value']
					default = con.defaultConfig[sectionObj.name].get(key)
					value = _coerceValue(key, value, default)

					# colors are stored as lowercase to match Oolite's
					if sectionObj.name == 'Colors':
						sectionDict[key.lower()] = value
					else:
						sectionDict[key] = value

					index = option.end('option')
					index = _saveComments(optionObj, option['optionTail'], index)
			else:
				break
		return index
	except Exception as exc:
		print(exc)
		traceback.print_exc()
		pdb.set_trace()

def _createAlias(alias, location):
	aliases = gv.CurrentOptions['Aliases']
	if alias not in aliases:
		aliases[alias] = gv.Alias(alias, location)
	return aliases[alias]				# convenience return

def _readAliases(sectionObj, string, index):
	try:
		while su.inbounds(index, string):
			name = rx.ALIAS_NAME_RE.match(string, index)
			if name:
				match = rx.POLLING_RE.match(string, name.end())
				if match:
					obj = _createAlias(name['name'], name.start('name'))
					sectionObj.addOption(name['name'], obj)
					mu.parsePollFlags(obj, match)
					obj.pollRead = obj.polled
					index = _saveComments(obj, match['aliasTail'],
										  match.end('aliasDefn'))
				else:
					msg = 'failed to read defn, index: {}'.format(index)
					gv.debugLogger.error(msg)
					if con.CAGSPC:
						print(msg)
						pdb.set_trace()
			else:
				msg = 'failed to read all aliases, index: {}'.format(index)
				gv.debugLogger.error(msg)
				if con.CAGSPC:
					print(msg)
					pdb.set_trace()
				break

	except Exception as exc:
		errmsg = 'error loading configuration: ' + repr(exc)
		gv.debugLogger.exception(errmsg)
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()

def _procLeadingCmts(string, index):
	while True:
		match = rx.ANY_COMMENT_OR_WS_RE.match(string, index)
		if match is None:
			return index
		gv.ConfigFile['leadingCmt'].append(match.group(0))
		index = match.end()

gv.ConfigFile['leadingCmt'] = []		# added in case user adds comments at start of CFGFILE
_aliasesRead = []
def _readCfgFile():
	global _writingCfg

	errmsg = ''
	try:
		with io.open(con.CFGFILE, mode='rt', encoding='utf-8') as fp:
			lines = fp.read()
		noTabs = lines.expandtabs(con.CFG_TAB_LENGTH)
		config = rx.ENDLINE_STRIP_WS_RE.sub(con.NL, noTabs)

		cfgIdx = 0
		while su.inbounds(cfgIdx, config):
			section = rx.SECTION_RE.match(config, cfgIdx)
			if section:
				sectionObj = gv.Section(section['name'], section.start('name'))
				gv.ConfigFile[section['name']] = sectionObj
				cfgIdx = section.end('section')
				cfgIdx = _saveComments(sectionObj, section['sectionTail'], cfgIdx)
				if section['name'] != 'Aliases':
					cfgIdx = readOptions(sectionObj, config, cfgIdx)
				else:
					gv.formattingAliases = gv.CurrentOptions['Settings'].get(
														'FormatAliasFns', False)
					_readAliases(sectionObj, config, cfgIdx)
					# unlike all the options (Option instances and their
					# gv.CurrentOptions counterparts), Alias's are not duplicated
					# - so we save a list of those loaded to detect deletions
					_aliasesRead.extend(gv.aliases.keys())
					break
			else:
				newIdx = _procLeadingCmts(config, cfgIdx)
				if newIdx == cfgIdx:	# both matches failed
					errmsg = '_readCfgFile, invalid configuration file '
					errmsg += '{!r}, halted at {} of {}'.format(
							con.CFGFILE, cfgIdx, len(config))
					raise ValueError(errmsg)
				cfgIdx = newIdx
		else:
			if cfgIdx != len(config) - 1:
				errmsg = '_readCfgFile, halted early reading '
				errmsg += '{!r}, halted at {} of {}'.format(
						con.CFGFILE, cfgIdx, len(config))
				raise ValueError(errmsg)

		settings = gv.ConfigFile['Settings'].keys()
		# check if CFGFILE was missing any options (ie. new to this version)
		if any(req not in settings for req in con.defaultConfig['Settings'] \
				   	if req not in con.settingsNotRequired):
			_writingCfg = True

		return True
	except IOError as exc:
		if exc.errno == errno.ENOENT:
			errmsg = 'no configuration file found'
			gv.debugLogger.debug(errmsg)
			return False
		else:
			errmsg = 'error reading configuration: '
			errmsg += repr(exc)
			gv.debugLogger.exception(errmsg)
	except ValueError:
		gv.debugLogger.exception(errmsg)
	except Exception as exc:
		errmsg = 'error loading configuration: '
		errmsg += repr(exc)
		gv.debugLogger.exception(errmsg)
	if con.CAGSPC:
		print(errmsg)
		traceback.print_stack(limit=4)
		pdb.set_trace()
	return False

def _getAppsCfg():
	"""update gv.ConfigFile from gv.CurrentOptions, noting which options have changed
	"""

	try:
		def _setCfg(cfgVal):
			# force all settings to conform to con.defaultConfig
			defaultVal = defaults.get(option)
			if isinstance(defaultVal, bool):
				cfgVal = 'yes' if cfgVal else 'no'
			elif option in con.optionsAreLists:
				cfgVal = ''.join(cfgVal) if isinstance(cfgVal, list) else cfgVal
			# values are written using .format(), so no more coersion needed
			inConfig[option] = cfgVal
			# inConfig.set(option, cnvValue())

		def _sameValue(first, second):
			if first is None:
				return second is None
			if second is None:
				return first is None
			if isinstance(first, bool) or isinstance(second, bool):
				return bool(first) == bool(second)
			if isinstance(first, int) or isinstance(second, int):
				return int(first) == int(second)
			if su.is_str(first) or su.is_str(first):
				return str(first.strip()) == str(second.strip())
			if isinstance(first, (list, tuple)) \
					and isinstance(second, (list, tuple)):
				return len(first) == len(second) \
					and all(val in second for val in first)
			return False

		def _sameOrder(first, second):
			if first is None and second is None:
				return True
			if isinstance(first, (list, tuple)) \
					and isinstance(second, (list, tuple)):
				return len(first) == len(second) \
					   and all(sv == first[x] \
							   for x, sv in enumerate(second))
			return False

		def _getGeometry(current):
			if not _sameValue(current, inConfig.get(option)):
				_setCfg(current)
				# update gv.CurrentOptions so won't trigger 'changed' again
				settings[option] = current
				changed.append(option)

		def _getSash():
			current = gv.sashPosns.get(option)
			# only save user generated (vs default) values
			if current is not None \
					and not _sameValue(current, inConfig.get(option)):
				_setCfg(current)
				# not in gv.CurrentOptions if not read from CFGFILE
				settings[option] = current
				changed.append(option)

		def _getPopup():
			popup = gv.popupWindows[option].searchBox
			if popup.searchXY:	# widget opened this session
				current = str(popup.searchXY)
				# only save user generated (vs default) values
				if not _sameValue(current, inConfig.get(option)):
					_setCfg(current)
					# update gv.CurrentOptions so won't trigger 'changed' again
					settings[option] = current
					changed.append(option)

		def _getList():
			if curr is not None:
				# value check is performed in calling fn
				lst = curr
				if option == 'FindPaths':
					# strip any quotes from paths else json goes boom
					lst = [cr.strip('\'"`') for cr in curr]
				elif option == 'FindSearches':
					lst = [[cr[0].replace("'", '"'), cr[1]] for cr in curr]
				inConfig[option] = json.dumps(lst)
				# inConfig.set(option, json.dumps(lst))
				# update gv.CurrentOptions so won't trigger 'changed' again
				settings[option] = lst
				changed.append(option)

		changed = []
		section = 'Settings'
		settings = gv.CurrentOptions[section]
		defaults = con.defaultConfig[section]
		inConfig = gv.ConfigFile[section]
		for option, default in defaults.items():
			if option == 'ConsolePort':
				pdb.set_trace()
			if option == 'SaveConfigNow': # never written
				pass
			elif option == 'Geometry':
				curr = gv.geometries[option].geometry()
				if curr == default and option not in inConfig:
					continue			# app never configured
				_getGeometry(curr)
			elif option == 'ToolTips':
				curr = wg.ToolTip.allToolTipNames()
				if len(curr) == len(con.toolTips):
					curr = 'all'
				elif len(curr) == 0:
					curr = 'none'
				saved = inConfig.get(option)
				coerced = json.dumps(curr) if isinstance(curr, list) else curr
				if saved != coerced:
					inConfig[option] = coerced
					changed.append(option)
			elif option in gv.sashPosns:
				_getSash()
			elif option in settings:
				value = settings[option]
				if option in inConfig:
					coerced = _coerceValue(option, inConfig.get(option), default)
					differentValue = not _sameValue(value, coerced)
				elif option in con.settingsNotRequired:
					# only save user generated (vs default) values
					differentValue = not _sameValue(value, default)
				else:
					differentValue = True
				if differentValue:
					_setCfg(value)	# prepare ConfigFile to save to CFGFILE
					changed.append(option)

		section = 'Font'
		font = gv.CurrentOptions[section]
		defaults = con.defaultConfig[section]
		inConfig = gv.ConfigFile[section]
		for option in defaults.keys():
			_setCfg(font[option])
			if not _sameValue(inConfig.get(option), font.get(option)):
				changed.append(option)

		section = 'Colors'
		colors = gv.CurrentOptions[section]
		defaults = con.defaultConfig[section]
		inConfig = gv.ConfigFile[section]
		# iter defaultConfig to prevent extra colors being saved
		for option in defaults.keys():
			lowOption = option.lower()
			_setCfg(colors[lowOption])
			if not _sameValue(inConfig.get(option), colors.get(lowOption)):
				changed.append(option)
		# CFGFILE color keys remain capitalized for backward compatibility

		section = 'History'
		history = gv.CurrentOptions[section]
		defaults = con.defaultConfig[section]
		inConfig = gv.ConfigFile[section]
		# all options are in con.settingsNotRequired
		for option, default in defaults.items():
			if option in gv.geometries:
				widget = gv.geometries[option]
				if widget.mouseXY:	# widget opened this session
					_getGeometry(widget.geometry())
			elif option in gv.sashPosns:
				_getSash()
			elif option in gv.popupWindows:
				# TopWindow's already caught by gv.geometries above
				_getPopup()
			elif option in con.optionsAreLists:
				curr = history.get(option)
				saved = inConfig.get(option)
				if option in con.optionsAreSelections:
					# only output if user has changed default
					combo = gv.findComboboxes[option]
					empty, default = gv.defaultSelectorList(combo, option)
					entryBlank = len(combo.get()) == 0
					if saved is None:
						if empty == entryBlank and _sameOrder(curr, default):
							# matches default, nothing to do
							continue
					elif curr is None:
						if option in inConfig:
							# remove option in CFGFILE
							del inConfig[option]
						changed.append(option)
						continue
					elif empty == entryBlank and saved == json.dumps(curr):
						# nothing's changed
						continue

					# if Entry is empty, prepend '<empty>' to list
					# - the Entry will be initialized to '' when the
					#   widget is built; removed in ba._initFindOptions
					if entryBlank:
						if combo.selectors == 0:
							empty = [con.NO_SELECTION]
						else:
							empty = [con.NO_SELECTION,
									 [con.UNCHECKED] * combo.selectors]
						if curr is None:
							curr = [empty]
						else:
							curr.insert(0, empty)
				if saved != json.dumps(curr):
					_getList()
			elif option in history:
				value = history[option]
				if option in inConfig:
					coerced = _coerceValue(option, inConfig.get(option), default)
					# maintain CFGFILE presence
					if _sameValue(value, coerced):
						continue
				elif _sameValue(value, default):
					# only save user generated (vs default) values
					continue
				# prepare ConfigFile to save to CFGFILE
				_setCfg(history[option])
				changed.append(option)

		# gv.aliases is a synonym gv.CurrentOptions['Aliases']
		deleted = [al for al in _aliasesRead if al not in gv.aliases]
		for alias in deleted:
			changed.append(alias)

		for alias, obj in gv.aliases.items():
			if obj.edited or obj.polled != obj.pollRead:
				changed.append(alias)

		# print('changed',changed)
		return len(changed) != 0
	except Exception as exc:
		errmsg = 'failed reading application configuration: '
		errmsg += repr(exc)
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.exception(errmsg)
			gv.app.colorPrint(errmsg)

def _areWritingCfg(saveNow):
	global _writingCfg

	try:
		settings = gv.CurrentOptions['Settings']
		if saveNow:
			settings['SaveConfigNow'] = False
			if _getAppsCfg():	# update ConfigFile
				_writingCfg = True
		else: # app is terminating, check if a save is needed
			if settings['SaveConfigOnExit']:
				if _getAppsCfg():	# retrieve app's configuration
					_writingCfg = True
			else:
				# if user changed 'SaveConfigOnExit' True -> False, still
				# have to update just that one option
				# ConfigFile contains the loaded config
				# and by skipping _getAppsCfg(), no other changes are saved
				inConfig =  gv.ConfigFile['Settings']
				saveOnexit = inConfig.get('SaveConfigOnExit', 'yes')
				if saveOnexit.lower() in con.TRUE_STRS:
					inConfig['SaveConfigOnExit'] = 'no'
				_writingCfg = True
		return _writingCfg			# convenience return

	except Exception as exc:
		print(exc)
		pdb.set_trace()

def writeCfgFile(saveNow=False):
	global _writingCfg

	# # used solely for alias output
	# def taggedCmtText(comments, select):
	# 	return ''.join(optn.text for optn in comments if optn.tag == select)

	if not _areWritingCfg(saveNow):
		return False

	hideDefComments \
		= gv.CurrentOptions['Settings'].get('HideDefaultComments', False)

	rpt = ''
	if 'leadingCmt' in gv.ConfigFile:
		rpt += ''.join(gv.ConfigFile['leadingCmt'])

	# loop through defaultConfig to maintain consistent order as some
	# options are optional or only appear later due to user actions
	for secName, defOptions in con.defaultConfig.items():
		section = gv.ConfigFile[secName]
		defComments = con.defaultComments[secName]
		secKey = '[{}]'.format(secName)
		rpt += secKey
		if not hideDefComments and secKey in defComments:
			rpt += ''.join(defComments[secKey])
		if len(section.comments):
			rpt += ''.join(section.comments)
		elif not rpt.endswith(con.NL):
			rpt += con.NL
		if secName == 'Aliases':
			break
		for optName in defOptions:
			if (optName in con.settingsNotRequired or secName == 'History') \
					and optName not in section.options:
				continue
			# Section emulates a dict, so need .options to fetch Option instance
			option = section.options[optName]
			assign = '{} = {}'.format(optName, option.value)
			if not hideDefComments and optName in defComments:
				insert = defComments[optName][:]
				# the leading '-' character flags this to precede option
				if insert[0].startswith('-'):
					rpt += insert.pop(0)[1:]
				if len(insert):
					if insert[0].startswith(con.NL):
						pad = ''
						if rpt[-1] == con.NL:
							insert[0] = insert[0][1:]
					else:
						pad = ' ' * max(0, con.CMT_OPTION_LINE_ALIGN - len(assign))
					rpt += assign + pad + ''.join(insert)
				else:
					rpt += assign
			else:
				rpt += assign
			if len(option.comments):
				rpt += ''.join(option.comments)
			elif not rpt.endswith(con.NL):
				rpt += con.NL
		if su.trailingWS(rpt, WS=con.NL) < 2:
			rpt += con.NL # blank like separates sections

	if len(gv.aliases):
		for alias, obj in sorted(gv.aliases.items(), key=lambda x: x[0].lower()):
			rpt += '{} :='.format(alias)
			flags = ''
			if obj.polled is not None:
				flags += 'P' if obj.polled == True else 'N'
			flags += 'M' if obj.inMenu else ''
			flags += ':' if len(flags) else ''
			if len(flags):
				rpt += obj.pollLead if len(obj.pollLead) else ' '
				rpt += flags
			elif len(obj.pollLead):
				# ignore pollLead if defn starts with a comment
				# (comments have leading whitespace)
				if obj.defn[su.leadingWS(obj.defn)] != '/':
					rpt += obj.pollLead
			else:
				rpt += ' '

			# if gv.formattingAliases:
			# 	# re-combine 'outer' comments
			# 	if obj.type is None:
			# 		rpt += taggedCmtText(obj.comments, 'preDefn')
			# 		rpt += obj.match['simpleAlias']
			# 		rpt += taggedCmtText(obj.comments, 'postDefn')
			# 	else:
			# 		rpt += taggedCmtText(obj.comments, 'fnLead')
			# 		if obj.type == 'iife':
			# 			rpt += '('
			# 		match = obj.match
			# 		rpt += 'function {}({})'.format(match['fnName'], match['fnArgs'])
			# 		fnHead = taggedCmtText(obj.comments, 'fnHead')
			# 		rpt += fnHead if len(fnHead) else ' '
			# 		rpt += match['fnBody']
			# 		rpt += taggedCmtText(obj.comments, 'fnTail')
			# 		if obj.type == 'iife':
			# 			rpt += ')'
			# 			rpt += taggedCmtText(obj.comments, 'preArgs')
			# 			rpt += '({})'.format(obj.iifeArgs)
			# 			rpt += taggedCmtText(obj.comments, 'postArgs')
			# 	rpt += '' if su.trailingWS(rpt, WS=con.NL) > 0 else con.NL
			# else:
			# 	rpt += obj.defn
			# endOfAlias = len(obj.defn)
			# trailing = [comment for comment in obj.comments
			# 				if comment.offset >= endOfAlias]
			# if len(trailing): # comments have whitespace
			# 	rpt += ''.join(tr.text for tr in trailing)

			rpt += obj.defn
			rpt += '' if rpt.endswith(con.NL) else con.NL

	fname = nextVersion(con.BASE_FNAME, con.CFG_EXT, con.MAX_CFG_VERSION)
	if not fname:
		fname = con.CFGFILE
		msg = 'File versioning failed, overwriting {!r}'.format(fname)
		gv.app.colorPrint(msg)

	try:
		with io.open(fname, mode='wt', encoding='utf-8') as fp:
			fp.write(rpt)
	except Exception as exc:
		errmsg = 'failed to save configuration file: '
		errmsg += repr(exc)
		if con.CAGSPC:
			print(errmsg)
			traceback.print_exc()
			pdb.set_trace()
		else:
			gv.debugLogger.exception(errmsg)
			gv.app.colorPrint(errmsg)
		return False

	_writingCfg = False
	# reset editing flags to reflect disk config is current
	for obj in gv.aliases.values():
		obj.edited = False
		obj.pollRead = obj.polled

	return True

