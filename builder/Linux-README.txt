
This will build an app tarball, with an executable that will work where python
 is unavailable.

It is aimed at Debian/Ubuntu systems.

It may work on other dists if the requirements are met and using 'nocheck'.


Short version:

    tar -xpzf Linux.tar
    cd Linux
    ./make.sh

Test:

    ./OoliteDebugConsole

To install to .local in a home directory:

    tar -C $HOME/.local/ -xpzf OoliteDebugConsole*-linux-installable.tar.gz


Detailed info:

Unpack the Linux.tar.gz in this folder.
The path relative to the what it's building is important due to symlinks.

    tar -xpzf Linux.tar.gz

This will create a directory "Linux", containing:-

    make.sh OoDebugConsole.cfg install-tree

make.sh is the script used to make the executable from the python source.

If run in the Linux directory as

    ./make.sh

The script will initially run apt install for packages it depends on.

    apt install python3-tk python3-pip python3-venv binutils

For most users, this will involve a prompt to authenticate.

After the first run (or if you know the packages are already installed),
 this step can be skipped by running the script with nocheck as an arg1:

    ./make.sh nocheck

Any other arg1 will be used as the output name for the tarball. Take care!

Either way, it will go on to:
    Create a "build" directory.
    Create a python3 venv in it.
    Activate the venv.
    Use pip inside the venv to install python dependencies and pyinstaller.
    Compile an executable of the project.
    Move the executable into the current (Linux) directory for quick testing.
    Make an installable tarball.

OoDebugConsole.cfg
    My current favourite config file.
    Gets used if you run the resulting binary with the Linux directory
     as current working directory.
    Is therefore easy to edit if you need a different font for testing.
    If you've installed the tarball this builder makes, you can copy
     it to $HOME/.Oolite/DebugConsole2/ to use it from the launcher.
    Could be replaced with a symlink to your own config so you can
     test the binary in-place, and still have your normal settings.

install-tree
    A directory structure used to make installer tarballs.
    Contains icon, .desktop file, and a wrapper script to make sure that
     config files and logs end up in a sane place ($HOME/.Oolite/DebugConsole2)
    Also a symlink to the executable that gets made by make.sh. this will be
     dereferenced by tar when the installable tarball gets made.

Why the wrapper script?

The wrapper script will change directory by default to $HOME/.Oolite/DebugConsole2
 so that config and logs are in a predictable place.

To change config directory set the variable OoliteDebugConsole2_conf

For example, to use the debug console configs in $HOME/OoDev/OoDC-config1:

    OoliteDebugConsole2_conf="$HOME/OoDev/OoDC-config1" OoDC

The wrapper script will attempt to create missing directories.
