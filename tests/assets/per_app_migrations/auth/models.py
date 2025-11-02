from tortoise import Model, fields


class Users(Model):
    name = fields.CharField(20)
