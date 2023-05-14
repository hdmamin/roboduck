import os
import pytest

from roboduck import set_openai_api_key


@pytest.fixture(autouse=True)
def set_dummy_openai_api_key(tmp_path):
    file_path = tmp_path/'config.yaml'
    set_openai_api_key('xyz', config_path=file_path, update_config_=True)
    os.environ['CONFIG_FILE'] = str(file_path)
    # File will exist while all tests are running, then get deleted afterwards.
    yield

    file_path.unlink()