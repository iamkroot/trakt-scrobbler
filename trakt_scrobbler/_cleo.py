from cleo import __version__ as cleo_version

if cleo_version.startswith('1.0.0'):
    from cleo.application import Application
    from cleo.commands.command import Command
else:
    from cleo import Application
    from cleo import Command

# vim: ft=python3:ts=4:et:
