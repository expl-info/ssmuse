#! /usr/bin/env python
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
    setenv %s "`%s/ssmuse_cleanpath ${%s}`"
endif\n""" % (name, name, heredir, name))

    def echo2err(self, s):
        pass

    def echo2out(self, s):
        if verbose:
            self.segs.append("""echo "[%s] %s"\n""" % (selfpid, s))

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

    def ssmuseonchangeddeps(self, args):
        if args:
            names = ["${%s}" % name for name in depnames]
            values = [os.environ.get(name, "") for name in depnames]
            quotedargs = ["'%s'" % arg for arg in args]
            self.segs.append("""
if ( "%s" != '%s' ) then
    source %s %s %s
    return
fi
""" % ("::".join(names), "::".join(values), "ssmuse-sh", verbose and "-v" or "", " ".join(quotedargs)))

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
    export %s="$(%s/ssmuse_cleanpath ${%s})"
fi\n""" % (name, name, heredir, name))

    def echo2out(self, s):
        if verbose:
            self.segs.append("""echo "[%s] %s"\n""" % (selfpid, s))

    def echo2err(self, s):
        if verbose:
            self.segs.append("""echo "[%s] %s" 1>&2\n""" % (selfpid, s))

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

    def ssmuseonchangeddeps(self, args):
        if args:
            names = ["${%s}" % name for name in depnames]
            values = [os.environ.get(name, "") for name in depnames]
            quotedargs = ["'%s'" % arg for arg in args]
            self.segs.append("""
if [ "%s" != '%s' ]; then
    . %s %s %s
    return
fi
""" % ("::".join(names), "::".join(values), "ssmuse-sh", verbose and "-v" or "", " ".join(quotedargs)))

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
            p = subprocess.Popen(joinpath(heredir, "ssmuse_platforms"), stdout=subprocess.PIPE)
            platforms, _ = p.communicate()
    return filter(None, platforms.split())

def is_dompath(path):
    return isdir(joinpath(path, "etc/ssm.d"))

def is_pkgpath(path):
    return exists(joinpath(path, ".ssm.d/control"))

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
    (["CPATH", "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "OBJC_INCLUDE_PATH", "SSM_INCLUDE_PATH"], ["/include"], "SSMUSE_XINCDIRS", isnotemptydir),
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

def augmentssmpath(pathtype, path):
    if path.startswith("/") \
        or path.startswith("./") \
        or path.startswith("../"):
        paths = [path]
    else:
        if "SSMUSE_PATH" in os.environ:
            basedirs = os.environ["SSMUSE_PATH"].split(":")
        elif "SSMUSE_BASE" in os.environ:
            basedirs = [os.environ["SSMUSE_BASE"]]
        elif "SSM_DOMAIN_BASE" in os.environ:
            basedirs = [os.environ["SSM_DOMAIN_BASE"]]
        else:
            basedirs = []
        paths = [os.path.join(basedir, path) for basedir in basedirs]

    for path in paths:
        path = realpath(path)
        if pathtype == None:
            pkgpath = matchpkgpath(path)
            if pkgpath != None:
                pathtype = "package"
            elif is_dompath(path):
                pathtype = "domain"
            elif isdir(path):
                pathtype = "directory"
            else:
                path = None
        elif pathtype == "domain" and not is_dompath(path):
            path = None
        elif pathtype == "package":
            pkgpath = matchpkgpath(path)
            if pkgpath != None:
                path = pkgpath
            else:
                path = None
        elif not exists(path):
            path = None

        if path != None:
            break
    return pathtype, path

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

def getdepnames():
    depnames = []
    for _, _, xdirsname, _ in VARS_SETUPTABLE:
        if xdirsname:
            depnames.append(xdirsname)
            for name in xdirsname.split(":"):
                path = os.environ.get(name)
                if path:
                    l = path.split("%")
                    if len(l) % 2 == 1:
                        names = l[1::2]
                        depnames.extend(names)
    return set(depnames)

def matchpkgpath(pkgpath):
    pkgname = basename(pkgpath)
    t = pkgname.split("_")
    if len(t) == 2:
        pkgdir = dirname(pkgpath)
        # check better platforms first
        for platform in platforms:
            path = joinpath(pkgdir, pkgname+"_"+platform)
            if is_pkgpath(path):
                return path
    elif is_pkgpath(pkgpath):
        return pkgpath
    return None

def loaddomain(pend, dompath):
    _dompath = dompath

    if dompath == None or not isdir(dompath):
        printe("loaddomain: invalid domain (%s)" % (dompath,))
        sys.exit(1)

    cg.echo2err("loaddomain: (%s) (%s)" % (pend, dompath))

    # load from worse to better platforms
    loadedplatforms = []
    for platform in revplatforms:
        platpath = joinpath(dompath, platform)
        if isdir(platpath):
            cg.echo2err("dompath: (%s) (%s) (%s)" % (pend, dompath, platform))
            exportpendpaths(pend, platpath)
            loadprofiles(dompath, platform)
            loadedplatforms.append(platform)
    if logger:
        log(dompath, "%s|loaddomain|%s|%s|%s|%s|%s|%s|%s|%s|%s" \
            % (nowst, os.environ.get("LOGNAME"), hostname, platform0,
                len(loadedplatforms), " ".join(loadedplatforms),
                shell, pend, _dompath, dompath))

def loadpackage(pend, pkgpath):
    _pkgpath = pkgpath

    if pkgpath == None or not isdir(pkgpath):
        printe("loadpackage: invalid package (%s)" % (pkgpath,))
        sys.exit(1)

    cg.echo2err("loadpackage: (%s) (%s)" % (pend, pkgpath))

    pkgname = os.path.basename(pkgpath)
    exportpendpaths(pend, pkgpath)
    path = joinpath(pkgpath, "etc/profile.d", pkgname+"."+shell)
    if exists(path):
        cg.sourcefile(path)
    if logger:
        log(pkgpath, "%s|loadpackage|%s|%s|%s|%s|%s|%s|%s" \
            % (nowst, os.environ.get("LOGNAME"), hostname,
                platform0, shell, pend, _pkgpath, pkgpath))

def loaddirectory(pend, dirpath):
    _dirpath = dirpath

    if dirpath == None or not isdir(dirpath):
        printe("loaddirectory: invalid directory (%s)" % (dirpath,))
        sys.exit(1)

    exportpendpaths(pend, dirpath)
    if logger:
        log(dirpath, "%s|loaddirectory|%s|%s|%s|%s|%s|%s|%s" \
            % (nowst, os.environ.get("LOGNAME"), hostname,
                platform0, shell, pend, _dirpath, dirpath))

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

def log(path, message):
    if logger:
        if logpathprefixes:
            for pref in logpathprefixes:
                if path.startswith(pref):
                    break
            else:
                return
        logger.info(message)

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

def setuplogger():
    global logger, logpathprefixes

    # set up optional logger
    if "SSMUSE_LOG" in os.environ:
        try:
            import logging

            logmethod, rest = os.environ["SSMUSE_LOG"].split(":", 1)
            if logmethod == "file":
                path = os.path.expanduser("~/.ssmuse/log")
                lh = logging.FileHandler(path)
            elif logmethod == "syslog":
                import logging.handlers
                lh = logging.handlers.SysLogHandler()
            elif logmethod == "russlog":
                import logging
                sys.path.insert(0, "/usr/lib/python")
                import pyruss

                class RusslogHandler(logging.Handler):
                    """
                    """
                    def __init__(self, spath):
                        logging.Handler.__init__(self)
                        self.spath = spath
                        self.addspath = "%s/add" % (spath,)

                    def emit(self, record):
                        message = self.format(record)
                        rv, ev = pyruss.dialv_wait(pyruss.to_deadline(1000), "execute", self.addspath, args=[message])

                spath = rest
                lh = RusslogHandler(spath)
            else:
                raise Exception()
            logger = logging.getLogger("ssmuse")
            logger.setLevel(logging.INFO)
            lh.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(lh)

            if "SSMUSE_LOG_FILTER" in os.environ:
                logpathprefixes = map(realpath, os.environ["SSMUSE_LOG_FILTER"].split(":"))
        except:
            sys.stderr.write("warning: no logging\n")
            #import traceback
            #traceback.print_exc()
            logger = None

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
    hostname = socket.gethostname()
    logger = None
    logpathprefixes = []
    nowst = time.strftime("%Y/%m/%dT%H:%M:%S", time.gmtime())
    platform0 = None
    selfpid = os.getpid()
    usetmp = False
    verbose = os.environ.get("SSMUSE_VERBOSE")

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

    setuplogger()

    try:
        heredir = realpath(dirname(sys.argv[0]))

        platforms = getplatforms()
        platform0 = platforms and platforms[0] or None
        revplatforms = platforms[::-1]

        depnames = getdepnames()

        cg.comment("host (%s)" % (socket.gethostname(),))
        cg.comment("date (%s)" % (time.asctime(),))
        cg.comment("platforms (%s)" % (" ".join(platforms),))
        cg.comment("depnames (%s)" % (" ".join(depnames),))
        for name in ["SSMUSE_BASE", "SSMUSE_LOG", "SSMUSE_PATH",
            "SSMUSE_PLATFORMS", "SSMUSE_XINCDIRS", "SSMUSE_XLIBDIRS"]:
            value = os.environ.get(name, "-").replace("\n\t", "  ")
            cg.comment("env (%s) (%s)" % (name, value))

        while args:
            arg = args.pop(0)
            if arg in ["-d", "+d"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                _dompath = args.pop(0)
                cg.exportvar("SSMUSE_PENDMODE", pend)
                _, dompath = augmentssmpath("domain", _dompath)
                loaddomain(pend, dompath)
                cg.ssmuseonchangeddeps(args)
            elif arg in ["-f", "+f"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                _dirpath = args.pop(0)
                cg.unexportvar("SSMUSE_PENDMODE")
                _, dirpath = augmentssmpath("directory", _dirpath)
                loaddirectory(pend, dirpath)
            elif arg in ["-p", "+p"] and args:
                pend = arg[0] == "-" and "prepend" or "append"
                _pkgpath = args.pop(0)
                cg.exportvar("SSMUSE_PENDMODE", pend)
                _, pkgpath = augmentssmpath("package", _pkgpath)
                loadpackage(pend, pkgpath)
                cg.ssmuseonchangeddeps(args)
            elif arg in ["-x", "+x"] and args:
                _xpath = args.pop(0)
                pathtype, xpath = augmentssmpath(None, _xpath)
                if pathtype == "directory":
                    args = [arg[0]+"f", _xpath]+args
                elif pathtype == "domain":
                    args = [arg[0]+"d", _xpath]+args
                elif pathtype == "package":
                    args = [arg[0]+"p", _xpath]+args
            elif arg == "--append":
                pend = "append"
                cg.echo2err("pendmode: append")
            elif arg == "--prepend":
                pend = "prepend"
                cg.echo2err("pendmode: prepend")
            elif arg == "-v":
                verbose = True
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
                #import traceback
                #traceback.print_exc()
                printe("fatal: could not create tmp file")
                sys.exit(1)

    except SystemExit:
        raise
    except:
        #import traceback
        #traceback.print_exc()
        printe("abort: unrecoverable error")
