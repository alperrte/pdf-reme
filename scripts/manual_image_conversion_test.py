import sys
import tempfile
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"

if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdf_reme.application.use_cases.convert_images_to_pdf import (
    ConvertImagesToPdfUseCase,
)
from pdf_reme.application.use_cases.convert_pdf_to_images import (
    ConvertPdfToImagesUseCase,
)
from pdf_reme.infrastructure.conversion.image_to_pdf_service import (
    ImageToPdfService,
)
from pdf_reme.infrastructure.conversion.pdf_to_image_service import (
    PdfToImageService,
)
from pdf_reme.infrastructure.database.connection import (
    SessionLocal,
)
from pdf_reme.infrastructure.database.repositories.document_repository import (
    SQLAlchemyDocumentRepository,
)
from pdf_reme.shared.paths.app_paths import AppPaths


def create_image(
    path: Path,
    size: tuple[int, int],
    mode: str = "RGB",
) -> None:
    image = Image.new(
        mode,
        size,
    )

    image.save(path)
    image.close()


def create_pdf(
    path: Path,
) -> None:
    writer = PdfWriter()

    writer.add_blank_page(
        width=72,
        height=100,
    )

    writer.add_blank_page(
        width=144,
        height=100,
    )

    writer.add_blank_page(
        width=216,
        height=100,
    )

    with path.open("wb") as file:
        writer.write(file)


def main() -> None:
    paths = AppPaths()
    paths.ensure_directories()

    session = SessionLocal()

    try:
        repository = (
            SQLAlchemyDocumentRepository(
                session
            )
        )

        images_to_pdf = (
            ConvertImagesToPdfUseCase(
                repository,
                ImageToPdfService(),
                paths,
            )
        )

        pdf_to_images = (
            ConvertPdfToImagesUseCase(
                repository,
                PdfToImageService(),
                paths,
            )
        )

        test_id = uuid4().hex[:8]

        print(
            "=== PDF-REME  "
            "GÖRSEL DÖNÜŞÜM TESTİ ==="
        )

        with tempfile.TemporaryDirectory() as temp:
            temp_path = Path(temp)

            first = temp_path / "first.jpg"
            second = temp_path / "second.png"
            third = temp_path / "third.jpeg"

            create_image(
                first,
                (101, 60),
            )

            create_image(
                second,
                (202, 60),
                mode="RGBA",
            )

            create_image(
                third,
                (303, 60),
            )

            original_bytes = {
                first: first.read_bytes(),
                second: second.read_bytes(),
                third: third.read_bytes(),
            }

            # JPG/PNG -> PDF
            pdf_document = (
                images_to_pdf.execute(
                    [
                        third,
                        first,
                        second,
                    ],
                    (
                        f"manual-images-"
                        f"{test_id}.pdf"
                    ),
                )
            )

            pdf_path = Path(
                pdf_document.stored_path
            )

            reader = PdfReader(
                str(pdf_path)
            )

            assert len(reader.pages) == 3

            widths = [
                round(
                    float(
                        page.mediabox.width
                    )
                )
                for page in reader.pages
            ]

            assert widths == [
                303,
                101,
                202,
            ]

            print()
            print("1. JPG / PNG → PDF")
            print(
                f"Sayfa sırası: {widths}"
            )
            print(
                "Şeffaf PNG işlendi: BAŞARILI"
            )
            print("SONUÇ: BAŞARILI")

            # PDF -> JPG
            source_pdf = (
                temp_path
                / "source.pdf"
            )

            create_pdf(source_pdf)

            pdf_before = (
                source_pdf.read_bytes()
            )

            jpg_documents = (
                pdf_to_images.execute(
                    input_path=source_pdf,
                    base_name=(
                        f"manual-jpg-"
                        f"{test_id}"
                    ),
                    page_numbers=[
                        3,
                        1,
                    ],
                    dpi=72,
                    quality=90,
                )
            )

            assert len(
                jpg_documents
            ) == 2

            output_names = [
                Path(
                    document.stored_path
                ).name
                for document in jpg_documents
            ]

            print()
            print("2. PDF → JPG")
            print(
                "Seçilen sayfalar: [3, 1]"
            )
            print(
                f"Çıktılar: {output_names}"
            )
            print("SONUÇ: BAŞARILI")

            # Sources unchanged
            for (
                source,
                before,
            ) in original_bytes.items():
                assert (
                    source.read_bytes()
                    == before
                )

            assert (
                source_pdf.read_bytes()
                == pdf_before
            )

            assert repository.get_by_id(
                pdf_document.id
            ) is not None

            for document in jpg_documents:
                assert repository.get_by_id(
                    document.id
                ) is not None

            session.commit()

            print()
            print(
                "Kaynak görseller değişmedi: "
                "BAŞARILI"
            )
            print(
                "Kaynak PDF değişmedi: "
                "BAŞARILI"
            )
            print(
                "Generated DB kayıtları: "
                "BAŞARILI"
            )

            print()
            print(
                "SONUÇ: GERÇEK "
                "GÖRSEL DÖNÜŞÜM TESTİ BAŞARILI"
            )

    except Exception:
        session.rollback()
        raise

    finally:
        session.close()


if __name__ == "__main__":
    main()