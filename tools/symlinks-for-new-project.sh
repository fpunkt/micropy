#! /bin/sh

relpath=../../../lib

files="board.py boot.py button.py can.py canconf.py canerror.py canid.py irqio.py motionsensor.py net.py pwm.py pwmcode.py sensors.py fsmqtt.py"

for file in $files; do
    f=$relpath/$file
    if [ ! -f $f ]; then
        echo "Error: file not found: $f"
        exit 1
    fi
    if [ -f $file ]; then
        echo "# Warning: File already exists in folder, ignoring: $file"
    fi
done


for file in $files; do
    if [ ! -f $file ]; then
        ln -s $relpath/$file .
    fi
done


