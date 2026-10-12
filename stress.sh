#! /bin/bash

# stress daemon service - recieves commands from stressctl.sh via named pipe 

PIPE=/tmp/stressctl.fifo

if [[ ! -p "$PIPE" ]]; then
    mkfifo "$PIPE"
fi

while true; do
    if read line < "$PIPE"; then
        echo 'recieved command:' "$line"
        case $line in
            cpu)
                stress-ng --cpu 8 --timeout 30
            ;;
            *)
                echo "command unrecognized"
            ;;
        esac
    fi
done