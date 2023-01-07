# HC clients in micropython (ESP32, including CAN bus)

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
