from tortoise import fields, models


class Question(models.Model):
    question_text = fields.CharField(max_length=200)
    pub_date = fields.DatetimeField(description="date published")
