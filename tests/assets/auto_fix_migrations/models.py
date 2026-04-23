from tortoise import Model, fields


class User(Model):
    age = fields.IntField()

    class Meta:
        table = "users"
