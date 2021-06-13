#! /bin/bash

# sync files via the webrepl interface

ipfile=".espip"

if [ ! -f "$ipfile" ]; then
    echo "ERROR: You don't have a '$ipfile' file."
    echo "Create one containing     192.168.178.XX    as single line and try again"
    exit 1
fi

ip=`cat "$ipfile"`
if [ $? -ne 0 ]; then
    ip="192.168.179.15"
fi

if [ -f .lastsync ]; then
    files=`find -L . -name '*.py' -newer .lastsync`
else
    files=`ls -1 *.py`
fi
nfiles=`echo $files | wc -w`
echo "# syncing $nfiles files to $ip"

#count=0

# echo $files

for f in $files; do
    if [ "$f" = "./secrets.py" ]; then
        echo "# ignoring secrets"
        continue
    fi
    if [ "$f" = "secrets.py" ]; then
        echo "# ignoring secrets"
        continue
    fi
    echo "# $f"
    webrepl_cli.py -p x $f $ip: >/dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR transfering $f"
        exit 1
    fi
#    let "count++"
done

touch .lastsync
#echo "# done syncing $count files"
