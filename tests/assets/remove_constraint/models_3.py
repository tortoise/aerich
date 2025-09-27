from tortoise import Model, fields


class Foo(Model):
    a = fields.IntField()
    b = fields.IntField()
    c = fields.IntField(unique=True)


class Sth(Model):
    a = fields.IntField()
    b = fields.IntField()
    c = fields.IntField()
    d = fields.IntField()
    e = fields.IntField(null=True)
    f = fields.IntField(null=True)

    class Meta:
        unique_together = [("a", "b"), ("e", "f")]
