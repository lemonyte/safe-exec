# safe-exec

`safe-exec` is a context manager that prevents calls to `exec` and `eval` in Python code, and reveals the code in calls that were attempted.

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

## Example

The `Safe` context manager takes either `exec` or `eval` as an argument.

```python
>>> from safe_exec import Safe
>>> with Safe(exec):
...     from base64 import b64decode
...     exec(b64decode("cHJpbnQoJ29iZnVzY2F0ZWQgY29kZScp"))

safe_exec.ExecBlockedError: blocked execution of b"print('obfuscated code')"
```

You can also use the `runpy` module to execute a different script in the `Safe` context:

```python
>>> import runpy
>>> with Safe(exec), Safe(eval):
...     runpy.run_path("path/to/script.py")
```

## False positives

Because `exec` and `eval` are used in a number of places within the Python standard library, `safe-exec` may prevent some necessary code from running. If you encounter a false positive, please [open an issue](https://github.com/lemonyte/safe-exec/issues).

Legitimate calls to `exec` and `eval` are allowed by inspecting the caller's frame. If the caller's code object is present in the list of allowed callers, the call is allowed. Such calls are logged as informational messages.

```python
>>> from safe_exec import Safe
>>> import logging
>>> logging.basicConfig(level=logging.INFO)
>>> from typing import NamedTuple
>>> with Safe(eval):
...     NamedTuple("Foo", [("bar", int)])

INFO:safe_exec:allowed eval call by 'namedtuple' from '.../lib/collections/__init__.py':345
```

## License

[MIT License](LICENSE.txt)
