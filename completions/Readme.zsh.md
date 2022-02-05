# Autocompleter for Z shell

## Installation

Copy trakts.zsh to any directory in `$fpath` and remove `~/.zcompdump` then reopen terminal

## Adding new subcommand/options

### Global options

Add global options in `options` array of `_trakts_args()` function

### Subcommands

#### Base subcommands

1. Add the subcommand and description to `commands` array of `_trakts_commands()` function.
2. Define a new function for that subcommand named `_trakts_<subcommand>()`.
3. Define a new function for verbs of the new subcommands in `_trakts_<subcommand>_commands()`.

eg.

```bash
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
```

#### Child subcommands
1. Define subcommand in `_trakts_<subcommand>_<child_snake_case>()`
2. Define child subbcomands of the  `_trakts_<subcommand>_<child_snake_case>_commands()`

eg.

```bash
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
```
