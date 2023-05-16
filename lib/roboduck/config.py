"""Allow us to easily read from and write to roboduck's config file.

Roboduck creates a config file at `~/.roboduck/config.yaml`. This currently
supports only two fields:

- `openai_api_key`: See the [Quickstart](https://hdmamin.github.io/roboduck/)
for setup help.

- `model_name` (optional): Roboduck is configured to use gpt-3.5-turbo by
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

from roboduck.utils import update_yaml, load_yaml


config_path = Path('~/.roboduck/config.yaml').expanduser()


def update_config(config_path=config_path, **kwargs):
    """Update roboduck config file with settings that persist for future
    sessions.

    Other fields may be configurable here in the future, but as of v1 this
    should really only be used to set openai_api_key and/or model_name.

    Parameters
    ----------
    config_path : str or Path
        Location of the roboduck config file.
    kwargs : any
        Available fields include:
            - openai_api_key
            - model_name: name like 'gpt-3.5-turbo' that controls what model
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
    update_yaml(path=config_path, delete_if_none=True, **kwargs)


def load_config(config_path=config_path):
    """Load roboduck config.

    Parameters
    ----------
    config_path : str or Path
        Location of the roboduck config file.

    Returns
    -------
    dict
    """
    config_path = Path(config_path)
    if not config_path.is_file():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.touch()
    return load_yaml(path=config_path)


def apply_config_defaults(chat_kwargs, template_only, config_path=config_path):
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
    config_path : str or Path
        Location of the roboduck config file.

    Returns
    -------
    None
        Update happens in place (if at all).
    """
    # If both are true, it means the user has already explicitly passed in a
    # model name so we should NOT override it with our config default.
    if 'model_name' in chat_kwargs and not template_only:
        return

    cfg = load_config(config_path=config_path)
    config_model_name = cfg.get('model_name', '')
    # We also don't want to add something like model_name='' if no default is
    # specified in the config. Better to revert to langchain class default than
    # set it to None, which could break things.
    if config_model_name:
        chat_kwargs['model_name'] = config_model_name


def set_openai_api_key(key=None, config_path=config_path,
                       strict=False, update_config_=False):
    """Set OPENAI_API_KEY environment variable for langchain.

    Parameters
    ----------
    key : str or None
        Optionally pass in openai api key (str). If not provided, we check the
        config path and try to load a key. If it is provided, we don't check
        config_path.
    config_path : str or Path
        Local yaml file containing the field openai_api_key. We only try to
        load the key from it if `key` is not provided. We do not write to
        this file by default.
    strict : bool
        Determines what happens when key is None and config path does not
        exist. Strict=True raises a runtime error, False just warns user.
    update_config_ : bool
        If True, we update the yaml config file with that api key.
    """
    config_path = Path(config_path).expanduser()
    var_name = 'OPENAI_API_KEY'
    key = key or os.environ.get(var_name)
    if not key:
        try:
            data = load_config(config_path)
            key = data[var_name.lower()]
        except Exception as e:
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
    if update_config_:
        update_config(config_path, **{var_name.lower(): key})