import pytest
import time

from roboduck.langchain import callbacks


def test_live_typing_callback_prints(capfd):
    callback = callbacks.LiveTypingCallbackHandler()
    callback.on_llm_new_token('hello')
    out, _ = capfd.readouterr()
    # Pretty weak test but it's hard to test exact output because pytest does
    # some weird color-related stuff here. At least confirm that something is
    # printed. ¯\_(ツ)_/¯
    assert out


def test_live_typing_callback_sleeps():
    sleep = .31
    token = 'about'
    callback = callbacks.LiveTypingCallbackHandler(sleep=sleep)
    start = time.perf_counter()
    callback.on_llm_new_token(token)
    end = time.perf_counter()
    elapsed = end - start
    # Not counting non-sleep time since that's trivial. We account for that by
    # leaving a little wiggle room in the test.
    expected = len(token)*sleep
    print(expected, elapsed)
    # Allow 2% deviation to account for time to execute actual printing.
    assert abs(elapsed - expected) / expected <= .02
