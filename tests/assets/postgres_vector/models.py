from tortoise import Model, fields
from tortoise.contrib.postgres.fields import TSVectorField


class Foo(Model):
    a = fields.IntField()
    b = TSVectorField()
