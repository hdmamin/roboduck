"""Miscellaneous functions to help us interact with langchain."""


MODEL_CONTEXT_WINDOWS = {
    'gpt-3.5-turbo': 4_096,
    'gpt-4': 8_192,
    'gpt-4-32k': 32_768,
    # Eventually would like to support anthropic's claude, but it's not
    # supported in roboduck v1 because they never gave me api access so I can't
    # test it. 🤷‍♂️.
    # 'claude': 8_000,
}


def model_context_window(model_name,
                         default=min(MODEL_CONTEXT_WINDOWS.values())):
    """Get context window (int) for a given model name. Relies on
    MODEL_CONTEXT_WINDOWS var in this module being updated manually.

    Parameters
    ----------
    model_name : str
        Model name to pass to langchain chat_class, e.g. 'gpt-3.5-turbo'.
        Typically specified in a prompt yaml file.
    default : int
        What to return if the model name isn't found in MODEL_CONTEXT_WINDOWS.
        Technically you could set this to any type (e.g. you could also
        choose to return None or float('inf') if the name was missing).

    Returns
    -------
    int
    """
    return MODEL_CONTEXT_WINDOWS.get(model_name, default)
