import pytest

from safe_exec import EvalBlockedError, ExecBlockedError, Safe, allow_eval, allow_exec


def run_exec() -> bool:
    exec("print('Hello, world!')")
    return True


def run_eval() -> int:
    return eval("0 + 1")


@allow_exec
def disallowed_exec() -> bool:
    return run_exec()


@allow_eval
def disallowed_eval() -> int:
    return run_eval()


@allow_exec
@allow_eval
def disallowed_both() -> tuple[bool, int]:
    return run_exec(), run_eval()


@allow_exec
def allowed_exec() -> bool:
    exec("print('Hello, world!')")
    return True


@allow_eval
def allowed_eval() -> int:
    return eval("0 + 1")


@allow_exec
@allow_eval
def allowed_both() -> tuple[bool, int]:
    exec("print('Hello, world!')")
    return True, eval("0 + 1")


def test_allowed_exec() -> None:
    with Safe(exec):
        assert allowed_exec()
        with allow_exec(run_exec) as f:
            assert f is run_exec
            assert run_exec()
            assert disallowed_exec()
        with pytest.raises(ExecBlockedError):
            assert run_exec()
        with pytest.raises(ExecBlockedError):
            assert disallowed_exec()


def test_allowed_eval() -> None:
    with Safe(eval):
        assert allowed_eval() == 1
        with allow_eval(run_eval) as f:
            assert f is run_eval
            assert run_eval() == 1
            assert disallowed_eval() == 1
        with pytest.raises(EvalBlockedError):
            assert run_eval() == 1
        with pytest.raises(EvalBlockedError):
            assert disallowed_eval() == 1


def test_allowed_both() -> None:
    with Safe(exec), Safe(eval):
        assert allowed_both() == (True, 1)
        with allow_exec(run_exec) as f1, allow_eval(run_eval) as f2:
            assert f1 is run_exec
            assert f2 is run_eval
            assert run_exec()
            assert run_eval() == 1
            assert disallowed_both() == (True, 1)
        with pytest.raises(ExecBlockedError):
            assert run_exec()
        with pytest.raises(EvalBlockedError):
            assert run_eval()
        with pytest.raises(ExecBlockedError):
            assert disallowed_both() == (True, 1)


def test_allowed_wrong_func() -> None:
    with Safe(exec), allow_eval(run_exec), pytest.raises(ExecBlockedError):
        assert run_exec()
    with Safe(eval), allow_exec(run_eval), pytest.raises(EvalBlockedError):
        assert run_eval() == 1
