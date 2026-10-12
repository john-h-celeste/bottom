#! /bin/bash

# api server
# read commands from nc
# one client can be connected at any time

if [ "$1" -eq sub ]; then
	while read line; do
        case $line in
            stats)
                cat /proc/stat
            ;;
            *)
                echo "command unrecognized"
            ;;
        esac
	done
	exit 0
fi

while true; do
	nc -l 9375 -e "$0 sub"
done