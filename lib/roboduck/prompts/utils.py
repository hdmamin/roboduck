"""Utilities for working with prompts (usually prompt templates, to be more
precise).
"""
from pathlib import Path

from roboduck.utils import load_yaml


PROMPT_DIR = Path(__file__).parent
VALID_MODES = set(p.name for p in PROMPT_DIR.iterdir() if p.is_dir()
                  and not p.name.startswith('_'))


def available_templates(mode=''):
    """List names of prompts included in roboduck.

    Parameters
    ----------
    mode : str
        Type of prompt template to list available names for, e.g. "chat" or
        "completion". Concretely, the name of a subdir in roboduck.prompts.
        If empty, return a dict mapping mode -> set of names rather than just
        the set of names.

    Returns
    -------
    dict[str, set[str]] or set[str]
        If mode is an empty str, we return a dict mapping keys (should be
        "chat" and "completion") to set of prompt name strings, e.g. "debug"
        (notice file extension is excluded). If a non-empty string is provided,
        we only return the set of strings for the given mode, e.g. only the
        available chat prompts if mode='chat'.
    """
    def _prompt_names_in_dir(dir_):
        # Ignore files like __template__.yaml.
        return set(path.stem for path in dir_.iterdir()
                   if path.suffix == '.yaml'
                   and not path.stem.startswith('__'))

    assert isinstance(mode, str), f'Mode should be type str, not {type(mode)}.'
    keys = [mode] if mode else VALID_MODES
    for key in keys:
        if key not in VALID_MODES:
            raise ValueError(
                f'Encountered unrecognized key "{key}". This might mean you '
                f'specified an invalid mode. Valid modes are: {VALID_MODES}.'
            )

    res = {key: _prompt_names_in_dir(PROMPT_DIR/key) for key in keys}
    return next(iter(res.values())) if len(keys) == 1 else res


def load_template(name, mode='chat'):
    """Load prompt template from the roboduck library or a user-provided yaml
    file.

    Parameters
    ----------
    name : str or Path
        Either the name of a prompt provided in the roboduck library, e.g.
        "debug", or the path to a yaml config file defining a custom prompt
        template.
    mode : str
        Type of prompt, currently either "chat" or "completion". As of March
        2023, we usually want to use "chat" because those models
        (gpt-3.5-turbo or gpt-4) are currently better for most tasks and,
        I believe, cheaper for a comparable model
        (e.g. gpt-3.5-turbo vs text-davinci-002).

    Returns
    -------
    dict
        Chat templates should have the following keys:
        "kwargs" (dict): used to instantiate a class like
        langchain.chat.ChatOpenAI. Mostly openai params but can also include
        'chat_model' for langchain. Note that unlike jabberwocky, we use the
        name max_tokens instead of max_length.

        "system" (str): system message (see openai chat model api docs).
        This should not contain user-specified fields.

        "user" (dict[str]): Allows you to specify multiple types of user
        messages for chat models (see openai chat model api docs). These will
        often contain fields the user will provide at runtime. If multiple
        message types are provided, the first one in the dict will be used as
        the default.
    """
    templates = available_templates(mode=mode)
    if name in templates:
        path = PROMPT_DIR/f'{mode}/{name}.yaml'
    elif Path(name).expanduser().is_file():
        path = Path(name)
    else:
        raise ValueError(
            f'`name` must either be a built-in roboduck prompt or a path to '
            f'a yaml file on your machine. "{name}" appears to be neither. '
            f'For your requested mode "{mode}", available options are: '
            f'{templates}.'
        )
    return load_yaml(path)
