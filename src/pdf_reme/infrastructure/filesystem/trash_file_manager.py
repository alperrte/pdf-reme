import os
import shutil
import time
from pathlib import Path
from uuid import uuid4

from pdf_reme.shared.paths.app_paths import AppPaths

_MOVE_RETRIES = 3
_MOVE_RETRY_DELAY_S = 0.15


class TrashIOError(OSError):
    """Dosya çöpe taşınırken/geri yüklenirken kalıcı bir G/Ç hatası oluştu.

    OneDrive/antivirüs/indeksleyici gibi araçların yeni oluşturulmuş bir
    dosyayı anlık kilitlemesi durumunda `os.rename` (dolayısıyla çıplak
    `shutil.move`) sessizce kopyala+sil'e düşebilir; kopyalama başarılı olup
    silme başarısız olursa öksüz (DB'siz) bir kopya kalabilir. `_safe_move`
    bu senaryoyu yakalayıp öksüz kopya bırakmadan bu hatayı fırlatır.
    """


class TrashFileManager:
    def __init__(self, paths: AppPaths) -> None:
        self.paths = paths

    def move_to_trash(self, file_path: str | Path) -> Path:
        source_path = Path(file_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Çöp kutusuna taşınacak dosya bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Çöp kutusuna yalnızca dosyalar taşınabilir: {source_path}"
            )

        self.paths.trash_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        target_path = self.paths.trash_dir / source_path.name

        if target_path.exists():
            target_path = self._create_unique_trash_target(
                source_path.name
            )

        _safe_move(source_path, target_path)

        return target_path

    def restore_from_trash(
        self,
        trash_path: str | Path,
        restore_path: str | Path,
    ) -> Path:
        source_path = Path(trash_path)
        target_path = Path(restore_path)

        if not source_path.exists():
            raise FileNotFoundError(
                f"Geri yüklenecek dosya bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                f"Yalnızca dosyalar geri yüklenebilir: {source_path}"
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        if target_path.exists():
            target_path = self._create_unique_restore_target(
                target_path
            )

        _safe_move(source_path, target_path)

        return target_path

    def permanently_delete(
        self,
        trash_path: str | Path,
    ) -> bool:
        file_path = Path(trash_path)

        trash_root = self.paths.trash_dir.resolve()
        resolved_path = file_path.resolve()

        if not resolved_path.is_relative_to(trash_root):
            raise ValueError(
                "Yalnızca PDF-REME çöp kutusundaki dosyalar "
                "kalıcı olarak silinebilir."
            )

        if not file_path.exists():
            return False

        if not file_path.is_file():
            raise ValueError(
                f"Yalnızca dosyalar kalıcı olarak silinebilir: {file_path}"
            )

        file_path.unlink()

        return True

    def _create_unique_trash_target(
        self,
        file_name: str,
    ) -> Path:
        file_path = Path(file_name)

        unique_name = (
            f"{file_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{file_path.suffix}"
        )

        return self.paths.trash_dir / unique_name

    def _create_unique_restore_target(
        self,
        target_path: Path,
    ) -> Path:
        unique_name = (
            f"{target_path.stem}_"
            f"{uuid4().hex[:8]}"
            f"{target_path.suffix}"
        )

        return target_path.parent / unique_name


def _safe_move(source: Path, target: Path) -> None:
    """`source`'u `target`'a taşır; geçici kilitlere karşı dayanıklıdır ve
    öksüz (DB'siz) bir kopya asla bırakmaz.

    Önce `os.replace` ile birkaç kez (backoff'lu) dener — bu atomik bir
    yeniden adlandırmadır, ara bir kopya oluşturmaz. Kalıcı olarak
    başarısız olursa (örn. farklı birim/disk ya da sürekli kilit),
    `copy2` + boyut doğrulama + kaynağı silme'ye düşer. Son silme adımı
    başarısız olursa (kaynak hâlâ kilitliyse), hedefteki kopya geri
    alınır (rollback) ve `TrashIOError` fırlatılır.
    """
    for attempt in range(_MOVE_RETRIES):
        try:
            os.replace(source, target)
            return
        except OSError:
            if attempt < _MOVE_RETRIES - 1:
                time.sleep(_MOVE_RETRY_DELAY_S * (attempt + 1))

    try:
        shutil.copy2(str(source), str(target))
    except OSError as error:
        raise TrashIOError(
            f"Dosya kopyalanamadı: {source} -> {target}"
        ) from error

    if target.stat().st_size != source.stat().st_size:
        target.unlink(missing_ok=True)

        raise TrashIOError(
            f"Kopyalanan dosyanın boyutu eşleşmiyor: {source} -> {target}"
        )

    try:
        source.unlink()
    except OSError as error:
        # Kaynak hâlâ kilitli; öksüz kopya bırakmamak için hedef geri alınır.
        target.unlink(missing_ok=True)

        raise TrashIOError(
            f"Kaynak dosya silinemedi, taşıma geri alındı: {source}"
        ) from error