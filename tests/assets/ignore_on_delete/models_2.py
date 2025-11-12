from __future__ import annotations

from tortoise import Model, fields
from tortoise.fields import OnDelete


class Group(Model):
    name = fields.CharField(20)

    users: fields.ReverseRelation[User]


class User(Model):
    name = fields.CharField(20)
    group: fields.ForeignKeyNullableRelation[Group] = fields.ForeignKeyField(
        "models.Group", on_delete=OnDelete.SET_NULL, related_name="users", null=True
    )

    profile: fields.ReverseRelation[Profile]


class Profile(Model):
    age = fields.IntField()
    user: fields.OneToOneRelation[User] = fields.OneToOneField(
        "models.User", on_delete=OnDelete.NO_ACTION, related_name="profile"
    )
