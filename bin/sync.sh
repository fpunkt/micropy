#! /bin/bash

ip=`cat .espip`
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
