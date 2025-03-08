import logging
from pathlib import Path

from safe_exec import safe

logging.basicConfig(level=logging.INFO)


@safe(eval)
def test_get_type_hints() -> None:
    def foo(_: "str") -> "int":
        return 0

    import typing

    hints = typing.get_type_hints(foo)
    assert hints == {"_": str, "return": int}


@safe(eval)
def test_namedtuple() -> None:
    from typing import NamedTuple

    class Foo(NamedTuple):
        bar: int

    assert Foo(1).bar == 1


@safe(exec)
def test_dataclasses() -> None:
    from dataclasses import dataclass

    @dataclass
    class Foo:
        bar: int

    assert Foo(1).bar == 1


@safe(exec)
def test_runpy() -> None:
    import runpy

    assert isinstance(runpy.run_path(str(Path(__file__).parent / "__init__.py")), dict)


@safe(exec)
def test_site_addpackage() -> None:
    import site
    import sysconfig

    assert site.addpackage(sysconfig.get_paths()["purelib"], "_virtualenv.pth", None) is None
