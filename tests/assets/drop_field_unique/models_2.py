from tortoise import Model
from tortoise.fields import CharField


class UserTicketPackage(Model):
    package_order_id = CharField(max_length=100)
    qr_code = CharField(max_length=100, unique=False)

    class Meta:
        table = "user_ticket_package"
