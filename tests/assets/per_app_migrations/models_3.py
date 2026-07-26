from __future__ import annotations

from typing import TYPE_CHECKING

import tortoise
from tortoise import Model
from tortoise import fields as models

if TYPE_CHECKING:
    from tortoise.fields import ForeignKeyRelation, ReverseRelation

if tortoise.__version__ < "1.1.8":
    models.DateTimeField = models.DatetimeField
    models.IntegerField = models.IntField
    models.ForeignKey = models.ForeignKeyField


class Question(Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField(description="date published")
    choice_set: ReverseRelation[Choice]


class Choice(Model):
    question: ForeignKeyRelation[Question] = models.ForeignKey(
        "polls.Question", on_delete=models.CASCADE, related_name="choice_set"
    )
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)
