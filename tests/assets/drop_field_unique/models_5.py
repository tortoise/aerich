from tortoise import Model
from tortoise.fields import CharField


class UserTicketPackage(Model):
    package_order_id = CharField(max_length=100, unique=True)
    qr_code = CharField(max_length=100, unique=True, db_index=True)
    name = CharField(max_length=100, default="")

    class Meta:
        table = "user_ticket_package"
