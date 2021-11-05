#! /bin/bash

# sync files via the webrepl interface

ipfile=".espip"
bindir=`dirname $0`

if [ ! -f "$ipfile" ]; then
    echo "ERROR: You don't have a '$ipfile' file."
    echo "Create one containing     192.168.178.XX    as single line and try again"
    exit 1
fi

ip=`cat "$ipfile"`
if [ $? -ne 0 ]; then
    ip="192.168.179.15"
    echo "No IP file ($ipfile) found"
    exit 1
fi

if [ -f .lastsync ]; then
    files=`find -L . -name '*.py' -newer .lastsync`
else
    files=`ls -1 *.py`
fi

# echo $# arguments
if [ "$#" -ne 0 ]; then
    files="$*"
fi


nfiles=`echo $files | wc -w`
echo "# syncing $nfiles files to $ip"

#count=0

# echo $files

for f in $files; do
    # echo "# file: $f"
    if [ "$f" = "./secrets.py" ]; then
        echo "# ignoring secrets"
        continue
    fi
    if [ "$f" = "secrets.py" ]; then
        echo "# ignoring secrets"
        continue
    fi
    if [ `basename $f` = "main.py" ]; then
        compiled=$f
    else
        mpy-cross $f
        #compiled=`basename $f .py`.mpy
        compiled=`echo $f| sed s/py$/mpy/`
    fi
    #echo $compiled
    if [ ! -f $compiled ]; then
        echo "# WARNING: cannot compile $f"
        compiled=$f
    fi
    echo "# $compiled"
    $bindir/../webrepl/webrepl_cli.py -p x $compiled $ip: >/dev/null
    if [ $? -ne 0 ]; then
        echo "ERROR transfering $compiled"
        exit 1
    fi
#    let "count++"
done

touch .lastsync
#echo "# done syncing $count files"
