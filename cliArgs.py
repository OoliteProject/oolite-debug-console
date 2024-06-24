#  Created by Mister Flibble 20240531
#  (c) 2024 Mister Flibble CC-by-NC-SA 4

"""
Parses cli args. Sets defaults for filepaths.
"""

# Do not import anything which is intended to be set up by values created here

import sys
Python2 = sys.version_info[0] == 2
if Python2:
    from pathlib2 import Path
else:
    from pathlib import Path

import re
import click
import os
#Might want to do this properly, with __version__ file.
from _version import __version__

# set up globals with sane defaults using same names as click
#Doen't work in 2.7 _HOME=Path.home()
#Doen't work in 2.7 _DEFPATH = os.path.join(_HOME, '.Oolite', 'DebugConsole2')
_HOME=os.path.expanduser("~") # Allows for python 2.7
_DEFPATH = os.path.join(_HOME, '.Oolite', 'DebugConsole2')

g = dict(
  base = "OoDebugConsole",
  cpath = _DEFPATH,
  lpath = _DEFPATH,
  cext = 'cfg',
  hext = 'dat',
  lext = 'log',
  debug = False,
)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help', '-?'])
@click.command(context_settings=CONTEXT_SETTINGS)
@click.version_option(
  __version__,
  "--version",
  "-v"
)

@click.option("--base","-b",
  help=( "Base filename for config/log :  Default=" +
    g['base'] + " (filter\u00a0A-Za-z0-9_-)"
  ), type=str)
@click.option("--cpath","-c",
  help=(
    "Directory for config files. " +
    "Will be created if missing. Default=" + g['cpath']),
      type=click.Path())
@click.option("--lpath","-l",
  help=(
    "Directory for log files. " +
    "Will be created if missing. Default=" + g['lpath']),
      type=click.Path())
@click.option("--cext","-x",
  help=("Config file extension. Default=" +
  str(g['cext']) + " (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--lext","-y",
  help=("Log file extension. Default=" +
  str(g['lext']) +" (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--hext","-z",
  help=("History file extension. Default=" +
  str(g['hext'])+" (filter\u00a0A-Za-z0-9)"), type=str)
@click.option("--debug","-d",
  help=(
  "Enable some internal debug functions. Default=" +
  str(g['debug'])), is_flag=True) #seems to like file OR dir.

def cli(base,cpath,lpath,cext,lext,hext,debug):
  """Oolite Debug Console.

  Command history and log are written to log directory.

  """
  global g

  if debug:
    g['debug'] = True

  #Parse dirs. Use defaults if not in cli args.
  isDir(g['cpath'],'cpath') if cpath is None else isDir(cpath,'cpath') 
  isDir(g['lpath'],'lpath') if lpath is None else isDir(lpath,'lpath')

  if base is not None:
    if re.match("^[A-Za-z0-9_-]*$", base):
      g['base'] = base
    else:
      raise click.BadParameter(
        'Invalid base filename. Only A-Za-z0-9_- are accepted.\n',
        param_hint=["--base"])

  isExt(cext,'cext')
  isExt(lext,'lext')
  isExt(hext,'hext')

  if g['debug']:
    click.echo("Command line parse good. Continuing.")
    print(g)
#    click.echo(f"cpath: {cpath!r}")
#    click.echo(f"lpath: {lpath!r}")
#    click.echo(f"base: {base!r}")
#    click.echo(f"debug: {debug!r}")
#    click.echo(f"cext: {cext!r}")
#    click.echo(f"lext: {lext!r}")
#    click.echo(f"hext: {hext!r}")

  global shouldquit
  shouldquit=False

def execc(): # in python 2.7 exec is reserved

  global shouldquit
  shouldquit=True

  try:
    cli()
  except SystemExit as e:
    if e.code != 0:
      raise

  if shouldquit:
#    quit() #breaks if frozen
    sys.exit(1)


def isDir(thisdir,key):
  """
  Sanity check directory name and either
   add it to the dict, or fail with sane err.
  """
  global g
  if Path(thisdir).exists():
    if Path(thisdir).is_dir():
      g[key] = thisdir
    elif Path(thisdir).is_file():
      raise click.BadParameter( (
        'Specified path "' + thisdir + '"is file. Directory expected.\n'
        ), param_hint=["--" + key]
      )
    else:
      raise click.BadParameter( (
        'Invalid path "' + thisdir ), param_hint=["--" + key])
        # May need to create dir. Prompt for it, and add a no-prompt option?
  else:
    if g['debug']:
      print('Could not find directory "' + thisdir 
        + ' for option --' + key + '. Attempting to create it.')
    try:
#      os.makedirs(thisdir, exist_ok = True)
      Path(thisdir).mkdir(exist_ok=True) # works in 2.7 with pathlib2
      g[key] = thisdir
      if g['debug']:
        print("Directory " , thisdir ,  " Created ")
    except:
      raise click.BadParameter( (
        'Path "' + thisdir + '" does not exist and could not be created.\n'
         ), param_hint=["--" + key])


def isExt(ext,key):
  """
  Sanity check file extension and either add it to the dict,
   or fail with sane err.
  Currently only checks for alphanumeric, so can be any length.
  """
  global g
  if ext is not None:
    if re.match("^[A-Za-z0-9]*$", ext):
      g[key] = ext
    else:
      raise click.BadParameter('Invalid file extension.\n', param_hint=["--" + key])


execc()

#  con.BASE_FNAME = base
#if __name__ == '__main__':
#    exec()
