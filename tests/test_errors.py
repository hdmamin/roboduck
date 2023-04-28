from functools import partial
import pytest
import sys

from roboduck import DummyChatModel


def test_enable_disable_errors():
    old_hook = sys.excepthook

    from roboduck import errors
    errors.enable(auto=True, chat_class=DummyChatModel)
    hook = sys.excepthook
    errors.disable()

    # Disable BEFORE asserts. We don't want roboduck auto errors behavior to
    # kick in if a test fails.
    assert isinstance(hook, partial)
    assert hook.func == errors.excepthook
    assert sys.excepthook == old_hook
