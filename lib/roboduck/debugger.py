"""A conversational debugger and drop-in replacement for pdb. Python's default
interactive debugging session is already a crude conversation with your
program or interpreter, in a sense - this just lets your program communicate to
you more effectively.

Quickstart
----------
# Our replacement for python's `breakpoint`.
from roboduck.debugger import duck

# Broken version of bubble sort. Notice the duck() call on the second to last
# line.
def bubble_sort(nums):
    for i in range(len(nums)):
        for j in range(len(nums)):
            if nums[j] > nums[j + 1]:
                nums[j + 1], nums[j] = nums[j], nums[j + 1]
                duck()
    return nums
"""
import cmd
from functools import partial
from htools import load, is_ipy_name
import inspect
import ipynbname
from pdb import Pdb
import sys
import time
import warnings

from htools.meta import add_docstring
from roboduck.langchain.chat import Chat
from roboduck.utils import type_annotated_dict_str, colored, load_ipynb, \
    truncated_repr, load_current_ipython_session, colordiff_new_str, \
    parse_completion, store_class_defaults


@store_class_defaults(attr_filter=lambda x: x.startswith('last_'))
class CodeCompletionCache:
    """Just stores the last completion from DuckDB in a way that our
    `duck` jupyter magic can access (without relying on global variable, though
    not sure if this is meaningfully different). The magic only needs to access
    it in insert mode (-i flag) to insert the fixed code snippet into a new
    code cell.
    """
    last_completion = ''
    last_explanation = ''
    last_code = ''
    last_new_code = ''
    last_code_diff = ''
    last_extra = {}


class DuckDB(Pdb):
    """Conversational debugger powered by gpt models (currently codex, possibly
    eventually chatGPT). Once you're in a debugging session, any user command
    containing a question mark will be interpreted as a question for gpt.
    Prefixing your question with "[dev]" will print out the full prompt before
    making the query.
    """

    def __init__(self, prompt_name='debug', max_len_per_var=79, silent=False,
                 pdb_kwargs=None, parse_func=parse_completion, **chat_kwargs):
        """
        Parameters
        ----------
        prompt_name: str
            Name of prompt template to use when querying chatGPT. Roboduck
            currently provides several builtin options
            (see roboduck.prompts.chat):
                debug - for interactive debugging sessions on the relevant
                    snippet of code.
                debug_full - for interactive debugging sessions on the whole
                    notebook (no difference from "debug" for scripts). Risks
                    creating a context that is too long.
                debug_stack_trace - for automatic error explanations or
                    logging.
            Alternatively, can also define your own template in a yaml file
            mimicking the format of the builtin templates and pass in the
            path to that file as a string.
        max_len_per_var: int
            Limits number of characters per variable when communicating
            current state (local or global depending on `full_context`) to
            gpt. If unbounded, that section of the prompt alone could grow
            very big . I somewhat arbitrarily set 79 as the default, i.e.
            1 line of python per variable. I figure that's usually enough to
            communicate the gist of what's happening.
        silent: bool
            If True, print gpt completions to stdout. One example of when False
            is appropriate is our logging module - we want to get the
            explanation and update the exception message which then gets
            logged, but we don't care about typing results in real time.
        pdb_kwargs: dict or None
            Additional kwargs for base Pdb class.
        parse_func: function
            This will be called on the generated text each time gpt provides a
            completion. It returns a dictionary whose values will be stored
            in CodeCompletionCache in this module. See the default function's
            docstring for guidance on writing a custom function.
        chat_kwargs: any
            Additional kwargs to configure our Chat class (passed to
            its `from_config` factory). Common example would be setting
            `chat_class=roboduck.langchain.chat.DummyChatModel`
            which mocks api calls (good for development, saves money).
        """
        super().__init__(**pdb_kwargs or {})
        self.prompt = '>>> '
        self.duck_prompt = '[Duck] '
        self.query_kwargs = {}
        chat_kwargs['streaming'] = not silent
        chat_kwargs['name'] = prompt_name
        # Must create self.chat before setting _chat_prompt_keys,
        # and full_context after both of those.
        self.chat = Chat.from_config(**chat_kwargs)
        self.default_user_key, self.backup_user_key = self._chat_prompt_keys()
        self.full_context = 'full_code' in self.field_names()
        self.prompt_name = prompt_name
        self.repr_func = partial(truncated_repr, max_len=max_len_per_var)
        self.silent = silent
        self.parse_func = parse_func
        # This gets updated every time the user asks a question.
        self.prev_kwargs_hash = None

    def _chat_prompt_keys(self):
        """Retrieve default and backup user reply prompt keys (names) from
        self.chat object. If the prompt template has only one reply type,
        the backup key will equal the default key.
        """
        keys = list(self.chat.user_templates)
        default = keys[0]
        backup = default
        if len(keys) > 1:
            backup = keys[1]
            if len(keys) > 2:
                warnings.warn(
                    'You\'re using a chat prompt template with >2 types or '
                    'user replies. This is not recommended because it\'s '
                    'not clear how to determine which reply type to use. We '
                    'arbitrarily choose the first non-default key as the '
                    f'backup reply type ("{backup}").'
                )
        return default, backup

    def field_names(self, key=''):
        """Get names of variables that are expected to be passed into default
        user prompt template.
        """
        return self.chat.input_variables(key)

    def _get_next_line(self, code_snippet):
        """Retrieve next line of code that will be executed. Must call this
        before we remove the duck() call.

        Parameters
        ----------
        code_snippet: str
        """
        lines = code_snippet.splitlines()
        max_idx = len(lines) - 1

        # Adjust f_lineno because it's 1 - indexed by default.
        # Set default next_line in case we don't find any valid line.
        line_no = self.curframe.f_lineno - 1
        next_line = ''
        while line_no <= max_idx:
            if lines[line_no].strip().startswith('duck('):
                line_no += 1
            else:
                next_line = lines[line_no]
                break
        return next_line

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
        # Fails when running code from cmd line like:
        # 'python -c "print(x)"'.
        # Haven't been able to find a way around this yet.
        try:
            # Find next line before removing duck call to avoid messing up our
            # index.
            code_snippet = inspect.getsource(self.curframe)
            res['next_line'] = self._get_next_line(code_snippet)
            res['code'] = self._remove_debugger_call(code_snippet)
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
                    full_code = load_ipynb(ipynbname.path())
                    res['file_type'] = 'jupyter notebook'
                except FileNotFoundError:
                    # TODO: maybe ipython session needs to use a modified
                    # version of this func regardless of self.full_context,
                    # and should return full code as list initially and
                    # override res['code'] with last executed cell. Otherwise
                    # I think getsource(curframe) may load a lot more code than
                    # we usually want in ipython session.
                    full_code = load_current_ipython_session()
                    res['file_type'] = 'ipython session'
            else:
                full_code = load(file, verbose=False)
                res['file_type'] = 'python script'
            res['full_code'] = self._remove_debugger_call(full_code)
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

    @staticmethod
    def _remove_debugger_call(code_str):
        """Remove `duck` function call (our equivalent of `breakpoint` from
        source code string. Including it introduces a slight risk that gpt
        will fixate on this mistery function as a potential bug cause.
        """
        return '\n'.join(line for line in code_str.splitlines()
                         if not line.strip().startswith('duck('))

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
        # Don't provide long context-laden prompt if nothing has changed since
        # the user's last question. This is often a followup/clarifying
        # question.
        prompt_kwargs = self._get_prompt_kwargs()
        kwargs_hash = hash(str(prompt_kwargs))
        if kwargs_hash == self.prev_kwargs_hash:
            prompt_kwargs.clear()
            prompt_key = self.default_user_key
        else:
            prompt_key = self.backup_user_key

        # Perform surgery on kwargs depending on what fields are expected.
        field_names = self.field_names(prompt_key)
        if 'question' in field_names:
            prompt_kwargs['question'] = question
        expect_stack_trace = 'stack_trace' in field_names
        if stack_trace and expect_stack_trace:
            prompt_kwargs['stack_trace'] = stack_trace
        assert bool(stack_trace) == expect_stack_trace,\
            f'Received stack_trace={stack_trace!r} but ' \
            f'field_names={field_names}.'

        prompt = self.chat.user_message(key_=prompt_key, **prompt_kwargs)
        if len(prompt.split()) > 1_000:
            warnings.warn(
                'Prompt is very long (>1k words). You\'re approaching a risky'
                ' zone where your prompt + completion might exceed the max '
                'sequence length.'
            )
        if verbose:
            print(colored(prompt, 'red'))

        if not self.silent:
            print(colored(self.duck_prompt, 'green'), end='')
        res = self.chat.reply(**prompt_kwargs, key_=prompt_key)

        # Strip trailing quotes because the entire prompt is inside a
        # docstring and codex may try to close it. We can't use it as a stop
        # phrase in case codex generates a fixed code snippet that includes
        # a docstring.
        answer = res.strip()
        if not answer:
            answer = 'Sorry, I don\'t know. Can you try ' \
                     'rephrasing your question?'
            # This is intentionally nested in if statement because if answer is
            # truthy, we will have already printed it via our callback if not
            # in silent mode.
            if not self.silent:
                print(colored(answer, 'green'))

        parsed_kwargs = self.parse_func(answer)
        # When using the `duck` jupyter magic in "insert" mode, we reference
        # the CodeCompletionCache to populate the new code cell.
        CodeCompletionCache.last_completion = answer
        CodeCompletionCache.last_explanation = parsed_kwargs['explanation']
        # TODO: maybe check if code or full_code is more appropriate to store
        # as last_code, either depending on self.full_context or by doing a
        # quick str similarity to each.
        old_code, new_code = prompt_kwargs['code'], parsed_kwargs['code']
        CodeCompletionCache.last_code_diff = colordiff_new_str(old_code,
                                                               new_code)
        CodeCompletionCache.last_code = old_code
        CodeCompletionCache.last_new_code = new_code
        CodeCompletionCache.last_extra = parsed_kwargs.get('extra', {})
        self.prev_kwargs_hash = kwargs_hash

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


@add_docstring(DuckDB.__init__)
def duck(**kwargs):
    """Roboduck equivalent of native python breakpoint().
    The DuckDB docstring is below. Any kwargs passed in to this function
    will be passed to its constructor.
    """
    DuckDB(**kwargs).set_trace(sys._getframe().f_back)
