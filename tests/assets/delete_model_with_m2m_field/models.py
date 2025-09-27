from tortoise import Model, fields


class Event(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    participants = fields.ManyToManyField(
        "models.Team", related_name="events", through="event_team"
    )


class Team(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)


class User(Model):
    name = fields.CharField(max_length=55)
    groups: fields.ReverseRelation["Group"]


class Group(Model):
    name = fields.TextField()
    users: fields.ManyToManyRelation[User] = fields.ManyToManyField(
        "models.User", related_name="groups"
    )
