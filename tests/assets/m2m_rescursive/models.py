from tortoise import Model, fields


class Node(Model):
    children = fields.ManyToManyField(
        "models.Node",
        related_name="parents",
    )
