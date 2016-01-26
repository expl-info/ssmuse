#! /usr/bin/python
#! /tmp/jpython
#
# __ssmuse.py

import os
from os.path import basename, dirname, exists, isdir, realpath
from os.path import join as joinpath
import socket
import subprocess
import sys
import tempfile
import time

class CodeGenerator:

    def __init__(self):
        self.segs = []

    def __str__(self):
        return "".join(self.segs)

class CshCodeGenerator(CodeGenerator):
    """Code generator for csh-family of shells.
    """

    def __init__(self):
        CodeGenerator.__init__(self)

    def comment(self, s):
        self.segs.append("# %s\n" % (s,))

    def deduppath(self, name):
        self.segs.append("""
if ( $?%s == 1 ) then
    setenv %s "`%s/__ssmuse_cleanpath.ksh ${%s}`"
endif\n""" % (name, name, heredir, name))

    def echo2err(self, s):
        pass

    def echo2out(self, s):
        if verbose:
            self.segs.append("""echo "%s"\n""" % (s,))

    def execute(self, s):
        self.segs.append("%s\n" % (s,))

    def exportpath(self, name, val, fallback):
        self.segs.append("""
if ( $?%s == 0 ) then
    setenv %s "%s"
else
    if ( "${%s}" != "" ) then
        setenv %s "%s"
    else
        setenv %s "%s"
    endif
endif\n""" % (name, name, fallback, name, name, val, name, fallback))

    def exportvar(self, name, val):
        self.segs.append("""setenv %s "%s"\n""" % (name, val))

    def sourcefile(self, path):
        self.segs.append("""source "%s"\n""" % (path,))

    def unexportvar(self, name):
        self.segs.append("""unsetenv %s\n""" % (name,))

class ShCodeGenerator(CodeGenerator):
    """Code generator for sh-family of shells.
    """

    def __init__(self):
        CodeGenerator.__init__(self)

    def comment(self, s):
        self.segs.append("# %s\n" % (s,))

    def deduppath(self, name):
        self.segs.append("""
if [ -n "${%s}" ]; then
    export %s="$(%s/__ssmuse_cleanpath.ksh ${%s})"
fi\n""" % (name, name, heredir, name))

    def echo2out(self, s):
        if verbose:
            self.segs.append("""echo "%s"\n""" % (s,))

    def echo2err(self, s):
        if verbose:
            self.segs.append("""echo "%s" 1>&2\n""" % (s,))

    def execute(self, s):
        self.segs.append("%s\n" % (s,))

    def exportpath(self, name, val, fallback):
        self.segs.append("""
if [ -n "${%s}" ]; then
    export %s="%s"
else
    export %s="%s"
fi\n""" % (name, name, val, name, fallback))

    def exportvar(self, name, val):
        self.segs.append("""export %s="%s"\n""" % (name, val))

    def sourcefile(self, path):
        self.segs.append(""". "%s"\n""" % (path,))

    def unexportvar(self, name):
        self.segs.append("""unset %s\n""" % (name,))

##
##
##

def getplatforms():
    platforms = os.environ.get("SSMUSE_PLATFORMS")
    if platforms == None:
        if exists("/etc/ssm/platforms"):
            platforms = open("/etc/ssm/platforms").read()
        else:
            p = subprocess.Popen(joinpath(heredir, "__ssmuse_platforms.sh"), stdout=subprocess.PIPE)
            platforms, _ = p.communicate()
    return filter(None, platforms.split())

def isemptydir(path):
    if not isdir(path):
        return True
    l = os.listdir(path)
    return len(l) == 0

def islibfreedir(path):
    if not isdir(path):
        return True
    l = [name for name in os.listdir(path) if name.endswith(".a") or name.endswith(".so")]
    return len(l) == 0

def isnotemptydir(path):
    return not isemptydir(path)

def isnotlibfreedir(path):
    return not islibfreedir(path)

def printe(s):
    sys.stderr.write(s+"\n")

VARS_SETUPTABLE = [
    # envvars, basenames, XDIR envvar, testfn
    (["PATH"], ["/bin"], None, None),
    (["CPATH", "SSM_INCLUDE_PATH"], ["/include"], "SSMUSE_XINCDIRS", isnotemptydir),
    (["LIBPATH", "LD_LIBRARY_PATH"], ["/lib"], "SSMUSE_XLIBDIRS", isnotlibfreedir),
    (["MANPATH"], ["/man", "/share/man"], None, None),
    (["PYTHONPATH"], ["/lib/python"], None, None),
    (["TCL_LIBRARY"], ["/lib/tcl"], None, None),
]
VARS = [name for t in VARS_SETUPTABLE for name in t[0]]

##
##
##

def __exportpendpath(pend, name, path):
    """No checks.
    """
    if pend == "prepend":
        val = "%s:${%s}" % (path, name)
    elif pend == "append":
        val = "${%s}:%s" % (name, path)
    cg.exportpath(name, val, path)

def __exportpendmpaths(pend, name, paths):
    """No checks.
    """
    if paths:
        jpaths = ":".join(paths)
        if pend == "prepend":
            val = "%s:${%s}" % (jpaths, name)
        elif pend == "append":
            val = "${%s}:%s" % (name, jpaths)
        cg.exportpath(name, val, jpaths)

def augmentssmpath(path):
    if path.startswith("/") \
        or path.startswith("./") \
        or path.startswith("../*"):
        pass
    else:
        if "SSMUSE_DOMAIN_BASE" in os.environ:
            key = "SSMUSE_DOMAIN_BASE"
        elif "SSMUSE_BASE" in os.environ:
            key = "SSMUSE_BASE"
        else:
            key = "SSM_DOMAIN_BASE"
        path = joinpath(os.environ.get(key, ""), path)
    return path

def deduppaths():
    cg.echo2err("deduppaths:")
    for name in VARS:
        cg.deduppath(name)

def exportpendlibpath(pend, name, path):
    if isdir(path) and not islibfreedir(path):
        __exportpendpath(pend, name, path)

def exportpendmpaths(pend, name, paths):
    if pend == "prepend":
        paths = reversed(paths)
    for path in paths:
        exportpendpath(pend, name, path)

def exportpendpath(pend, name, path):
    if isdir(path) and not isemptydir(path):
        __exportpendpath(pend, name, path)

def exportpendpaths(pend, basepath):
    cg.echo2err("exportpendpaths: (%s) (%s)" % (pend, basepath))

    # table-driven
    for varnames, basenames, xdirsname, testfn in VARS_SETUPTABLE:
        if xdirsname:
            xdirnames = resolvepcvar(os.environ.get(xdirsname, "")).split(":")
            xdirnames = filter(None, xdirnames)
        else:
            xdirnames = []
        for basename in basenames:
            dirnames = [basename]+xdirnames
            paths = []
            for name in dirnames:
                if name.startswith("/"):
                    path = joinpath(basepath, name[1:])
                else:
                    path = joinpath(basepath, basename[1:], name)
                if testfn == None or testfn(path):
                    paths.append(path)
        for varname in varnames:
            __exportpendmpaths(pend, varname, paths)

def loaddomain(pend, dompath):
    dompath = augmentssmpath(dompath)

    if not isdir(dompath):
        printe("loaddomain: invalid domain (%s)" % (dompath,))
        sys.exit(1)

    cg.echo2err("loaddomain: (%s) (%s)" % (pend, dompath))

    # load from worse to better platforms
    for platform in revplatforms:
        platpath = joinpath(dompath, platform)
        if isdir(platpath):
            cg.echo2err("dompath: (%s) (%s) (%s)" % (pend, dompath, platform))
            exportpendpaths(pend, platpath)
            loadprofiles(dompath, platform)

def loadpackage(pend, pkgpath):
    pkgpath = augmentssmpath(pkgpath)

    pkgname = basename(pkgpath)
    t = pkgname.split("_")
    if len(t) == 2:
        pkgdir = dirname(pkgpath)
        # check better platforms first
        for platform in platforms:
            path = joinpath(pkgdir, pkgname+"_"+platform)
            if exists(path):
                pkgpath = path
                break
        else:
            printe("loadpackage: cannot find package (%s)" % (pkgpath,))
            sys.exit(1)

    cg.echo2err("loadpackage: (%s) (%s)" % (pend, pkgpath))

    if isdir(pkgpath):
        exportpendpaths(pend, pkgpath)
        path = joinpath(pkgpath, "etc/profile.d", pkgname+"."+shell)
        if exists(path):
            cg.sourcefile(path)

def loaddirectory(pend, dirpath):
    if isdir(dirpath):
        exportpendpaths(pend, dirpath)

def loadprofiles(dompath, platform):
    cg.echo2err("loadprofiles: (%s) (%s)" % (dompath, platform))

    root = joinpath(dompath, platform, "etc/profile.d")
    if exists(root):
        suff = ".%s" % (shell,)
        names = [name for name in os.listdir(root) if name.endswith(suff)]
        for name in names:
            path = joinpath(root, name)
            if exists(path):
                cg.sourcefile(path)

def resolvepcvar(s):
    """Resolve instances of %varname% in s as environment variables.
    """
    l = s.split("%")
    if len(l) % 2 != 1:
        return s
    l2 = [l[0]]
    for i in range(1, len(l), 2):
        v = os.environ.get(l[i], "%%%s%%" % l[i])
        l2.extend([v, l[i+1]])
    return "".join(l2)

HELP = """\
usage: ssmuse-sh [options]
       ssmuse-csh [options]

Load domains, packages, and generic/non-SSM directory tree. This
program should be sourced for the results to be incorporated into
the current shell.

Options:
-d|+d <dompath>
        Load domain.
-f|+f <dirpath>
        Load generic/non-SSM directory tree.
-h|--help
        Print help.
-p|+p <pkgpath>
        Load package.
--noeval
        Do not evaluate. Useful for debugging.

Use leading - (e.g., -d) to prepend new paths, leading + to append
new paths."""

if __name__ == "__main__":
    usetmp = False
    verbose = 0

    args = sys.argv[1:]

    if not args:
        printe("fatal: missing shell type")
        sys.exit(1)

    shell = args.pop(0)
    if shell == "sh":
        cg = ShCodeGenerator()
    elif shell == "csh":
        cg = CshCodeGenerator()
    else:
        printe("fatal: bad shell type")
        sys.exit(1)

    if args and args[0] in ["-h", "--help"]:
        print HELP
        sys.exit(0)

    if args and args[0] == "--tmp":
        args.pop(0)
        usetmp = True

    try:
        heredir = realpath(dirname(sys.argv[0]))

        platforms = getplatforms()
        revplatforms = platforms[::-1]

        cg.comment("host (%s)" % (socket.gethostname(),))
        cg.comment("date (%s)" % (time.asctime(),))
        cg.comment("platforms (%s)" % (" ".join(platforms),))

        while args:
            arg = args.pop(0)
            if arg in ["-d", "+d"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                dompath = args.pop(0)
                cg.exportvar("SSMUSE_PENDMODE", pend)
                loaddomain(pend, dompath)
            elif arg in ["-f", "+f"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                dirpath = args.pop(0)
                cg.unexportvar("SSMUSE_PENDMODE")
                loaddirectory(pend, dirpath)
            elif arg in ["-p", "+p"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                pkgpath = args.pop(0)
                cg.exportvar("SSMUSE_PENDMODE", pend)
                loadpackage(pend, pkgpath)
            elif arg == "--append":
                pend = "append"
                cg.echo2err("pendmode: append")
            elif arg == "--prepend":
                pend = "prepend"
                cg.echo2err("pendmode: prepend")
            elif arg == "-v":
                verbose = 1
            else:
                printe("fatal: unknown argument (%s)" % (arg,))
                sys.exit(1)
        cg.unexportvar("SSMUSE_PENDMODE")
        deduppaths()

        # prepare to write out (to stdout or tempfile)
        if not usetmp:
            sys.stdout.write(str(cg))
        else:
            try:
                fd, tmpname = tempfile.mkstemp(prefix="ssmuse", dir="/tmp")
                out = os.fdopen(fd, "w")

                # prefix code with self removal calls
                cg.comment("remove self/temp file")
                cg.execute("/bin/rm -f %s" % (tmpname,))
                cg.comment("")
                cg.segs = cg.segs[-3:]+cg.segs[:-3]
                out.write(str(cg))
                print "%s" % (tmpname,)
                out.close()
            except:
                import traceback
                traceback.print_exc()
                printe("fatal: could not create tmp file")
                sys.exit(1)

    except SystemExit:
        raise
    except:
        import traceback
        #traceback.print_exc()
        printe("abort: unrecoverable error")
