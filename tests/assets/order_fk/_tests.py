import pytest
from models import Continent


@pytest.mark.anyio
async def test_1():
    obj1 = await Continent.create(name="Asia")
    obj2 = await Continent.create(name="Europe")
    assert obj2.id > obj1.id
    assert (await Continent.first()).name == "Asia"


@pytest.mark.anyio
async def test_2():
    from models import City, Country, Region

    continent, _ = await Continent.get_or_create(name="continent")
    country = await Country.create(name="country", continent=continent)
    region = await Region.create(name="region", country=country)
    city = await City.create(name="city", region=region)
    assert city.pk
