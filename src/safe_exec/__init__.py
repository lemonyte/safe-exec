# ruff: noqa: SLF001, PYI024
from __future__ import annotations

import builtins
import collections
import dataclasses
import importlib._bootstrap
import logging
import logging.config
import runpy
import site
import sys
import typing
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import CodeType, TracebackType

    from _typeshed import ReadableBuffer

__version__ = "0.0.1"

ReturnT = TypeVar("ReturnT", None, Any)

KNOWN_CALLERS = {
    "exec": {
        importlib._bootstrap._call_with_frames_removed.__code__,  # type: ignore[reportAttributeAccessIssue]
        site.addpackage.__code__,
        runpy._run_code.__code__,  # type: ignore[reportAttributeAccessIssue]
    },
    "eval": {
        collections.namedtuple.__code__,
        typing.ForwardRef._evaluate.__code__,
    },
}
if sys.version_info >= (3, 13):
    KNOWN_CALLERS["exec"].add(dataclasses._FuncBuilder.add_fns_to_class.__code__)  # type: ignore[reportAttributeAccessIssue]
else:
    KNOWN_CALLERS["exec"].add(dataclasses._create_fn.__code__)  # type: ignore[reportAttributeAccessIssue]

logger = logging.getLogger(__name__)
original_exec = builtins.exec
original_eval = builtins.eval


class BlockedError(RuntimeError):
    def __init__(
        self,
        caller: CodeType,
        source: str | ReadableBuffer | CodeType,
        globals: dict[str, Any] | None = None,
        locals: Mapping[str, object] | None = None,
        *args: object,
    ) -> None:
        super().__init__(f"blocked execution of {source!r}", *args)
        self.caller = caller
        self.source = source
        self.globals = globals
        self.locals = locals


class ExecBlockedError(BlockedError):
    pass


class EvalBlockedError(BlockedError):
    pass


BLOCK_EXC_CLS = {"exec": ExecBlockedError, "eval": EvalBlockedError}


def wrap_builtin(builtin: Callable, /) -> Callable[[Callable], Callable]:
    def decorator(func: Callable, /) -> Callable:
        builtins.__dict__[builtin.__name__] = func
        return func

    return decorator


class Safe(Generic[ReturnT]):
    def __init__(
        self,
        func: Callable[[str | ReadableBuffer | CodeType, dict[str, Any] | None, Mapping[str, object] | None], ReturnT],
        /,
    ) -> None:
        self._already_wrapped = False
        if isinstance(func, self.__class__):
            self._already_wrapped = True
            func = func._func
        elif func not in {original_exec, original_eval}:
            msg = f"unsupported function {func!r}"
            raise ValueError(msg)
        self._func = func
        self._known_callers = KNOWN_CALLERS[func.__name__]
        self._exc_cls = BLOCK_EXC_CLS[func.__name__]

    def __call__(
        self,
        source: str | ReadableBuffer | CodeType,
        globals: dict[str, Any] | None = None,
        locals: Mapping[str, object] | None = None,
    ) -> ReturnT:
        caller = sys._getframe(1).f_code
        if caller in self._known_callers:
            logger.info(
                "allowed %s call by %r from %r:%i",
                self._func.__name__,
                caller.co_name,
                caller.co_filename,
                caller.co_firstlineno,
            )
            return self._func(source, globals, locals)
        raise self._exc_cls(caller=caller, source=source, globals=globals, locals=locals)

    def __enter__(self) -> None:
        if not self._already_wrapped:
            builtins.__dict__[self._func.__name__] = self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if not self._already_wrapped:
            builtins.__dict__[self._func.__name__] = self._func
