import dict_comparison as dc
import numpy as np
import os
import os.path
import stat
import json
from custom_json import json_dumper, json_hook

par_ext = ".params"
run_ext = ".run"

# maybe move the following to grace plot?
class InDirectory:
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        self.oldwd = os.getcwd()
        os.chdir(os.path.dirname(self.path))
    def __exit__(self, exc_type, exc_val, exc_tb):
        os.chdir(self.oldwd)

def save(d, filename):
    fp = open(filename, "w")
    json.dump(d, fp, default=json_dumper, sort_keys=True, indent=4)
    fp.close()

def load(filename):
    fp = open(filename, "r")
    d = json.load(fp, object_hook=json_hook)
    fp.close()
    return d

def get_shortest_possible_hash(ha, all_hashes, min_len=4):
    all_hashes = list(all_hashes)
    if ha in all_hashes:
        all_hashes.remove(ha)
    l = min_len
    while l < len(ha):
        col = False
        for oh in all_hashes:
            if oh.startswith(ha[:l]):
                col = True
                break
        if col:
            l += 1
        else:
            break
    return ha[:l]

def file_system_boundary_crossed(p1, p2):
    return os.stat(p1)[stat.ST_DEV] != os.stat(p2)[stat.ST_DEV]

def find_in_parents(path):
    path = os.path.realpath(path)
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)

    while True:
        if os.path.exists(dirname + "/" + basename):
            return dirname + "/" + basename
        elif dirname != '/':
            dirname = os.path.dirname(dirname) # up to parent 
        if dirname == "/" or file_system_boundary_crossed(os.path.dirname(path), dirname):
            break
    raise IOError("'%s' not found up to file system boundary" % basename)

def find_all_in_parents(path):
    path = os.path.realpath(path)
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    
    res = []

    while True:
        if os.path.exists(dirname + "/" + basename):
            res.append(dirname + "/" + basename)
        if dirname != '/':
            dirname = os.path.dirname(dirname) # up to parent 
        if dirname == "/" or file_system_boundary_crossed(os.path.dirname(path), dirname):
            break
    if len(res) == 0:
        IOError("'%s' not found up to file system boundary" % basename)
    return res

def load_parameters_incrementally(path):
    fns = find_all_in_parents(path)
    pd = {}
    for fn in fns[::-1]:
        d = load(fn)
        pd.update(d)
    return pd


def load_run(name):
    if os.path.exists(name):
        return name, load(name)
    else:
        rs = load_runs_in_dir(os.path.dirname(os.path.realpath(name)))
        resrfn = ""
        resr = None
        for rfn, r in rs:
            if rfn.startswith(os.path.basename(name)):
                if resr is not None:
                    raise IOError("'%s' does not unambiguously identify a run" % os.path.basename(name))
                resr = r
                resrfn = rfn
        if len(rs) == 0 or resr is None:
            raise IOError("'%s' not found" % name)
        return resrfn, resr

def load_runs_in_dir(d="."):
    rfns = [rfn for rfn in os.listdir(d) if rfn.endswith(run_ext)]
    return [(rfn, load(d + "/" + rfn)) for rfn in rfns]

def load_newest_run(d="."):
    return load_newest_run_matching({}, d)

def load_newest_run_matching(compare_to, d=".", enforce_subtree=True):
    rs = load_runs_in_dir(d)
    if len(rs) == 0:
        raise IOError("no %s files in %s" % (run_ext, d))
    wd = [(r["timestamp"], rfn, r) for rfn, r in rs if dc.is_subtree(compare_to, r)]
    if len(wd) == 0:
        raise IOError("no run found of which the requested is a subtree")
    wd.sort(key=lambda x: x[0])
    t, rfn, r = wd[-1]
    return rfn, r

