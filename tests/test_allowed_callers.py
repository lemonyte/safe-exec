import logging
from pathlib import Path

from safe_exec import Safe

logging.basicConfig(level=logging.INFO)


def test_get_type_hints() -> None:
    with Safe(eval):

        def foo(_: "str") -> "int":
            return 0

        import typing

        hints = typing.get_type_hints(foo)
        assert hints == {"_": str, "return": int}


def test_namedtuple() -> None:
    with Safe(eval):
        from typing import NamedTuple

        class Foo(NamedTuple):
            bar: int

        assert Foo(1).bar == 1


def test_dataclasses() -> None:
    with Safe(exec):
        from dataclasses import dataclass

        @dataclass
        class Foo:
            bar: int

        assert Foo(1).bar == 1


def test_runpy() -> None:
    with Safe(exec):
        import runpy

        assert isinstance(runpy.run_path(str(Path(__file__).parent / "__init__.py")), dict)


def test_site_addpackage() -> None:
    with Safe(exec):
        import site
        import sysconfig

        assert site.addpackage(sysconfig.get_paths()["purelib"], "_virtualenv.pth", None) is None
