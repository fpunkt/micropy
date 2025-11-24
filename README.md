# HC clients in micropython (ESP32, including CAN bus)

## Compile and upload files

Install `net.mpy` and `c.mpy` by using `ampy` (adafruits). Once these are installed you can upload software and connnect to the repl via WebSocket.

### Main Appliation

Create an `app.py` and  and then use

- `mpycompile` compiles all requiremd files into the `.build` directory. The compile command parses the `app.py` (and all files?) in the current directory for dependencies and compiles all files that have changed. `mpycompile` automatically uploads all changed files to the board.

- `mpyterm` connects via websock and opens a terminal

## Connect to serial port terminal

- `mpremote` as terminal to a MP device connected to USB

## Standard tools for VS-CODE

- maybe: `micropico`
Uploading buffers kind of works, but the repl seems to use another namespace, so typing something into the repl doesn't work. Not clear where the uploaded stuff is stored (not in filesystem, not in modues, not visible in repl)

  - Keybinding `meta-R` to run the current buffer

### Initialize net library

See `tools/initial-setup.sh`

## Installing micropython

### pre built

    esptool erase-flash
    esptool --baud 460800 write-flash 0  ESP32_GENERIC_C3-20250911-v1.26.1.bin


### Install required packages for networking

    alias amp="ampy  -p /dev/cu.usbmodem3144301"
    amp put c.mpy
    amp put net.mpy

    mpremote
    # maybe hit CTRL-C to get the repl
    import net
    net.net(32)
    # CTRL-X to terminate mpremote


### Compile your own (with CAN support)

Install the EPS IDF

    brew install cmake ninja dfu-util ccache
    git clone -b v4.3.2 --recursive https://github.com/espressif/esp-idf.git
    cd esp_idf
    ./install.sh esp32
    mv ~/.espressif ../espressif

Compile micropython

    git clone --recursive git@github.com:fpunkt/micropython.git
    mv micropython micropython-fpunkt
    cd micropython-fpunkt
    git checkout develop
    git merge master

    git diff main/CMakeLists.txt
    diff --cc ports/esp32/main/CMakeLists.txt
    index 6760eff44,fccfd6b7c..000000000
    --- a/ports/esp32/main/CMakeLists.txt
    +++ b/ports/esp32/main/CMakeLists.txt
    @@@ -47,10 -62,10 +62,11 @@@ set(MICROPY_SOURCE_POR
          ${PROJECT_DIR}/machine_pin.c
          ${PROJECT_DIR}/machine_touchpad.c
          ${PROJECT_DIR}/machine_adc.c
    +     ${PROJECT_DIR}/machine_adcblock.c
    +     ${PROJECT_DIR}/machine_can.c
          ${PROJECT_DIR}/machine_dac.c
          ${PROJECT_DIR}/machine_i2c.c
    -     ${PROJECT_DIR}/machine_pwm.c
    +     ${PROJECT_DIR}/machine_i2s.c
          ${PROJECT_DIR}/machine_uart.c
          ${PROJECT_DIR}/modmachine.c
          ${PROJECT_DIR}/modnetwork.c

See `firmware/upload-firmware.sh`

## Obsolete stuff

Connect to USB and run

    gterm

Press `M-.` twice to quit the gterm

## Upload clients
