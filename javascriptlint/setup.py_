#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

from javascriptlint import version

class _BuildError(Exception):
    pass

def _main():
    cmdclass = {
        'build': distutils.command.build.build,
        'clean': distutils.command.clean.clean,
    }
    args = {}
    args.update(
        name = 'javascriptlint',
        version = version.version,
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
        cmdclass = cmdclass,
        description = 'JavaScript Lint %s' % version.version,
        packages = ['javascriptlint'],
        scripts = ['jsl']
    )
    setup(**args)


if __name__ == '__main__':
    _main()
