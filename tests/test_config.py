import os
from pathlib import Path
import pytest

from roboduck import config


def test_get_config_path():
    old_path = os.environ[config.CONFIG_PATH_ENV_VAR]

    # First test with no env var set.
    del os.environ[config.CONFIG_PATH_ENV_VAR]
    config_path = config.get_config_path()
    assert config_path == config.CONFIG_PATH

    # Now test when env var is set.
    custom_path = '/custom/path/config.yaml'
    os.environ[config.CONFIG_PATH_ENV_VAR] = custom_path
    config_path = config.get_config_path()
    assert config_path == Path(custom_path)
    os.environ[config.CONFIG_PATH_ENV_VAR] = old_path


def test_set_default_model_name():
    cfg = config.load_config()
    assert 'model_name' not in cfg
    assert 'openai_api_key' in cfg

    model_name = 'gpt-3.5-turbo'
    config.update_config(model_name=model_name)
    cfg = config.load_config()
    assert cfg['model_name'] == model_name
    assert 'openai_api_key' in cfg

    config.update_config(model_name=None)
    cfg = config.load_config()
    assert 'model_name' not in model_name
    assert 'openai_api_key' in cfg


def test_apply_config_defaults():
    model_name = 'gpt-4'
    config.update_config(model_name=model_name)
    old_model_name = 'gpt-3.5-turbo'
    kwargs = {'model_name': old_model_name, 'temperature': 0.0}
    config.apply_config_defaults(kwargs, template_only=True)
    assert kwargs['model_name'] == model_name

    kwargs = {'model_name': old_model_name, 'temperature': 0.0}
    config.apply_config_defaults(kwargs, template_only=False)
    assert kwargs['model_name'] == old_model_name

