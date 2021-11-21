# source this file for convenient aliases

mp=$HOME/Projects/fpunkts/micropy

if [ ! -f $mp/tools/alias.sh ]; then
    echo "Cannot find installation directory in $mp"
    exit 1
fi

alias sync=$mp/bin/sync.sh
alias ampyput=$mp/bin/ampyput.sh

PS1="(mpy) \u\$ "
echo "# Aliases set up"
echo "# run sync [files]       to copy files over wlan"
echo "# run ampyput file       to copy files over USB"