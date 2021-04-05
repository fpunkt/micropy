*******
Network
*******

Connect via USB
################

.. code-block:: shell

    screen /dev/ttyUSB0 115200



Run ampy
#################

.. code-block:: shell

    conda activate ampy
    alias a='ampy -p /dev/ttyUSB0'

    a put myfile.py
    a run myfile.py
    a get boot.py


Install ampy
############

.. code-block:: shell

    frank@f3:~$ conda create -n ampy python=3.8
    conda activate ampy



Inquire IP
##########

Change subnetmask on linux

.. code-block:: shell

    sudo ifconfig eno2 192.168.178.3 netmask 255.255.0.0

Use GUI and run

.. code-block:: shell

    sudo systemctl restart NetworkManager.service


.. code-block:: python

    import network
    ap = network.WLAN(network.AP_IF)
    ap.ifconfig()
    # ('192.168.4.1', '255.255.255.0', '192.168.4.1', '0.0.0.0')
    ap.active(True)
    ap.config(essid='wID', authmode=network.AUTH_WPA_WPA2_PSK, password='espID..xx')
    print(ap.config('essid'))


Build with CAN support

.. code-block:: shell

    git clone --recursive https://github.com/espressif/esp-idf.git
    git checkout 310beae373446ceb9a4ad9b36b5428d7fdf2705f
    git submodule update --init --recursive


    conda create -n pyparse python=3.8
    conda activate pyparse
    python3 -m pip install pyparsing==2.3.1
    pip install pyserial


    export ESPIDF=~/NoBackup/00_external/esp-idf
    git clone https://github.com/nos86/micropython.git micropython-nos86-with-CAN
    cd micropython-nos86-with-CAN
    git checkout esp32-can-driver
    cd mpy-cross
    make
    cd ..
    cd ports/esp32
    git submodule update --init
    make

    esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
    esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 build-GENERIC/firmware.bin


You need to patch around

.. code-block:: diff

    index 56c806bd5..3622d1fd2 100644
    --- a/ports/esp32/machine_can.c
    +++ b/ports/esp32/machine_can.c
    @@ -267,7 +267,7 @@ STATIC mp_obj_t machine_hw_can_send(size_t n_args, const mp_obj_t *pos_args, mp_
            flags += CAN_MSG_FLAG_EXTD;
            id &= 0x1FFFFFFF;
        } else {
    -        id &= 0x1FF;
    +        id &= 0x7FF;
        }
        if (self->loopback) {
            flags += CAN_MSG_FLAG_SELF;
    @@ -298,7 +298,9 @@ STATIC mp_obj_t machine_hw_can_recv(size_t n_args, const mp_obj_t *pos_args, mp_
            ARG_timeout
        };
        static const mp_arg_t allowed_args[] = {
    -        { MP_QSTR_list, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE} },
    +//        { MP_QSTR_list, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE} },
    +        { MP_QSTR_list, MP_ARG_OBJ, {.u_rom_obj = MP_ROM_PTR(&mp_const_none_obj)} },
    +
            { MP_QSTR_timeout, MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 5000} },
        };



Precompiled binary doesn't work
================================

Don't fiddle around: load https://github.com/Tbruno25/pycom-esp32-universal

.. code-block:: shell

    pycom-fwtool-cli --port /dev/ttyUSB0 erase_all
    pycom-fwtool-cli -r --port /dev/ttyUSB0 flash --tar ESP32-4MB-1.20.2.rc11.tar.gz

