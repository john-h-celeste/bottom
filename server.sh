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
            mountinfo)
                cat /proc/self/mountinfo
            ;;
            partitions)
                cat /proc/partitions
            ;;
            diskstats)
                cat /proc/diskstats
            ;;
            mounts)
                cat /proc/self/mounts
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