import warnings

from roboduck.debug import duck, DuckDB, CodeCompletionCache
from roboduck.langchain.chat import Chat, DummyChatModel
from roboduck.config import update_config, load_config, set_openai_api_key
from roboduck.ipy_utils import is_colab
from roboduck.utils import available_models


__version__ = '0.10.1'
set_openai_api_key()
if is_colab():
    warnings.warn(
        'It looks like you\'re using Google Colab, which may make your '
        'roboduck experience slightly sub-optimal (e.g. typing can be a bit '
        'laggy).'
    )
