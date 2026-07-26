from tortoise import Model, fields


class Users(Model):
    age = fields.IntField()

    class Meta:
        table = "users"
