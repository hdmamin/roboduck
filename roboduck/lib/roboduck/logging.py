from logging import Logger
import sys
import warnings


# TODO: looks like sys.last_value isn't getting updated so the error that gets
# debugged is wrong.
class RoboDuckLogger(Logger):

    def __init__(self, name, *args, roboduck_kwargs=None, **kwargs):
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

    def _log(self, level, msg, args, exc_info=None, extra=None,
             stack_info=False):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        if isinstance(msg, Exception):
            from roboduck import errors
            errors.excepthook(type(msg), msg, msg.__traceback__,
                              **self.roboduck_kwargs)
            msg = sys.last_value
            errors.disable()

        return super()._log(level, msg, args, exc_info=exc_info,
                            extra=extra, stack_info=stack_info)