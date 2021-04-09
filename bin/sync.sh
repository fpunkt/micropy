#! /bin/bash

ip="192.168.179.15"

files=`find -L . -name '*.py' -newer .lastsync`

# echo "# syncing $files"

count=0

for f in $files; do
    echo "# $f"
    webrepl_cli.py -p x $f $ip: >/dev/null
    let "count++"
done

touch .lastsync
echo "# done syncing $count files"
