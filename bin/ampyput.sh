#! /bin/sh

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
    echo "# uploading $1"
    ampy -p $serial put $1
}

for f in $*; do
    upload $f
done
