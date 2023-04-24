"""Miscellaneous functions to help us interact with langchain.
"""
import os
from pathlib import Path
import warnings


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
            msg = 'Openai api key must either be provided directly or stored '\
                f'in {config_path}. No key found.'
            if strict:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg + ' Not raising error because strict=False, '
                              'but openai API will not be available.')
                return
    os.environ['OPENAI_API_KEY'] = key
