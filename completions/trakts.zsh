#compdef trakts
#
# Zsh auto complete function for trakts
#
# shellcheck shell=bash
# shellcheck disable=SC2168

## Section @globals ##
_trakts_args() {
    local -a options
    options=(
        {-h,--help}"[Display help message]"
        "(-v --verbose)"{-q,--quiet}"[Do not output any message]"
        "(-q --quiet)"{-v,--verbose}"[Increase the verbosity of messages]"
        {-V,--version}"[Display this application version]"
        {-n,--no-interaction}"[Do not ask any interactive question]"
        "(--no-ansi)--ansi[Force ANSI output]"
        "(--ansi)--no-ansi[Disable ANSI output]"
    )
    [[ $1 == opts ]] && set "$@" ': :' && shift
    _arguments "${options[@]}" "$@"
}
__trakts_debug() {
    # shellcheck disable=SC2059
    if [[ -e ~/pipe:comp ]];then
        printf "$@" > ~/pipe:comp
        printf '\n' > ~/pipe:comp
    fi
}

_trakts_finish() {
    _message 'no more arguments'
}
## endSection @globals ##

## Section @simpleCommands ##
### command auth
_trakts_auth() {
   _trakts_args opts -s '-f[Force run the flow]'
}
### command init
_trakts_init()
{
    _trakts_args opts
}
### command plex
_trakts_plex()
{
    _trakts_args \
        -{f,-force}'[Force run the flow, ignoring already existing credentials]' \
        -{t,-token}'[Enter plex token directly instead of password. Implies -f]'
}
### command run
_trakts_run()
{
    _trakts_args opts
}
### command start
_trakts_start()
{
    _trakts_args opts -s {-r,--restart}'[Restart the service]'
}
### command status
_trakts_status()
{
    _trakts_args opts
}
### command stop
_trakts_stop()
{
    _trakts_args opts
}
## Section @simpleCommands ##

## Section autostart ##
_trakts_autostart_commands()
{
    local commands
    commands=(
        "enable:Install and enable the autostart service"
        "disable:Disable the autostart service"
    )
    _describe 'commands' commands
}
### command autostart
_trakts_autostart()
{
    _trakts_args -s ':action:_trakts_autostart_commands'
}
### command autostart enable
_trakts_autostart_enable() {
    _trakts_args opts
}
### command autostart disable
_trakts_autostart_disable() {
    _trakts_args opts
}
## endSection autostart ##

## Section backlog ##
_trakts_backlog_commands()
{
    local commands
    commands=(
        "clear:Try to sync the backlog with trakt servers"
        "list:List the files in backlog"
    )
    _describe 'commands' commands
}
### command backlog
_trakts_backlog()
{
    _trakts_args -s ':action:_trakts_backlog_commands'
}
## endSection backlog ##

## Section config ##
_trakts_config_commands()
{
    local commands
    commands=(
        'list:List configuration settings'
        'set:Set the value for a config parameter'
        'unset:Reset a config value to its default'
    )
    _describe 'commands' commands
}
_trakts_config_keys()
{
    local keys
    # shellcheck disable=SC2034,SC2296
    keys=("${(@f)"$(trakts config list --all|cut -d\  -f1)"}")
    _describe 'keys' keys
}
### command config
_trakts_config()
{
    _trakts_args '1:action:_trakts_config_commands'
}
### command config set
_trakts_config_set()
{
    _trakts_args \
        '--add[Append to list instead of overwriting]' \
        '2:key:_trakts_config_keys' \
        '*:value:'
}
### command config list
_trakts_config_list()
{
    _trakts_args opts '--all[Include default values]'
}
### command config unset
_trakts_config_unset()
{
    _trakts_config_keys "$@"
}
## endSection config ##

## Section log ##
_trakts_log_commands()
{
    local commands
    commands=(
        'open:Open Latest log.'
        'path:Prints the location of the log file'
    )
    _describe 'commands' commands
}
### command log
_trakts_log()
{
    _trakts_args '1:action:_trakts_log_commands'
}
## endSection log ##

## Section lookup ##
### command lookup
_trakts_lookup()
{
    local -a opts
    opts=(
        '--type[Type of media (show/movie) (multiple values allowed)]:type:'
        -s '--year[Specific year]:year:'
        -s '--brief[Only print trakt ID of top result]'
        -s '--limit[Number of results to fetch per page (default: 3)]:limit:'
        -s '--page[Number of page of results to fetch (default: 1)]:page:'
        '*:name:'
    )
    _trakts_args "${opts[@]}"
}
## endSection lookup ##

## Section test ##
### command test
_trakts_test()
{
    local -a opts
    opts=(
        '*:player:'
    )
    _trakts_args "${opts[@]}"
}
## endSection test ##

## Section whitelist ##
_trakts_whitelist_commands()
{
    local commands
    commands=(
        'add:Add folder(s) to whitelist'
        'remove:Remove folder(s) from whitelist'
        'show:Show the current whitelist'
        'test:Check whether the given file/folder is whitelisted'
    )
    _describe 'commands' commands
}
### command whitelist
_trakts_whitelist()
{
    _trakts_args ':action:_trakts_whitelist_commands'
}
### command whitelist add
_trakts_whitelist_add()
{
    _trakts_args '2:path:_tilde_files -/'
}
### command whitelist test
_trakts_whitelist_test()
{
    _trakts_args '2:path:_tilde_files'
}
## endSection whitelist ##

## Section @main ##
_trakts_commands()
{
    local commands
    # shellcheck disable=SC2034
    commands=(
        "auth:Runs the authetication flow for trakt.tv"
        "autostart:Controls the autostart behaviour of the scrobbler"
        "backlog:Manage the not-yet-synced backlog of watched media"
        "config:Edit the scrobbler config settings"
        "help:Display the manual of a command"
        "init:Run the initial setup of the scrobble"
        "log:Access the log file"
        "lookup:Performs a search for the given media title"
        "plex:Run the authetication flow for plex media server"
        "run:Run the scrobbler in the foreground"
        "start:Start the trakt-scrobbler service"
        "status:Show the status trakt-scrobbler service"
        "stop:Stop the trakt-scrobbler service"
        "test:Test player-monitor connection"
        "whitelist:Add the given folder(s) to whitelist"
    )
    _describe 'commands' commands
}

_trakts_arguments() {
    # shellcheck disable=SC1087,SC1105,SC2211,SC2288,SC2086
	case $line[1] in
		(help)
		    local cmdfunc shifted
		    cmdfunc=$(printf '_%s' "${line[@]:1:-1}") shifted=0
		    if [[ $cmdfunc != _ ]] ;then
                until [[ $cmdfunc == _ ]] || ((shifted++));do
                    if (( $+functions[_trakts${cmdfunc}_commands] ));then
                        "_trakts${cmdfunc}_commands" "$@"
                        return
                    fi
                    cmdfunc=$cmdfunc:gs+_+/+:h:gs+/+_+
                done
                _trakts_finish
            else
                _trakts_commands
            fi
		;;
		(*)
		    local cmdfunc
		    cmdfunc=$(
		        for word in $line;do
		            [[ ${word:0:1} == - ]] && break
		            printf '_%s' "$word"
		        done
		    )
		    if [[ $cmdfunc != _ ]] ;then
		        until [[ $cmdfunc == _ ]];do
                    if (( $+functions[_trakts$cmdfunc] ));then
                        "_trakts$cmdfunc" "$@"
                        break
                    fi
                    cmdfunc=$cmdfunc:gs+_+/+:h:gs+/+_+
                done
		    else
		        _trakts_finish
		    fi
		;;
	esac
}

### command trakts
local line args
args=(
    "1:commands:_trakts_commands"
    "*::arguments:_trakts_arguments"
)
_trakts_args "${args[@]}"
## endSection @main ##
# vim: ft=sh:ts=4:noet:
