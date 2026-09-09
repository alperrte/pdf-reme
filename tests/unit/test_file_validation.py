from PIL import Image
from pypdf import PdfWriter
from zipfile import ZipFile
from pdf_reme.infrastructure.filesystem.file_validation import (
    detect_document_type,
    validate_file,
)


def test_detect_supported_document_types():
    assert detect_document_type("sample.pdf") == "pdf"
    assert detect_document_type("sample.doc") == "word"
    assert detect_document_type("sample.docx") == "word"
    assert detect_document_type("sample.ppt") == "powerpoint"
    assert detect_document_type("sample.pptx") == "powerpoint"
    assert detect_document_type("sample.jpg") == "image"
    assert detect_document_type("sample.jpeg") == "image"
    assert detect_document_type("sample.png") == "image"


def test_detect_document_type_is_case_insensitive():
    assert detect_document_type("SAMPLE.PDF") == "pdf"
    assert detect_document_type("IMAGE.JPG") == "image"


def test_unsupported_extension_returns_none():
    assert detect_document_type("sample.xlsx") is None
    assert detect_document_type("sample.txt") is None


def test_valid_pdf_is_accepted(tmp_path):
    pdf_path = tmp_path / "valid.pdf"

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)

    with pdf_path.open("wb") as file:
        writer.write(file)

    result = validate_file(pdf_path)

    assert result.is_valid is True
    assert result.document_type == "pdf"
    assert result.extension == ".pdf"
    assert result.error is None


def test_corrupted_pdf_is_rejected(tmp_path):
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"this is not a real pdf")

    result = validate_file(pdf_path)

    assert result.is_valid is False
    assert result.document_type == "pdf"
    assert result.error is not None


def test_valid_image_is_accepted(tmp_path):
    image_path = tmp_path / "valid.png"

    image = Image.new("RGB", (100, 100))
    image.save(image_path)

    result = validate_file(image_path)

    assert result.is_valid is True
    assert result.document_type == "image"
    assert result.extension == ".png"


def test_corrupted_image_is_rejected(tmp_path):
    image_path = tmp_path / "corrupted.jpg"
    image_path.write_bytes(b"this is not a real image")

    result = validate_file(image_path)

    assert result.is_valid is False
    assert result.document_type == "image"
    assert result.error is not None


def test_missing_file_is_rejected(tmp_path):
    missing_path = tmp_path / "missing.pdf"

    result = validate_file(missing_path)

    assert result.is_valid is False
    assert result.document_type is None
    assert result.error == "Dosya bulunamadı."


def test_unsupported_file_is_rejected(tmp_path):
    unsupported_path = tmp_path / "sample.xlsx"
    unsupported_path.write_bytes(b"dummy content")

    result = validate_file(unsupported_path)

    assert result.is_valid is False
    assert result.document_type is None
    assert result.error == "Desteklenmeyen dosya türü."


def create_valid_docx(path):
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr("word/document.xml", "<document></document>")


def create_valid_pptx(path):
    with ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types></Types>")
        archive.writestr(
            "ppt/presentation.xml",
            "<presentation></presentation>",
        )


def test_valid_docx_is_accepted(tmp_path):
    docx_path = tmp_path / "valid.docx"
    create_valid_docx(docx_path)

    result = validate_file(docx_path)

    assert result.is_valid is True
    assert result.document_type == "word"
    assert result.extension == ".docx"


def test_valid_pptx_is_accepted(tmp_path):
    pptx_path = tmp_path / "valid.pptx"
    create_valid_pptx(pptx_path)

    result = validate_file(pptx_path)

    assert result.is_valid is True
    assert result.document_type == "powerpoint"
    assert result.extension == ".pptx"


def test_fake_docx_is_rejected(tmp_path):
    docx_path = tmp_path / "fake.docx"
    docx_path.write_bytes(b"this is not a real docx")

    result = validate_file(docx_path)

    assert result.is_valid is False
    assert result.document_type == "word"
    assert result.error is not None


def test_fake_pptx_is_rejected(tmp_path):
    pptx_path = tmp_path / "fake.pptx"
    pptx_path.write_bytes(b"this is not a real pptx")

    result = validate_file(pptx_path)

    assert result.is_valid is False
    assert result.document_type == "powerpoint"
    assert result.error is not None