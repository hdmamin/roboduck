"""Miscellaneous functions to help us interact with langchain.
"""
import os
from pathlib import Path
import warnings

from roboduck.utils import load_yaml, update_yaml


MODEL_CONTEXT_WINDOWS = {
    'gpt-3.5-turbo': 4_096,
    'gpt-4': 8_192,
    'gpt-4-32k': 32_768,
    'code-davinci-002': 8_001,
    'claude': 8_000,   # Anthropic says this is approximate.
}


def set_openai_api_key(key=None, config_path='~/.roboduck/config.yaml',
                       strict=False, update_config=False):
    """Set OPENAI_API_KEY environment variable for langchain.

    Parameters
    ----------
    key: str or None
        Optionally pass in openai api key (str). If not provided, we check the
        config path and try to load a key. If it is provided, we don't check
        config_path.
    config_path: str or Path
        Local yaml file containing the field openai_api_key. We only try to
        load the key from it if `key` is not provided. We do not write to
        this file by default.
    strict: bool
        Determines what happens when key is None and config path does not
        exist. Strict=True raises a runtime error, False just warns user.
    update_config: bool
        If True, we update the yaml config file with that api key.
    """
    config_path = Path(config_path).expanduser()
    var_name = 'OPENAI_API_KEY'
    key = key or os.environ.get(var_name)
    if not key:
        try:
            data = load_yaml(config_path)
            key = data[var_name.lower()]
        except (FileNotFoundError, IsADirectoryError) as e:
            msg = 'Openai api key must either be passed into this function ' \
                  f'or stored in {config_path} with field name ' \
                  f'{var_name.lower()}. No key found.'
            if strict:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg + ' Not raising error because strict=False, '
                              'but openai API will not be available.')
                return
    os.environ[var_name] = key
    if update_config:
        update_yaml(config_path, **{var_name.lower(): key})


def model_context_window(model_name,
                         default=min(MODEL_CONTEXT_WINDOWS.values())):
    """Get context window (int) for a given model name. Relies on
    MODEL_CONTEXT_WINDOWS var in this module being updated manually.

    Parameters
    ----------
    model_name: str
        Model name to pass to langchain chat_class, e.g. 'gpt-3.5-turbo'.
        Typically specified in a prompt yaml file.
    default: int
        What to return if the model name isn't found in MODEL_CONTEXT_WINDOWS.
        Technically you could set this to any type (e.g. you could also
        choose to return None or float('inf') if the name was missing).

    Returns
    -------
    int
    """
    return MODEL_CONTEXT_WINDOWS.get(model_name, default)
