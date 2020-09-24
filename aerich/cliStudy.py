
import typer
app=typer.Typer()
@app.command()
def hello(name:str,lastname:bool=typer.Option(False,'--lastname','-n',help="your lastname",),format:bool=False):
    if format:
        typer.echo("format is true")
    if lastname:
        print(f"lastname is {lastname}")
    typer.echo(f"Hello {name} {lastname}")

if __name__ == '__main__':
    app()