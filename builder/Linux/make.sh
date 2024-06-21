#!/bin/bash

q(){ echo "Error at: $*" >&2 ; exit 5 ; } # exit function

#Do apt installs. Only needed on first run.
#To not do this, simply call this script with arg 1 of: nocheck

alttarbase="$2"
alttardir="$3"

debdeps(){
  step="package install"
  sudo apt install python3-tk python3-pip python3-venv binutils || q "$step"
}

cleaner(){
  step="Remove build directory"
  echo "$step" ; rm -Rf build || q "$step"
}

basedir="$(dirname $(realpath $0))"
[ -d "$basedir" ] || q "Insane basedir '$basedir'"
cd "$basedir" || q "Can't cd to $basedir"



builddirname=build
builddir="$basedir/$builddirname" # this can be deleted to retry a build
basename=OoliteDebugConsole2 # gets used a lot
inscript=DebugConsole.py # the name of the script we'll be 'compiling'
venv="$builddir/pyinstaller"
relpath="../../../"

onefilebase="install-tree-onefile"
onedirbase="install-tree-onedir"

prep(){
  mkdir -p "$builddir" || q "Can't create $builddir."
  cd "$builddir" || q "Can't cd to builddir $builddir"
  step="setting up venv and building tools"
  python3 -m venv "$venv" &&
  source "$venv"/bin/activate &&
  pip install click &&
  pip install twisted &&
  pip install pyinstaller || q "$step"
}

desktop="[Desktop Entry]
Type=Application
Name=Oolite Debug Console $version
GenericName=Oolite Debug Console $version
Comment=$basename : the Oolite Debug Console $version
Exec=$basename
Icon=$basename-icon.png
Terminal=false
Categories=Game;Simulation;Development
Keywords=Space;Game;Simulation;Debug;Programming
"

setupvars(){
 #cd to base directory and set up base variables
 cd "$basedir"
 cd ../.. && ver=$(echo "
from _version import __version__
print(__version__)
" | python) && cd - || q "error ascertaining version"
 [ "x$ver" = "x" ] && q "version not found. version file empty or absent"
 [ "x$alttarbase" != "x" ] && tarbase="$alttarbase" || tarbase="${basename}-$ver-linux_$(arch)"
 [ "x$alttardir" != "x" ] && tardir="$alttardir" || tardir="$basedir"
 mkdir -p "$tardir" || q "could not create dir '$tardir' to house tarballs"
}

commonparts(){
 mkdir -p bin &&
  mkdir -p share/applications &&
   mkdir -p share/icons/hicolor/256x256/apps &&
    echo "$desktop" > share/applications/OoDC.desktop &&
     cp ../../../../OoJSC256x256.png share/icons/hicolor/256x256/apps/$basename-icon.png ||
 q "commonparts : failed to make output tree"
}

onefile(){
step="making onefile executable"
# This will MOVE the executable to 'here' getting it out of the way for onedir.
echo "$step"
#mkdir -p "$builddir" || q "Can't create $builddir."
#cd "$builddir" || q "Can't cd to builddir $builddir"
mkdir -p "$onefilebase" || q "couldn't make directory $onefilebase"
cd $onefilebase && commonparts && cd - || q "commonparts fail"
#prep &&
pyinstaller --name "$basename" --onefile "${relpath}$inscript" \
 --add-binary "${relpath}oojsc.xbm:." --add-binary "${relpath}OoJSC.ico:." \
 --add-binary "${relpath}OoJSC256x256.png:." &&
mv "dist/$basename" "${onefilebase}"/bin &&
tarname="$tarbase-onefile.tgz"
tar -C "$builddir/$onefilebase" --numeric-owner --dereference \
 -cpzf "$tardir/$tarname" . || q "$failed $step"
echo "
Finished $step.

To test the executable run:

 ./$builddirname/$onefilebase/bin/$basename

An install tarball is at '$tardir/$tarname'.
To install it as a user-local install, extract it in \$HOME/.local

example:-
tar -xpzf '$tarname' -C \$HOME/.local

If you have root access, you can install it system local like this:
sudo tar -xpzf '$tarname' -C /usr/local

If it's installed user-local, that install will (for that user) take priority over system versions.

" || q "$step"
}

onedir(){
step="making onedir executable"
#Moves the result dir into the target lib.
#No deref in tar.
echo "$step"
#mkdir -p "$builddir" || q "Can't create $builddir."
#cd "$builddir" || q "Can't cd to builddir $builddir"
mkdir -p "$onedirbase/lib" || q "couldn't make directory $onefilebase"
cd $onedirbase && commonparts && cd - || q "commonparts fail"
#prep &&
pyinstaller --name "$basename" --onedir "${relpath}$inscript" \
 --add-binary "${relpath}oojsc.xbm:." --add-binary "${relpath}OoJSC.ico:." \
 --add-binary "${relpath}OoJSC256x256.png:." &&
mv "dist/$basename" $onedirbase/lib &&
cd $onedirbase/bin && ln -s ../lib/$basename/$basename && cd -
tarname="$tarbase-onedir.tgz"
tar -C "$builddir/$onedirbase" --numeric-owner \
 -cpzf "$tardir/$tarname" . || q "$failed $step"
echo "
Finished $step.

To test the executable run:
 ./$builddirname/$onedirbase/lib/$basename/$basename

An install tarball is at '$tardir/$tarname'.
To install it as a user-local install, extract it in \$HOME/.local

example:-
tar -xpzf '$tarname' -C \$HOME/.local

If you have root access, you can install it system local like this:
sudo tar -xpzf '$tarname' -C /usr/local

If it's installed user-local, that install will (for that user) take priority over system versions.

" || q "$step"
}


#Arg 1 chooses action. Empty builds onedir tarball. 'onefile' makes as onefile.
case "$1" in
    debdeps) debdeps ;; # install dependencies
    clean) cleaner ;; # remove entire build directory
    onefile) setupvars && prep && onefile ;;
    dist) cleaner && setupvars && prep && onedir && rm -Rf build/build && onefile ;;
    desktop) echo "$desktop" ;;
    onedir) setupvars && prep && onedir ;;
    *) q "Setup: Invalid arg 1: [debdeps|onefile|onedir|clean|dist]" ;;
esac

#end
