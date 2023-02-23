from functools import wraps
import pdb
import sys
import traceback


def monkeypatch(obj, attr):
    def decorator(func):
        print(f'Registering function {func} as {obj}.{attr}.')
        setattr(obj, attr, func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


@monkeypatch(sys, 'excepthook')
def excepthook(type_, val, tb):
    traceback.print_exception(type_, val, tb)
    pdb.post_mortem(tb)


def main():
    x = 3
    y = 'z'
    return x + y

if __name__ == '__main__':
    res = main()
    print()
    print('Afterwards')
    print(res)


# NOTE: below is old attempt at doing this. Never quite got it working though,
# above approach is better.
# """Trying to prototype my idea for a way to run a script that enters an
# interactive session on failure and lets us debug and resume execution. Not
# working yet though - haven't figured out how to access vars inside called
# function.
# """
#
# from functools import wraps
# import linecache
# import time
# import sys
#
#
# def debuggable(func):
#     @wraps(func)
#     def wrapper(*args, **kwargs):
#         try:
#             res = func(*args, **kwargs)
#         except Exception as e:
#             print(e)
#             breakpoint()
#         return res
#     return wrapper
#
#
# @debuggable
# def main(n=10):
#     for i in range(n):
#         time.sleep(.5)
#         try:
#             print(2 / (i - 3))
#         except Exception as e:
#             cls, err, trace = sys.exc_info()
#             frame = trace.tb_frame
#             fname = frame.f_code.co_filename
#             linecache.checkcache(fname)
#             line = linecache.getline(fname, trace.tb_lineno, frame.f_globals)
#             print(line)
#             print(err)
#
#
# if __name__ == '__main__':
#     main()

