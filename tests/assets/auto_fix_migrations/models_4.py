from tortoise import Model, fields


class Users(Model):
    age = fields.IntField(null=True)

    class Meta:
        table = "users"


class Member(Model):
    user = fields.ForeignKeyField("models.Users")
    name = fields.CharField(20)
