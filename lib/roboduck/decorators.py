"""Miscellaneous decorators used throughout the library."""
import warnings
from functools import partial, wraps
from inspect import signature, Parameter


def typecheck(func_=None, **types):
    """Decorator to enforce type checking for a function or method. There are
    two ways to call this: either explicitly passing argument types to the
    decorator, or letting it infer them using type annotations in the function
    that will be decorated. We allow both usage methods since older
    versions of Python lack type annotations, and also because I feel the
    annotation syntax can hurt readability.

    Ported from [htools](https://github.com/hdmamin/htools) to avoid extra
    dependency.

    Parameters
    ----------
    func_ : function
        The function to decorate. When using decorator with
        manually-specified types, this is None. Underscore is used so that
        `func` can still be used as a valid keyword argument for the wrapped
        function.
    types : type
        Optional way to specify variable types. Use standard types rather than
        importing from the typing library, as subscripted generics are not
        supported (e.g. typing.List[str] will not work; typing.List will but at
        that point there is no benefit over the standard `list`).

    Examples
    --------
    In the first example, we specify types directly in the decorator. Notice
    that they can be single types or tuples of types. You can choose to
    specify types for all arguments or just a subset.

    ```
    @typecheck(x=float, y=(int, float), iters=int, verbose=bool)
    def process(x, y, z, iters=5, verbose=True):
        print(f'z = {z}')
        for i in range(iters):
            if verbose: print(f'Iteration {i}...')
            x *= y
        return x
    ```

    >>> process(3.1, 4.5, 0, 2.0)
    TypeError: iters must be <class 'int'>, not <class 'float'>.

    >>> process(3.1, 4, 'a', 1, False)
    z = a
    12.4

    Alternatively, you can let the decorator infer types using annotations
    in the function that is to be decorated. The example below behaves
    equivalently to the explicit example shown above. Note that annotations
    regarding the returned value are ignored.

    ```
    @typecheck
    def process(x:float, y:(int, float), z, iters:int=5, verbose:bool=True):
        print(f'z = {z}')
        for i in range(iters):
            if verbose: print(f'Iteration {i}...')
            x *= y
        return x
    ```

    >>> process(3.1, 4.5, 0, 2.0)
    TypeError: iters must be <class 'int'>, not <class 'float'>.

    >>> process(3.1, 4, 'a', 1, False)
    z = a
    12.4
    """
    # Case 1: Pass keyword args to decorator specifying types.
    if not func_:
        return partial(typecheck, **types)
    # Case 2: Infer types from annotations. Skip if Case 1 already occurred.
    elif not types:
        types = {k: v.annotation
                 for k, v in signature(func_).parameters.items()
                 if not v.annotation == Parameter.empty}

    @wraps(func_)
    def wrapper(*args, **kwargs):
        sig = signature(wrapper)
        try:
            fargs = sig.bind(*args, **kwargs).arguments
        except TypeError as e:
            # Default error message is not very helpful if we don't handle this
            # case separately.
            expected_positional = [name for name, p in sig.parameters.items()
                                   if 'positional' in str(p.kind).lower()]
            if args and not expected_positional:
                raise TypeError(
                    'Received positional arg(s) but expected none. Expected '
                    f'arguments: {list(sig.parameters)}'
                )
            else:
                raise e
        for k, v in types.items():
            if k in fargs and not isinstance(fargs[k], v):
                raise TypeError(
                    f'{k} must be {str(v)}, not {type(fargs[k])}.'
                )
        return func_(*args, **kwargs)
    return wrapper


def add_kwargs(func, fields, hide_fields=(), strict=False):
    """Decorator that adds parameters into the signature and docstring of a
    function that accepts **kwargs.

    Parameters
    ----------
    func : function
        Function to decorate.
    fields : list[str]
        Names of params to insert into signature + docstring.
    hide_fields : list[str]
        Names of params that are *already* in the function's signature that
        we want to hide. To use a non-empty value here, we must set strict=True
        and the param must have a default value, as this is what will be used
        in all subsequent calls.
    strict : bool
        If true, we do two things:
        1. On decorated function call, check that the user provided all
        expected arguments.
        2. Enable the use of the `hide_fields` param.

    Returns
    -------
    function
    """
    # Hide_fields must have default values in existing function. They will not
    # show up in the new docstring and the user will not be able to pass in a
    # value when calling the new function - it will always use the default.
    # To set different defaults, you can pass in a partial rather than a
    # function as the first arg here.
    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    if hide_fields and not strict:
        raise ValueError(
            'You must set strict=True when providing one or more '
            'hide_fields. Otherwise the user can still pass in those args.'
        )
    sig = signature(wrapper)
    params_ = {k: v for k, v in sig.parameters.items()}

    # Remove any fields we want to hide.
    for field in hide_fields:
        if field not in params_:
            warnings.warn(f'No need to hide field {field} because it\'s not '
                          'in the existing function signature.')
        elif params_.pop(field).default == Parameter.empty:
            raise TypeError(
                f'Field "{field}" is not a valid hide_field because it has '
                'no default value in the original function.'
            )

    if getattr(params_.pop('kwargs', None), 'kind') != Parameter.VAR_KEYWORD:
        raise TypeError(f'Function {func} must accept **kwargs.')
    new_params = {
        field: Parameter(field, Parameter.KEYWORD_ONLY)
        for field in fields
    }
    overlap = set(new_params) & set(params_)
    if overlap:
        raise RuntimeError(
            f'Some of the kwargs you tried to inject into {func} already '
            'exist in its signature. This is not allowed because it\'s '
            'unclear how to resolve default values and parameter type.'
        )

    params_.update(new_params)
    wrapper.__signature__ = sig.replace(parameters=params_.values())
    if strict:
        # In practice langchain checks for this anyway if we ask for a
        # completion, but outside of that context we need typecheck
        # because otherwise we could provide no kwargs and _func wouldn't
        # complain. Just use generic type because we only care that a value is
        # provided.
        wrapper = typecheck(wrapper, **{f: object for f in fields})
    return wrapper


def store_class_defaults(cls=None, attr_filter=None):
    """Class decorator that stores default values of class attributes (can be
    all or a subset). Default here refers to the value at class definition
    time.

    Examples
    --------
    ```
    @store_class_defaults(attr_filter=lambda x: x.startswith('last_'))
    class Foo:
        last_bar = 3
        last_baz = 'abc'
        other = True
    ```

    >>> Foo._class_defaults

    {'last_bar': 3, 'last_baz': 'abc'}

    Or use the decorator without parentheses to store all values at definition
    time. This is usually unnecessary. If you do provide an attr_filter, it
    must be a named argument.

    Foo.reset_class_vars() will reset all relevant class vars to their
    default values.
    """
    if cls is None:
        return partial(store_class_defaults, attr_filter=attr_filter)
    if not isinstance(cls, type):
        raise TypeError(
            f'cls arg in store_class_defaults decorator has type {type(cls)} '
            f'but expected type `type`, i.e. a class. You may be passing in '
            f'an attr_filter as a positional arg which is not allowed - it '
            f'must be a named arg if provided.'
        )
    if not attr_filter:
        def attr_filter(x):
            return True
    defaults = {}
    for k, v in vars(cls).items():
        if attr_filter(k):
            defaults[k] = v

    name = '_class_defaults'
    if hasattr(cls, name):
        raise AttributeError(
            f'Class {cls} already has attribute {name}. store_class_defaults '
            'decorator would overwrite that. Exiting.'
        )
    setattr(cls, name, defaults)

    @classmethod
    def reset_class_vars(cls):
        """Reset all default class attributes to their defaults."""
        for k, v in cls._class_defaults.items():
            try:
                setattr(cls, k, v)
            except Exception as e:
                warnings.warn(f'Could not reset class attribute {k} to its '
                              f'default value:\n\n{e}')

    meth_name = 'reset_class_vars'
    if hasattr(cls, meth_name):
        raise AttributeError(
            f'Class {cls} already has attribute {meth_name}. '
            f'store_class_defaults decorator would overwrite that. Exiting.'
        )
    setattr(cls, meth_name, reset_class_vars)
    return cls


def add_docstring(func):
    """Add the docstring from another function/class to the decorated
    function/class.

    Ported from [htools](https://github.com/hdmamin/htools) to avoid extra
    dependency.

    Parameters
    ----------
    func : function
        Function to decorate.

    Examples
    --------
    ```
    @add_docstring(nn.Conv2d)
    class ReflectionPaddedConv2d(nn.Module):
        # ...
    ```
    """
    def decorator(new_func):
        new_func.__doc__ = f'{new_func.__doc__}\n\n{func.__doc__}'
        @wraps(new_func)
        def wrapper(*args, **kwargs):
            return new_func(*args, **kwargs)
        return wrapper
    return decorator
