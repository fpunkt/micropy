# Compile library files

LIBFILES=board.py boot.py button.py can.py cancodes.py cancommon.py canconf.py canerror.py canesp32.py canid.py caninfo.py canoverlan.py canstub.py config_beta1.py irqio.py motionsensor.py net.py pwm.py pwmcode.py relais.py sensors.py

COMPILED=$(LIBFILES:.py=.mpy)

default: $(COMPILED)

.SUFFIXES: .py .mpy

.py.mpy:
	mpy-cross $<

