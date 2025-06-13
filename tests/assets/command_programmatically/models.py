from tortoise import Model, fields


class Foo(Model):
    a = fields.IntField()
