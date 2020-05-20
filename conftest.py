import os

import pytest
from tortoise.contrib.test import finalizer, initializer


@pytest.fixture(scope="module", autouse=True)
def initialize_tests(request):
    db_url = os.environ.get("TEST_DB", "sqlite://:memory:")
    initializer(["tests.models"], db_url=db_url)
    request.addfinalizer(finalizer)
