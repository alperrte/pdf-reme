import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from pypdf import PdfWriter

from pdf_reme.infrastructure.conversion.office_to_pdf_service import (
    OfficeToPdfService,
)


def create_source(
    path: Path,
) -> Path:
    path.write_bytes(
        b"test-office-file"
    )

    return path


def create_valid_pdf(
    path: Path,
) -> None:
    writer = PdfWriter()

    writer.add_blank_page(
        width=100,
        height=100,
    )

    with path.open("wb") as file:
        writer.write(file)


@pytest.mark.parametrize(
    "extension",
    [
        ".doc",
        ".docx",
        ".ppt",
        ".pptx",
        ".xls",
        ".xlsx",
    ],
)
def test_supported_office_extensions(
    tmp_path,
    extension,
):
    service = OfficeToPdfService()

    source = create_source(
        tmp_path / f"source{extension}"
    )

    service._validate_source(source)


def test_missing_source_is_rejected(
    tmp_path,
):
    service = OfficeToPdfService()

    with pytest.raises(
        FileNotFoundError,
    ):
        service._validate_source(
            tmp_path / "missing.docx"
        )


def test_unsupported_extension_is_rejected(
    tmp_path,
):
    service = OfficeToPdfService()

    source = create_source(
        tmp_path / "source.txt"
    )

    with pytest.raises(
        ValueError,
        match="DOC, DOCX, PPT, PPTX",
    ):
        service._validate_source(
            source
        )


def test_output_must_be_pdf(tmp_path):
    service = OfficeToPdfService()

    source = create_source(
        tmp_path / "source.docx"
    )

    with pytest.raises(
        ValueError,
        match="PDF formatında",
    ):
        service._validate_output_path(
            source,
            tmp_path / "output.txt",
        )


def test_missing_runtime_is_rejected(
    tmp_path,
):
    service = OfficeToPdfService(
        runtime_path=(
            tmp_path
            / "missing-runtime"
        )
    )

    with pytest.raises(
        FileNotFoundError,
        match="LibreOffice Runtime",
    ):
        service._resolve_soffice()


def test_successful_conversion(
    tmp_path,
    monkeypatch,
):
    runtime = (
        tmp_path
        / "soffice.exe"
    )
    runtime.write_bytes(b"fake")

    source = create_source(
        tmp_path / "source.docx"
    )

    output = (
        tmp_path
        / "result.pdf"
    )

    service = OfficeToPdfService(
        runtime_path=runtime
    )

    def fake_run(
        args,
        **kwargs,
    ):
        outdir = Path(
            args[
                args.index(
                    "--outdir"
                )
                + 1
            ]
        )

        create_valid_pdf(
            outdir / "source.pdf"
        )

        return SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    result = service.convert(
        source,
        output,
    )

    assert result == output
    assert output.exists()


def test_nonzero_exit_code_is_rejected(
    tmp_path,
    monkeypatch,
):
    runtime = (
        tmp_path
        / "soffice.exe"
    )
    runtime.write_bytes(b"fake")

    source = create_source(
        tmp_path / "source.xlsx"
    )

    service = OfficeToPdfService(
        runtime_path=runtime
    )

    def fake_run(
        args,
        **kwargs,
    ):
        return SimpleNamespace(
            returncode=1,
            stdout="",
            stderr="conversion failed",
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        RuntimeError,
        match="başarısız",
    ):
        service.convert(
            source,
            tmp_path / "output.pdf",
        )


def test_missing_generated_pdf_is_rejected(
    tmp_path,
    monkeypatch,
):
    runtime = (
        tmp_path
        / "soffice.exe"
    )
    runtime.write_bytes(b"fake")

    source = create_source(
        tmp_path / "source.pptx"
    )

    service = OfficeToPdfService(
        runtime_path=runtime
    )

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs:
        SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="PDF dosyası oluşturmadı",
    ):
        service.convert(
            source,
            tmp_path / "output.pdf",
        )


def test_timeout_is_reported(
    tmp_path,
    monkeypatch,
):
    runtime = (
        tmp_path
        / "soffice.exe"
    )
    runtime.write_bytes(b"fake")

    source = create_source(
        tmp_path / "source.docx"
    )

    service = OfficeToPdfService(
        runtime_path=runtime,
        timeout_seconds=1,
    )

    def timeout_run(
        *args,
        **kwargs,
    ):
        raise subprocess.TimeoutExpired(
            cmd="soffice",
            timeout=1,
        )

    monkeypatch.setattr(
        subprocess,
        "run",
        timeout_run,
    )

    with pytest.raises(
        TimeoutError,
        match="zaman aşımına",
    ):
        service.convert(
            source,
            tmp_path / "output.pdf",
        )