import os
from pathlib import Path


def set_openai_api_key(key=None, config_path='~/.openai'):
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
