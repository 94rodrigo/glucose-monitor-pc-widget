import pytest

from glucowidget.i18n import set_language


@pytest.fixture(autouse=True)
def _english_by_default():
    set_language("en")
    yield
    set_language("en")
