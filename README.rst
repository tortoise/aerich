======
Aerich
======

.. image:: https://img.shields.io/pypi/v/aerich.svg?style=flat
   :target: https://pypi.python.org/pypi/aerich
.. image:: https://img.shields.io/github/license/long2ice/aerich
   :target: https://github.com/long2ice/aerich
.. image:: https://github.com/long2ice/aerich/workflows/pypi/badge.svg
   :target: https://github.com/long2ice/aerich/actions?query=workflow:pypi

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
      --config TEXT        Tortoise-ORM config module, will auto read config dict variable
                           from it.  [default: settings]
      --tortoise-orm TEXT  Tortoise-ORM config dict variable.  [default:
                           TORTOISE_ORM]
      --location TEXT      Migrate store location.  [default: ./migrations]
      --app TEXT           Tortoise-ORM app name.  [default: models]
      -h, --help           Show this message and exit.

    Commands:
      downgrade  Downgrade to previous version.
      heads      Show current available heads in migrate location.
      history    List all migrate items.
      init       Init migrate location and generate schema, you must exec first.
      migrate    Generate migrate changes file.
      upgrade    Upgrade to latest version.

Usage
=====

Init schema and migrate location
--------------------------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql init

    Success create migrate location ./migrations/models
    Success init for app "models"

Update models and make migrate
------------------------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql migrate --name drop_column

    Success migrate 1_202029051520102929_drop_column.json

Format of migrate filename is ``{version}_{datetime}_{name|update}.json``

Upgrade to latest version
-------------------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql upgrade

    Success upgrade 1_202029051520102929_drop_column.json

Now your db is migrated to latest.

Downgrade to previous version
-----------------------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql downgrade

    Success downgrade 1_202029051520102929_drop_column.json

Now your db rollback to previous version.

Show history
------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql history

    1_202029051520102929_drop_column.json

Show heads to be migrated
-------------------------

.. code-block:: shell

    $ aerich --config tests.backends.mysql heads

    1_202029051520102929_drop_column.json

License
=======
This project is licensed under the `MIT <https://github.com/long2ice/aerich/blob/master/LICENSE>`_ License.
