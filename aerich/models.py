from tortoise import Model, fields


class Aerich(Model):
    version = fields.CharField(max_length=50)

    class Meta:
        ordering = ["-id"]
