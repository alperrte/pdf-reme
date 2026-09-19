"""Sıkıştırma motoru (Hafif / Dengeli / Güçlü) — yalnızca tmp'de sentetik PDF'ler."""

import random
import zlib
from io import BytesIO
from pathlib import Path

import pikepdf
import pytest
from PIL import Image, ImageFilter
from pikepdf import Dictionary, Name, Pdf, Stream

from pdf_reme.infrastructure.pdf.pdf_compression_engine import (
    PdfCompressionEngine,
)

IMAGE_SIZE = (1600, 1100)
IMAGE_COUNT = 3


@pytest.fixture(scope="module", autouse=True)
def qt_application():
    # Güçlü seviye sayfaları Qt ile rasterize eder.
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])

    yield app


def photo_like(seed: int) -> Image.Image:
    """Gürültü + bulanıklıkla fotoğrafa benzer sıkıştırılabilirlikte görüntü."""
    width, height = IMAGE_SIZE
    rng = random.Random(seed)

    small = Image.frombytes(
        "RGB",
        (width // 8, height // 8),
        rng.randbytes((width // 8) * (height // 8) * 3),
    )
    image = small.resize((width, height), Image.Resampling.BICUBIC)
    noise = Image.effect_noise((width, height), 14).convert("RGB")

    return Image.blend(image, noise, 0.08).filter(
        ImageFilter.GaussianBlur(0.8)
    )


def _image_stream(pdf: Pdf, image: Image.Image, *, jpeg_quality: int | None):
    if jpeg_quality is None:
        stream = Stream(pdf, zlib.compress(image.tobytes(), 6))
        stream.Filter = Name.FlateDecode
    else:
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=jpeg_quality)
        stream = Stream(pdf, buffer.getvalue())
        stream.Filter = Name.DCTDecode

    stream.Type = Name.XObject
    stream.Subtype = Name.Image
    stream.Width, stream.Height = image.size
    stream.ColorSpace = Name.DeviceRGB
    stream.BitsPerComponent = 8

    return stream


def _add_smask(pdf: Pdf, stream: Stream, size) -> None:
    mask = Stream(pdf, zlib.compress(Image.new("L", size, 255).tobytes(), 6))
    mask.Filter = Name.FlateDecode
    mask.Type = Name.XObject
    mask.Subtype = Name.Image
    mask.Width, mask.Height = size
    mask.ColorSpace = Name.DeviceGray
    mask.BitsPerComponent = 8

    stream.SMask = pdf.make_indirect(mask)


def build_pdf(path: Path, kind: str) -> Path:
    pdf = Pdf.new()

    if kind == "text":
        font = pdf.make_indirect(
            Dictionary(
                Type=Name.Font,
                Subtype=Name.Type1,
                BaseFont=Name.Helvetica,
            )
        )
        page = Dictionary(
            Type=Name.Page,
            MediaBox=[0, 0, 600, 800],
            Resources=Dictionary(Font=Dictionary(F1=font)),
            Contents=pdf.make_stream(b"BT /F1 12 Tf 40 700 Td (Merhaba) Tj ET"),
        )
        pdf.pages.append(pikepdf.Page(page))
        pdf.save(path)

        return path

    resources = Dictionary(XObject=Dictionary())
    content = b""

    for index in range(IMAGE_COUNT):
        image = photo_like(index)

        if kind == "flate":
            stream = _image_stream(pdf, image, jpeg_quality=None)
        elif kind == "jpeg95":
            stream = _image_stream(pdf, image, jpeg_quality=95)
        elif kind == "jpeg75":
            stream = _image_stream(pdf, image, jpeg_quality=75)
        elif kind == "smask":
            stream = _image_stream(pdf, image, jpeg_quality=95)
            _add_smask(pdf, stream, image.size)
        else:
            raise ValueError(kind)

        resources.XObject[Name(f"/Im{index}")] = pdf.make_indirect(stream)
        content += (
            f"q 500 0 0 350 30 {40 + index * 380} cm /Im{index} Do Q\n"
        ).encode()

    page = Dictionary(
        Type=Name.Page,
        MediaBox=[0, 0, 560, 40 + 380 * IMAGE_COUNT],
        Resources=resources,
        Contents=pdf.make_stream(content),
    )
    pdf.pages.append(pikepdf.Page(page))
    pdf.save(path)

    return path


def compress(tmp_path: Path, kind: str, level: str) -> tuple[Path, Path]:
    source = build_pdf(tmp_path / f"{kind}.pdf", kind)
    output = tmp_path / f"{kind}_{level}.pdf"

    PdfCompressionEngine().compress(source, output, level)

    return source, output


def saving(source: Path, output: Path) -> float:
    return 1 - output.stat().st_size / source.stat().st_size


def page_count(path: Path) -> int:
    with pikepdf.open(path) as pdf:
        return len(pdf.pages)


@pytest.mark.parametrize("kind", ["flate", "jpeg95", "jpeg75", "smask"])
def test_light_compresses_image_heavy_pdfs(tmp_path, kind):
    # Eski davranışta JPEG'ler ve maskeli görüntüler neredeyse hiç küçülmüyordu.
    source, output = compress(tmp_path, kind, "light")

    assert page_count(output) == 1
    assert saving(source, output) >= 0.12, (kind, saving(source, output))


@pytest.mark.parametrize("kind", ["flate", "jpeg95", "smask"])
def test_balanced_compresses_more_than_light(tmp_path, kind):
    source, light = compress(tmp_path, kind, "light")
    _, balanced = compress(tmp_path, kind, "balanced")

    assert balanced.stat().st_size < light.stat().st_size
    assert saving(source, balanced) >= 0.40, (kind, saving(source, balanced))


def test_strong_still_compresses_and_keeps_pages(tmp_path):
    source, output = compress(tmp_path, "flate", "strong")

    assert page_count(output) == 1
    assert saving(source, output) >= 0.50


def test_smask_objects_survive_light_and_balanced(tmp_path):
    for level in ("light", "balanced"):
        _, output = compress(tmp_path, "smask", level)

        with pikepdf.open(output) as pdf:
            images = [
                obj
                for obj in pdf.pages[0].Resources.XObject.values()
                if obj.get("/Subtype") == Name.Image
            ]

            assert len(images) == IMAGE_COUNT
            assert all("/SMask" in image for image in images), level


@pytest.mark.parametrize("level", ["light", "balanced", "strong"])
def test_text_only_pdf_never_grows(tmp_path, level):
    source, output = compress(tmp_path, "text", level)

    assert page_count(output) == 1
    assert output.stat().st_size <= source.stat().st_size + 512
