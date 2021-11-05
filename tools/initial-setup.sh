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
mydir=`dirname $0`
libdir=$mydir/../lib
echo $mydir $libdir
# serial=/dev/tty.usbserial-22310

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

#
# secrets file contains
#   wlan_ssid = 'sentinel'
#   wlan_password = 'xxxxx'
#   mqtt_server = '192.168.178.2'

upload()
{
    echo "# uploading $1"
    ampy -p $serial put $1
}

upload /usr/local/etc/secrets.py
upload $libdir/net.py
# upload $libdir/board.py
# ampy -p $serial put /usr/local/etc/secrets.py
# ampy -p $serial put $libdir/net.py
# ampy -p $serial put $libdir/board.py

echo "# Files copied to board. Now start a terminal (FLTerm on macOS, tio on linux) and run"
echo "#"
echo "import net"
echo "net."
