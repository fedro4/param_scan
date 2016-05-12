import json
import pint
from parameter_sets import Evaluator
from param_scan import ureg
from datetime import datetime 

dtfmt = "%Y-%m-%d %H:%M:%S.%f"

def json_dumper(o):
    try:
        if hasattr(o, "tolist"):
            try:
                o = o.tolist()
                return o
            except (AttributeError, TypeError):
                pass # if it's a pint Quantity that does not contain an array
        if hasattr(o, "to_json"):
            return o.to_json()
        if hasattr(o, "strftime"):
            return o.strftime(dtfmt)
        if hasattr(o, "dimensionless"): # it seems to be a pint Quantity
            if o.dimensionless:
                return float(o)
            else:
                return "{:~}".format(o).strip()
        return o.__repr__()
        #return o.__dict__()
    except Exception as e:
        print o
        raise e


def parse_item(it):
    if isinstance(it, basestring):
        # first, try reading a DateTime. pint's parser is a bit too forgiving and will happily read that as a dimensionless value if we don't catch it before
        try:
            it = datetime.strptime(it, dtfmt)
            return it
        except ValueError:
            pass
        # try reading a pint Quantity
        try:
            it = ureg.Quantity(it)
            return it
        except: #(pint.UndefinedUnitError):
            pass
        # apparently not a Quantity, Evaluator?
        for when in ['before_unroll', 'after_unroll']:
            if hasattr(it, "startswith") and it.startswith("eval_%s(" % when):
                it = Evaluator(it[6+len(when):-1], when)
    return it

def json_hook(o):
    for k, v in o.items():
        if isinstance(v, list):
            o[k] = [parse_item(it) for it in v]
        else:
            o[k] = parse_item(v)
    return o
