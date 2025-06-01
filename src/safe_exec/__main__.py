"""Command-line interface for safe-exec."""

import argparse
import importlib._bootstrap_external
import logging
import runpy
import time
from pathlib import Path
from types import CodeType

from safe_exec import EvalBlockedError, ExecBlockedError, safe


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("script", help="Path to the script to run")
    parser.add_argument("--out-file", help="Output file (default: stdout)", default="-")
    args = parser.parse_args()
    logger = logging.getLogger("safe_exec.cli")
    logging.basicConfig(level=logging.INFO)

    with safe(exec), safe(eval):
        try:
            logger.info("Running script: %s", args.script)
            runpy.run_path(args.script)
        except (ExecBlockedError, EvalBlockedError) as exc:
            if isinstance(exc, ExecBlockedError):
                func_name = "exec"
            elif isinstance(exc, EvalBlockedError):
                func_name = "eval"
            else:
                func_name = "unknown"
            logger.warning("Detected %s call", func_name)
            logger.warning("Globals: %r", exc.globals)
            logger.warning("Locals: %r", exc.locals)
            logger.warning("Caller: %s", exc.caller.co_name)
            source = exc.source.decode("utf-8") if isinstance(exc.source, bytes) else exc.source
            if args.out_file and args.out_file != "-":
                if isinstance(source, CodeType):
                    out_file = Path(args.out_file).with_suffix(".pyc")
                    # Manually create a .pyc file from an already compiled code object.
                    # I use the private API here so it generates a .pyc file
                    # for whatever version of Python the user is running,
                    # and it saves me from reimplementing the .pyc header code myself.
                    data = importlib._bootstrap_external._code_to_timestamp_pyc(  # noqa: SLF001 # type: ignore[unresolved-attribute]
                        source,
                        time.time(),
                        len(source.co_code),
                    )
                    out_file.write_bytes(data)
                else:
                    out_file = Path(args.out_file).with_suffix(".py")
                    out_file.write_text(str(source))
                logger.info("Deobfuscated source written to %s", out_file)
            else:
                logger.info("Deobfuscated source:\n")
                print(source)  # noqa: T201
            raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
