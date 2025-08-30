from tortoise import Model, fields


class Node(Model):
    children = fields.ManyToManyField(
        "models.Node",
        related_name="parents",
    )


class Dummy(Model):
    name = fields.CharField(max_length=100, null=True)
