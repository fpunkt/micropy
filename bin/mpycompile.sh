#!/bin/bash

f=$1

# echo "# mpycompile $f" >&2

if [ x = x"$f" ]; then
    echo "# ERROR: mpycompile needs an argument" >&2
    exit 1
fi

ignore="secrets.py"
dontcompile="main.py"

for i in $ignore; do
    if [ "`basename $f`" = "$i" ]; then
        echo "# ignoring secrets" >&2
        exit 1
    fi
done

for i in $dontcompile; do
    if [ "`basename $f`" = "$i" ]; then
        echo $f
        exit 0
    fi
done

# check extension if already compiled
if [ "${f##*.}" = mpy ]; then
    echo $f
    exit 0
fi

mpy-cross $f
#compiled=`basename $f .py`.mpy
compiled=`echo $f| sed s/py$/mpy/`

if [ ! -f $compiled ]; then
    echo "# WARNING: cannot compile $f" >&2
    compiled=$f
fi

echo "$compiled"
