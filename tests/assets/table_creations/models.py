from tortoise import Model, fields


class Foo(Model):
    name = fields.CharField(20)
