The Mac version of this is currently quite crude compared to its Linux brother.

This will build an app tarball, with an executable that will work where python
 is unavailable.

Then, build the app.

    ./make.sh app

If rebuilding for any reason, delete the build directory.

    ./make.sh clean

Detailed info:

The script needs to be in the build tree at ./MacOS/make.sh

It expects to be executed in that directory.

Any arg2 will be used as the base name for the tarball. Take care!

Any arg3 will be used as a destination directory for the tarballs.

arg1 can be:

clean : delete the build sub-directory.
onefile : makes a standalone executable without icons.
app : makes a MacOS app image.
dist : makes both app and standalone.

It will:
    Create a "build" directory.
    Create a python3 venv in it.
    Activate the venv.
    Use pip inside the venv to install python dependencies and pyinstaller.
    Compile an executable of the project.
    Create a tar archive with that in it.
