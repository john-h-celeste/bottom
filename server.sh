#! /bin/bash

set -ex

# api server
# read commands from nc
# only one client can be connected at any time

if [ "$1" == sub ]; then
	while read line; do
        case $line in
            stats)
                cat /proc/stat
            ;;
            load)
                cat /proc/loadavg
            ;;
            cpu)
                cat /proc/cpuinfo
            ;;
            meminfo)
                cat /proc/meminfo
            ;;
            lsblk)
                lsblk -Jlb -o NAME,KNAME,PATH,MAJ:MIN,FSAVAIL,FSSIZE,FSTYPE,FSUSED,FSROOTS,FSVER,MOUNTPOINT,MOUNTPOINTS,LABEL,UUID,PTUUID,PTTYPE,PARTTYPE,PARTTYPENAME,PARTLABEL,PARTUUID,PARTFLAGS,RO,MODEL,SERIAL,SIZE,STATE,OWNER,GROUP,MODE,TYPE,WWN,PKNAME,REV,VENDOR | jq '.blockdevices'
            ;;
            diskstats)
                cat /proc/diskstats
            ;;
            *)
                echo "command unrecognized"
            ;;
        esac
        echo END "$line"
	done
	exit 0
fi

while true; do
	nc -l 9375 --keep-open -e "$0 sub"
done