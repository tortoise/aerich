from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "widgets" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "name" VARCHAR(100) NOT NULL,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "eJztlV1r2zAUhv+K8VUHXWm99IPduVlGM5ZktN46WopRLMURkSVXkpeGkv8+HdmOEueDFj"
    "bWwK5sveeVdM5j+ejZzwQmTB3dUpwS7X/0nn2OMmJeGpFDz0d57nQQNBoya51aj9XQUGmJ"
    "ElhqhJgiRsJEJZLmmgpuVF4wBqJIjJHy1EkFp48FibUwa42JNIH7ByNTjskTUfUwn8QjSh"
    "heyZVi2NvqsZ7lVuty/dkaYbdhnAhWZNyZ85keC75wU25rTAknEmkCy2tZQPqQXVVoXVGZ"
    "qbOUKS7NwWSECqaXyn0hg0Rw4GeyUbbAFHZ5H5y0zlsXH85aF8ZiM1ko5/OyPFd7OdES6E"
    "f+3MaRRqXDYnTc7HONXHuM5GZ0tb8Bz6TchFej2kWvFhw+d2T+EL8MPcWM8FSPzfDk+HgH"
    "rR/hdfsqvD4wrndQjTDHuDze/SoUlDFA6hAmkkDJMdLrID+ZiKYZ2QxzdWYDKa6mHtUvbx"
    "SwqQEPOJtVZ38H36jb69xEYe8bVJIp9cgsojDqQCSw6qyhHpw1PsViEe+2G115MPTuBv2O"
    "JSiUTqXd0fmiOx9yQoUWMRfTGOGl37RWazBzaDCjydKvAsIQJZMpkjhei4hAbPOuh7Igay"
    "qIo9R+FoALaVY9NySSJuNN3biK7OzGyHn+N+M9asa/iFSQ0iv68dKU/WzJwenpC1qycW1t"
    "yTa22pLh13gFxMq+nwD/zp0muCZ8w4X25WbQ33KZuSkNkN+5KfAe00Qfeowq/fA2se6gCF"
    "WvXFo1vINe+LPJtf11cNm8jWCBS8P4n14v8980Wcwa"
)
