from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PageEditState:
    file_path: str
    operation: str


class PageEditHistory:
    def __init__(
        self,
        initial_path: str | Path,
    ) -> None:
        self._states = [
            PageEditState(
                file_path=str(initial_path),
                operation="initial",
            )
        ]

        self._index = 0

    @property
    def current(self) -> PageEditState:
        return self._states[self._index]

    @property
    def can_undo(self) -> bool:
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        return self._index < len(self._states) - 1

    def push(
        self,
        file_path: str | Path,
        operation: str,
    ) -> PageEditState:
        if self.can_redo:
            self._states = self._states[
                : self._index + 1
            ]

        state = PageEditState(
            file_path=str(file_path),
            operation=operation,
        )

        self._states.append(state)
        self._index += 1

        return state

    def undo(self) -> PageEditState:
        if not self.can_undo:
            raise ValueError(
                "Geri alınacak işlem bulunmuyor."
            )

        self._index -= 1
        return self.current

    def redo(self) -> PageEditState:
        if not self.can_redo:
            raise ValueError(
                "İleri alınacak işlem bulunmuyor."
            )

        self._index += 1
        return self.current