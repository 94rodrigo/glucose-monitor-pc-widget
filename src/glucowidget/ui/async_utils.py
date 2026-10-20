"""Execução de tarefas bloqueantes fora da thread de UI."""
from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_alive: set["_Signals"] = set()


class _Signals(QObject):
    done = Signal(object)
    failed = Signal(object)


class _Task(QRunnable):
    def __init__(self, fn: Callable[[], Any], signals: _Signals):
        super().__init__()
        self.fn = fn
        self.signals = signals

    def run(self):
        try:
            result = self.fn()
        except Exception as exc:  # noqa: BLE001 - repassado para a UI
            self.signals.failed.emit(exc)
        else:
            self.signals.done.emit(result)


def run_async(fn: Callable[[], Any], on_done: Callable[[Any], None], on_error: Callable[[Exception], None]) -> None:
    signals = _Signals()
    _alive.add(signals)

    def finish(cb, value):
        _alive.discard(signals)
        cb(value)

    signals.done.connect(lambda r: finish(on_done, r))
    signals.failed.connect(lambda e: finish(on_error, e))
    QThreadPool.globalInstance().start(_Task(fn, signals))
