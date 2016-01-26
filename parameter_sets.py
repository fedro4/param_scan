import numpy as np
import json

class Evaluator:
    max_printout = 256    

    def __init__(self, expr):
        self.expr = expr
    def eval(self, p):
        return eval(self.expr, {}, p)
    def __repr__(self):
        return "eval(%s)" % self.expr[:Evaluator.max_printout] + ("..." if len(self.expr) > Evaluator.max_printout else "")
    def __str__(self):
        return __repr__(self)
    def __eq__(self, other): 
        if hasattr(other, "expr"):
            return self.expr == other.expr
        else: return False
    def to_json(self):
        return "eval(%s)" % self.expr

def get_axes(p):
    axes = []
    for k in p:
        if hasattr(p[k], "__iter__"):
            axes.append(k)
    return axes

def run_evaluators(p, ignore_failed_ones=False):
    def get_eval_keys(p):
        res = []
        for k in p.keys():
            if hasattr(p[k], "eval"):
                res.append(k)
        return res

    inorder = []
    # Evaluators might depend on being run in a certain order, and it would be tough to figure out which one -- so we rely on systematic trial and error
    while True:
        evaled_something = False
        evalkeys = get_eval_keys(p)
        failed_eval_keys = []
        for k in evalkeys:
            try:
                p[k] = p[k].eval(p)
                evaled_something = True # Evaluators that failed before may have depended on this one, so after we're done go for another round
                inorder.append(k)
            except:
                failed_eval_keys.append(k)
        if not evaled_something:
            if not ignore_failed_ones and len(failed_eval_keys) > 0:
                # we evaluated all we could, and there are still errors
                raise ValueError("Evaluators failed: %s" % ", ".join(failed_eval_keys))
            break
    return inorder
    

def unroll_axis(p, axis):
    res = []
    p = dict(p)
    if not p.has_key(axis): 
        raise ValueError("%s not an axis" % axis)
    if not hasattr(p[axis], "__iter__"):
        p[axis]=[p[axis]]
    vs = []
    if isinstance(axis, tuple):
        vs = zip(*p[axis])
    else:     
        vs = p[axis]
    for v in vs:
        pp = dict(p)
        del pp[axis]
        if isinstance(axis, tuple):
            for i in range(len(axis)):
                pp[axis[i]] = v[i]
        else:
            pp[axis] = v
        res.append(pp)
    
    return res

def unroll(p, axes=None):
    if not axes:
        axes = get_axes(p) # all of them
    if not hasattr(axes, "__iter__"):
        axes = [axes]
    l1 = [p]
    l2 = []
    for a in axes:
        for p in l1:
            l2 += unroll_axis(p, a)
        l1 = list(l2)
        l2 = []
    
    # run Evaluators on first set to determine an order that works
    ordered_eval_keys = run_evaluators(l1[0])
    for p in l1[1:]:
        for k in ordered_eval_keys:
            p[k] = p[k].eval(p)

    return l1

def write_parameters(prms, fp):
    def json_dumper(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        elif hasattr(o, "to_json"):
            return o.to_json()
        else:
            return o.__dict__()
    return json.dump(prms, fp, default=json_dumper, indent=4)

def read_parameters(fp):
    d = json.load(fp)
    for k, v in d.items():
        if hasattr(v, "startswith") and v.startswith("eval("):
            d[k] = Evaluator(v[5:-1])
    return d

