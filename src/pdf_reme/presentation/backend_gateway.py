import json
import math
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
from pypdf import PdfReader
from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from pdf_reme.application.services.import_document_service import (
    ImportDocumentService,
)
from pdf_reme.application.services.library_service import LibraryService
from pdf_reme.application.services.page_selection_parser import (
    PageSelectionParser,
)
from pdf_reme.application.services.trash_service import TrashService
from pdf_reme.application.use_cases.convert_images_to_pdf import (
    ConvertImagesToPdfUseCase,
)
from pdf_reme.application.use_cases.convert_office_to_pdf import (
    ConvertOfficeToPdfUseCase,
)
from pdf_reme.application.use_cases.convert_pdf_to_images import (
    ConvertPdfToImagesUseCase,
)
from pdf_reme.application.use_cases.edit_pdf_pages import (
    EditPdfPagesUseCase,
)
from pdf_reme.application.use_cases.merge_pdfs import MergePdfsUseCase
from pdf_reme.infrastructure.conversion.image_to_pdf_service import (
    ImageToPdfService,
)
from pdf_reme.infrastructure.conversion.office_to_pdf_service import (
    OfficeToPdfService,
)
from pdf_reme.infrastructure.conversion.pdf_to_image_service import (
    PdfToImageService,
)
from pdf_reme.infrastructure.database.models.document import Document
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.infrastructure.database.session import session_scope
from pdf_reme.infrastructure.filesystem.file_hash import calculate_sha256
from pdf_reme.infrastructure.filesystem.file_validation import (
    SUPPORTED_EXTENSIONS,
)
from pdf_reme.infrastructure.pdf.pdf_merge_service import PdfMergeService
from pdf_reme.infrastructure.pdf.pdf_page_edit_service import (
    PdfPageEditService,
)
from pdf_reme.infrastructure.filesystem.trash_file_manager import (
    TrashFileManager,
)
from pdf_reme.shared.paths.app_paths import AppPaths


# Presentation katmanının application/infrastructure servislerine
# tek giriş noktası. Her sayfa kendi session_scope()/repository/
# servis kurulum tekrarını yazmasın diye burada toplandı. session_scope()
# çıkışta commit eder; SQLAlchemy'nin varsayılan expire_on_commit=True
# davranışı yüzünden commit sonrası tüm alanlar "expired" olur ve session
# kapandıktan sonra (sayfalar Document alanlarını okurken) DetachedInstanceError
# fırlatır. Bunu infrastructure/session.py'a dokunmadan, sadece bu presentation
# katmanı dosyasında, session bazında expire_on_commit=False ayarlayarak çözüyoruz.
@contextmanager
def _scope():
    with session_scope() as session:
        session.expire_on_commit = False
        yield session


def _library_service(session) -> LibraryService:
    return LibraryService(
        SQLAlchemyDocumentRepository(session)
    )


def _trash_service(session) -> TrashService:
    return TrashService(
        SQLAlchemyDocumentRepository(session),
        TrashFileManager(AppPaths()),
    )


def _sort_by_created_at_desc(
    documents: list[Document],
) -> list[Document]:
    # Belgeleri en son eklenen en üstte olacak şekilde sıralar.
    # LibraryService'in filtre metotları (get_uploaded_documents vb.)
    # kendi çıktısını sıralamıyor; repository.get_all() SQL tarafında
    # created_at DESC ile sıralasa da, eşit created_at değerlerinde
    # (toplu içe aktarımdan gelen belgeler gibi) veritabanı motoru
    # kararlı bir sıra garanti etmez. Bu da örn. bir belge favoriye
    # eklenip liste yenilendiğinde kartın listede yer değiştirmesi
    # gibi kullanıcıyı şaşırtan bir davranışa yol açar. id'yi ikincil
    # anahtar olarak kullanmak, her `refresh()` çağrısında aynı sırayı
    # garanti eder.
    return sorted(
        documents,
        key=lambda document: (document.created_at, document.id),
        reverse=True,
    )


def fetch_library_documents() -> list[Document]:
    with _scope() as session:
        service = _library_service(session)

        documents = (
            service.get_uploaded_documents()
            + service.get_generated_documents()
        )

        return _sort_by_created_at_desc(documents)


# Favori sırası: Document modelinde "favoriye eklenme zamanı" alanı yok
# (application/infrastructure salt-okunur). "En son favorilenen en üstte"
# davranışı için, belge id -> artan sıra numarası eşlemesini uygulama
# veri klasöründeki küçük bir JSON dosyasında tutuyoruz. Kaydı olmayan
# (bu özellikten önce favorilenmiş) belgeler listenin altında, kendi
# aralarında created_at'e göre sıralanır.
def _favorite_order_file():
    return AppPaths().data_dir / "favorite_order.json"


def _load_favorite_order() -> dict[str, int]:
    try:
        raw = json.loads(
            _favorite_order_file().read_text(encoding="utf-8")
        )
    except (OSError, ValueError):
        return {}

    if not isinstance(raw, dict):
        return {}

    return {
        str(key): value
        for key, value in raw.items()
        if isinstance(value, int)
    }


def _save_favorite_order(order: dict[str, int]) -> None:
    path = _favorite_order_file()

    try:
        temp_path = path.with_suffix(".json.part")
        temp_path.write_text(json.dumps(order), encoding="utf-8")
        temp_path.replace(path)
    except OSError:
        # Sıra bilgisi kozmetik; yazılamazsa favori işlemi başarısız olmasın.
        pass


def _record_favorite_state(
    document_id: str,
    is_favorite: bool,
) -> None:
    order = _load_favorite_order()

    if is_favorite:
        order[document_id] = max(order.values(), default=0) + 1
    else:
        order.pop(document_id, None)

    _save_favorite_order(order)


def fetch_favorites() -> list[Document]:
    with _scope() as session:
        documents = _library_service(session).get_favorites()

    order = _load_favorite_order()

    return sorted(
        documents,
        key=lambda document: (
            order.get(document.id, 0),
            document.created_at,
            document.id,
        ),
        reverse=True,
    )


def fetch_recent(
    limit: int = 50,
) -> list[Document]:
    with _scope() as session:
        return _library_service(session).get_recent_documents(
            limit=limit
        )


def fetch_trashed() -> list[Document]:
    with _scope() as session:
        return _trash_service(session).get_trashed_documents()


def toggle_favorite(
    document_id: str,
) -> Document:
    with _scope() as session:
        document = _library_service(session).toggle_favorite(
            document_id
        )

    _record_favorite_state(document.id, document.is_favorite)

    return document


def set_favorite(
    document_id: str,
    value: bool,
) -> Document:
    with _scope() as session:
        service = _library_service(session)

        document = service.repository.get_by_id(document_id)

        if document is None:
            raise ValueError("Belge bulunamadı.")

        if document.is_favorite != value:
            document = service.toggle_favorite(document_id)

    _record_favorite_state(document.id, document.is_favorite)

    return document


def mark_as_opened(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _library_service(session).mark_as_opened(
            document_id
        )


def move_to_trash(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _trash_service(session).move_to_trash(
            document_id
        )


def restore_from_trash(
    document_id: str,
) -> Document:
    with _scope() as session:
        return _trash_service(session).restore(
            document_id
        )


def permanently_delete(
    document_id: str,
) -> None:
    with _scope() as session:
        _trash_service(session).permanently_delete(
            document_id
        )


def clear_trash() -> int:
    with _scope() as session:
        return _trash_service(session).clear_trash()


@dataclass(frozen=True)
class ImportOutcome:
    """Tek bir dosyanın içe aktarma sonucu (sunum katmanı için)."""

    path: str
    status: str  # "imported" | "duplicate" | "failed"
    reason: str | None = None
    existing_name: str | None = None
    existing_trashed: bool = False


# Alt katmanların döndürdüğü hata metinleri -> sunum katmanı neden kodları.
_ERROR_REASONS = {
    "Dosya bulunamadı.": "not_found",
    "Desteklenmeyen dosya türü.": "unsupported",
}

_CORRUPT_REASONS = {
    "pdf": "corrupt_pdf",
    "image": "corrupt_image",
}


def _failure_reason(path: Path, error: str | None) -> str:
    reason = _ERROR_REASONS.get(error or "")

    if reason is not None:
        return reason

    if error and "bozuk" in error:
        return _CORRUPT_REASONS.get(
            SUPPORTED_EXTENSIONS.get(path.suffix.lower(), ""),
            "corrupt_office",
        )

    return "unknown"


def _precheck_failure(path: Path) -> str | None:
    if not path.is_file():
        return "not_found"

    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return "unsupported"

    try:
        if path.stat().st_size == 0:
            return "empty"

        with path.open("rb") as handle:
            handle.read(1)

    except PermissionError:
        return "no_access"

    except OSError:
        return "unreadable"

    return None


def _find_existing(path: Path) -> tuple[str | None, bool]:
    try:
        sha256 = calculate_sha256(path)

        with _scope() as session:
            existing = SQLAlchemyDocumentRepository(
                session
            ).get_by_sha256(sha256)

            if existing is None:
                return None, False

            return existing.display_name, existing.status == "trashed"

    except Exception:
        return None, False


def import_documents(
    source_paths: list[str],
) -> list[ImportOutcome]:
    service = ImportDocumentService(AppPaths())
    outcomes: list[ImportOutcome] = []

    for raw_path in source_paths:
        path = Path(raw_path)

        reason = _precheck_failure(path)

        if reason is not None:
            outcomes.append(ImportOutcome(raw_path, "failed", reason))
            continue

        try:
            result = service.import_document(path)

        except Exception:
            outcomes.append(ImportOutcome(raw_path, "failed", "save_failed"))
            continue

        if result.imported:
            outcomes.append(ImportOutcome(raw_path, "imported"))

        elif result.duplicate_document is not None:
            name, trashed = _find_existing(path)

            outcomes.append(
                ImportOutcome(
                    raw_path,
                    "duplicate",
                    existing_name=name,
                    existing_trashed=trashed,
                )
            )

        else:
            outcomes.append(
                ImportOutcome(
                    raw_path,
                    "failed",
                    _failure_reason(path, result.error),
                )
            )

    return outcomes


# ----------------------------------------------------------------------
# Dönüştürme ve PDF düzenleme
# ----------------------------------------------------------------------


class OperationError(Exception):
    """Dönüştürme/düzenleme hatası; `reason` sunum katmanı neden kodudur."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(detail or reason)

        self.reason = reason


_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
_OFFICE_EXTENSIONS = {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}

CONVERT_SUPPORTED_EXTENSIONS = (
    _IMAGE_EXTENSIONS | _OFFICE_EXTENSIONS | {".pdf"}
)


def detect_convert_kind(paths: list[str]) -> str:
    """Seçilen dosyalardan dönüştürme türünü otomatik algılar.

    "images_to_pdf" | "pdf_to_images" | "office_to_pdf" |
    "mixed" (birden çok türün karışımı) | "unsupported" | "empty".
    """
    if not paths:
        return "empty"

    kinds: set[str] = set()

    for raw_path in paths:
        extension = Path(raw_path).suffix.lower()

        if extension in _IMAGE_EXTENSIONS:
            kinds.add("images_to_pdf")
        elif extension == ".pdf":
            kinds.add("pdf_to_images")
        elif extension in _OFFICE_EXTENSIONS:
            kinds.add("office_to_pdf")
        else:
            return "unsupported"

    if len(kinds) > 1:
        return "mixed"

    return next(iter(kinds))


def _operation_error_from(error: Exception) -> OperationError:
    if isinstance(error, OperationError):
        return error

    message = str(error)

    if isinstance(error, FileNotFoundError):
        if "LibreOffice" in message:
            return OperationError("libreoffice_missing", message)

        return OperationError("not_found", message)

    if isinstance(error, TimeoutError):
        return OperationError("timeout", message)

    if isinstance(error, ValueError):
        lowered = message.lower()

        if "şifreli" in lowered:
            return OperationError("encrypted", message)

        if "dosya adı" in lowered or "klasör yolu" in lowered:
            return OperationError("invalid_name", message)

        if "tüm sayfalar silinemez" in lowered:
            return OperationError("all_pages_deleted", message)

        return OperationError("invalid_input", message)

    if isinstance(error, RuntimeError):
        return OperationError("conversion_failed", message)

    return OperationError("unknown", message)


def read_pdf_page_count(path: str) -> int:
    """PDF'in sayfa sayısı; şifreli/bozuk/eksik dosyada OperationError."""
    try:
        reader = PdfReader(str(path))

        if reader.is_encrypted:
            raise OperationError("encrypted")

        return len(reader.pages)

    except OperationError:
        raise

    except FileNotFoundError as error:
        raise OperationError("not_found", str(error)) from error

    except Exception as error:
        raise OperationError("corrupt_pdf", str(error)) from error


def parse_page_selection(expression: str, total_pages: int) -> list[int]:
    try:
        return PageSelectionParser().parse(expression, total_pages)

    except ValueError as error:
        raise OperationError("invalid_range", str(error)) from error


@dataclass(frozen=True)
class ConvertRequest:
    """Tek bir dönüştürme işi (sunum katmanının seçimleri)."""

    paths: list[str]
    output_name: str = ""
    page_numbers: list[int] | None = None
    dpi: int = 150
    quality: int = 90
    # Office: True ise tüm dosyalar tek PDF'te birleştirilir.
    combine: bool = False
    # Görsel -> PDF: "a4" (beyaz A4'te ortalı) | "original" (görsel boyutu).
    page_mode: str = "a4"


ProgressReport = Callable[[int, str], None]

# A4 @ 150 DPI
_A4_SHORT_SIDE = 1240
_A4_LONG_SIDE = 1754
_A4_MARGIN_RATIO = 0.05


class _Progress:
    """Yalnızca ileri giden, yinelenmeyen ilerleme bildirimi."""

    def __init__(self, report: ProgressReport | None) -> None:
        self._report = report
        self._last_percent = -1
        self._last_text = ""
        self._lock = threading.Lock()

    def __call__(self, percent: float, text: str = "") -> None:
        if self._report is None:
            return

        percent = int(max(0, min(100, percent)))

        with self._lock:
            percent = max(percent, self._last_percent)

            if percent == self._last_percent and text == self._last_text:
                return

            self._last_percent = percent
            self._last_text = text

            self._report(percent, text)


@contextmanager
def _estimated_progress(
    progress: _Progress,
    start: float,
    end: float,
    text: str,
    expected_seconds: float = 10.0,
):
    """Bloklayan tek bir işin içi için zamana dayalı (tahmini) ilerleme.

    LibreOffice çağrısı bitene kadar ara değer vermediğinden yüzde,
    aralığın %95'ine asimptotik olarak yaklaşır; iş bitince çağıran
    aralığın sonunu bildirir.
    """
    stop = threading.Event()

    def loop() -> None:
        began = time.monotonic()

        while not stop.wait(0.25):
            fraction = 1 - math.exp(
                -(time.monotonic() - began) / expected_seconds
            )

            progress(start + (end - start) * 0.95 * fraction, text)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=1)


def _prepare_a4_page(source: str, target: Path) -> None:
    """Görseli beyaz zeminli A4 sayfaya ortalayıp JPEG olarak kaydeder."""
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)

        if image.mode in {"RGBA", "LA"} or (
            image.mode == "P" and "transparency" in image.info
        ):
            rgba = image.convert("RGBA")
            flat = Image.new("RGB", rgba.size, (255, 255, 255))
            flat.paste(rgba, mask=rgba.getchannel("A"))
            image = flat
        else:
            image = image.convert("RGB")

        landscape = image.width > image.height

        size = (
            (_A4_LONG_SIDE, _A4_SHORT_SIDE)
            if landscape
            else (_A4_SHORT_SIDE, _A4_LONG_SIDE)
        )

        margin = round(min(size) * _A4_MARGIN_RATIO)

        fitted = ImageOps.contain(
            image,
            (size[0] - margin * 2, size[1] - margin * 2),
            Image.Resampling.LANCZOS,
        )

        canvas = Image.new("RGB", size, (255, 255, 255))
        canvas.paste(
            fitted,
            ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2),
        )

        canvas.save(target, format="JPEG", quality=92, dpi=(150, 150))


def _new_convert_workspace() -> Path:
    workspace = AppPaths().temp_dir / f"convert_{uuid4().hex[:10]}"
    workspace.mkdir(parents=True, exist_ok=True)

    return workspace


def _convert_images(
    request: ConvertRequest,
    repository: SQLAlchemyDocumentRepository,
    progress: _Progress,
) -> list[Document]:
    image_paths = list(request.paths)
    total = len(image_paths)

    workspace: Path | None = None

    try:
        if request.page_mode == "a4":
            workspace = _new_convert_workspace()
            prepared: list[str] = []

            for index, source in enumerate(image_paths):
                target = workspace / f"{index:04d}.jpg"

                _prepare_a4_page(source, target)
                prepared.append(str(target))

                progress(
                    (index + 1) / total * 85,
                    f"{index + 1}/{total} — {Path(source).name}",
                )

            image_paths = prepared

        else:
            progress(85, "")

        document = ConvertImagesToPdfUseCase(
            repository, ImageToPdfService(), AppPaths()
        ).execute(image_paths, request.output_name)

        return [document]

    finally:
        if workspace is not None:
            shutil.rmtree(workspace, ignore_errors=True)


def _convert_office(
    request: ConvertRequest,
    repository: SQLAlchemyDocumentRepository,
    progress: _Progress,
) -> list[Document]:
    paths = AppPaths()
    sources = list(request.paths)
    total = len(sources)

    combine = request.combine and total > 1

    # Birleştirmede son %10 birleştirme adımına ayrılır.
    span = 90 if combine else 100

    def slot(index: int) -> tuple[float, float]:
        return index / total * span, (index + 1) / total * span

    if not combine:
        use_case = ConvertOfficeToPdfUseCase(
            repository, OfficeToPdfService(), paths
        )

        documents: list[Document] = []

        for index, source in enumerate(sources):
            begin, finish = slot(index)
            label = f"{index + 1}/{total} — {Path(source).name}"

            name = (
                request.output_name
                if total == 1 and request.output_name
                else Path(source).stem
            )

            with _estimated_progress(progress, begin, finish, label):
                documents.append(use_case.execute(source, name))

            progress(finish, label)

        return documents

    workspace = _new_convert_workspace()

    try:
        service = OfficeToPdfService()
        temp_pdfs: list[Path] = []

        for index, source in enumerate(sources):
            begin, finish = slot(index)
            label = f"{index + 1}/{total} — {Path(source).name}"
            target = workspace / f"{index:04d}_{Path(source).stem}.pdf"

            with _estimated_progress(progress, begin, finish, label):
                service.convert(source, target)

            temp_pdfs.append(target)
            progress(finish, label)

        name = request.output_name or f"{Path(sources[0]).stem}_merged"

        document = MergePdfsUseCase(
            repository, PdfMergeService(), paths
        ).execute(temp_pdfs, name)

        return [document]

    finally:
        shutil.rmtree(workspace, ignore_errors=True)


def _convert_pdf_to_images(
    request: ConvertRequest,
    repository: SQLAlchemyDocumentRepository,
    progress: _Progress,
) -> list[Document]:
    paths = AppPaths()
    sources = list(request.paths)
    single = len(sources) == 1

    use_case = ConvertPdfToImagesUseCase(
        repository, PdfToImageService(), paths
    )

    expected_pages = [
        len(request.page_numbers)
        if single and request.page_numbers
        else read_pdf_page_count(source)
        for source in sources
    ]
    grand_total = max(1, sum(expected_pages))

    documents: list[Document] = []
    finished_pages = 0

    for source, expected in zip(sources, expected_pages):
        name = (
            request.output_name
            if single and request.output_name
            else Path(source).stem
        )

        label = Path(source).name

        paths.generated_dir.mkdir(parents=True, exist_ok=True)
        known = {item.name for item in paths.generated_dir.glob("*.jpg")}

        stop = threading.Event()

        def poll(known=known, base=finished_pages, label=label) -> None:
            while not stop.wait(0.2):
                created = sum(
                    1
                    for item in paths.generated_dir.glob("*.jpg")
                    if item.name not in known
                )

                progress(min(99, (base + created) / grand_total * 100), label)

        poller = threading.Thread(target=poll, daemon=True)
        poller.start()

        try:
            documents.extend(
                use_case.execute(
                    source,
                    name,
                    page_numbers=request.page_numbers if single else None,
                    dpi=request.dpi,
                    quality=request.quality,
                )
            )
        finally:
            stop.set()
            poller.join(timeout=1)

        finished_pages += expected
        progress(min(99, finished_pages / grand_total * 100), label)

    return documents


def convert_files(
    request: ConvertRequest,
    report: ProgressReport | None = None,
) -> list[Document]:
    """Dosya türüne göre uygun dönüştürmeyi çalıştırır.

    Uzun sürebileceği için sunum katmanı bunu arka plan iş parçacığında
    çağırır (session_scope çağrı başına kendi oturumunu açar). `report`
    verilirse `report(yüzde, metin)` ile 0-100 arası, geriye gitmeyen
    ilerleme bildirilir.
    """
    kind = detect_convert_kind(request.paths)

    if kind in ("mixed", "unsupported", "empty"):
        raise OperationError(kind)

    progress = _Progress(report)
    progress(0, "")

    try:
        with _scope() as session:
            repository = SQLAlchemyDocumentRepository(session)

            if kind == "images_to_pdf":
                documents = _convert_images(request, repository, progress)
            elif kind == "office_to_pdf":
                documents = _convert_office(request, repository, progress)
            else:
                documents = _convert_pdf_to_images(
                    request, repository, progress
                )

    except Exception as error:
        raise _operation_error_from(error) from error

    progress(100, "")

    return documents


def reveal_in_folder(path: str) -> None:
    """Dosyayı işletim sisteminin dosya yöneticisinde gösterir.

    Windows'ta dosya seçili olarak açılır; dosya yoksa klasörü açar.
    """
    target = Path(path)
    folder = target if target.is_dir() else target.parent

    if not folder.exists():
        raise OperationError("not_found", str(target))

    try:
        if sys.platform == "win32" and target.is_file():
            subprocess.Popen(f'explorer /select,"{target}"')
            return

        opened = QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    except OSError as error:
        raise OperationError("reveal_failed", str(error)) from error

    if not opened:
        raise OperationError("reveal_failed", str(folder))


# PDF düzenleme: her adım geçici bir çalışma klasöründe, kaynağı
# değiştirmeden uygulanır; kalıcı çıktı yalnızca "Kaydet"te, son adımın
# use-case ile çalıştırılmasıyla kütüphaneye tek belge olarak eklenir.
_EDIT_OPERATIONS = (
    "rotate_pages",
    "delete_pages",
    "duplicate_pages",
    "reorder_pages",
    "insert_pages",
    "insert_blank_page",
)


@dataclass(frozen=True)
class EditOperation:
    name: str
    args: dict = field(default_factory=dict)


def new_edit_workspace() -> Path:
    workspace = AppPaths().temp_dir / f"edit_{uuid4().hex[:10]}"
    workspace.mkdir(parents=True, exist_ok=True)

    return workspace


def discard_edit_workspace(workspace: Path | None) -> None:
    if workspace is not None:
        shutil.rmtree(workspace, ignore_errors=True)


def apply_edit_step(
    input_path: str,
    operation: EditOperation,
    output_path: str,
) -> Path:
    if operation.name not in _EDIT_OPERATIONS:
        raise OperationError("unknown", operation.name)

    try:
        return getattr(PdfPageEditService(), operation.name)(
            input_path=input_path,
            output_path=output_path,
            **operation.args,
        )

    except Exception as error:
        raise _operation_error_from(error) from error


def save_edit_result(
    input_path: str,
    operation: EditOperation,
    display_name: str,
) -> Document:
    """Son düzenleme adımını kalıcı çıktı olarak kütüphaneye kaydeder."""
    if operation.name not in _EDIT_OPERATIONS:
        raise OperationError("unknown", operation.name)

    try:
        with _scope() as session:
            use_case = EditPdfPagesUseCase(
                SQLAlchemyDocumentRepository(session),
                PdfPageEditService(),
                AppPaths(),
            )

            return getattr(use_case, operation.name)(
                input_path=input_path,
                display_name=display_name,
                **operation.args,
            )

    except Exception as error:
        raise _operation_error_from(error) from error
