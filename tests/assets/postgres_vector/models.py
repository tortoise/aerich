from tortoise import Model, fields
from tortoise.contrib.postgres.fields import TSVectorField
from tortoise_vector.field import VectorField


class Foo(Model):
    a = fields.IntField()
    b = TSVectorField()
    c = VectorField(1536)
