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
flashsize=4MB
#flashsize=detect
chip=esp32

ORANGE='\033[0;33m'
NC='\033[0m' # No Color

nusb=`echo $serial |wc -l`

red() {
  echo "\033[0;31m$*${NC}" >&2
}

green() {
  echo "\033[0;32m$*${NC}" >&2
}

findusb() {
  if [ 1 -ne $nusb ]; then
      red "** ERROR: cannot find USB device in $lookfor"
      exit 1
  fi
  green "# Using $serial"
}

erase_flash() {
  green "# Erasing flash"
  esptool.py --port $serial --chip $chip erase_flash
}


PARAMS=""
while (( "$#" )); do
  case "$1" in
    -e|--erase-only)
      findusb
      erase_flash
      exit 0
      ;;
    -f|--flash-size)
      if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
        flashsize=$2
        case "$flashsize" in
          4MB|detect)
          ;;
        *)
          echo "Error: Bad flash size for $1, must be 4MB or detect" >&2
        esac
        shift 2
      else
        echo "Error: Argument for $1 is missing" >&2
        exit 1
      fi
      ;;

    # -a|--my-boolean-flag)
    #   MY_FLAG=0
    #   shift
    #   ;;
    # -b|--my-flag-with-argument)
    #   if [ -n "$2" ] && [ ${2:0:1} != "-" ]; then
    #     MY_FLAG_ARG=$2
    #     shift 2
    #   else
    #     echo "Error: Argument for $1 is missing" >&2
    #     exit 1
    #   fi

    -*|--*=) # unsupported flags
      echo "Error: Unsupported flag $1" >&2
      echo "Use one of" >&2
      echo "  -e --erase-only    erase flash and exit" >&2
      exit 1
      ;;
    *) # preserve positional arguments
      PARAMS="$PARAMS $1"
      shift
      ;;
  esac
done
# set positional arguments in their proper place
eval set -- "$PARAMS"


# esptool.py esp32 -p /dev/ttyUSB0 -b 460800 --before=default_reset --after=hard_reset write_flash --flash_mode dio --flash_freq 40m --flash_size 4MB 0x1000 bootloader.bin 0x10000 micropython-can.bin.bin 0x8000 partition-table.bin

if [ -f firmware/bootloader.bin ]; then
  cd firmware
fi


findusb

erase_flash

green "# Flashing new firmware"

esptool.py  -p $serial -b 460800 \
    --before=default_reset --after=hard_reset \
    --chip $chip write_flash --flash_mode dio --flash_freq 40m \
    --flash_size $flashsize \
    0x1000 bootloader.bin \
    0x8000 partition-table.bin \
    0x10000 micropython.bin

green "# Firmware updated, see tools/initial-setup.sh to start the network"
