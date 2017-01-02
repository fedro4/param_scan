import subprocess as sp

def build_argstr(p):
    argstr = ""
    for k in p.keys():
        if not k.startswith("_"):
            try:
                valstr = "{:~}".format(p[k]).replace(" ", "")
            except ValueError: # not a pint Quantity, apparently
                valstr = str(p[k])
            argstr += "--" + str(k) + "=" + valstr + " "
    return argstr

def xargs_submitter(exe_name, dir_names, param_sets, args={}):
    
    if args.has_key("nproc") and args["nproc"]:
        nprocstr = str(nproc)
    else: nprocstr = "`nproc`"

    if len(param_sets) > 0:
        p = sp.Popen("xargs -P%(nprocstr)s -I ^ bash -c 'P=('^');cd ${P[0]};%(exe_name)s ${P[@]:1} > %(stdout_name)s 2> %(stderr_name)s'" % {"exe_name": exe_name, "nprocstr": nprocstr, "stdout_name": "stdout",  "stderr_name": "stderr"}, stdin=sp.PIPE, shell=True)
    for dir_name, params in zip(dir_names, param_sets):
        print >> p.stdin, dir_name, build_argstr(params)

    print "PID:", p.pid
    if args.has_key("wait") and args["wait"]:
        p.communicate()
    
    if p.returncode > 0:
        out, err = p.communicate()
        print err
        print "Ret val", p.returncode

def condor_submitter(exe_name, dir_names, param_sets, args={}):
    submitstr = """
universe = vanilla
executable = /home/fedro/bin/shim_dmtcp_rike
kill_sig = 2
    """
    prio = 0
    if args.has_key("prio"):
        prio = args["prio"]
    memstr = ""
    if args.has_key("mem"):
        memstr = "Request_memory = %i" % args["mem"]
    for dir_name, params in zip(dir_names, param_sets):
        submitstr += """
initialdir = %(dir_name)s
output = %(dir_name)s/condor_shimout
error = %(dir_name)s/condor_shimerr
log = %(dir_name)s/condor_log
priority = %(prio)i
dmtcp_args = --log %(dir_name)s/condor_shimlog --stdout %(dir_name)s/%(stdout_name)s --stderr %(dir_name)s/%(stderr_name)s
dmtcp_env = DMTCP_TMPDIR=./;JALIB_STDERR_PATH=/dev/null;DMTCP_PREFIX_ID=job.$(CLUSTER).$(PROCESS)
arguments = $(dmtcp_args) -- %(exe_name)s %(argstr)s
environment = $(dmtcp_env)
%(memstr)s 
queue
        """ % {"exe_name": exe_name, "dir_name": dir_name, "argstr": build_argstr(params), "prio": prio, 
                "memstr": memstr, "stdout_name": "stdout", "stderr_name": "stderr"}
    print submitstr
    if len(param_sets) > 0:
        cp = sp.Popen(["condor_submit"], stdin=sp.PIPE)
        cp.stdin.write(submitstr + "\n")
        cp.stdin.close()
        cp.communicate()

