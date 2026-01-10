from rich.console import Console
from rich.theme import Theme


custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "danger": "bold red",
    "error": "red",
})

console = Console(theme=custom_theme)
