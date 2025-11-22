# HC clients in micropython (ESP32, including CAN bus)

## Compile and upload files

Create an `app.py` and then use tools

- `mpycompile` compiles all requiremd files into the `.build` directory. The compile command parses the `app.py` (and all files?) in the current directory for dependencies and compiles all files that have changed.

- `mpyupload` checks the .build directory for new entries and uploads via the webex interface as needed. A potentially running

- `mpyterm` connects via websock and opens a terminal

## Standard tools for VS-CODE

- `micropico`
Uploading buffers kind of works, but the repl seems to use another namespace, so typing something into the repl doesn't work. Not clear where the uploaded stuff is stored (not in filesystem, not in modues, not visible in repl)

  - Keybinding `meta-R` to run the current buffer

- `mpremote` as terminal to a MP device connected to USB

## Connect to serial port terminal

Connect to USB and run

    gterm

Press `M-.` twice to quit the gterm

## Upload clients

### Initialize net library

See `tools/initial-setup.sh`

## Installing micropython

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
