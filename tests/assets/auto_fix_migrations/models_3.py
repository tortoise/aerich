from tortoise import Model, fields


class UserAge(Model):
    age = fields.IntField()

    class Meta:
        table = "users"


class Member(Model):
    user = fields.ForeignKeyField("models.UserAge")
    name = fields.CharField(20)
