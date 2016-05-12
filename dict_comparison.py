import numpy as np

def values_differ(a, b):
    """ compare a and b for equality """
    eq = False
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        return not np.array_equal(a, b)
    else:
        return a != b

def is_dictlike(d):
    """ return true if d looks, for our purposes, sufficiently dict-like """
    return hasattr(d, "keys") and hasattr(d, "__getitem__") and hasattr(d, "has_key")

def get_common(ps):
    """ for a list of dictionaries ds, return a dictionary that contains all entries common to all of them. recurses into sub-dictionaries. """
    common = dict(ps[0])
    for p in ps:
        for k in common.keys():
            if p.has_key(k) and is_dictlike(p[k]) and is_dictlike(common[k]):
                common[k] = get_common([p[k], common[k]])
                if common[k] == {}:
                    del common[k]
            elif not p.has_key(k) or values_differ(p[k], common[k]):
                del common[k]
    return common

def get_difference_to_common(p, common):
    """ return a dictionary that contains entries of p that do not also appear in common. recurses into sub-dictionaries. """
    d = {}
    for k in p.keys():
        if common.has_key(k) and is_dictlike(p[k]) and is_dictlike(common[k]):
            d[k] = get_difference_to_common(p[k], common[k])
            if d[k] == {}:
                del d[k]
        elif not common.has_key(k):
            d[k] = p[k]
    return d

def get_difference(p1, p2):
    keys1 = set(p1.keys())
    keys2 = set(p2.keys())
    onlyin1 = keys1.difference(keys2)
    onlyin2 = keys2.difference(keys1)
    inboth = keys1.intersection(keys2)
    d1 = {}
    d2 = {}
    for k in inboth:
        if is_dictlike(p1[k]) and is_dictlike(p2[k]):
            d1[k], d2[k] = get_difference(p1[k], p2[k])
            if d1[k] == {}: # in this case d2[k] == {} as well
                del d1[k]
                del d2[k]
        elif values_differ(p1[k], p2[k]):
            d1[k] = p1[k]
            d2[k] = p2[k]
    for k in onlyin1:
        d1[k] = p1[k]
        d2[k] = None
    for k in onlyin2:
        d1[k] = None
        d2[k] = p2[k]
    return d1, d2

def is_subtree(d1, d2):
    """ is d1 a subtree of d2? """
    for k in d1.keys():
        if d2.has_key(k) and is_dictlike(d1[k]) and is_dictlike(d2[k]):
            if not is_subtree(d1[k], d2[k]):
                return False
        elif not d2.has_key(k) or values_differ(d1[k], d2[k]):
            return False
    return True

def get_leaf_count(d):
    """ count all leafs (and sub-leafs) within a dictionary d, where a leaf is each entry that is not itself a dictionary """
    if is_dictlike(d):
        return sum([get_leaf_count(d[k]) for k in d.keys()])
    else: return 1

def get_distance(p1, p2):
    """ a difference metric between d1 and d2 that gives a result between 0 (identical) and get_leaf_count(d1) + get_leaf_count(d2) """
    d1, d2 = get_difference(p1, p2)
    return get_leaf_count(d1)
