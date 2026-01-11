import typer

app = typer.Typer()


@app.command(help="Run the scrobbler in the foreground.")
def run():
    from trakt_scrobbler.main import main

    main()
