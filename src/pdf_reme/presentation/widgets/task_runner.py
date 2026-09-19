from collections.abc import Callable

from PySide6.QtCore import QObject, QThread, Signal


class _TaskThread(QThread):
    succeeded = Signal(object)
    errored = Signal(object)
    progressed = Signal(int, str)

    def __init__(
        self,
        task: Callable[..., object],
        wants_progress: bool = False,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._task = task
        self._wants_progress = wants_progress

    def _report(self, percent: int, text: str = "") -> None:
        self.progressed.emit(max(0, min(100, int(percent))), text)

    def run(self) -> None:
        try:
            if self._wants_progress:
                result = self._task(self._report)
            else:
                result = self._task()

        except Exception as error:
            self.errored.emit(error)
            return

        self.succeeded.emit(result)


class TaskRunner(QObject):
    """Uzun süren backend çağrısını arayüzü dondurmadan arka planda çalıştırır.

    Aynı anda tek iş çalışır. Sonuç sinyalleri her zaman ana (arayüz)
    iş parçacığında teslim edilir.
    """

    succeeded = Signal(object)
    errored = Signal(object)
    running_changed = Signal(bool)
    progressed = Signal(int, str)

    def __init__(
        self,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)

        self._thread: _TaskThread | None = None
        self._outcome: tuple[bool, object] | None = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None

    def run(
        self,
        task: Callable[..., object],
        progress: bool = False,
    ) -> bool:
        """progress=True ise görev `report(percent, text="")` alır."""

        if self._thread is not None:
            return False

        thread = _TaskThread(task, progress, self)
        thread.progressed.connect(self.progressed)
        thread.succeeded.connect(self._on_succeeded)
        thread.errored.connect(self._on_errored)
        thread.finished.connect(self._on_finished)

        self._thread = thread

        self.running_changed.emit(True)

        thread.start()

        return True

    def wait(self, timeout_ms: int = 60_000) -> None:
        if self._thread is not None:
            self._thread.wait(timeout_ms)

    def _on_succeeded(self, result: object) -> None:
        self._outcome = (True, result)

    def _on_errored(self, error: object) -> None:
        self._outcome = (False, error)

    def _on_finished(self) -> None:
        # Sonuç sinyalleri finished'ten önce kuyruğa girer; iş parçacığı
        # tamamen bittikten sonra serbest bırakıp sonucu ilet.
        thread = self._thread
        outcome = self._outcome

        self._thread = None
        self._outcome = None

        if thread is not None:
            thread.deleteLater()

        self.running_changed.emit(False)

        if outcome is None:
            return

        ok, payload = outcome

        if ok:
            self.succeeded.emit(payload)
        else:
            self.errored.emit(payload)
