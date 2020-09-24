import functools
import os

import typer
from tortoise import Tortoise

app =typer.Typer()

def close_db(func):
    @functools.wraps(func)
    async def close_db_inner(*args, **kwargs):
        result = await func(*args, **kwargs)
        await Tortoise.close_connections()
        return result
    return close_db_inner

@app.command()
async def init(
    tortoise_orm:str, location:str=typer.Argument( "./migrations",metavar="-t"
):
    """
    Init config file and generate root migrate location.
        --tortoise-orm:Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM."
        --location", default="./migrations",Migrate store location.
    """
    config_file = ctx.obj["config_file"]
    name = ctx.obj["name"]
    if os.path.exists(config_file):
        return click.secho("You have inited", fg=Color.yellow)

    parser.add_section(name)
    parser.set(name, "tortoise_orm", tortoise_orm)
    parser.set(name, "location", location)

    with open(config_file, "w", encoding="utf-8") as f:
        parser.write(f)

    if not os.path.isdir(location):
        os.mkdir(location)

    click.secho(f"Success create migrate location {location}", fg=Color.green)
    click.secho(f"Success generate config file {config_file}", fg=Color.green)



@cli.command(help="Generate schema and generate app migrate location.")
@click.option(
    "--safe",
    type=bool,
    default=True,
    help="When set to true, creates the table only when it does not already exist.",
    show_default=True,
)
@click.pass_context
@close_db
async def init_db(ctx: Context, safe):
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]

    dirname = os.path.join(location, app)
    if not os.path.isdir(dirname):
        os.mkdir(dirname)
        click.secho(f"Success create app migrate location {dirname}", fg=Color.green)
    else:
        return click.secho(f"Inited {app} already", fg=Color.yellow)

    Migrate.write_old_models(config, app, location)

    await Tortoise.init(config=config)
    connection = get_app_connection(config, app)
    await generate_schema_for_client(connection, safe)

    schema = get_schema_sql(connection, safe)

    version = await Migrate.generate_version()
    await Aerich.create(version=version, app=app)
    with open(os.path.join(dirname, version), "w", encoding="utf-8") as f:
        content = {
            "upgrade": [schema],
        }
        json.dump(content, f, ensure_ascii=False, indent=2)
    return click.secho(f'Success generate schema for app "{app}"', fg=Color.green)


@app.command()
@click.option("--name", default="update", show_default=True, help="Migrate name.")
@click.pass_context
@close_db
async def migrate(ctx: Context, name):
    """
    Generate migrate changes file.
    """
    config = ctx.obj["config"]
    location = ctx.obj["location"]
    app = ctx.obj["app"]

    ret = await Migrate.migrate(name)
    if not ret:
        return click.secho("No changes detected", fg=Color.yellow)
    Migrate.write_old_models(config, app, location)
    click.secho(f"Success migrate {ret}", fg=Color.green)
if __name__ == '__main__':
    app()