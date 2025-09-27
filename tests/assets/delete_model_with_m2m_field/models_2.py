from tortoise import Model, fields


class User(Model):
    name = fields.CharField(max_length=55)
    groups: fields.ReverseRelation["Group"]


class Group(Model):
    name = fields.TextField()
    users: fields.ManyToManyRelation[User] = fields.ManyToManyField(
        "models.User", related_name="groups"
    )
