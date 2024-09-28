"""Allow us to easily read from and write to roboduck's config file.

Roboduck creates a config file at `~/.roboduck/config.yaml`. You can also
change this path by setting the ROBODUCK_CONFIG_PATH environment variable
in a python script:

```python
import os

os.environ["ROBODUCK_CONFIG_PATH"] = "/Users/path/to/custom/config.yaml"
```

or by adding this to your ~/.bashrc file:

```bash
export ROBODUCK_CONFIG_PATH=/Users/path/to/custom/config.yaml
```

The config currently supports only two fields:

- `openai_api_key`: See the [Quickstart](https://hdmamin.github.io/roboduck/)
for setup help.

- `model_name` (optional): Roboduck is configured to use gpt-4o-mini by
default. This field lets you change that (e.g. to gpt-4). If present in the
config file, this will take priority over any model_name field specified in a
chat template
(e.g. our [default debug prompt template](https://github.com/hdmamin/roboduck/blob/7ff904972921fd3f82b8b9fd862c4ffc7b61aee4/lib/roboduck/prompts/chat/debug.yaml#L2)).
You can view valid options with `roboduck.available_models()`.
You can still override the config default by manually passing a value into a
function, e.g. `duck(model_name='gpt-4-32k')`.

You can manually edit your config file or use a command like
`roboduck.update_config(model_name='gpt-4')`. Passing in a value of None
(e.g. `roboduck.update_config(model_name=None)`) will delete that field from
your config file.
"""
import os
from pathlib import Path
import warnings
from typing import Dict, Any, Optional

from roboduck.utils import update_yaml, load_yaml


CONFIG_PATH = Path('~/.roboduck/config.yaml').expanduser()
# User can optionally set this to a custom path. This should still end
# with ".yaml" or ".yml".
CONFIG_PATH_ENV_VAR = "ROBODUCK_CONFIG_PATH"


def get_config_path() -> Path:
    """Get the path to the roboduck config file. We use this instead of just
    referencing the variable in case the user sets a custom location.

    Returns
    -------
    Path
        The path to the roboduck config file (yaml), either the default path
        or the path specified by the user-set environment variable.
    """
    return Path(os.environ.get(CONFIG_PATH_ENV_VAR, CONFIG_PATH))


def update_config(**kwargs) -> None:
    """Update roboduck config file with settings that persist for future
    sessions.

    Other fields may be configurable here in the future, but as of v1 this
    should really only be used to set openai_api_key and/or model_name.

    Parameters
    ----------
    kwargs : any
        Available fields include:
            - openai_api_key
            - model_name: name like 'gpt-4o-mini' that controls what model
            to use for completions. Model_name is resolved as follows:
            1. kwargs explicitly passed in by user (e.g.
            `duck(model_name='gpt-4')` always override everything else.
            2. if global config file (which this function updates) has a
            model_name, it is the next highest priority.
            3. specific chat template (e.g. roboduck/prompts/chat/debug.yaml)
            model name is used if neither #1 or #2 are provided.

            The reason for the global config taking priority over specific
            templates is that we want to make it easy for a user to always use
            a specific model that is not the roboduck default (i.e. without
            having to pass in a model_name in every single duck() call). This
            does come with the tradeoff of making it hard to define both a
            different default model AND a custom prompt template with yet
            another model, but that seems like a less common use case.

            Passing in a value of None indicates that the corresponding key
            should be deleted from the config file, NOT that we will explicitly
            set {field}: None.
    """
    recognized_keys = {'openai_api_key', 'model_name'}
    if set(kwargs) - recognized_keys:
        warnings.warn(f'You are setting unrecognized key(s): '
                      f'{set(kwargs) - recognized_keys}.')
    update_yaml(path=get_config_path(), delete_if_none=True, **kwargs)


def load_config() -> Dict[str, Any]:
    """Load roboduck config.

    Returns
    -------
    dict
    """
    config_path = get_config_path()
    if not config_path.is_file():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
    return load_yaml(path=config_path)


def apply_config_defaults(chat_kwargs: Dict[str, Any],
                          template_only: bool) -> None:
    """Help resolve model_name in place. Recall we prioritize sources in this
    order:

    1. value a user specified explicitly, e.g. Chat(..., model_name='gpt-4').
    2. value specified in roboduck config file
    3. value specified in a prompt template (can be native to roboduck or
    user-defined)

    Parameters
    ----------
    chat_kwargs : dict
        Kwargs to pass to our langchain.chat.Chat constructor. May include a
        model_name str field.
    template_only : bool
        Specifies whether chat_kwargs are passed in directly from a prompt
        template (template_only=True) or include kwargs that a user passed in
        explicitly (template_only=False).

    Returns
    -------
    None
        Update happens in place (if at all).
    """
    # If both are true, it means the user has already explicitly passed in a
    # model name so we should NOT override it with our config default.
    if 'model_name' in chat_kwargs and not template_only:
        return

    cfg = load_config()
    config_model_name = cfg.get('model_name', '')
    # We also don't want to add something like model_name='' if no default is
    # specified in the config. Better to revert to langchain class default than
    # set it to None, which could break things.
    if config_model_name:
        chat_kwargs['model_name'] = config_model_name


def set_openai_api_key(key: Optional[str] = None,
                       strict: bool = False,
                       update_config_: bool = False) -> None:
    """Set OPENAI_API_KEY environment variable for langchain.

    Parameters
    ----------
    key : str or None
        Optionally pass in openai api key (str). If not provided, we check the
        users's roboduck config and try to load a key (using the
        "openai_api_key" field). If `key` is provided, we don't check the
        config.
    strict : bool
        Determines what happens when key is None and the roboduck config does
        not exist. Strict=True raises a runtime error, False just warns user.
    update_config_ : bool
        If True, we update the roboduck yaml config file with the provided
        api key.
    """
    var_name = 'OPENAI_API_KEY'
    key = key or os.environ.get(var_name, '')
    if not key:
        try:
            data = load_config()
            key = data[var_name.lower()]
        except Exception as e:
            # Just creating this for warning/error message.
            config_path = get_config_path()
            msg = 'Openai api key must either be passed into this function ' \
                  f'or stored in {config_path} with field name ' \
                  f'{var_name.lower()}. No key found.'
            if strict:
                raise RuntimeError(msg)
            else:
                warnings.warn(msg + ' Not raising error because strict=False, '
                              'but openai API will not be available until you '
                              'make key available via one of these methods.')
                return

    if not key.startswith('sk-'):
        partially_redacted_key = key[:4] + '*'*max(0, len(key) - 4)
        warnings.warn(
            f'Your openai api key ({partially_redacted_key}) looks unusual. '
            f'Are you sure it\'s correct? (Key is partially redacted in '
            f'warning to err on the side of caution.)'
        )
    os.environ[var_name] = key
    if update_config_:
        update_config(**{var_name.lower(): key})
