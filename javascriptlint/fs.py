# vim: ts=4 sw=4 expandtab
import codecs
import os

def readfile(path, encoding):
    with codecs.open(path, 'r', encoding) as f:
        contents = f.read()
    if contents and contents[0] == str(codecs.BOM_UTF8, 'utf8'):
        contents = contents[1:]
    return contents

def normpath(path):
    path = os.path.abspath(path)
    path = os.path.normcase(path)
    path = os.path.normpath(path)
    return path

