from unittest import TestCase

from alice.utils import cp_models


class TestUtils(TestCase):
    def test_cp_models(self):
        ret = cp_models('models.py', 'new_models.py', 'new_models')
        print(ret)
