======
Aerich
======

.. image:: https://img.shields.io/pypi/v/aerich.svg?style=flat
   :target: https://pypi.python.org/pypi/aerich
.. image:: https://img.shields.io/github/license/long2ice/aerich
   :target: https://github.com/long2ice/aerich
.. image:: https://github.com/long2ice/aerich/workflows/pypi/badge.svg
   :target: https://github.com/long2ice/aerich/actions?query=workflow:pypi
.. image:: https://github.com/long2ice/aerich/workflows/test/badge.svg
   :target: https://github.com/long2ice/aerich/actions?query=workflow:test

Introduction
============

Tortoise-ORM is the best asyncio ORM now, but it lacks a database migrations tool like alembic for SQLAlchemy, or Django ORM with it's own migrations tool.

This project aim to be a best migrations tool for Tortoise-ORM and which written by one of contributors of Tortoise-ORM.

Install
=======

Just install from pypi:

.. code-block:: shell

    $ pip install aerich

Quick Start
===========

.. code-block:: shell

    $ aerich -h

    Usage: aerich [OPTIONS] COMMAND [ARGS]...

    Options:
      -c, --config TEXT  Config file.  [default: aerich.ini]
      --app TEXT         Tortoise-ORM app name.  [default: models]
      -n, --name TEXT    Name of section in .ini file to use for aerich config.
                         [default: aerich]
      -h, --help         Show this message and exit.

    Commands:
      downgrade  Downgrade to previous version.
      heads      Show current available heads in migrate location.
      history    List all migrate items.
      init       Init config file and generate root migrate location.
      init-db    Generate schema and generate app migrate location.
      migrate    Generate migrate changes file.
      upgrade    Upgrade to latest version.

Usage
=====
You need add ``aerich.models`` to your ``Tortoise-ORM`` config first, example:

.. code-block:: python

    TORTOISE_ORM = {
        "connections": {"default": "mysql://root:123456@127.0.0.1:3306/test"},
        "apps": {
            "models": {
                "models": ["tests.models", "aerich.models"],
                "default_connection": "default",
            },
        },
    }

Initialization
--------------

.. code-block:: shell

    $ aerich init -h

    Usage: aerich init [OPTIONS]

      Init config file and generate root migrate location.

    Options:
      -t, --tortoise-orm TEXT  Tortoise-ORM config module dict variable, like settings.TORTOISE_ORM.
                               [required]
      --location TEXT          Migrate store location.  [default: ./migrations]
      -h, --help               Show this message and exit.

Init config file and location:

.. code-block:: shell

    $ aerich init -t tests.backends.mysql.TORTOISE_ORM

    Success create migrate location ./migrations
    Success generate config file aerich.ini

Init db
-------

.. code-block:: shell

    $ aerich init-db

    Success create app migrate location ./migrations/models
    Success generate schema for app "models"

Update models and make migrate
------------------------------

.. code-block:: shell

    $ aerich migrate --name drop_column

    Success migrate 1_202029051520102929_drop_column.json

Format of migrate filename is ``{version_num}_{datetime}_{name|update}.json``

Upgrade to latest version
-------------------------

.. code-block:: shell

    $ aerich upgrade

    Success upgrade 1_202029051520102929_drop_column.json

Now your db is migrated to latest.

Downgrade to previous version
-----------------------------

.. code-block:: shell

    $ aerich downgrade

    Success downgrade 1_202029051520102929_drop_column.json

Now your db rollback to previous version.

Show history
------------

.. code-block:: shell

    $ aerich history

    1_202029051520102929_drop_column.json

Show heads to be migrated
-------------------------

.. code-block:: shell

    $ aerich heads

    1_202029051520102929_drop_column.json

License
=======
This project is licensed under the `MIT <https://github.com/long2ice/aerich/blob/master/LICENSE>`_ License.
