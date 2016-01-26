import subprocess as sp
import numpy as np
import os
import hashlib
import json
import parameter_sets as ps

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
    if os.path.exists(exe):
        print "Found %s." % exe
    else:
        print "%s not found. Will build it..." % exe
        if not git_is_clean(sim):
            raise SimulationRunException("git: working directory is not clean. commit first!")
        oldhead = git_get_sha1(sim, "HEAD")
        oldwd = os.getcwd()
        try:
            git_checkout(sim, git_get_sha1(sim, rev))
            os.chdir(build_path)
            sp.check_call(sim["build_command"], shell=True)
        finally:
            os.chdir(oldwd)
            git_checkout(sim, oldhead)

def get_prefix(sim, git_sha1, prms):
    def json_dumper(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        elif hasattr(o, "to_json"):
            return o.to_json()
        else:
            return o.__dict__()
    print json.dumps({"sim": sim, "git_sha1": git_sha1, "parameters": prms}, default=json_dumper, sort_keys=True)
    return hashlib.sha1(json.dumps({"sim": sim, "git_sha1": git_sha1, "parameters": prms}, default=json_dumper, sort_keys=True)).hexdigest()

def run(sim, prm_sets):
    exe = get_executable(sim)
    
