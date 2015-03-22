#compdef lancet

_lancet_commands() {
    local -a commands
    local -a opts
    opts=(
        "${(@f)$(lancet _arguments)}"
    )
    commands=(
        "${(@f)$(lancet _commands)}"
    )
    _arguments $opts '*:: :->subcmds' && ret=0
    _describe -t commands 'lancet command' commands && ret=0
}

_lancet() {
    local curcontext=$curcontext ret=1

    if ((CURRENT == 2)); then
        _lancet_commands
    else
        shift words
        ((CURRENT --))
        curcontext="${curcontext%:*:*}:lancet-$words[1]:"
        _arguments -s "${(@f)$(lancet _arguments $words[1])}" && ret=0
    fi
}

compdef _lancet lancet
