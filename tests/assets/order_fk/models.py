from tortoise import Model, fields


class Continent(Model):
    name = fields.CharField(max_length=127)
