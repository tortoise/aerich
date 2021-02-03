# Aerich

[![image](https://img.shields.io/pypi/v/aerich.svg?style=flat)](https://pypi.python.org/pypi/aerich)
[![image](https://img.shields.io/github/license/long2ice/aerich)](https://github.com/long2ice/aerich)
[![image](https://github.com/long2ice/aerich/workflows/pypi/badge.svg)](https://github.com/long2ice/aerich/actions?query=workflow:pypi)
[![image](https://github.com/long2ice/aerich/workflows/test/badge.svg)](https://github.com/long2ice/aerich/actions?query=workflow:test)

## Introduction

Aerich is a database migrations tool for Tortoise-ORM, which like alembic for SQLAlchemy, or Django ORM with it\'s own
migrations solution.

~~**Important: You can only use absolutely import in your `models.py` to make `aerich` work.**~~

From version `v0.5.0`, there is no such limitation now.

## Install

Just install from pypi:

```shell
> pip install aerich
```

## Quick Start

```shell
> aerich -h

Usage: aerich [OPTIONS] COMMAND [ARGS]...

Options:
  -c, --config TEXT  Config file.  [default: aerich.ini]
  --app TEXT         Tortoise-ORM app name.  [default: models]
  -n, --name TEXT    Name of section in .ini file to use for aerich config.
                     [default: aerich]
  -h, --help         Show this message and exit.

Commands:
  downgrade  Downgrade to specified version.
  heads      Show current available heads in migrate location.
  history    List all migrate items.
  init       Init config file and generate root migrate location.
  init-db    Generate schema and generate app migrate location.
  inspectdb  Introspects the database tables to standard output as...
  migrate    Generate migrate changes file.
  upgrade    Upgrade to latest version.
```

## Usage

You need add `aerich.models` to your `Tortoise-ORM` config first, example:

```python
TORTOISE_ORM = {
    "connections": {"default": "mysql://root:123456@127.0.0.1:3306/test"},
    "apps": {
        "models": {
            "models": ["tests.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
```

### Initialization

```shell
> aerich init -h

Usage: aerich init [OPTIONS]

  Init config file and generate root migrate location.

Options:
  -t, --tortoise-orm TEXT  Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM.
                           [required]
  --location TEXT          Migrate store location.  [default: ./migrations]
  -h, --help               Show this message and exit.
```

Init config file and location:

```shell
> aerich init -t tests.backends.mysql.TORTOISE_ORM

Success create migrate location ./migrations
Success generate config file aerich.ini
```

### Init db

```shell
> aerich init-db

Success create app migrate location ./migrations/models
Success generate schema for app "models"
```

If your Tortoise-ORM app is not default `models`, you must specify
`--app` like `aerich --app other_models init-db`.

### Update models and make migrate

```shell
> aerich migrate --name drop_column

Success migrate 1_202029051520102929_drop_column.sql
```

Format of migrate filename is
`{version_num}_{datetime}_{name|update}.sql`.

And if `aerich` guess you are renaming a column, it will ask `Rename {old_column} to {new_column} [True]`, you can
choice `True` to rename column without column drop, or choice `False` to drop column then create, note that the after
maybe lose data.

### Upgrade to latest version

```shell
> aerich upgrade

Success upgrade 1_202029051520102929_drop_column.sql
```

Now your db is migrated to latest.

### Downgrade to specified version

```shell
> aerich init -h

Usage: aerich downgrade [OPTIONS]

  Downgrade to specified version.

Options:
  -v, --version INTEGER  Specified version, default to last.  [default: -1]
  -d, --delete           Delete version files at the same time.  [default:
                         False]

  --yes                  Confirm the action without prompting.
  -h, --help             Show this message and exit.
```

```shell
> aerich downgrade

Success downgrade 1_202029051520102929_drop_column.sql
```

Now your db rollback to specified version.

### Show history

```shell
> aerich history

1_202029051520102929_drop_column.sql
```

### Show heads to be migrated

```shell
> aerich heads

1_202029051520102929_drop_column.sql
```

### Inspect db tables to TortoiseORM model

Currently, only support MySQL.

```shell
Usage: aerich inspectdb [OPTIONS]

  Introspects the database tables to standard output as TortoiseORM model.

Options:
  -t, --table TEXT  Which tables to inspect.
  -h, --help        Show this message and exit.
```

Inspect all tables and print to console:

```shell
aerich --app models inspectdb
```

Inspect a specified table in default app and redirect to `models.py`:

```shell
aerich inspectdb -t user > models.py
```

Note that this command is restricted, which is not supported in some solutions, such as `IntEnumField`
and `ForeignKeyField` and so on.

### Multiple databases

```python
tortoise_orm = {
    "connections": {
        "default": expand_db_url(db_url, True),
        "second": expand_db_url(db_url_second, True),
    },
    "apps": {
        "models": {"models": ["tests.models", "aerich.models"], "default_connection": "default"},
        "models_second": {"models": ["tests.models_second"], "default_connection": "second", },
    },
}
```

You need only specify `aerich.models` in one app, and must specify `--app` when run `aerich migrate` and so on.

## Support this project

| AliPay                                                                                 | WeChatPay                                                                                 | PayPal                                                           |
| -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| <img width="200" src="https://github.com/long2ice/aerich/raw/dev/images/alipay.jpeg"/> | <img width="200" src="https://github.com/long2ice/aerich/raw/dev/images/wechatpay.jpeg"/> | [PayPal](https://www.paypal.me/long2ice) to my account long2ice. |

## License

This project is licensed under the
[Apache-2.0](https://github.com/long2ice/aerich/blob/master/LICENSE) License.
