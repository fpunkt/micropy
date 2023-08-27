#! /bin/sh

# - Download binary for micropython
# - Connect device to USB
#
# esptool.py --port /dev/tty.usbserial-22310 erase_flash
#
#
# esptool.py --port /dev/tty.usbserial-22310 --baud 460800 write_flash --flash_size=detect 0 esp8266-20210902-v1.17.bin
#
# esptool.py --port /dev/ttyUSB0 --baud 460800 write_flash --flash_size=detect 0 esp8266-20170108-v1.8.7.bin
# esptool.py --port /dev/tty.usbserial-213440  --baud 460800 --before=default_reset write_flash --flash_mode dio --flash_freq 40m --flash_size=detect 0 ~/Downloads/esp8266-20220618-v1.19.1.bin
#
# onetime
#
# sudo pip3 install adafruit-ampy

#
# on 1M devices asyncio is missing
#
# import upip
# upip.install("uasyncio")
#
#

# comiled file with password - must be in tools directory
pwname=c.mpy

if [ -f tools/$pwname ]; then
  tooldir=./tools
elif [ -f $pwname ]; then
  # running from tools directory
  tooldir=.
fi

pwfile=$tooldir/$pwname
libdir=$tooldir/../lib/
# libdir=`realpath $tooldir/../lib/`
# serial=/dev/tty.usbserial-22310

NC='\033[0m' # No Color

green() {
  echo "\033[0;32m$*${NC}" >&2
}

red() {
  echo "\033[0;31m$*${NC}" >&2
}

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
    red "** ERROR: cannot find USB device in $lookfor"
    exit 1
fi

green "# Using $serial"

#
# secrets file contains
#   wlan_ssid = 'sentinel'
#   wlan_password = 'xxxxx'
#   mqtt_server = '192.168.178.2'

upload()
{
    green "# uploading $1"
    ampy -p $serial put $1
}


echo "# compiling net.py"

builddir="$tooldir/.build"

net="$libdir/net.py"
bnet="$builddir/net.mpy"
rm -f $$bnet
mkdir -p $builddir

mpy-cross -o $bnet $net
if [ $? != 0 ]; then
  red "Cannot compile $net"
  exit 1
fi


upload $bnet
upload $pwfile
# upload $libdir/board.py
# ampy -p $serial put /usr/local/etc/secrets.py
# ampy -p $serial put $libdir/net.py
# ampy -p $serial put $libdir/board.py

green "# Network stuff copied to board. Now start a terminal (gterm or FLTerm on macOS, tio on linux) and run"
green "#"
echo "import net; net.net(32)"
green "#"
green "# After this you can use the bin/upload.sh script to upload all files needed for your project"
