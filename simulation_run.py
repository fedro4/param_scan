import subprocess as sp
import numpy as np
import os
import hashlib
import json
from custom_json import json_dumper
import parameter_sets as ps
import submitters as su
import output_parsing as op
import dict_comparison as dc
from datetime import datetime
from time import sleep

# which git commands are porcelain? avoid them

class SimulationRunException(Exception):
    pass

def run_git_command(sim, command):
    """ run 'git command' making sure we're in the source dir """
    res = None
    curdir = os.getcwd()
    try:
        os.chdir(os.path.abspath(sim["src_path"]))
        res = sp.check_output(("git " + command).split(" "), stderr=sp.STDOUT) 
    finally:
        os.chdir(curdir)
    return res

def git_get_current_branch(sim):
    try:
        return run_git_command(sim, "symbolic-ref HEAD HEAD").strip()
    except sp.CalledProcessError:
        return None

def git_get_sha1(sim, rev):
    return run_git_command(sim, "rev-parse %s" % rev).strip()

def git_is_clean(sim):
    return (run_git_command(sim, "status --porcelain").strip() == "")

def git_checkout(sim, rev):
    if git_get_sha1(sim, "HEAD") != git_get_sha1(sim, rev):
        print "checking out %s..." % rev
        out = run_git_command(sim, "checkout %s" % rev)

def get_executable_path(sim, rev):
    return os.path.abspath(sim["build_path"] + "/" + (sim["executable"] % {"GIT_SHA1": git_get_sha1(sim, rev)}))

def build_executable_if_needed(sim, rev):
    """ return the name of the executable for a given revision, build it if its not found """
    build_path = os.path.abspath(sim["build_path"])
    exe = get_executable_path(sim, rev) 
  
    if not os.path.exists(exe) or (git_get_sha1(sim, rev) == git_get_sha1(sim, "HEAD")):
        if not git_is_clean(sim):
            raise SimulationRunException("git: working directory is not clean. commit first!")

    if os.path.exists(exe):
        print "Found %s." % exe
    else:
        print "%s not found. Will build it..." % exe
        if git_get_current_branch(sim) is not None:
            oldhead = git_get_current_branch(sim)
            print "previously on branch", oldhead
        else:
            oldhead = git_get_sha1(sim, "HEAD")
            print "previously at commit", oldhead
        oldwd = os.getcwd()
        try:
            git_checkout(sim, git_get_sha1(sim, rev))
            os.chdir(build_path)
            sp.check_call(sim["build_command"], shell=True)
        finally:
            os.chdir(oldwd)
            git_checkout(sim, oldhead)
    # XXX check if its there now!

def get_run(sim, rev, prms, data_dir, unique=False): # should a run be a class?
    sim = dict(sim)
    sim.update({'git_sha1':  git_get_sha1(sim, rev)})
    
    sim["build_path"] = os.path.realpath(sim["build_path"])
    sim["src_path"] = os.path.abspath(sim["src_path"])

    r = {'sim': sim, 'parameters': prms, 'timestamp': str(datetime.now()), 'data_dir': os.path.abspath(data_dir)}
    r['uniqueness'] = 0 if not unique else r['timestamp']
    return r

def get_prefix(sim, prms, uniqueness, ignore_underscore=True):
    d = {'sim': dict((k, v) for (k, v) in sim.items() if not (ignore_underscore and k.startswith("_"))), 
         'parameters': dict((k, v) for (k, v) in prms.items() if not (ignore_underscore and k.startswith("_"))), 
         'uniqueness': uniqueness}
    json.encoder.FLOAT_REPR = lambda o: format(o, '.15g') # otherwise, we get different reprs for sth like 0.1 (internally 0.10000000000000001) between (e.g.) Python 2.7.9 and Python 2.7.13 :: Anaconda 4.3.1 (64-bit), which can both be called cause /usr/bin/python is invoked in the shebang line in various scripts
# XXX in all likelyhood, this breaks compatibility with the old  
    return  hashlib.sha1(json.dumps(d, default=json_dumper, sort_keys=True)).hexdigest()

def get_output_path(r, p, filename):
    return r["data_dir"] + "/" + get_prefix(r["sim"], p, r["uniqueness"]) + "/" + filename

# ist das in diesm modul richtig aufgehoben?
def read_values(r, psets, valuekeys, filename, in_units=None, ignore_errors=False):
    def inu(v, u):
        if in_units is not None:
            r = v / u
        else: r = v
        #print repr(r)
        try:
            return float(r)
        except ValueError:
            return r

    res = []
    if in_units is not None and len(in_units) != len(valuekeys):
        raise ValueError("need valuekeys and in_units to have the same length")
    for p in psets:
        tmpvals = []
        for k, u in zip(valuekeys, in_units if in_units is not None else np.ones(len(valuekeys))):
            if p.has_key(k): 
                tmpvals.append(inu(p[k], u))
            else:
                try:
                    tmpvals.append(inu(op.read_value(get_output_path(r, p, filename), k), u))
                except Exception as e:
                    if not ignore_errors:
                        raise e
                    else:
                        break
        if len(tmpvals) == len(valuekeys):
            res.append(tmpvals)
    return zip(*res)
    #return np.array(zip(*res))


def submit(sim, prms, data_dir, rev="HEAD", unique=False, submitter=su.xargs_submitter, dry_run=False, submitter_args={}):
    # should the run file be written here?
    # in which path i currenly am is unclear and should be less of an issue
    r = get_run(sim, rev, prms, data_dir, unique)
    r_prfx = get_prefix(r["sim"], r["parameters"], r["uniqueness"], ignore_underscore=False)
    r_name = r_prfx + ".run"
    build_executable_if_needed(sim, rev)

    dir_names = []
    param_sets = []
   

    for p in ps.unroll(prms):
        dir_name = os.path.abspath(data_dir + "/" + get_prefix(r['sim'], p, r['uniqueness']))

        if (not os.path.exists(dir_name)):
            os.makedirs(dir_name)
        if (not os.path.lexists(dir_name + "/" + r_name)):
            # this link can end up pointing into nothing due to us not being in the right dir
            os.symlink(os.path.abspath(r_name), dir_name + "/" + r_name)      
        else:
            if (sim.has_key("_finished_condition") and 
               os.path.exists(dir_name + "/" + sim["_finished_condition"]["file"]) and 
               op.output_contains(dir_name + "/" + sim["_finished_condition"]["file"], sim["_finished_condition"]["contains"])):
                print "already finished:", dir_name, " - skipping"
                continue
        dir_names.append(dir_name)
        param_sets.append(p)
    
    if dry_run:
        print get_executable_path(sim, rev)
        print dir_names
        print param_sets
    elif len(dir_names) > 0:
        submitter(get_executable_path(sim, rev), dir_names, param_sets, submitter_args)
    return r

