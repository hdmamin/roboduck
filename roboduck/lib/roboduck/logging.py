from logging import Logger, Formatter, StreamHandler, FileHandler
from pathlib import Path
import os
import sys
import warnings


# TODO: looks like sys.last_value isn't getting updated so the error that gets
# debugged is wrong.
class RoboDuckLogger(Logger):
    """Replacement for logging.Logger class that uses our errors module to
    log natural language explanations and fixes along with the original error.
    (More specifically, we just wait for the errors module to update the
    message in the original exception before logging.)
    """

    def __init__(self, name, *args, roboduck_kwargs=None,
                 fmt='%(asctime)s [%(levelname)s]: %(message)s', stdout=True,
                 path='', fmode='a', **kwargs):
        """
        Parameters
        ----------
        name: str
            Same as base logger name arg.
        args: any
            Additional positional args for base logger.
        roboduck_kwargs: dict or None
            Kwargs that can be passed to our debugger class (RoboDuckDB)
            constructor.
        fmt: str
            Defines logging format. The default format produces output like
            this when an error is logged:
            2023-03-08 19:20:52,514 [ERROR]: list indices must be integers or
            slices, not tuple
        path: str or Path
            If provided, we log to this file (the dir structure does not need
            to exist already). If None, we do not log to a file.
        fmode: str
            Write mode used when path is not None. Usually 'a' but 'w' might
            be a reasonable choice in some circumstances.
        kwargs: any
            Additional kwargs for the base logger.
        """
        super().__init__(name, *args, **kwargs)
        self.roboduck_kwargs = roboduck_kwargs or {}
        defaults = dict(auto=True, sleep=0, silent=True)
        for k, v in defaults.items():
            if self.roboduck_kwargs.get(k, v) != v:
                warnings.warn(
                    f'You tried to set {k}={self.roboduck_kwargs[k]} '
                    f'but it must equal {v} in logger.'
                )
        self.roboduck_kwargs.update(defaults)
        self._add_handlers(fmt, stdout, path, fmode)

    def _add_handlers(self, fmt, stdout, path, fmode):
        """Set up handlers to log to stdout and/or a file."""
        formatter = Formatter(fmt)
        handlers = []
        if stdout:
            handlers.append(StreamHandler(sys.stdout))
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
                              **self.roboduck_kwargs)
            msg = sys.last_value
            errors.disable()

        return super()._log(level, msg, args, exc_info=exc_info,
                            extra=extra, stack_info=stack_info)