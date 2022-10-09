from cleo import __version__ as cleo_version

if cleo_version.startswith('1.0.0'):
    from cleo.application import Application
    from cleo.commands.command import Command
else:
    from cleo import Application
    from cleo import Command
    setattr(Command, 'name', property(lambda x: getattr(
        getattr(x, '_config', None), 'name', None)
    ))


# vim: ft=python3:ts=4:et:
