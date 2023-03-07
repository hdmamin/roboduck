from logging import Logger
import sys
import warnings


# TODO: looks like sys.last_value isn't getting updated so the error that gets
# debugged is wrong.
class RoboDuckLogger(Logger):

    def __init__(self, name, *args, roboduck_kwargs=None, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.roboduck_kwargs = roboduck_kwargs or {}
        if self.roboduck_kwargs.get('auto', False):
            warnings.warn('You tried to set auto=False in roboduck_kwargs '
                          'but this must equal True. Overriding.')
        self.roboduck_kwargs['auto'] = True

    def _log(self, level, msg, args, exc_info=None, extra=None,
             stack_info=False):
        """
        Low-level logging routine which creates a LogRecord and then calls
        all the handlers of this logger to handle the record.
        """
        if isinstance(msg, Exception):
            from roboduck import errors
            errors.excepthook(sys.last_type, sys.last_value,
                              sys.last_traceback, **self.roboduck_kwargs)
            msg = sys.last_value
            errors.disable()

        return super()._log(level, msg, args, exc_info=exc_info,
                            extra=extra, stack_info=stack_info)