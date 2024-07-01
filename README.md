This is a major fluffing of version 2.

This version should work with python 2.7 and >3.6.

Default file save locations are preset within $HOME/.Oolite on all platforms. They can be changed. See below. Previous versions put the config and logs in whatever the working directory happened to be, which was for some at least, suboptimal.

CLI args have been added to allow file locations/debug etc. to be changed. This should work in icons/launchers as well as on the command line.

The CLI output is not directly visible on the Windows executable version, since that has no console. For now, all output that 'would' go to STDOUT and STDERR goes into a text file in the working directory.

To run from source, click and twisted need to be installed via pip. On Debian/Ubuntu systems, assuming python3 is installed, you may need to apt install python3-tk

On Python 2.7 pathlib2 is required

```
# Running from source directory in a linux xterm to get the help 
./DebugConsole.py -h
Usage: DebugConsole.py [OPTIONS]

  Oolite Debug Console.

  Command history and log are written to log directory.

Options:
  -v, --version     Show the version and exit.
  -b, --base TEXT   Base filename for config/log :  Default=DebugConsole2
                    (filter A-Za-z0-9_-)
  -c, --cpath PATH  Directory for config files. Will be created if missing.
                    Default=/home/username/.Oolite/Configs
  -l, --lpath PATH  Directory for log files. Will be created if missing.
                    Default=/home/username/.Oolite/Logs
  -x, --cext TEXT   Config file extension. Default=cfg (filter A-Za-z0-9)
  -y, --lext TEXT   Log file extension. Default=log (filter A-Za-z0-9)
  -z, --hext TEXT   History file extension. Default=dat (filter A-Za-z0-9)
  -d, --debug       Enable some internal debug functions. Default=False
  -h, -?, --help    Show this message and exit.
```

The paths will differ on other platforms. The defaults will settle in the next update.

On Linux:

To run from source (best/fastest), if on Ubuntu bassed systems:
```apt install python3-tk python3-click python3-twisted
python3 OoDC.py #append -h to see the list of arguments.
```
In the 'installable' builder, the wrapper script and ENV var are gone. The builder make script in the source can simply spit out a desktop file if you want to run directy from source and have a pretty icon in your application menus. If enough people ask, I'll give clearer instructions for that, or maybe even write a very simple installer to put a copy of the source in ~/.local/lib, symlink the main python script into ~/.local/bin, the desktop file in ~/.local/share/applications, and the icon place in... oh you can guess that! /usr/local will work too of course.

On MacOS:

If not running from source, you'll need to cd into the app bundle to launch from a terminal with --help. Whether Mac Oolite can talk to it 'out of the box' is yet to be ascertined, but is should function as a remote debugger. ( I've tested it using ssh to forward from a Linux running Oolite by adding -L127.0.0.1:8563:127.0.0.1:8563 into the ssh args from the Linux to the Mac.(Flibble))

Assuming you've installed to /Applications, you can execute from a terminal, in this example invoking the help, with:

```/Applications/Oolite\ Debug\ Console\ 2.app/Contents/MacOS/OoliteDebugConsole2 -h```

On Windows:

To avoid launching a console, standard output and standard error (STDOUT and STDERR) have nowhere to go, and cannot be used. This renders the app unable to send out help or errors until the main log file is open. Using the Windows executable by double-clicking will create a text file in the launching directory for standard input and output. In normal circumstances it should remain empty. If you drop the executable on cmd or powershell and give it an argument (like -h), the output will go into a file in whatever the current working directory is in that console. You can create a shortcut with arguments to change the options shown in the help, and that shortcut can make the current working directory such that the stdio txt file will be created out of harms way.

All:

I would advise you to stay clear of the Aliases menu for the moment, it's under reconstruction.

Hopefully this is nearly feature complete, and should be stable in short order.

