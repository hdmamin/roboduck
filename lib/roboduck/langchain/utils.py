"""Miscellaneous functions to help us interact with langchain.
"""
import os
from pathlib import Path
import warnings


MODEL_CONTEXT_WINDOWS = {
    'gpt-3.5-turbo': 4_096,
    'gpt-4': 8_192,
    'gpt-4-32k': 32_768,
    'code-davinci-002': 8_001,
    'claude': 8_000,   # Anthropic says this is approximate.
}


def set_openai_api_key(key=None, config_path='~/.openai', strict=False):
    """Set OPENAI_API_KEY environment variable for langchain.

    Parameters
    ----------
    key: str or None
        Optionally pass in openai api key (str). If not provided, we check the
        config path and try to load a key. If it is provided, we don't check
        config_path.
    config_path: str or Path
        Local file containing openai api key and nothing else.
    strict: bool
        Determines what happens when key is None and config path does not
        exist. Strict=True raises a runtime error, False just warns user.
    """
    config_path = Path(config_path).expanduser()
    if not key:
        try:
            with open(config_path, 'r') as f:
                key = f.read().strip()
        except (FileNotFoundError, IsADirectoryError) as e:
            msg = 'Openai api key must either be passed into this function ' \
                  f'or stored in {config_path}. No key found.'
            if strict:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg + ' Not raising error because strict=False, '
                              'but openai API will not be available.')
                return
    os.environ['OPENAI_API_KEY'] = key


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
