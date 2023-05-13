from roboduck.debug import duck, DuckDB, CodeCompletionCache
from roboduck.langchain.chat import Chat, DummyChatModel
from roboduck.config import update_config, load_config, set_openai_api_key
from roboduck.utils import available_models


__version__ = '0.2.0'
set_openai_api_key()
# TODO rm
import os
print('after:', os.environ.get('OPENAI_API_KEY'))
