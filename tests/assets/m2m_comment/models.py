from tortoise import Model, fields


class DataLibGroup(Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(unique=True, max_length=100)
    parent = fields.ForeignKeyField(
        "models.DataLibGroup", related_name="by_children_list", null=True
    )
    level = fields.IntField(default=0)
    disabled = fields.BooleanField(default=False)
