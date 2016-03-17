#! /bin/ksh93
#
# ssmuse_cleanpath.ksh

if [ -z "${KSH_VERSION}" ]; then
	echo "$1"
	exit 0
fi

typeset -A arr
typeset -a res
IFS=":"
for a in $1; do
	if [ -z "${arr[x$a]}" ]; then
		arr["x$a"]=1
		res+=("$a")
	fi
done
if [ "${1%%*:}" != "$1" -a "${arr[x]}" != "1" ]; then
	res+=("")
fi
echo "${res[*]}"
