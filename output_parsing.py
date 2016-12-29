import re
from param_scan import pint_ureg

def read_value_from_str(ostr, key):
    #f_re = r'([+-]?\d+(?:\.\d+)?(?:[eE][+-]\d+)?)'
    #try:
    #    v = float(re.findall("^" + key + " = " + f_re, ostr, re.MULTILINE)[0])
    #except (IndexError):
    #    raise ValueError("key '%s' not in string '%s'" % (key, ostr))
    #return v
    i0 = ostr.find(key)
    if i0 < 0:
        raise ValueError("key '%s' not found" % key)
    i1 = ostr.find("\n", i0)
    if i1 < 0:
        i1 = len(ostr)
    _, v = ostr[i0:i1].split("=")
    if pint_ureg is not None:
        return pint_ureg.parse_expression(v)
    else:
        return float(v)
    

def read_value(filename, key):
    fh = open(filename, "r")
    ostr = fh.read()
    fh.close()
    return read_value_from_str(ostr, key)

def output_contains(filename, s):
    fh = open(filename, "r")
    ostr = fh.read()
    fh.close()
    return s in ostr

