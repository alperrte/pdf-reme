from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImageReader, QPainter, QPainterPath, QPixmap


_CACHE_LIMIT = 200

# (yol, değişim zamanı, piksel boyutu) -> QPixmap
_cache: OrderedDict[tuple[str, int, int], QPixmap] = OrderedDict()


def image_thumbnail(
    path: str | Path,
    size: int,
    radius: int,
    device_pixel_ratio: float = 1.0,
) -> QPixmap | None:
    """Görseli size x size kareye "cover" biçiminde kırpıp yuvarlatır.

    Dosya yoksa/okunamıyorsa None döner; çağıran ikon gösterir.
    """
    file_path = Path(path)

    try:
        modified = file_path.stat().st_mtime_ns
    except OSError:
        return None

    pixel_size = max(1, round(size * device_pixel_ratio))

    key = (str(file_path), modified, pixel_size)

    cached = _cache.get(key)

    if cached is not None:
        _cache.move_to_end(key)
        return cached

    reader = QImageReader(str(file_path))
    reader.setAutoTransform(True)

    source_size = reader.size()

    if source_size.isValid() and not source_size.isEmpty():
        scale = pixel_size / min(source_size.width(), source_size.height())

        # Tam çözünürlüklü görseli belleğe almadan, okurken küçült.
        if scale < 1:
            reader.setScaledSize(
                QSize(
                    max(pixel_size, round(source_size.width() * scale)),
                    max(pixel_size, round(source_size.height() * scale)),
                )
            )

    image = reader.read()

    if image.isNull():
        return None

    scaled = QPixmap.fromImage(
        image.scaled(
            pixel_size,
            pixel_size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
    )

    result = QPixmap(pixel_size, pixel_size)
    result.fill(Qt.GlobalColor.transparent)

    painter = QPainter(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    clip = QPainterPath()
    clip.addRoundedRect(
        QRectF(0, 0, pixel_size, pixel_size),
        radius * device_pixel_ratio,
        radius * device_pixel_ratio,
    )
    painter.setClipPath(clip)

    painter.drawPixmap(
        (pixel_size - scaled.width()) // 2,
        (pixel_size - scaled.height()) // 2,
        scaled,
    )
    painter.end()

    result.setDevicePixelRatio(device_pixel_ratio)

    _cache[key] = result

    while len(_cache) > _CACHE_LIMIT:
        _cache.popitem(last=False)

    return result
