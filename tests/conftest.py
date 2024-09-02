import os
import pytest

from roboduck.config import set_openai_api_key, CONFIG_PATH_ENV_VAR


@pytest.fixture(autouse=True)
def set_dummy_openai_api_key(tmp_path):
    file_path = tmp_path/'config.yaml'
    os.environ[CONFIG_PATH_ENV_VAR] = str(file_path)
    set_openai_api_key('xyz', update_config_=True)
    # File will exist while all tests are running, then get deleted afterwards.
    yield

    file_path.unlink()