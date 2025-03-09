# ruff: noqa: SLF001, PYI024, N801
"""Context managers and helpers to deobfuscate and inspect code passed into `exec` and `eval`."""

from __future__ import annotations

import abc
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
from contextlib import ContextDecorator
from typing import TYPE_CHECKING, Any, Callable, Generic, Protocol, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import CellType, CodeType, TracebackType

    from _typeshed import ReadableBuffer


__version__ = "0.0.1"
__all__ = (
    "BlockedError",
    "EvalBlockedError",
    "ExecBlockedError",
    "allow_eval",
    "allow_exec",
    "safe",
)

TRUSTED_CALLERS: dict[str, set[CodeType]] = {
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
    TRUSTED_CALLERS["exec"].add(dataclasses._FuncBuilder.add_fns_to_class.__code__)  # type: ignore[reportAttributeAccessIssue]
else:
    TRUSTED_CALLERS["exec"].add(dataclasses._create_fn.__code__)  # type: ignore[reportAttributeAccessIssue]

logger = logging.getLogger(__name__)
original_exec_id = id(builtins.exec)
original_eval_id = id(builtins.eval)


class BlockedError(RuntimeError):
    """Raised when a call to `exec` or `eval` is blocked."""

    def __init__(
        self,
        caller: CodeType,
        source: str | ReadableBuffer | CodeType,
        globals: dict[str, Any] | None = None,
        locals: Mapping[str, object] | None = None,
        *args: object,
    ) -> None:
        """Save the caller, source, globals, and locals of the attempted call."""
        super().__init__(f"blocked execution of {source!r}", *args)
        self.caller = caller
        self.source = source
        self.globals = globals
        self.locals = locals


class ExecBlockedError(BlockedError):
    """Raised when an `exec` call is blocked."""


class EvalBlockedError(BlockedError):
    """Raised when an `eval` call is blocked."""


BLOCK_EXC_CLS: dict[str, type[BlockedError]] = {"exec": ExecBlockedError, "eval": EvalBlockedError}

ReturnT_co = TypeVar("ReturnT_co", covariant=True)
ParamT = ParamSpec("ParamT")


class AllowContextDecorator(abc.ABC, Generic[ParamT, ReturnT_co]):
    def __init__(self, func: Callable[ParamT, ReturnT_co], /) -> None:
        self._func = func
        self._register(func)

    def _register(self, func: Callable[..., Any], /) -> None:
        TRUSTED_CALLERS[self._builtin_name].add(func.__code__)

    def _unregister(self, func: Callable[..., Any], /) -> None:
        TRUSTED_CALLERS[self._builtin_name].remove(func.__code__)

    def __call__(self, *args: ParamT.args, **kwargs: ParamT.kwargs) -> ReturnT_co:
        return self._func(*args, **kwargs)

    def __enter__(self) -> Callable[ParamT, ReturnT_co]:
        self._register(self._func)
        return self._func

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._unregister(self._func)

    @property
    def __code__(self) -> CodeType:
        return self._func.__code__

    @property
    @abc.abstractmethod
    def _builtin_name(self) -> str: ...


class allow_exec(AllowContextDecorator[ParamT, ReturnT_co]):
    """Allow the provided function to call `exec`."""

    @property
    def _builtin_name(self) -> str:
        return "exec"


class allow_eval(AllowContextDecorator[ParamT, ReturnT_co]):
    """Allow the provided function to call `eval`."""

    @property
    def _builtin_name(self) -> str:
        return "eval"


class ExecType(Protocol):
    __name__: str

    if sys.version_info >= (3, 13):

        def __call__(
            self,
            source: str | ReadableBuffer | CodeType,
            /,
            globals: dict[str, Any] | None,
            locals: Mapping[str, object] | None,
            *,
            closure: tuple[CellType, ...] | None = None,
        ) -> None: ...
    elif sys.version_info >= (3, 11):

        def __call__(
            self,
            source: str | ReadableBuffer | CodeType,
            globals: dict[str, Any] | None,
            locals: Mapping[str, object] | None,
            /,
            *,
            closure: tuple[CellType, ...] | None = None,
        ) -> None: ...
    else:

        def __call__(
            self,
            source: str | ReadableBuffer | CodeType,
            globals: dict[str, Any] | None,
            locals: Mapping[str, object] | None,
            /,
        ) -> None: ...


class EvalType(Protocol):
    __name__: str

    if sys.version_info >= (3, 13):

        def __call__(
            self,
            source: str | ReadableBuffer | CodeType,
            /,
            globals: dict[str, Any] | None,
            locals: Mapping[str, object] | None,
        ) -> Any: ...  # noqa: ANN401
    else:

        def __call__(
            self,
            source: str | ReadableBuffer | CodeType,
            globals: dict[str, Any] | None,
            locals: Mapping[str, object] | None,
            /,
        ) -> Any: ...  # noqa: ANN401


class safe(ContextDecorator):
    """Context manager and decorator for blocking `exec` and `eval` calls."""

    def __init__(
        self,
        func: ExecType | EvalType,
        /,
    ) -> None:
        """Initialize the context manager by passing in the built-in `exec` or `eval` function."""
        self._already_wrapped = False
        if isinstance(getattr(func, "__self__", None), self.__class__):
            # If the passed function has already been replaced by a previous safe() context,
            # we don't do anything.
            self._already_wrapped = True
            func = func.__self__._bare_func  # type: ignore[reportFunctionMemberAccess]
        elif id(func) not in (original_exec_id, original_eval_id):
            # Even with typing protocols, functions like `print` will still fit into the `func` param.
            # We only want to replace `exec` and `eval` functions.
            msg = f"unsupported function {func!r}"
            raise ValueError(msg)
        self._bare_func = func
        self._known_callers = TRUSTED_CALLERS[func.__name__]
        self._exc_cls = BLOCK_EXC_CLS[func.__name__]

    def _safe_func(
        self,
        source: str | ReadableBuffer | CodeType,
        /,
        globals: dict[str, Any] | None = None,
        locals: Mapping[str, object] | None = None,
        *,
        closure: tuple[CellType, ...] | None = None,
    ) -> Any | None:  # noqa: ANN401
        caller = sys._getframe(1).f_code
        if caller in self._known_callers:
            logger.info(
                "allowed %s call by %r from %r:%i",
                self._bare_func.__name__,
                caller.co_name,
                caller.co_filename,
                caller.co_firstlineno,
            )
            if sys.version_info >= (3, 11) and id(self._bare_func) == original_exec_id:
                # The `closure` parameter was added to `exec` in Python 3.11.
                return self._bare_func(source, globals, locals, closure=closure)  # type: ignore[reportCallIssue]
            return self._bare_func(source, globals, locals)
        raise self._exc_cls(caller=caller, source=source, globals=globals, locals=locals)

    def __enter__(self) -> None:
        """Replace the built-in `exec` or `eval` function with the safe version."""
        if not self._already_wrapped:
            builtins.__dict__[self._bare_func.__name__] = self._safe_func

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Restore the original built-in `exec` or `eval` function."""
        if not self._already_wrapped:
            builtins.__dict__[self._bare_func.__name__] = self._bare_func
