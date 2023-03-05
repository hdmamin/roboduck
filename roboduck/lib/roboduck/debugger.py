import cmd
from functools import partial
from htools import load, is_ipy_name
import inspect
import ipynbname
from jabberwocky.openai_utils import PromptManager, GPTBackend
from pdb import Pdb
import sys
import time
import warnings

from roboduck.utils import type_annotated_dict_str, colored, load_ipynb, \
    truncated_repr, load_current_ipython_session


ROBODUCK_GPT = GPTBackend(log_stdout=False)
PROMPT_MANAGER = PromptManager(['debug', 'debug_full', 'debug_stack_trace'],
                               verbose=False,
                               gpt=ROBODUCK_GPT)


class CodeCompletionCache:
    """Just stores the last completion from RoboDuckDB in a way that our
    `duck` jupyter magic can access (without relying on global variable, though
    not sure if this is meaningfully different). The magic only needs to access
    it in insert mode (-i flag) to insert the fixed code snippet into a new
    code cell.
    """
    last_completion = ''


class RoboDuckDB(Pdb):
    """Conversational debugger powered by gpt models (currently codex, possibly
    eventually chatGPT). Once you're in a debugging session, any user command
    containing a question mark will be interpreted as a question for gpt.
    Prefixing your question with "[dev]" will print out the full prompt before
    making the query.
    """

    def __init__(self, *args, backend='openai', model=None,
                 task='debug', log=False, max_len_per_var=79, **kwargs):
        """
        Parameters
        ----------
        args: any
            Misc args for base Pdb class.
        backend: str
            Specifies which GPT api to use, e.g. 'openai' or 'gooseai'. Since
            we currently use codex, backends besides 'openai' are not
            supported.
        model: str or int or None
            Specifies which model to using format defined by
            jabberwocky.openai_utils.EngineMap. If none is specified, we fall
            back to whatever is defined in the jabberwocky `debug` or
            `debug_full` prompts. 'code-davinci-002' is the current default,
            though 'text-davinci-002' may be a decent option as well.
        full_context: bool
            If True, provide the whole notebook source code to gpt
            (when used in a script, this has no effect). This
            increases the risk of creating a prompt that is too long. Note that
            even when full_context=False, global variables with names that
            appear in the relevant code snippet will be sent to gpt.
        log: bool
            Specifies whether jabberwocky should log gpt api calls. If true,
            these are stored as jsonlines files.
        max_len_per_var: int
            Limits number of characters per variable when communicating
            current state (local or global depending on `full_context`) to
            gpt. If unbounded, that section of the prompt alone could grow
            very big . I somewhat arbitrarily set 79 as the default, i.e.
            1 line of python per variable. I figure that's usually enough to
            communicate the gist of what's happening.
        kwargs: any
            Additional kwargs for base Pdb class.
        """
        super().__init__(*args, **kwargs)
        self.prompt = '>>> '
        self.duck_prompt = '[Duck] '
        # Check if None explicitly because model=0 is different.
        self.query_kwargs = {'model': model} if model is not None else {}
        self.backend = backend
        self.full_context = '_full' in task
        self.field_names = PROMPT_MANAGER.field_names(task)
        self.task = task
        self.log = log
        self.repr_func = partial(truncated_repr, max_len=max_len_per_var)

    def _get_prompt_kwargs(self):
        """Construct a dictionary describing the current state of our code
        (variable names and values, source code, file type). This will be
        passed to our jabberwocky PromptManager to fill in the debug prompt
        template.

        Returns
        -------
        dict: contains keys 'code', 'local_vars', 'global_vars', 'file_type'.
        If we specified full_context=True on init, we also include the key
        'full_code'.
        """
        res = {}

        # Get current code snippet.
        # TODO: fails when running code from cmd line like:
        # 'python -c "print(x)"'.
        try:
            res['code'] = inspect.getsource(self.curframe)
        except OSError as err:
            self.error(err)
        res['local_vars'] = type_annotated_dict_str(
            {k: v for k, v in self.curframe_locals.items()
             if not is_ipy_name(k)},
            self.repr_func
        )

        # Get full source code if necessary.
        if self.full_context:
            # File is a string, either a file name or something like
            # <ipython-input-50-e97ed612f523>.
            file = inspect.getsourcefile(self.curframe.f_code)
            if file.startswith('<ipython'):
                # If we're in ipython, ipynbname.path() throws a
                # FileNotFoundError.
                try:
                    res['full_code'] = load_ipynb(ipynbname.path())
                    res['file_type'] = 'jupyter notebook'
                except FileNotFoundError:
                    # TODO: maybe ipython session needs to use a modified
                    # version of this func regardless of self.full_context,
                    # and should return full code as list initially and
                    # override res['code'] with last executed cell. Otherwise
                    # I think getsource(curframe) may load a lot more code than
                    # we usually want in ipython session.
                    res['full_code'] = load_current_ipython_session()
                    res['file_type'] = 'ipython session'
            else:
                res['full_code'] = load(file, verbose=False)
                res['file_type'] = 'python script'
            used_tokens = set(res['full_code'].split())
        else:
            # This is intentionally different from the used_tokens line in the
            # if clause - we only want to consider local code here.
            used_tokens = set(res['code'].split())

        # Namespace is often polluted with lots of unused globals (htools is
        # very much guilty of this 😬) and we don't want to clutter up the
        # prompt with these.
        res['global_vars'] = type_annotated_dict_str(
            {k: v for k, v in self.curframe.f_globals.items()
             if k in used_tokens and not is_ipy_name(k)},
            self.repr_func
        )
        return res

    def onecmd(self, line):
        """Base class describes this as follows:

        Interpret the argument as though it had been typed in response to the
        prompt. Checks whether this line is typed at the normal prompt or in
        a breakpoint command list definition.

        We add an extra check in the if block to check if the user asked a
        question. If so, we ask gpt. If not, we treat it as a regular pdb
        command.

        Parameters
        ----------
        line: str or tuple
            If str, this is a regular line like in the standard debugger.
            If tuple, this contains (line str, stack trace str - see
            roboduck.errors.post_mortem for the actual insertion into the
            cmdqueue). This is for use with the debug_stack_trace mode.
        """
        if isinstance(line, tuple):
            line, stack_trace = line
        else:
            stack_trace = ''
        if not self.commands_defining:
            if '?' in line:
                return self.ask_language_model(
                    line,
                    stack_trace=stack_trace,
                    verbose=line.startswith('[dev]')
                )
            return cmd.Cmd.onecmd(self, line)
        else:
            return self.handle_command_def(line)

    def ask_language_model(self, question, stack_trace='', verbose=False):
        """When the user asks a question during a debugging session, query
        gpt for the answer and type it back to them live.

        Parameters
        ----------
        question: str
            User question, e.g. "Why are the first three values in nums equal
            to 5 when the input list only had a single 5?". (Example is from
            a faulty bubble sort implementation.)
        stack_trace: str
            When using the "debug_stack_trace" prompt, we need to pass a
            stack trace string into the prompt.
        verbose: bool
            If True, print the full gpt prompt in red before making the api
            call. User activates this mode by prefixing their question with
            '[dev]'.
        """
        prompt_kwargs = self._get_prompt_kwargs()
        if 'question' in self.field_names:
            prompt_kwargs['question'] = question
        expect_stack_trace = 'stack_trace' in self.field_names
        if stack_trace and expect_stack_trace:
            prompt_kwargs['stack_trace'] = stack_trace
        assert bool(stack_trace) == expect_stack_trace,\
            f'Received stack_trace={stack_trace!r} but ' \
            f'self.field_names={self.field_names}.'

        prompt = PROMPT_MANAGER.prompt(self.task, prompt_kwargs)
        if len(prompt.split()) > 1_000:
            warnings.warn(
                'Prompt is very long (>1k words). You\'re approaching a risky'
                ' zone where your prompt + completion might exceed the max '
                'sequence length.'
            )
        if verbose:
            print(colored(prompt, 'red'))

        print(colored(self.duck_prompt, 'green'), end='')
        res = ''
        # Suppress jabberwocky auto-warning about codex model name.
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore')
            with ROBODUCK_GPT(self.backend, verbose=False):
                prev_is_title = False
                for i, (cur, full) in enumerate(PROMPT_MANAGER.query(
                        self.task,
                        prompt_kwargs,
                        **self.query_kwargs,
                        log=self.log,
                        stream=True
                )):
                    # We do this BEFORE the checks around SOLUTION PART 2
                    # because we don't want to print that line, but we do want
                    # to retain it in our CodeCompletionCache so that our
                    # jupyter magic can easily extract the code portion later.
                    res += cur

                    # Slightly fragile logic - openai currently returns this
                    # in a single streaming step even though the current codex
                    # tokenizer splits it into 5 tokens. If they return this
                    # as multiple tokens, we'd need to change this logic.
                    if cur == 'SOLUTION PART 2':
                        prev_is_title = True
                        continue
                    # Avoid printing the ':' after 'SOLUTION PART 2'. Openai
                    # returns this at a different streaming step.
                    if prev_is_title and cur.startswith(':'):
                        continue
                    prev_is_title = False
                    if not i:
                        cur = cur.lstrip('\n')
                    for char in cur:
                        print(colored(char, 'green'), end='')
                        time.sleep(.02)

        # Strip trailing quotes because the entire prompt is inside a
        # docstring and codex may try to close it. We can't use it as a stop
        # phrase in case codex generates a fixed code snippet that includes
        # a docstring.
        answer = res.strip()
        if not answer:
            answer = 'Sorry, I don\'t know. Can you try ' \
                     'rephrasing your question?'
            print(colored(answer, 'green'))

        # When using the `duck` jupyter magic in "insert" mode, we reference
        # the CodeCompletionCache to populate the new code cell.
        CodeCompletionCache.last_completion = answer

    def precmd(self, line):
        """We need to define this to make our errors module work. Our
        post_mortem function sometimes places a tuple in our debugger's
        cmdqueue and precmd is called as part of the default cmdloop method.
        Technically it calls postcmd too but we don't need to override that
        because it does nothing with its line argument.
        """
        if isinstance(line, tuple):
            line, trace = line
            return super().precmd(line), trace
        return super().precmd(line)


def duck(backend='openai', model=None, **kwargs):
    # Equivalent of native breakpoint().
    RoboDuckDB(backend=backend, model=model, **kwargs)\
        .set_trace(sys._getframe().f_back)