import importlib
import os
import sys
from enum import Enum

import click
from click import BadParameter, ClickException

sys.path.append(os.getcwd())


class Color(str, Enum):
    green = 'green'
    red = 'red'


@click.group(context_settings={'help_option_names': ['-h', '--help']})
@click.option('-c', '--config', default='settings',
              help='Tortoise-ORM config module, will read config variable from it, default is `settings`.')
@click.option('-t', '--tortoise-orm', default='TORTOISE_ORM',
              help='Tortoise-ORM config dict variable, default is `TORTOISE_ORM`.')
@click.option('-l', '--location', default='./migrations',
              help='Migrate store location, default is `./migrations`.')
@click.option('--connection', default='default', help='Tortoise-ORM connection name, default is `default`.')
@click.pass_context
def cli(ctx, config, tortoise_orm, location, connection):
    ctx.ensure_object(dict)
    try:
        config_module = importlib.import_module(config)
        config = getattr(config_module, tortoise_orm, None)
        if not config:
            raise BadParameter(param_hint=['--config'],
                               message=f'Can\'t get "{tortoise_orm}" from module "{config_module}"')
        ctx.obj['config'] = config
        ctx.obj['location'] = location
        if connection not in config.get('connections').keys():
            raise BadParameter(param_hint=['--connection'], message=f'No connection found in "{config}"')
    except ModuleNotFoundError:
        raise BadParameter(param_hint=['--tortoise-orm'], message=f'No module named "{config}"')


@cli.command()
@click.pass_context
def migrate(ctx):
    config = ctx.obj['config']


@cli.command()
@click.pass_context
def upgrade():
    pass


@cli.command()
@click.pass_context
def downgrade():
    pass


@cli.command()
@click.pass_context
def initdb():
    pass


@cli.command()
@click.option('--overwrite', type=bool, default=False, help='Overwrite old_models.py.')
@click.pass_context
def init(ctx, overwrite):
    location = ctx.obj['location']
    config = ctx.obj['config']
    if not os.path.isdir(location) or overwrite:
        os.mkdir(location)
        connections = config.get('connections').keys()
        for connection in connections:
            dirname = os.path.join(location, connection)
            if not os.path.isdir(dirname):
                os.mkdir(dirname)
                click.secho(f'Success create migrate location {dirname}', fg=Color.green)
            if overwrite:
                pass
    else:
        raise ClickException('Already inited')
