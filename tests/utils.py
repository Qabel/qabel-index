
from index_service import utils


def test_short_id():
    id = utils.short_id(5)
    assert len(id) == 5
    other_id = utils.short_id(5)
    assert other_id != id  # failure probability: 18**-5 ~ 529 ppb
