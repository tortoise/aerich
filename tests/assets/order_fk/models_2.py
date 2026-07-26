from tortoise import Model, fields


class NameBase(Model):
    name = fields.CharField(max_length=255)

    class Meta:
        abstract = True


class Continent(NameBase):
    id = fields.IntField(pk=True)


class Country(NameBase):
    continent = fields.ForeignKeyField("models.Continent", on_delete=fields.CASCADE)


class Region(NameBase):
    country = fields.ForeignKeyField("models.Country", on_delete=fields.CASCADE)


class City(NameBase):
    region = fields.ForeignKeyField("models.Region", on_delete=fields.CASCADE)
