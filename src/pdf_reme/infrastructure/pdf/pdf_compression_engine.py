import shutil
from io import BytesIO
from pathlib import Path

import pikepdf
from pikepdf import JobBuilder, Name, PdfImage
from PIL import Image
from PySide6.QtCore import (
    QByteArray,
    QBuffer,
    QIODevice,
    QSize,
)
from PySide6.QtPdf import QPdfDocument


class PdfCompressionEngine:
    TARGET_SAVINGS = {
        "light": 0.20,
        "balanced": 0.50,
        "strong": 0.75,
    }

    IMAGE_RECIPES = {
        "light": {
            "scale": 1.00,
            "quality": 95,
            "min_pixels": 250_000,
        },
        "balanced": {
            "scale": 0.80,
            "quality": 80,
            "min_pixels": 100_000,
        },
        "strong": {
            "scale": 0.60,
            "quality": 60,
            "min_pixels": 50_000,
        },
    }

    def compress(
        self,
        source_path: Path,
        output_path: Path,
        level: str,
    ) -> None:
        target_savings = (
            self.TARGET_SAVINGS[level]
        )

        preserve_candidate = (
            output_path.parent
            / f"{output_path.stem}_preserve.pdf"
        )

        raster_candidate = (
            output_path.parent
            / f"{output_path.stem}_raster.pdf"
        )

        self._run_structure_preserving_compression(
            source_path=source_path,
            output_path=preserve_candidate,
            level=level,
        )

        chosen_path = preserve_candidate

        # Light ve Balanced mümkün olduğunca
        # gerçek PDF yapısını korur.
        #
        # Strong hedeflenen küçültmeye yaklaşamazsa
        # raster fallback kullanabilir.
        if level == "strong":
            preserve_savings = (
                self._calculate_savings_fraction(
                    source_path,
                    preserve_candidate,
                )
            )

            if preserve_savings < 0.70:
                self._run_adaptive_raster_compression(
                    source_path=source_path,
                    output_path=raster_candidate,
                    target_savings=target_savings,
                )

                if (
                    raster_candidate.exists()
                    and raster_candidate.stat().st_size
                    < preserve_candidate.stat().st_size
                ):
                    chosen_path = raster_candidate

        try:
            shutil.move(
                str(chosen_path),
                str(output_path),
            )

        finally:
            for candidate in (
                preserve_candidate,
                raster_candidate,
            ):
                if candidate.exists():
                    candidate.unlink()

    def _run_structure_preserving_compression(
        self,
        source_path: Path,
        output_path: Path,
        level: str,
    ) -> None:
        recipe = self.IMAGE_RECIPES[
            level
        ]

        scale = recipe["scale"]
        quality = recipe["quality"]
        min_pixels = recipe["min_pixels"]

        target_saved_bytes = int(
            source_path.stat().st_size
            * self.TARGET_SAVINGS[level]
        )

        intermediate_path = (
            output_path.parent
            / (
                f"{output_path.stem}"
                "_image_stage.pdf"
            )
        )

        estimated_saved_bytes = 0

        try:
            with pikepdf.open(
                source_path
            ) as pdf:
                image_objects = []
                seen_objects = set()

                for page in pdf.pages:
                    for raw_image in (
                        page.get_images().values()
                    ):
                        objgen = tuple(
                            raw_image.objgen
                        )

                        if objgen != (0, 0):
                            object_key = (
                                "objgen",
                                objgen,
                            )
                        else:
                            object_key = (
                                "direct",
                                id(raw_image),
                            )

                        if (
                            object_key
                            in seen_objects
                        ):
                            continue

                        seen_objects.add(
                            object_key
                        )

                        try:
                            if raw_image.get(
                                "/ImageMask",
                                False,
                            ):
                                continue

                            if (
                                "/SMask" in raw_image
                                or "/Mask" in raw_image
                            ):
                                continue

                            raw_size = len(
                                raw_image.read_raw_bytes()
                            )

                            pdf_image = PdfImage(
                                raw_image
                            )

                            pixel_count = (
                                pdf_image.width
                                * pdf_image.height
                            )

                            if (
                                pixel_count
                                < min_pixels
                            ):
                                continue

                            image_objects.append(
                                (
                                    raw_size,
                                    raw_image,
                                )
                            )
                        except Exception:
                            continue
                image_objects.sort(
                    key=lambda item: item[0],
                    reverse=True,
                )

                for (
                    raw_size,
                    raw_image,
                ) in image_objects:
                    if (
                        estimated_saved_bytes
                        >= target_saved_bytes
                    ):
                        break
                    saved = (
                        self._recompress_image_stream(
                            raw_image=raw_image,
                            original_raw_size=raw_size,
                            scale=scale,
                            quality=quality,
                        )
                    )
                    estimated_saved_bytes += (
                        saved
                    )

                pdf.save(
                    intermediate_path
                )
            (
                JobBuilder()
                .input(
                    str(intermediate_path)
                )
                .output(
                    str(output_path)
                )
                .compress(
                    compress_streams=True,
                    object_streams="generate",
                    recompress_flate=True,
                    compression_level=9,
                    decode_level="generalized",
                )
                .run()
            )

        finally:
            if intermediate_path.exists():
                intermediate_path.unlink()

    def _recompress_image_stream(
        self,
        raw_image,
        original_raw_size: int,
        scale: float,
        quality: int,
    ) -> int:
        pil_image = None
        working_image = None

        try:
            pdf_image = PdfImage(
                raw_image
            )

            pil_image = (
                pdf_image.as_pil_image()
            )

            pil_image.load()

            original_width = (
                pil_image.width
            )

            original_height = (
                pil_image.height
            )

            new_width = max(
                1,
                round(
                    original_width
                    * scale
                ),
            )

            new_height = max(
                1,
                round(
                    original_height
                    * scale
                ),
            )

            if pil_image.mode == "CMYK":
                working_image = (
                    pil_image.convert(
                        "CMYK"
                    )
                )

                color_space = (
                    Name.DeviceCMYK
                )

            elif pil_image.mode in {
                "1",
                "L",
            }:
                working_image = (
                    pil_image.convert(
                        "L"
                    )
                )

                color_space = (
                    Name.DeviceGray
                )

            else:
                working_image = (
                    pil_image.convert(
                        "RGB"
                    )
                )

                color_space = (
                    Name.DeviceRGB
                )

            if (
                new_width
                != working_image.width
                or new_height
                != working_image.height
            ):
                resized = (
                    working_image.resize(
                        (
                            new_width,
                            new_height,
                        ),
                        Image.Resampling.LANCZOS,
                    )
                )

                working_image.close()
                working_image = resized

            buffer = BytesIO()

            working_image.save(
                buffer,
                format="JPEG",
                quality=quality,
                optimize=True,
                progressive=True,
            )

            new_data = (
                buffer.getvalue()
            )

            buffer.close()

            if (
                len(new_data)
                >= original_raw_size * 0.97
            ):
                return 0

            for key in (
                "/DecodeParms",
                "/Decode",
            ):
                if key in raw_image:
                    del raw_image[key]

            raw_image.write(
                new_data,
                filter=Name.DCTDecode,
            )

            raw_image.Width = (
                working_image.width
            )

            raw_image.Height = (
                working_image.height
            )

            raw_image.BitsPerComponent = 8

            raw_image.ColorSpace = (
                color_space
            )

            return max(
                0,
                original_raw_size
                - len(new_data),
            )

        except Exception:
            return 0

        finally:
            if working_image is not None:
                working_image.close()

            if pil_image is not None:
                pil_image.close()

    def _run_adaptive_raster_compression(
        self,
        source_path: Path,
        output_path: Path,
        target_savings: float,
    ) -> None:
        recipes = [
            (144, 70),
            (120, 58),
            (96, 48),
        ]

        best_candidate = None
        best_size = None

        candidate_paths = []

        try:
            for index, (
                dpi,
                quality,
            ) in enumerate(recipes):
                candidate = (
                    output_path.parent
                    / f"raster_{index}.pdf"
                )

                candidate_paths.append(
                    candidate
                )

                self._rasterize_pdf(
                    source_path=source_path,
                    output_path=candidate,
                    dpi=dpi,
                    jpeg_quality=quality,
                )

                candidate_size = (
                    candidate.stat().st_size
                )

                if (
                    best_size is None
                    or candidate_size
                    < best_size
                ):
                    best_size = (
                        candidate_size
                    )

                    best_candidate = (
                        candidate
                    )

                savings = (
                    self._calculate_savings_fraction(
                        source_path,
                        candidate,
                    )
                )

                if savings >= target_savings:
                    best_candidate = (
                        candidate
                    )
                    break

            if best_candidate is None:
                raise RuntimeError(
                    "Güçlü sıkıştırma için "
                    "geçerli çıktı üretilemedi."
                )

            shutil.copy2(
                best_candidate,
                output_path,
            )

        finally:
            for candidate in candidate_paths:
                if candidate.exists():
                    candidate.unlink()

    def _rasterize_pdf(
        self,
        source_path: Path,
        output_path: Path,
        dpi: int,
        jpeg_quality: int,
    ) -> None:
        document = QPdfDocument()

        load_error = document.load(
            str(source_path)
        )

        if (
            load_error
            != QPdfDocument.Error.None_
        ):
            document.close()

            raise RuntimeError(
                "PDF raster sıkıştırma "
                "için açılamadı."
            )

        pages: list[Image.Image] = []

        try:
            page_count = (
                document.pageCount()
            )

            if page_count <= 0:
                raise RuntimeError(
                    "PDF içerisinde sayfa "
                    "bulunamadı."
                )

            for page_index in range(
                page_count
            ):
                point_size = (
                    document.pagePointSize(
                        page_index
                    )
                )

                scale = (
                    dpi / 72.0
                )

                image_size = QSize(
                    max(
                        1,
                        round(
                            point_size.width()
                            * scale
                        ),
                    ),
                    max(
                        1,
                        round(
                            point_size.height()
                            * scale
                        ),
                    ),
                )

                rendered = (
                    document.render(
                        page_index,
                        image_size,
                    )
                )

                if rendered.isNull():
                    raise RuntimeError(
                        "PDF sayfası render "
                        "edilemedi: "
                        f"{page_index + 1}"
                    )

                byte_array = QByteArray()

                qt_buffer = QBuffer(
                    byte_array
                )

                qt_buffer.open(
                    QIODevice.OpenModeFlag.WriteOnly
                )

                success = rendered.save(
                    qt_buffer,
                    "JPEG",
                    jpeg_quality,
                )

                qt_buffer.close()

                if not success:
                    raise RuntimeError(
                        "PDF sayfası JPEG "
                        "formatına çevrilemedi."
                    )

                pil_buffer = BytesIO(
                    bytes(byte_array)
                )

                with Image.open(
                    pil_buffer
                ) as image:
                    rgb_image = (
                        image.convert(
                            "RGB"
                        )
                    )

                    rgb_image.load()

                    pages.append(
                        rgb_image
                    )

                pil_buffer.close()

            first_page = pages[0]

            first_page.save(
                output_path,
                format="PDF",
                save_all=True,
                append_images=pages[1:],
                resolution=dpi,
                quality=jpeg_quality,
                optimize=True,
            )

        finally:
            document.close()

            for page in pages:
                page.close()

    def _calculate_savings_fraction(
        self,
        source_path: Path,
        output_path: Path,
    ) -> float:
        original_size = (
            source_path.stat().st_size
        )

        output_size = (
            output_path.stat().st_size
        )

        if original_size <= 0:
            return 0.0

        return max(
            0.0,
            (
                original_size
                - output_size
            )
            / original_size,
        )