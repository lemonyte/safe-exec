# safe-exec

`safe-exec` provides a context manager that prevents calls to `exec` and `eval` in Python code, and reveals the code in calls that were attempted.

This is useful for retrieving deobfuscated code from obfuscated malware samples that use `exec` or `eval` as the entry point.

> [!CAUTION]
> **This package does not guarantee that a script is safe to run**. It is only a tool to help deobfuscate code. It does **not** sandbox code, nor does it intend to be foolproof. Never run potentially malicious code outside of a secure sandboxed environment.

## Installation

```shell
pip install safe-exec
```

Or install from source:

```shell
pip install git+https://github.com/lemonyte/safe-exec.git
```

Python versions 3.9 through 3.13 are supported.

## Simple example

The `safe` context manager takes either `exec` or `eval` as an argument.

```python
>>> from safe_exec import safe
>>> with safe(exec):
...     from base64 import b64decode
...     exec(b64decode("cHJpbnQoJ29iZnVzY2F0ZWQgY29kZScp"))

safe_exec.ExecBlockedError: blocked execution of b"print('obfuscated code')"
```

You can also use the `runpy` module to execute a different script in the `safe` context:

```python
>>> import runpy
>>> with safe(exec), safe(eval):
...     runpy.run_path("path/to/script.py")
```

## Advanced usage

`safe` can also be used as a decorator to block calls to `exec` or `eval` in a function:

```python
from safe_exec import safe

@safe(exec)
@safe(eval)
def untrused_func():
    exec("print('This is an untrusted function')")
```

And as a function to register a third-party function as an untrusted caller:

```python
from safe_exec import safe
import runpy

runpy.run_path = safe(exec)(runpy.run_path)
```

However, the context manager is recommended for most use cases, as it ensures the functions that are overwritten are restored after the context exits.

### Allowing certain calls

`safe-exec` provides `allow_exec` and `allow_eval` context decorators to allow specific calls to `exec` and `eval`, respectively.

These can be used as decorators on functions that should be allowed to call `exec` or `eval`:

```python
from safe_exec import allow_exec, allow_eval

@allow_exec
@allow_eval
def trusted_func():
    exec("print('This is a trusted function')")
    eval("print('This is a trusted function')")

trusted_func()
```

> [!CAUTION]
> If other code calls the decorated function, the `exec` and `eval` calls will still be allowed.

As context managers to temporarily allow a function to call `exec` or `eval`:

```python
from safe_exec import allow_exec, allow_eval

def semi_trusted_func():
    exec("print('This is a semi-trusted function')")
    eval("print('This is a semi-trusted function')")

with allow_exec(semi_trusted_func), allow_eval(semi_trusted_func):
    semi_trusted_func()  # Calls are allowed here.
semi_trusted_func()  # Calls are blocked here.
```

Or as functions to register a third-party function as an allowed caller:

```python
from safe_exec import allow_eval
import collections

allow_eval(collections.namedtuple)
```

### `safe` vs `allow_exec` and `allow_eval`

The two groups of context managers have slightly different purposes, and therefore different interfaces.

`safe` creates a 'safe' context wherein calls to `exec` or `eval` are blocked.
If used as a decorator, it does not do anything with the decorated function itself.

`allow_exec` and `allow_eval` on the other hand need to take a callable (besides `exec` or `eval`) as an argument.
This is because they register the callable as a trusted caller of `exec` or `eval`, whether they are used as decorators or context managers.

## False positives

Because `exec` and `eval` are used in a number of places within the Python standard library, `safe-exec` may prevent some necessary code from running. If you encounter a false positive, please [open an issue](https://github.com/lemonyte/safe-exec/issues).

As a temporary workaround, if you can determine the calling function that depends on `exec` or `eval`, you can use the `allow_exec` and `allow_eval` context managers to register it as a trusted caller.

Legitimate calls to `exec` and `eval` are allowed by inspecting the caller's frame. If the caller's code object is present in the list of trusted callers, the call is allowed. Such calls are logged as informational messages.

```python
>>> from safe_exec import safe
>>> import logging
>>> logging.basicConfig(level=logging.INFO)
>>> from typing import NamedTuple
>>> with safe(eval):
...     Foo = NamedTuple("Foo", [("bar", int)])

INFO:safe_exec:allowed eval call by 'namedtuple' from '.../lib/collections/__init__.py':345
```

## License

[MIT License](LICENSE.txt)
