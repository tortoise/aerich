from tortoise import Model, fields
from tortoise.indexes import Index


class CustomIndex(Index): ...


class Foo(Model):
    name = fields.CharField(20)
