import tempfile
from pathlib import Path

from aerich.utils import write_version_file


def test_write_version_file():
    content = {
        "upgrade": [
            "CREATE TABLE IF NOT EXISTS `newmodel` (\n    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,\n    `name` VARCHAR(50) NOT NULL\n) CHARACTER SET utf8mb4;",
            "CREATE TABLE `email_user` (\n    `email_id` INT NOT NULL REFERENCES `email` (`email_id`) ON DELETE CASCADE,\n    `user_id` INT NOT NULL REFERENCES `user` (`id`) ON DELETE CASCADE\n) CHARACTER SET utf8mb4",
        ],
        "downgrade": [
            "DROP TABLE IF EXISTS `email_user`",
            "DROP TABLE IF EXISTS `newmodel`",
        ],
    }
    with tempfile.NamedTemporaryFile(mode="r", delete=True) as f:
        write_version_file(Path(f.name), content)
        result = f.read()
        assert result == (
            "-- upgrade --\n"
            "CREATE TABLE IF NOT EXISTS `newmodel` (\n"
            "    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,\n"
            "    `name` VARCHAR(50) NOT NULL\n"
            ") CHARACTER SET utf8mb4;\n"
            "CREATE TABLE `email_user` (\n"
            "    `email_id` INT NOT NULL REFERENCES `email` (`email_id`) ON DELETE CASCADE,\n"
            "    `user_id` INT NOT NULL REFERENCES `user` (`id`) ON DELETE CASCADE\n"
            ") CHARACTER SET utf8mb4;\n"
            "-- downgrade --\n"
            "DROP TABLE IF EXISTS `email_user`;\n"
            "DROP TABLE IF EXISTS `newmodel`;\n"
        )
