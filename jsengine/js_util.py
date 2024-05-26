# vim: ts=4 sw=4 expandtab
from .parser import kind as tok

def numeric_property_str(node):
    assert node.kind == tok.NUMBER
    if node.atom.startswith('0x'):
        value = int(node.atom, 16)
    else:
        value = float(node.atom)
        if value.is_integer():
            value = int(value)
    return str(value)

def object_property_str(node):
    assert node.kind == tok.COLON

    left, right = node.kids
    while left.kind == tok.RP:
        left, = left.kids
    if left.kind == tok.NUMBER:
        return numeric_property_str(left)

    assert left.kind in (tok.STRING, tok.NAME)
    return left.atom

