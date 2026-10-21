#! /bin/bash

# stress daemon service - recieves commands from stressctl.sh via named pipe

set -ex

PIPE=/tmp/stressctl.fifo

if [[ ! -p "$PIPE" ]]; then
    mkfifo "$PIPE"
fi

while true; do
    read line < "$PIPE" || true
    echo 'recieved command:' "$line"
    case $line in
        cpu)
            stress-ng --cpu 8 --timeout 60
        ;;
        mmap)
            stress-ng --vm 128 --timeout 60
        ;;
        disk)
            stress-ng --hdd 4 --timeout 60
        ;;
        net)
            stress-ng --sock 4 --timeout 60
        ;;
        *)
            echo "command unrecognized"
        ;;
    esac
done