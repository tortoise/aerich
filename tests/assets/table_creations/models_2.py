from tortoise import Model, fields


class Foo(Model):
    name = fields.CharField(20)
    g = fields.OneToOneField("models.G", null=True)
    h = fields.ForeignKeyField("models.H", null=True)


class B(Model):
    name = fields.CharField(20)


class C(Model):
    name = fields.CharField(20)


class G(Model):
    name = fields.CharField(20)


class H(Model):
    name = fields.CharField(20)


class A(Model):
    name = fields.CharField(20)
    b = fields.ForeignKeyField("models.B")
    c = fields.OneToOneField("models.C")
