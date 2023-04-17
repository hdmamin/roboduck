import os
from pathlib import Path


def set_openai_api_key(key=None, config_path='~/.openai'):
    """Set OPENAI_API_KEY environment variable for langchain.

    Parameters
    ----------
    key: str or None
        Optionally pass in openai api key (str). If not provided, we check the
        config path and try to load a key. If it is provided, we don't check
        config_path.
    config_path: str or Path
        Local file containing openai api key and nothing else.
    """
    config_path = Path(config_path).expanduser()
    if not key:
        try:
            with open(config_path, 'r') as f:
                key = f.read().strip()
        except (FileNotFoundError, IsADirectoryError) as e:
            raise RuntimeError(
                'Openai api key must either be provided directly or stored '
                f'in {config_path}. No key found.'
            )
    os.environ['OPENAI_API_KEY'] = key
