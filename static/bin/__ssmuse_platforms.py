#! /bin/bash
#
# __ssmuse_platforms.sh
#
# Uniquely identify the current platform(s) as a
# combination of OS, OS (kernel) release/version,
# and architecture in accordance with the ssm
# platform specification: <OS><release>-<architecture>
#
# A machine may be compatible with one or more
# platforms, each of which are returned to the
# caller.

# GPL--start
# This file is part of ssm (Simple Software Manager)
# Copyright (C) 2005-2012 Environment/Environnement Canada
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# GPL--end

import os
import subprocess

uname = os.uname()

def get_plat_arch(plat_dist, plat_ver):
	plat_arch = "unk-unk"

	if uname.sysname == "AIX":
		p = subprocess.Popen("lsattr -El proc0 -a type", stdout=subprocess.PIPE)
		x, _ = p.communicate()
		x = x.split()[2]
		if x == "PowerPC_POWER7":
			plat_arch = "ppc7-64"
		elif x == "PowerPC_POWER5":
			plat_arch = "ppc-64"
		else:
			# 32 or 64?
			plat_arch = "ppc-32"
	elif uname.sysname in ["Linux", "FreeBSD", "CYGWIN_NT-5.1"]:
		if uname.machine in ["i386", "i486", "i586", "i686"]:
			plat_arch = "%s-32" % (uname.sysname,)
		elif uname.sysname in ["x86_64", "amd64"]:
			plat_arch="amd64-64"
	elif uname.sysname == "IRIX64":
		plat_arch = "mips-64"
	return plat_arch

def aix_platform():
	plat_dist = "aix"
	plat_ver = "%s.%s" % (uname.version, uname.release)
	plat_arch = get_plat_arch(plat_dist, plat_ver)
	return plat_arch

freebsd_platform() {
	plat_dist = "freebsd"
	plat_ver = uname.release.split("-")[0]
	plat_arch = get_plat_arch(plat_dist, plat_ver)
	return "%s-%s-%s" % (plat_dist, plat_ver, plat_arch)


def irix64_platform():
	pass

def linux_platform_lsb():
	plat_dist = ""
	plat_ver = ""
	for line in open("/etc/lsb-release"):
		if line.startswith("DISTRIB_ID"):
			plat_dist = line.split("=", 1)[1]
		elif line.startswith("DISTRIB_RELEASE"):
			plat_ver = line.split("=", 1)[1]

	lines = [line for line in open("/etc/lsb-release").read() \
		if line.startswith("DISTRIB_ID") or line.startswith("DISTRIB_RELEASE")]

	# faster than cat which also requires extra, useless case tests
	OIFS="${IFS}"; IFS="${NEWLINE}"
	lines=(`egrep 'DISTRIB_ID|DISTRIB_RELEASE' /etc/lsb-release`)
	IFS="${OIFS}"
	for line in "${lines[@]}"; do
		case "${line%=*}" in
		DISTRIB_ID)
			plat_dist=${line#*=}
			;;
		DISTRIB_RELEASE)
			plat_ver=${line#*=}
			#plat_ver=${plat_ver%*.*} # major and minor only
			;;
		esac
	done
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	
	echo "${plat_dist}-${plat_ver}-${plat_arch}" | tr '[A-Z]' '[a-z]'
}

linux_platform_debian() {
	local plat_dist plat_ver plat_arch

	plat_dist="debian"
	plat_ver=`cat /etc/debian_version`
	#plat_ver=${plat_ver%*.*} # major and minor only
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`

	echo "${plat_dist}-${plat_ver}-${plat_arch}" | tr '[A-Z]' '[a-z]'
}

# for RHEL and clones (centos, scientific linux, ...)
linux_platform_redhat() {
	local plat_dist plat_ver plat_arch line

        # pattern "* release <ver> *"
	line=`cat /etc/redhat-release`
	plat_dist="rhel"
	plat_ver=${line#*release }
	plat_ver=${plat_ver% *}
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`

	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

linux_platform_suse() {
	local plat_dist plat_ver plat_arch
	local line lines

	OIFS="${IFS}"; IFS="${NEWLINE}"
	lines=(`cat /etc/SuSE-release`)
	IFS="${OIFS}"
	if [ "${lines[0]#SUSE Linux Enterprise Server}" != "${lines[0]}" ]; then
		plat_dist="sles"
	elif [ "${lines[0]#SUSE Linux Enterprise Desktop}" != "${lines[0]}" ]; then
		plat_dist="sled"
	else
		plat_dist="suse-unk"
	fi
	plat_ver="${lines[1]#*= }"
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`

	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

linux_platform() {
	local platform

	if [ -e /etc/redhat-release ]; then
		platform=`linux_platform_redhat`
	elif [ -e /etc/SuSE-release ]; then
		platform=`linux_platform_suse`
	elif [ -e /etc/lsb-release ]; then
		platform=`linux_platform_lsb`
	elif [ -e /etc/debian_version ]; then
		# after /etc/lsb-release (for ubuntu)
		platform=`linux_platform_debian`
	else
		platform=""
	fi
	echo "${platform}"
}

irix_platform() {
	local plat_dist plat_ver plat_arch

	plat_dist="irix"
	case "${UNAME_R}" in
	6.5|6.5.*)
		plat_ver=6.5
		;;
	*)
		return
		;;
	esac
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

cygwin_platform() {
	local plat_dist plat_ver plat_arch

	plat_dist="cygwin"

	case "${UNAME_R}" in
	1.5|1.5.*)
		plat_ver=1.5
		;;
	*)
		return
		;;
	esac
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

# TODO: domain_home does not need to be passed (for local host only)
get_base_platform() {
	local platform platforms
	
	case ${UNAME_S} in
	AIX)
		platform=`aix_platform`
		;;
	FreeBSD)
		platform=`freebsd_platform`
		;;
	Linux)
		platform=`linux_platform`
		;;
	CYGWIN_NT-5.1)
		platform=`cygwin_platform`
		;;
	IRIX64)
		platform=`irix64_platform`
		;;
	*)
		platform=""
		;;
	esac

	echo "${platform}"
}

get_compatible_platforms() {
	local platform
	local comp_platforms platforms
	local filename line

	platform=$1

	platforms=""

	while [ "${platform}" != "" ]; do
		plat_dist=${platform%%-*}
		filename="${platforms_dir}/${plat_dist}/${platform}"

		if [ -r "${filename}" ]; then
			line=`cat "${filename}"`
			comp_platforms=${line%:*}
			platforms="${platforms} ${comp_platforms}"
			platform=${line#*:}
		else
			platform=""
		fi
	done
	platforms="${platforms} all multi"
	# allow leading blanks to drop
	echo ${platforms}
}

print_usage() {
	PROG_NAME=$(basename $0)
	echo "\
usage: ${PROG_NAME}

Determine the SSM platforms (primary and compatible) for the host."
}

#
# main
#

NEWLINE='
'

while [ $# -gt 0 ]; do
	case ${1} in
	-h|--help)
		print_usage
		exit 0
		;;
	*)
		echo "error: bad/missing argument" 1>&2
		exit 1
		;;
	esac
done

# must be run with #! or full path
heredir=$(readlink -f "$(dirname $0)")
platforms_dir="${heredir}/../etc/ssm.d/platforms"

UNAME_S=`uname -s`
UNAME_M=`uname -m`
UNAME_R=`uname -r`

platform=`get_base_platform`
get_compatible_platforms "${platform}"
