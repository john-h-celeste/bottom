#! /bin/bash

# send commands to the stress daemon

PIPE=/tmp/stressctl.fifo

if [[ ! -p "$PIPE" ]]; then
    echo "stress service is not currently running, exiting."
    exit 1
fi

if [[ $# -ne 1 ]]; then
    echo "Usage: bash $0 <command>"
    echo
    echo "Send a command to the stress daemon"
fi

{ echo $1 > "$PIPE"; exit 0; } &

sleep 5
echo "stress service is not currently running, exiting."
exit 1