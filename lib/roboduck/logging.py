"""Logger that attempts to diagnose and propose a solution for any errors it
is asked to log. Unlike our debugger and errors modules, explanations are
not streamed because the intended use case is not focused on live development.

Quickstart
----------
```
from roboduck import logging

logger = logging.getLogger(path='/tmp/log.txt')
data = {'x': 0}
try:
    x = data.x
except Exception as e:
    logger.error(e)
```
"""
from logging import Logger, Formatter, StreamHandler, FileHandler
from pathlib import Path
import os
import sys
import warnings


class DuckLogger(Logger):
    """Replacement for logging.Logger class that uses our errors module to
    log natural language explanations and fixes along with the original error.
    (More specifically, we just wait for the errors module to update the
    message in the original exception before logging.)
    """

    def __init__(self, name, colordiff=False,
                 fmt='%(asctime)s [%(levelname)s]: %(message)s', stdout=True,
                 path='', fmode='a', **kwargs):
        """
        Parameters
        ----------
        name : str
            Same as base logger name arg.
        colordiff : bool
            Another kwarg to pass to our excepthook function. This is separate
            from the others because we want to use a different default than the
            function has since we often log to a file, in which case
            colordiff=True may be undesirable.
        fmt : str
            Defines logging format. The default format produces output like
            this when an error is logged:
            2023-03-08 19:20:52,514 [ERROR]: list indices must be integers or
            slices, not tuple
        stdout : bool
            If True, logged items will appear in stdout. You are free to log
            to both stdout and a file OR just one (selecting neither will raise
            an error because logger would be useless in that case).
        path : str or Path
            If provided, we log to this file (the dir structure does not need
            to exist already). If None, we do not log to a file.
        fmode : str
            Write mode used when path is not None. Usually 'a' but 'w' might
            be a reasonable choice in some circumstances.
        kwargs : any
            Kwargs that can be passed to our excepthook function. Most of these
            should generally be kwargs for your debugger class,
            e.g. RoboDuckDb. These will be updated with the specified
            `colordiff` as well - we want to set the default to False here
             because we often want to log to a file, where this will probably
             not render correctly.
        """
        if not stdout and not path:
            raise RuntimeError(
                f'{type(self).__name__} requires that you set stdout=True '
                f'and/or provide a non-empty path. Currently, your logger '
                f'would do neither and be useless.'
            )

        super().__init__(name)
        self.excepthook_kwargs = kwargs or {}
        # Always want silent=True because we don't care about live typing here.
        # If stdout=True, our super()._log() call still ensures that we log to
        # stdout after the gpt call completes.
        defaults = dict(auto=True, sleep=0, silent=True, interactive=False)
        for k, v in defaults.items():
            if self.excepthook_kwargs.get(k, v) != v:
                warnings.warn(
                    f'You tried to set {k}={self.excepthook_kwargs[k]} '
                    f'but it must equal {v} in logger. Your arg will be'
                    f'overridden.'
                )
        self.excepthook_kwargs.update(defaults)
        self.excepthook_kwargs['colordiff'] = self.excepthook_kwargs.get(
            'colordiff', colordiff
        )
        self._add_handlers(fmt, stdout, path, fmode)

    def _add_handlers(self, fmt, stdout, path, fmode):
        """Set up handlers to log to stdout and/or a file."""
        formatter = Formatter(fmt)
        handlers = []
        if stdout:
            handlers.append(StreamHandler(sys.stdout))
        else:
            # If we don't set this when stdout is False, the root logger ends
            # up logging to stdout anyway.
            self.propagate = False

        if path:
            path = Path(path).resolve()
            os.makedirs(path.parent, exist_ok=True)
            handlers.append(FileHandler(path, fmode))
        for handler in handlers:
            handler.setFormatter(formatter)
            self.addHandler(handler)

    def _log(self, level, msg, args, exc_info=None, extra=None,
             stack_info=False):
        """This is where we insert our custom logic to get error explanations.
        We keep the import inside the method to avoid overwriting
        sys.excepthook whenever the logging module is imported.

        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        if isinstance(msg, Exception) and sys.exc_info()[2]:
            from roboduck import errors
            errors.excepthook(type(msg), msg, msg.__traceback__,
                              **self.excepthook_kwargs)
            msg = sys.last_value
            errors.disable()

        return super()._log(level, msg, args, exc_info=exc_info,
                            extra=extra, stack_info=stack_info)


def getLogger(name=None, **kwargs):
    """Mimics interface of builtin logging.getLogger, but with our custom
    logger that ensures all errors explain themselves.

    Parameters
    ----------
    kwargs : any
        These are passed to roboduck.errors.post_mortem which in turn passes
        them to our custom debugger class. The most important arg here is:

        prompt_name (str) - determines what prompt/prompt_name the custom
            debugger uses, e.g. "debug_stack_trace". Users can also define
            their own custom prompt
            (https://hdmamin.github.io/roboduck/custom_prompts/)
            and pass in the file path here.

    Examples
    --------
    ```
    from roboduck import logging

    logger = logging.getLogger()
    ```
    """
    return DuckLogger(name=name, **kwargs)