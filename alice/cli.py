import importlib
import os
import sys
from enum import Enum

import asyncclick as click
from asyncclick import BadParameter, ClickException
from tortoise import Tortoise, generate_schema_for_client

from alice.backends.mysql import MysqlDDL
from alice.migrate import Migrate
from alice.utils import get_app_connection

sys.path.append(os.getcwd())


class Color(str, Enum):
    green = 'green'
    red = 'red'


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-c', '--config', default='settings', show_default=True,
              help='Tortoise-ORM config module, will read config variable from it, default is `settings`.')
@click.option('-t', '--tortoise-orm', default='TORTOISE_ORM', show_default=True,
              help='Tortoise-ORM config dict variable, default is `TORTOISE_ORM`.')
@click.option('-l', '--location', default='./migrations', show_default=True,
              help='Migrate store location, default is `./migrations`.')
@click.option('-a', '--app', default='models', show_default=True, help='Tortoise-ORM app name, default is `models`.')
@click.pass_context
async def cli(ctx, config, tortoise_orm, location, app):
    ctx.ensure_object(dict)
    try:
        config_module = importlib.import_module(config)
        config = getattr(config_module, tortoise_orm, None)
        if not config:
            raise BadParameter(param_hint=['--config'],
                               message=f'Can\'t get "{tortoise_orm}" from module "{config_module}"')

        await Tortoise.init(config=config)

        ctx.obj['config'] = config
        ctx.obj['location'] = location
        ctx.obj['app'] = app

        if app not in config.get('apps').keys():
            raise BadParameter(param_hint=['--app'], message=f'No app found in "{config}"')

    except ModuleNotFoundError:
        raise BadParameter(param_hint=['--tortoise-orm'], message=f'No module named "{config}"')


@cli.command()
@click.pass_context
def migrate(ctx):
    config = ctx.obj['config']
    location = ctx.obj['location']
    app = ctx.obj['app']

    old_models = Migrate.read_old_models(app, location)
    print(old_models)

    new_models = Tortoise.apps.get(app)
    print(new_models)

    ret = Migrate(MysqlDDL(get_app_connection(config, app))).diff_models(old_models, new_models)
    print(ret)


@cli.command()
@click.pass_context
def upgrade():
    pass


@cli.command()
@click.pass_context
def downgrade():
    pass


@cli.command()
@click.option('--safe', is_flag=True, default=True,
              help='When set to true, creates the table only when it does not already exist..', show_default=True)
@click.pass_context
async def initdb(ctx, safe):
    location = ctx.obj['location']
    config = ctx.obj['config']
    app = ctx.obj['app']

    await generate_schema_for_client(get_app_connection(config, app), safe)

    Migrate.write_old_models(app, location)

    click.secho(f'Success initdb for app `{app}`', fg=Color.green)


@cli.command()
@click.option('--overwrite', is_flag=True, default=False, help=f'Overwrite {Migrate.old_models}.', show_default=True)
@click.pass_context
def init(ctx, overwrite):
    location = ctx.obj['location']
    app = ctx.obj['app']
    if not os.path.isdir(location):
        os.mkdir(location)
        dirname = os.path.join(location, app)
        if not os.path.isdir(dirname):
            os.mkdir(dirname)
            click.secho(f'Success create migrate location {dirname}', fg=Color.green)
    if overwrite:
        Migrate.write_old_models(app, location)
    else:
        raise ClickException('Already inited')


if __name__ == '__main__':
    cli(_anyio_backend='asyncio')
