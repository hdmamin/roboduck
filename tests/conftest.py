import pytest

from roboduck.langchain import set_openai_api_key


@pytest.fixture(autouse=True)
def set_dummy_openai_api_key():
    set_openai_api_key('xyz')
