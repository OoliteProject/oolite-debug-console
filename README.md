Nearly ready to merge with the mothership.

I've brought in some good stuff from the alpha and pushed a few things back from lessons learned.

Default file save locations are preset preset within $HOME/.Oolite on all paltforms.

CLI args have been added to allow file locations/debug etc. to be set. Should work in icons/launchers as well as on the command line.

The CLI output is not directly visible on the Windows executable version, since that has no console. For now, all output that 'would' go to STDOUT and STDERR goes into a text file in the working directory.

```
# Running from source directory in a linux xterm to get the help 
./DebugConsole.py -h
Usage: DebugConsole.py [OPTIONS]

  Oolite Debug Console.

  Command history and log are written to log directory.

Options:
  -v, --version     Show the version and exit.
  -b, --base TEXT   Base filename for config/log :  Default=OoDebugConsole
                    (filter A-Za-z0-9_-)
  -c, --cpath PATH  Directory for config files. Will be created if missing.
                    Default=/home/username/.Oolite/DebugConsole2
  -l, --lpath PATH  Directory for log files. Will be created if missing.
                    Default=/home/username/.Oolite/DebugConsole2
  -x, --cext TEXT   Config file extension. Default=cfg (filter A-Za-z0-9)
  -y, --lext TEXT   Log file extension. Default=log (filter A-Za-z0-9)
  -z, --hext TEXT   History file extension. Default=dat (filter A-Za-z0-9)
  -d, --debug       Enable some internal debug functions. Default=False
  -h, -?, --help    Show this message and exit.
```

The paths will differ on other platforms.

App now has an icon in task switcher if running from source when pwd is 'other' than source code dir.

Running via python from another pwd, it now finds it's icons.

On Linux 'installable' builder, the wrapper script and ENV var are gone. The install make script can simply spit out a desktop file if you want to run from source and have a pretty icon in your application menus.

Lots of other fixes.
