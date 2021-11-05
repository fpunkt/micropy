#
# Compile py files and upload changed ones
#
# Don't use, stick with the sync.sh script
#

lastsync=.lastsync

src_files := $(wildcard *.py)

compiled_files := $(src_files:%.py=%.mpy)

%.mpy : %.py
	mpy-cross $<

default:
	@echo "src: $(src_files)"
	@echo "obj: $(compiled_files)"

compile: $(compiled_files)

upload: compile $(lastsync)


