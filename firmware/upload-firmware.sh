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
# esptool.py esp32 -p /dev/ttyUSB0 -b 460800 --before=default_reset --after=hard_reset write_flash --flash_mode dio --flash_freq 40m --flash_size 4MB 0x1000 bootloader.bin 0x10000 micropython-can.bin.bin 0x8000 partition-table.bin

esptool.py --port $serial erase_flash

esptool.py  -p $serial -b 460800 --before=default_reset --after=hard_reset write_flash --flash_mode dio --flash_freq 40m --flash_size 4MB \
    0x1000 bootloader.bin \
    0x10000 micropython.bin \
    0x8000 partition-table.bin


echo "# Firmware updated, see tools/initial-setup.sh to start the network"