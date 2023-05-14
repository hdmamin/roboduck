import os
import pytest

from roboduck import config


def test_set_default_model_name():
    file_path = os.environ.get('CONFIG_FILE')
    cfg = config.load_config(file_path)
    assert 'model_name' not in cfg
    assert 'openai_api_key' in cfg

    model_name = 'gpt-3.5-turbo'
    config.update_config(file_path, model_name=model_name)
    cfg = config.load_config(file_path)
    assert cfg['model_name'] == model_name
    assert 'openai_api_key' in cfg

    config.update_config(file_path, model_name=None)
    cfg = config.load_config(file_path)
    assert 'model_name' not in model_name
    assert 'openai_api_key' in cfg


def test_apply_config_defaults():
    file_path = os.environ.get('CONFIG_FILE')
    model_name = 'gpt-4'
    config.update_config(file_path, model_name=model_name)
    old_model_name = 'gpt-3.5-turbo'
    kwargs = {'model_name': old_model_name, 'temperature': 0.0}
    config.apply_config_defaults(kwargs, template_only=True,
                                 config_path=file_path)
    assert kwargs['model_name'] == model_name

    kwargs = {'model_name': old_model_name, 'temperature': 0.0}
    config.apply_config_defaults(kwargs, template_only=False,
                                 config_path=file_path)
    assert kwargs['model_name'] == old_model_name

