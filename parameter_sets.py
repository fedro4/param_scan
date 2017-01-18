from param_scan import pint_ureg
import numpy as np
import __builtin__

def near(a, b, rtol=1e-05):#, atol=1e-08):
    #return abs(a-b) <= (atol + rtol*abs(b)) 
    return abs(a-b) <= rtol*abs(b) # what does atol even mean for a Quantity? 


# we cannot simply check for "__iter__" cause pint.Quantity always has that, even if it just holds a float
def is_iterable(x):
    try:
        _ = iter(x)
        return True
    except TypeError:
        return False

# XXX one could probably get rid of "before/after_unroll" and automate that by just considering whether the evaluator reaturns an iterable
class Evaluator:
    max_printout = 256    

    def __init__(self, expr, when='after_unroll'):
        self.expr = expr
        self.when = when
    def eval(self, p):
        # what non-builtin function might one want to use in evaluators?
        funcs = {'linspace': np.linspace, 
                 'logspace': np.logspace, 
                 'concatenate': np.concatenate, 
                 'near': near}
        class MyDictReplacement:
            def __getitem__(self, name):
                if name in dir(__builtin__):
                    return eval(name)
                elif funcs.has_key(name):
                    return funcs[name]
                elif p.has_key(name):
                    if hasattr(p[name], "eval"):
                        raise ValueError("%s is a not yet eval'd Evaluator" % name)
                    return p[name]
                elif pint_ureg is not None:
                    return pint_ureg.parse_expression(name)
                else:
                    raise ValueError("'%s' unknown" % name)
        res = eval(self.expr, {}, MyDictReplacement()) 
        if self.when == "after_unroll" and is_iterable(res):
            raise ValueError("an after-unroll Evaluator must never evaluate to an iterable")
        return res
    def __repr__(self):
        return "eval_%s(%s)" % (self.when, self.expr[:Evaluator.max_printout] + ("..." if len(self.expr) > Evaluator.max_printout else ""))
    def __str__(self):
        return self.__repr__()
    def __eq__(self, other): 
        if hasattr(other, "expr"):
            return (self.expr == other.expr) and (self.when == other.when)
        else: return False
    def __ne__(self, other):
        return not self.__eq__(other)
    def to_json(self):
        return "eval_%s(%s)" % (self.when, self.expr)

def get_axes(p):
    axes = []
    for k in p:
        if not isinstance(p[k], basestring) and is_iterable(p[k]):
            axes.append(k)
    return axes

def run_evaluators(p, when, ignore_failed_ones=False):
    def get_eval_keys(p, when):
        res = []
        for k in p.keys():
            if hasattr(p[k], "eval") and p[k].when == when:
                res.append(k)
        return res

    # Evaluators might depend on being run in a certain order, and it would be tough to figure out which one -- so we rely on systematic trial and error
    inorder = []
    while True:
        evaled_something = False
        evalkeys = get_eval_keys(p, when)
        failed_eval_keys = []
        eval_exceptions = {}
        for k in evalkeys:
            try:
                pko = p[k]
                p[k] = p[k].eval(p)
                evaled_something = True # Evaluators that failed before may have depended on this one, so after we're done go for another round
                inorder.append(k)
            except Exception as e:
                failed_eval_keys.append(k)
                eval_exceptions[k] = e
        if not evaled_something:
            if not ignore_failed_ones and len(failed_eval_keys) > 0:
                # we evaluated all we could, and there are still errors
                raise ValueError("Evaluators failed: %s" % str(eval_exceptions))
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
    p = dict(p)
    run_evaluators(p, 'before_unroll')
    ignore_eval_errors = False
    if not axes:
        axes = get_axes(p) # all of them
    elif axes != get_axes(p):
        ignore_eval_errors = True # if we're only unrolling one axis (of many), then some Evaluators can fail 
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
    ordered_eval_keys = run_evaluators(l1[0], 'after_unroll', ignore_eval_errors)
    for p in l1[1:]:
        #print ordered_eval_keys
        #pn = dict(p)
        for k in ordered_eval_keys:
            try:
                p[k] = p[k].eval(p)
                #pn[k] = pn[k].eval(pn)
                #print k, p[k], pn[k]
            except Exception as e:
                #print pn
                # the values of the first param set may have been incidentally such that we
                # did not determine an order that works for all evaluators
                #print ordered_eval_keys
                ordered_eval_keys = run_evaluators(p, 'after_unroll', False)
                #print ordered_eval_keys

                #raise ValueError("Evaluator failed: %s" % str({k: e}))
                break
        #p.update(pn)
    return l1

        
