#! /bin/bash
#
# ssmuse_platforms.sh
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

get_major_minor() {
	local a b c

	a=$1
	b="${a#*.}"
	a="${a%%.*}"
	c="${b#*.}"
	if [ "${a}" == "${b}" ]; then
		echo "${a}"
	else
		b="${b%%.*}"
		echo "${a}.${b}"
	fi
}

get_plat_arch() {
	local plat_dist plat_ver plat_arch

	plat_dist=$1
	plat_ver=$2

	case "${UNAME_S}" in
	AIX)
		# warning: the following should have been power5- and power7-
		case "`lsattr -El proc0 -a type | cut -f2 -d' '`" in
		PowerPC_POWER7)
			plat_arch="ppc7-64"
			;;
		PowerPC_POWER5)
			plat_arch="ppc-64"
			;;
		*)
			# 32 or 64?
			plat_arch="ppc-32"
			;;
		esac
		;;
	Linux|FreeBSD|CYGWIN_NT-5.1)
		case "${UNAME_M}" in
		i[3456]86)
			plat_arch="${UNAME_M}-32"
			;;
		x86_64|amd64)
			plat_arch="amd64-64"
			;;
		ppc|ppc64|power*)
			plat_arch=$(get_power_plat_arch)
			;;
		*)
			plat_arch="unk-unk"
			;;
		esac
		;;
	IRIX64)
		plat_arch=mips-64
		;;
	*)
		plat_arch="unk-unk"
		;;
	esac
	echo "${plat_arch}"
}

get_power_plat_arch() {
	case "${UNAME_S}" in
	Linux)
		arch=$(grep -m 1 cpu /proc/cpuinfo | awk '{print tolower($3)}')
		case "${UNAME_M}" in
		ppc)
			objmode=32
			;;
		*)
			objmode=64
			;;
		esac
		plat_arch="${arch}-${objmode}"
		;;
	*)
		plat_arch="unk-unk"
		;;
	esac
	echo "${plat_arch}"
}

aix_platform() {
	local plat_dist plat_ver plat_arch

	plat_dist="aix"
	plat_ver="`uname -v`.`uname -r`"
	plat_ver=$(get_major_minor "${plat_ver}")
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

freebsd_platform() {
	local plat_dist plat_ver plat_arch

	plat_dist="freebsd"
	plat_ver="`uname -r`"
	plat_ver=${plat_ver%%-*}
	plat_ver=$(get_major_minor "${plat_ver}")
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	echo "${plat_dist}-${plat_ver}-${plat_arch}"
}

irix64_platform() {
	:
}

linux_platform_lsb() {
	local plat_dist plat_ver plat_arch
	local line lines

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
			;;
		esac
	done
	plat_ver=$(get_major_minor "${plat_ver}")
	plat_arch=`get_plat_arch ${plat_dist} ${plat_ver}`
	
	echo "${plat_dist}-${plat_ver}-${plat_arch}" | tr '[A-Z]' '[a-z]'
}

linux_platform_debian() {
	local plat_dist plat_ver plat_arch

	plat_dist="debian"
	plat_ver=`cat /etc/debian_version`
	plat_ver=$(get_major_minor "${plat_ver}")
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
	plat_ver="${plat_ver% *}"
	plat_ver=$(get_major_minor "${plat_ver}")
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
	plat_ver=$(get_major_minor "${plat_ver}")
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
usage: ${PROG_NAME} [<primary_platform>]

Determine the SSM platforms (primary and compatible) for the host.
If <primay_platform> is given, then use it instead of automatically
sensing it from the host."
}

#
# main
#

NEWLINE='
'

if [ $# -eq 1 ]; then
	case ${1} in
	-h|--help)
		print_usage
		exit 0
		;;
	-*)
		echo "error: bad/missing argument" 1>&2
		exit 1
		;;
	*)
		platform=$1; shift 1
		;;
	esac
elif [ $# -gt 1 ]; then
	echo "error: bad/missing argument" 1>&2
	exit 1
fi

# must be run with #! or full path
herefile=$(readlink -f "$0")
heredir=$(dirname "${herefile}")
platforms_dir=$(readlink -f "${heredir}/../../etc/ssmuse/platforms")

if [ -z "${platform}" ]; then
	UNAME_S=`uname -s`
	UNAME_M=`uname -m`
	UNAME_R=`uname -r`

	platform=`get_base_platform`
fi

get_compatible_platforms "${platform}"
