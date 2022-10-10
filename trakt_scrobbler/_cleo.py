from copy import deepcopy as _deepcopy
from cleo import __version__ as cleo_version

use_v1_unstable = cleo_version.startswith("1.0.0")

if use_v1_unstable:
    from cleo.application import Application
    from cleo.commands.command import Command
    from cleo.io.outputs.output import Verbosity as output
    from cleo.io.inputs.string_input import StringInput as StringArgs
    from cleo.io.null_io import NullIO
    from cleo.ui.table import Table as _Table
    from cleo.ui.table_cell import TableCell as _TableCell
    from cleo.terminal import Terminal as _Terminal
    from cleo.formatters.formatter import Formatter as _fmt
    _FMT = _fmt()
else:
    from cleo import Application
    from cleo import Command
    from clikit.io import NullIO
    from clikit.args import StringArgs
    from clikit.api.io import output
    from clikit.ui.style.table_style import TableStyle as _TableStyle
    from clikit.ui.components.table import Table as _Table
    from clikit.ui.style.alignment import Alignment as _Alignment
    setattr(Command, 'name', property(lambda x: getattr(
        getattr(x, '_config', None), 'name', None)
    ))

class Table(_Table):
    def __init__(self, io):
        if use_v1_unstable:
            super().__init__(io, "compact")
            style = _deepcopy(self.column_style(0))
            style.set_pad_type("left")
            self.set_column_style(0, style)
        else:
            self._io = io
            style = _deepcopy(_TableStyle.borderless())
            style.set_column_alignment(0, _Alignment.RIGHT)
            super().__init__(style)

    def render(self):
        if use_v1_unstable:
            return super().render()
        return super().render(self._io)

if use_v1_unstable:
    def _line_cleanup(line: str):
        return '\n'.join([
            n.strip() for n in line.splitlines() if n.strip()
        ])

    def _line_length(line: str):
        return len(next(reversed(
            _line_cleanup(_FMT.remove_format(line)).splitlines()
        )))

    def _wrap_lines(line, width):
        words = []
        for word in line.split():
            if _line_length(' '.join(words + [word])) >= width:
                pos = len(words)
                words.insert(pos, '\n')
            words.append(word)
        return _line_cleanup(' '.join(words))

def Row(name: str, data: str):
    if use_v1_unstable:
        width = _Terminal().width - _line_length(name) - 4
        if width < _line_length(data):
            data = _wrap_lines(data, width)
        lines = data.splitlines()
        data = _TableCell(data, rowspan=len(lines))

    return [name, data]
# vim: ft=python3:ts=4:et:
