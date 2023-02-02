"""
# This runs from command line but requires logic performed inside loop to be
# extracted out into its own function.
jurigged -v ~/tmp/reload.py

# This starts develoop repl. Changes made inside for loop seem to take effect.
jurigged --loop foo ~/tmp/reload.py
"""

from contextlib import contextmanager
from functools import wraps
import scipy
import traceback
import inspect
import jurigged
from jurigged import make_recoder
import sys
import textwrap
import time
import warnings


from htools import hr, save, is_ipy_name
from jabberwocky.openai_utils import GPT


fixed_foo_str = """
def foo(x):
    time.sleep(1)
    if x - 6:
        res = 1 / (x - 6)
    else:
        res = 0
    return 'FIXED: ' + str(res)
""".strip()


def truncate_generated_function(code):
	"""Try to extract one function or class generated by codex, which sometimes
	rambles on for a bit. Basic idea is that once we've started a 
	function/class, all following lines containing code belonging to that code
	block must be indented. If we encounter another non-indented line, this
	presumably means codex has started another function/method.

	TODO: Need to test this logic more. Another alternative is to try to parse
	the string into a code object but that might be slow (or not - I forget if
	# that's true.

	TODO: if it creates a function that calls another helper function, this 
	won't work. Maybe better to create custom stop sequence like ### and put
	that before the first function in our prompt.
	"""
	lines = code.strip().splitlines()
	# We expect the 
	seen_start_tok = False
	for i, row in enumerate(lines):
		if row.startswith(('def', 'class')):
			seen_start_tok = True
		if seen_start_tok and row and not row.startswith((' ', '\t')): break
	return '\n'.join(lines[:i]).strip()


# Triggers this error when trying to rewrite func:
# ValueError: Recoder for foo cannot be used to define foo
def auto_debug(fixed_func_str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                warnings.warn(f'Rewriting function due to error:\n{e}')
                recoder = make_recoder(func)
                recoder.patch(fixed_func_str)
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Works from cmd line. Seems to crash develoop though. Haven't identified why
# yet.
@contextmanager
def auto_debug_ctx(func, fixed_func_str):
    # TODO: check that specified func is actually the one to raise the error.
    # Or for now just assume the convention of using this ctx manager to make
    # a single function call.
    try:
        yield
    # (Running with develoop)
    # This happens on each iteration after our first fix. Don't want to keep
    # trying to rewrite func so we handle it separately. However, this does
    # restart the loop. Forget if that's intended behavior or it means we broke
    # develoop.
    except jurigged.loop.develoop.Abort:
        print('IN ABORT EXCEPT')
        pass
    except Exception as e:
        warnings.warn(f'Rewriting function {func} due to error:\n{e}')
        frame = sys.exc_info()[-1]
        while frame.tb_next:
            frame = frame.tb_next
        f_locals = {k: v for k, v in frame.tb_frame.f_locals.items()
                    if not is_ipy_name(k)}
        recoder = make_recoder(func)
        tb_pretty = traceback.format_exc().rstrip('\n')
        func_str = inspect.getsource(func).rstrip('\n')
        prompt = (
            'Executing this function caused an error. Fix the bug that caused '
            'the error by revising the function so that it will run '
            f'successfully.'
            f'\n\n# ERROR\n{e!r}'
            f'\n\n# FULL TRACEBACK\n{tb_pretty}'
            f'\n\n# LOCAL VARIABLES DURING FUNCTION EXECUTION\n{f_locals}'
            f'\n\n# BUGGY FUNCTION\n{func_str}'
            '\n\n# REVISED FUNCTION'
        ).strip()
        print(f'PROMPT:\n{prompt}')
        save(prompt, 'tmp/prompt.txt')
        query_kwargs = {
            'model': 'code-davinci-002',
            'temperature': 0.0,
            'top_p': 0.99,
            'max_tokens': 200,
            'frequency_penalty': 0.0,
            'presence_penalty': 0.0,
            'stop': ['"""', "'''", "```"],
            'version': 0
        }
        # res, res_full = GPT.query(prompt, **query_kwargs)
        # save(res[0], 'tmp/reply.txt')
        # TODO: before enabling, need to get sandboxing worked out to run code
        # safely.
        # TODO: maybe also use classifier(s) to check if dangerous to run.
        # TODO: adjust max_tokens based on input func length
        # TODO: logic/model/something to extract func from response (or find
        # better way to enforce ending. See tmp/reply.txt: model sometimes just
        # keeps going beyond the end of the function.
        # fixed_func_str = res[0]
        recoder.patch(fixed_func_str)


# @auto_debug(fixed_foo_str)
def foo(x):
    time.sleep(1)
    return 1 / (x - 6)


def main():
    # Note: need to extract logic that's performed in loop into a function when
    # running w/ plain jurigged. When using with develoop, it seems to spot
    # changes inside loop /shrug.
    # Jurigged doesn't update running loops.
    for i in range(10):
        with auto_debug_ctx(foo, fixed_foo_str):
            print(foo(i))
            print(inspect.getsource(foo))
            print('-'*3)
            hr()


if __name__ == '__main__':
    main()
