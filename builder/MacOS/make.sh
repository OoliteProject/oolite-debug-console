#!/bin/bash

q(){ echo "Error at: $*" >&2 ; exit 5 ; } # exit function

alttarbase="$2"
alttardir="$3"

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
appPrettyName="Oolite Debug Console 2.app"
inscript=DebugConsole.py # the name of the script we'll be 'compiling'
venv="$builddir/pyinstaller"
relpath="../../../"

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


setupvars(){
 #cd to base directory and set up base variables
 cd "$basedir"
 cd ../.. && ver=$(echo "
from _version import __version__
print(__version__)
" | python3 ) && cd - || q "error ascertaining version"
 [ "x$ver" = "x" ] && q "version not found. version file empty or absent"
 [ "x$alttarbase" != "x" ] && tarbase="$alttarbase" || tarbase="${basename}-$ver-macos_$(arch)"
 [ "x$alttardir" != "x" ] && tardir="$alttardir" || tardir="$basedir"
 mkdir -p "$tardir" || q "could not create dir '$tardir' to house tarballs"
}

onefile(){
step="making executable"
echo "$step"
pyinstaller --name "$basename" --onefile "${relpath}$inscript" &&
tarname="$tarbase-onefile.tgz" &&
tar -C "$builddir/dist" --numeric-owner --dereference \
 -cpzf "$tardir/$tarname" . || q "$failed $step"
mv  dist/$basename $basedir &&
echo "
Finished $step.

To test the executable run:

./$basename

A tarball is at '$tardir/$tarname'.

" || q "$step"
}

appbundle(){
step="making appbundle"
echo "$step"
pyinstaller --name "$basename" --onedir "${relpath}$inscript" \
 --windowed --icon "${relpath}/images/OoJSC.icns" || q "failed appbundle"
mv "$builddir/dist/${basename}.app" "$builddir/dist/${appPrettyName}" &&
tarname="$tarbase-app.tgz" &&
tar -C "$builddir/dist" --numeric-owner \
 -cpzf "$tardir/$tarname" "${appPrettyName}" || q "$failed $step"
mv  dist/"$appPrettyName" $basedir &&
echo "
Finished $step.

A tarball is at '$tardir/$tarname'.

" || q "$step"
}

#Arg 1 chooses action. clean or dist.
case "$1" in
    clean) cleaner ;; # remove entire build directory
    onefile) cleaner && setupvars && prep && onefile ;;
    app) cleaner && setupvars && prep && appbundle ;;
    dist) cleaner && setupvars && prep && onefile && rm -Rf build/build && appbundle ;;
    *) q "Setup: Invalid arg 1: [clean|onefile|appbundle|dist]" ;;
esac

#end
