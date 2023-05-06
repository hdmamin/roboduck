import inspect
import pytest

from roboduck.langchain.chat import Chat, DummyChatModel


@pytest.mark.parametrize(
    'name',
    [
        'debug',
        'debug_full',
        'debug_stack_trace',
        'debug_full_stack_trace',
    ]
)
def test_chat_generated_methods(name):
    chat = Chat.from_config(name)
    field_names = chat.input_variables()
    assert hasattr(chat, 'contextful') and callable(chat.contextful)
    assert hasattr(chat, 'contextless') and callable(chat.contextless)
    assert field_names == \
           set(inspect.signature(chat.reply).parameters) - {'key_'}

    # Either both or neither should be present.
    assert ('full_code' in field_names) + ('full' in name) != 1
    assert ('stack_trace' in field_names) + ('stack_trace' in name) != 1


def test_chat_extra_kwargs():
    chat = Chat.from_config('debug', chat_class=DummyChatModel)
    assert isinstance(chat.chat, DummyChatModel)

    temp = .637
    max_tokens = 28
    chat = Chat.from_config('debug', temperature=temp, max_tokens=max_tokens)
    assert chat.kwargs['temperature'] == temp
    assert chat.kwargs['max_tokens'] == max_tokens
