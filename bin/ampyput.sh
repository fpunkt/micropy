#! /bin/sh

bindir=`dirname $0`

case "$OSTYPE" in
  solaris*) echo "SOLARIS" ;;
  darwin*)  lookfor='/dev/tty.usb*' ;;
  linux*)   lookfor='/dev/ttyUSB*' ;;
  bsd*)     echo "BSD" ;;
  msys*)    echo "WINDOWS" ;;
  cygwin*)  echo "ALSO WINDOWS" ;;
  *)        echo "unknown: $OSTYPE" ;;
esac

serial=`ls -1 $lookfor`

nusb=`echo $serial |wc -l`

if [ 1 -ne $nusb ]; then
    echo "** ERROR: cannot find USB device in $lookfor"
    exit 1
fi

echo "# Using $serial"

upload()
{
    cfile=`$bindir/mpycompile.sh $f`
    if [ $? -ne 0 ]; then
        exit
    fi

    echo "# uploading $cfile"
    ampy -p $serial put $cfile
}

for f in $*; do
    upload $f
done
