# safe-exec

`safe-exec` is a context manager that prevents calls to `exec` and `eval` in Python code, and reveals the code in calls that were attempted.

This is useful for retrieving deobfuscated code from obfuscated malware samples that use `exec` or `eval` as the entry point.

> [!CAUTION]
> **This package does not guarantee that a script is safe to run**. It is only a tool to help deobfuscate code. It does **not** sandbox code, nor does it intend to be foolproof. Never run potentially malicious code outside of a secure sandboxed environment.

## Installation

> [!IMPORTANT]
> You **must** install `safe-exec` into an activated virtual environment for it to work properly.

```shell
pip install safe-exec
```

Verify that `safe-exec` is installed correctly and will execute when Python starts:

```shell
python -c 'exec("print(\"if this prints normally, safe-exec is NOT installed\")")'
```

```text
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/.../site-packages/safe_exec/__init__.py", line 75, in safe_exec
    raise ExecBlockedError(caller=caller, source=source, globals=globals, locals=locals)
safe_exec.ExecBlockedError: blocked execution of 'print("if this prints normally, safe-exec is NOT installed")'
```

If the exception is thrown, `safe-exec` is installed correctly.

If the exception is **not** thrown, try the following:

1. Run `SITE_PACKAGES=$(python -c 'import sysconfig; print(sysconfig.get_path("purelib"))')` to get the path to the Python site-packages directory.
2. Run `echo "import safe_exec" > "$SITE_PACKAGES/safe_exec.pth"` to register `safe-exec` on startup.

> [!NOTE]
> If using PowerShell, use `$SITE_PACKAGES` instead of `SITE_PACKAGES` to assign the variable.

## Example

When `safe-exec` is installed, `exec` calls will raise an `ExecBlockedError` exception:

```python
from base64 import b64decode
from safe_exec import ExecBlockedError

try:
    exec(b64decode("cHJpbnQoJ29iZnVzY2F0ZWQgY29kZScp"))
except ExecBlockedError as exc:
    print(f"Blocked code: {exc.source!r}")
    print(f"Globals: {exc.globals}")
    print(f"Locals: {exc.locals}")
    print(f"Caller: {exc.caller}")
```

```text
Blocked code: b"print('obfuscated code')"
Globals: None
Locals: None
Caller: <module>
```

## False positives

Because `exec` and `eval` are used in a number of places within the Python standard library, `safe-exec` may prevent some necessary code from running. If you encounter a false positive, please [open an issue](https://github.com/lemonyte/safe-exec/issues).

Legitimate calls to `exec` and `eval` are allowed by inspecting the caller's frame. If the caller's code object is present in the list of allowed callers, the call is allowed. Such calls are logged as informational messages.

```python

```

## License

[MIT License](LICENSE.txt)
