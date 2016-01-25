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

out = sys.stdout

##
## csh support
##

def csh_comment(s):
    out.write("# %s\n" % (s,))

def csh_deduppath(name):
    out.write("""
if ( $?%s == 1 ) then
    setenv %s "`%s/__ssmuse_cleanpath.ksh ${%s}`"
endif\n""" % (name, name, heredir, name))

def csh_echo2err(s):
    pass

def csh_echo2out(s):
    if version:
        out.write("""echo "%s"\n""" % (s,))

def csh_execute(s):
    out.write("%s\n" % (s,))

def csh_exportpath(name, val, fallback):
    out.write("""
if ( $?%s == 0 ) then
    setenv %s "%s"
else
    if ( "${%s}" != "" ) then
        setenv %s "%s"
    else
        setenv %s "%s"
    endif
endif\n""" % (name, name, fallback, name, name, val, name, fallback))

def csh_exportvar(name, val):
    out.write("""setenv %s "%s"\n""" % (name, val))

def csh_sourcefile(path):
    out.write("""source "%s"\n""" % (path,))

def csh_unexportvar(name):
    out.write("""unsetenv %s\n""" % (name,))

##
## sh support
##

def sh_comment(s):
    out.write("# %s\n" % (s,))

def sh_deduppath(name):
    out.write("""
if [ -n "${%s}" ]; then
    export %s="$(%s/__ssmuse_cleanpath.ksh ${%s})"
fi\n""" % (name, name, heredir, name))

def sh_echo2out(s):
    if verbose:
        out.write("""echo "%s"\n""" % (s,))

def sh_echo2err(s):
    if verbose:
        out.write("""echo "%s" 1>&2\n""" % (s,))

def sh_execute(s):
    out.write("%s\n" % (s,))

def sh_exportpath(name, val, fallback):
    out.write("""
if [ -n "${%s}" ]; then
    export %s="%s"
else
    export %s="%s"
fi\n""" % (name, name, val, name, fallback))

def sh_exportvar(name, val):
    out.write("""export %s="%s"\n""" % (name, val))

def sh_sourcefile(path):
    out.write(""". "%s"\n""" % (path,))

def sh_unexportvar(name):
    out.write("""unset %s\n""" % (name,))

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

def printe(s):
    sys.stderr.write(s+"\n")

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
    exportpath(name, val, path)

def __exportpendmpaths(pend, name, paths):
    """No checks.
    """
    if pend == "prepend":
        paths = reversed(paths)
    for path in paths:
        __exportpendpath(pend, name, path)

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
    echo2err("deduppaths:")
    for name in ["PATH", "CPATH", "LIBPATH", "LD_LIBRARY_PATH", "MANPATH", "PYTHONPATH", "TCL_LIBRARY"]:
        deduppath(name)

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
    echo2err("exportpendpaths: (%s) (%s)" % (pend, basepath))

    exportpendpath(pend, "PATH", joinpath(basepath, "bin"))

    # special handling for include
    ssmuse_incdirs = resolvepcvar(os.environ.get("SSMUSE_INCDIRS", "")).split(":")
    ssmuse_incdirs = ["/include"]+filter(None, ssmuse_incdirs)
    paths = []
    for name in ssmuse_incdirs:
        if name.startswith("/"):
            path = joinpath(basepath, name[1:])
        else:
            path = joinpath(basepath, "include", name)
        paths.append(path)
    exportpendmpaths(pend, "CPATH", paths)
    exportpendmpaths(pend, "SSM_INCLUDE_PATH", paths)

    # special handling for lib
    ssmuse_libdirs = resolvepcvar(os.environ.get("SSMUSE_LIBDIRS", "")).split(":")
    ssmuse_libdirs = ["/lib"]+filter(None, ssmuse_libdirs)
    paths = []
    for name in ssmuse_libdirs:
        if name.startswith("/"):
            path = joinpath(basepath, name[1:])
        else:
            path = joinpath(basepath, "lib", name)
        if not islibfreedir(path):
            paths.append(path)
    __exportpendmpaths(pend, "LIBPATH", paths)
    __exportpendmpaths(pend, "LD_LIBRARY_PATH", paths)

    #if os.environ.get("COMP_ARCH"):
        #comparch = os.environ.get("COMP_ARCH")
        #exportpendlibpath(pend, "LIBPATH", joinpath(basepath, "lib", comparch))
        #exportpendlibpath(pend, "LD_LIBRARY_PATH", joinpath(basepath, "lib", comparch))

    exportpendpath(pend, "MANPATH", joinpath(basepath, "man"))
    exportpendpath(pend, "MANPATH", joinpath(basepath, "share/man"))
    exportpendpath(pend, "PYTHONPATH", joinpath(basepath, "lib/python"))
    exportpendpath(pend, "TCL_LIBRARY", joinpath(basepath, "lib/tcl"))

def loaddomain(pend, dompath):
    dompath = augmentssmpath(dompath)

    if not isdir(dompath):
        printe("loaddomain: invalid domain (%s)" % (dompath,))
        exit(1)

    echo2err("loaddomain: (%s) (%s)" % (pend, dompath))

    # load from worse to better platforms
    for platform in revplatforms:
        platpath = joinpath(dompath, platform)
        if isdir(platpath):
            echo2err("dompath: (%s) (%s) (%s)" % (pend, dompath, platform))
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
            exit(1)

    echo2err("loadpackage: (%s) (%s)" % (pend, pkgpath))

    if isdir(pkgpath):
        exportpendpaths(pend, pkgpath)
        path = joinpath(pkgpath, "etc/profile.d", pkgname+"."+shell)
        if exists(path):
            sourcefile(path)

def loaddirectory(pend, dirpath):
    if isdir(dirpath):
        exportpendpaths(pend, dirpath)

def loadprofiles(dompath, platform):
    echo2err("loadprofiles: (%s) (%s)" % (dompath, platform))

    root = joinpath(dompath, platform, "etc/profile.d")
    if exists(root):
        suff = ".%s" % (shell,)
        names = [name for name in os.listdir(root) if name.endswith(suff)]
        for name in names:
            path = joinpath(root, name)
            if exists(path):
                sourcefile(path)

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
    tmpname = None
    verbose = 0

    args = sys.argv[1:]

    if not args:
        printe("fatal: missing shell type")
        exit(1)

    shell = args.pop(0)
    if shell == "sh":
        comment = sh_comment
        deduppath = sh_deduppath
        echo2err = sh_echo2err
        echo2out = sh_echo2out
        execute = sh_execute
        exportvar = sh_exportvar
        exportpath = sh_exportpath
        sourcefile = sh_sourcefile
        unexportvar = sh_unexportvar
    elif shell == "csh":
        comment = csh_comment
        deduppath = csh_deduppath
        echo2err = csh_echo2err
        echo2out = csh_echo2out
        execute = csh_execute
        exportvar = csh_exportvar
        exportpath = csh_exportpath
        sourcefile = csh_sourcefile
        unexportvar = csh_unexportvar
    else:
        printe("fatal: bad shell type")
        exit(1)

    if args and args[0] in ["-h", "--help"]:
        print HELP
        exit(0)

    if args and args[0] == "--tmp":
        args.pop(0)
        try:
            fd, tmpname = tempfile.mkstemp(prefix="ssmuse", dir="/tmp")
            out = os.fdopen(fd, "w")
            comment("remove self/temp file")
            execute("/bin/rm -f %s" % (tmpname,))
            comment("")
        except:
            import traceback
            traceback.print_exc()
            printe("fatal: could not create tmp file")
            exit(1)

    try:
        heredir = realpath(dirname(sys.argv[0]))

        platforms = getplatforms()
        revplatforms = platforms[::-1]

        comment("host (%s)" % (socket.gethostname(),))
        comment("date (%s)" % (time.asctime(),))
        comment("platforms (%s)" % (" ".join(platforms),))

        while args:
            arg = args.pop(0)
            if arg in ["-d", "+d"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                dompath = args.pop(0)
                exportvar("SSMUSE_PENDMODE", pend)
                loaddomain(pend, dompath)
            elif arg in ["-f", "+f"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                dirpath = args.pop(0)
                unexportvar("SSMUSE_PENDMODE")
                loaddirectory(pend, dirpath)
            elif arg in ["-p", "+p"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                pkgpath = args.pop(0)
                exportvar("SSMUSE_PENDMODE", pend)
                loadpackage(pend, pkgpath)
            elif arg == "--append":
                pend = "append"
                echo2err("pendmode: append")
            elif arg == "--prepend":
                pend = "prepend"
                echo2err("pendmode: prepend")
            elif arg == "-v":
                verbose = 1
            else:
                printe("fatal: unknown argument (%s)" % (arg,))
                exit(1)
        unexportvar("SSMUSE_PENDMODE")
        deduppaths()

        if tmpname:
            print "%s" % (tmpname,)
    except:
        import traceback
        #traceback.print_exc()
        printe("abort: unrecoverable error")
        if tmpname:
            os.remove(tmpname)
