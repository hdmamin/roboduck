from logging import Logger, Formatter, StreamHandler, FileHandler
from pathlib import Path
import os
import sys
import warnings


# TODO: looks like sys.last_value isn't getting updated so the error that gets
# debugged is wrong.
class RoboDuckLogger(Logger):

    def __init__(self, name, *args, roboduck_kwargs=None,
                 fmt='%(asctime)s [%(levelname)s]: %(message)s', stdout=True,
                 path='', fmode='a', **kwargs):
        """TODO docs

        Parameters
        ----------
        name
        args
        roboduck_kwargs
        fmt
        path
        fmode
        kwargs
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
        """
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