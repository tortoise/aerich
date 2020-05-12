from tests.backends.mysql import DBTestCase
from tests.models import Category, User


class TestDDL(DBTestCase):
    def test_create_table(self):
        ret = self.ddl.create_table(Category)
        self.assertEqual(
            ret, """CREATE TABLE IF NOT EXISTS `category` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `slug` VARCHAR(200) NOT NULL,
    `name` VARCHAR(200) NOT NULL,
    `created_at` DATETIME(6) NOT NULL  DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` INT NOT NULL COMMENT 'User',
    CONSTRAINT `fk_category_user_e2e3874c` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;""")

    def test_drop_table(self):
        ret = self.ddl.drop_table(Category)
        self.assertEqual(ret, "DROP TABLE category IF EXISTS")

    def test_add_column(self):
        ret = self.ddl.add_column(Category, Category._meta.fields_map.get('name'))
        self.assertEqual(ret, "ALTER TABLE category ADD `name` VARCHAR(200) NOT NULL")

    def test_drop_column(self):
        ret = self.ddl.drop_column(Category, 'name')
        self.assertEqual(ret, "ALTER TABLE category DROP COLUMN name")

    def test_add_index(self):
        ret = self.ddl.add_index(Category, ['name'])
        self.assertEqual(ret, "ALTER TABLE category ADD  INDEX idx_category_name_8b0cb9 (`name`)")
        ret = self.ddl.add_index(Category, ['name'], True)
        self.assertEqual(ret, "ALTER TABLE category ADD UNIQUE INDEX uid_category_name_8b0cb9 (`name`)")

    def test_drop_index(self):
        ret = self.ddl.drop_index(Category, ['name'])
        self.assertEqual(ret, "ALTER TABLE category DROP INDEX idx_category_name_8b0cb9")
        ret = self.ddl.drop_index(Category, ['name'], True)
        self.assertEqual(ret, "ALTER TABLE category DROP INDEX uid_category_name_8b0cb9")

    def test_add_fk(self):
        ret = self.ddl.add_fk(Category, Category._meta.fields_map.get('user'))
        self.assertEqual(ret,
                         "ALTER TABLE category ADD CONSTRAINT `fk_category_user_366ffa6f` FOREIGN KEY (`user`) REFERENCES `user` (`id`) ON DELETE CASCADE")

    def test_drop_fk(self):
        ret = self.ddl.drop_fk(Category, Category._meta.fields_map.get('user'))
        self.assertEqual(ret, "ALTER TABLE category DROP FOREIGN KEY fk_category_user_366ffa6f")

    async def test_aa(self):
        user = await User.get(username='test')
        await user.save()
