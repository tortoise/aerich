from __future__ import annotations

from tortoise import Model, fields
from tortoise.fields import OnDelete


class Users(Model):
    name = fields.CharField(20)
    roles: fields.ReverseRelation[Users]


class Role(Model):
    name = fields.CharField(20)
    user: fields.ForeignKeyNullableRelation[Users] = fields.ForeignKeyField(
        "auth.Users", on_delete=OnDelete.CASCADE, related_name="roles", null=True
    )
