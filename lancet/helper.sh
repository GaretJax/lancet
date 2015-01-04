if [ -z "$LANCET_BIN" ]; then LANCET_BIN=$(which lancet); fi

function lancet_helper() {
    export LANCET_SHELL_HELPER=$(mktemp -u -t lancet_)
    $LANCET_BIN $@
    if [[ $? && -f $LANCET_SHELL_HELPER ]] ; then
        source $LANCET_SHELL_HELPER
    fi
    rm -f $LANCET_SHELL_HELPER
    unset LANCET_SHELL_HELPER
}

alias lancet=lancet_helper
