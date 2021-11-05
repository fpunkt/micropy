#! /bin/bash

# copy files via the webrepl interface

ipfile=".espip"

bindir=`dirname $0`

if [ ! -f "$ipfile" ]; then
    echo "ERROR: You don't have a '$ipfile' file."
    echo "Create one containing     192.168.178.XX    as single line and try again"
    exit 1
fi


for f in $*; do
    echo "# $f"
    if [ ! -f $f ]; then
        echo "FILE NOT FOUND ERROR: $f"
        continue
    fi
    $bindir/../webrepl/webrepl_cli.py -p x $f $ip: >/dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR transfering $f"
        exit 1
    fi
#    let "count++"
done

