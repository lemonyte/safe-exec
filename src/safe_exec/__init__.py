# ruff: noqa: SLF001, PYI024, N801
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
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Mapping
    from types import CodeType, TracebackType

    from _typeshed import ReadableBuffer


__version__ = "0.0.1"
__all__ = (
    "BlockedError",
    "EvalBlockedError",
    "ExecBlockedError",
    "Safe",
    "allow_eval",
    "allow_exec",
)

BuiltinReturnT = TypeVar("BuiltinReturnT", None, Any)
ReturnT_co = TypeVar("ReturnT_co", covariant=True)
ParamT = ParamSpec("ParamT")

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


class AllowContextDecorator(abc.ABC, Generic[ParamT, ReturnT_co]):
    def __init__(self, func: Callable[ParamT, ReturnT_co], /) -> None:
        self._func = func
        self._register(func)

    def _register(self, func: Callable, /) -> None:
        KNOWN_CALLERS[self._builtin_name].add(func.__code__)

    def _unregister(self, func: Callable, /) -> None:
        KNOWN_CALLERS[self._builtin_name].remove(func.__code__)

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
    @property
    def _builtin_name(self) -> str:
        return "exec"


class allow_eval(AllowContextDecorator[ParamT, ReturnT_co]):
    @property
    def _builtin_name(self) -> str:
        return "eval"


class Safe(Generic[BuiltinReturnT]):
    def __init__(
        self,
        func: Callable[
            [str | ReadableBuffer | CodeType, dict[str, Any] | None, Mapping[str, object] | None],
            BuiltinReturnT,
        ],
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
    ) -> BuiltinReturnT:
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
