from rich.console import Console
from rich.theme import Theme


custom_theme = Theme({
    "info": "dim cyan",
    "question": "yellow",
    "warning": "magenta",
    "danger": "bold red",
    "error": "red",
    "comment": "green"
})

console = Console(theme=custom_theme)
