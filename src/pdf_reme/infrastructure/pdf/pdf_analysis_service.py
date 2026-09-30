from pathlib import Path
import math
import pikepdf

from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)


class PdfAnalysisService:
    _TEXT_OPERATORS = {
        "Tj",
        "TJ",
        "'",
        '"',
    }

    _VECTOR_OPERATORS = {
        "S",
        "s",
        "f",
        "F",
        "f*",
        "B",
        "B*",
        "b",
        "b*",
        "sh",
    }

    def analyze(
        self,
        input_path: str | Path,
    ) -> PdfAnalysisResult:
        source_path = Path(input_path)

        self._validate_source(source_path)

        try:
            with pikepdf.open(source_path) as pdf:
                return self._analyze_pdf(
                    source_path,
                    pdf,
                )

        except pikepdf.PasswordError as exc:
            raise ValueError(
                "Şifreli PDF analiz edilemez."
            ) from exc

    def _analyze_pdf(
        self,
        source_path: Path,
        pdf,
    ) -> PdfAnalysisResult:
        images: dict[str, dict] = {}

        text_page_count = 0
        vector_page_count = 0

        for page_number, page in enumerate(
            pdf.pages,
            start=1,
        ):
            has_text, has_vector = (
                self._analyze_page_content(page)
            )

            if has_text:
                text_page_count += 1

            if has_vector:
                vector_page_count += 1

            self._collect_page_images(
                page=page,
                page_number=page_number,
                images=images,
            )

            self._collect_page_image_usage(
                page=page,
                page_number=page_number,
                images=images,
            )

        analyzed_images = tuple(
            self._build_image_analysis(
                object_id,
                metadata,
            )
            for object_id, metadata in images.items()
        )

        return PdfAnalysisResult(
            source_path=source_path,
            file_size_bytes=source_path.stat().st_size,
            page_count=len(pdf.pages),
            images=analyzed_images,
            text_page_count=text_page_count,
            vector_page_count=vector_page_count,
        )

    def _collect_page_images(
        self,
        page,
        page_number: int,
        images: dict[str, dict],
    ) -> None:
        try:
            page_images = page.get_images()
        except Exception:
            return

        for resource_name, raw_image in page_images.items():
            object_id = self._object_id(
                raw_image=raw_image,
                page_number=page_number,
                resource_name=resource_name,
            )

            if object_id not in images:
                images[object_id] = {
                    "page_numbers": set(),
                    "width_px": self._safe_int(
                        raw_image.get("/Width")
                    ),
                    "height_px": self._safe_int(
                        raw_image.get("/Height")
                    ),
                    "stream_size_bytes": (
                        self._stream_size(raw_image)
                    ),
                    "filters": self._filters(
                        raw_image.get("/Filter")
                    ),
                    "color_space": self._string_or_none(
                        raw_image.get("/ColorSpace")
                    ),
                    "bits_per_component": self._safe_int(
                        raw_image.get(
                            "/BitsPerComponent"
                        )
                    ),
                    "has_smask": (
                        "/SMask" in raw_image
                    ),
                    "has_mask": (
                        "/Mask" in raw_image
                    ),
                    "is_image_mask": bool(
                        raw_image.get(
                            "/ImageMask",
                            False,
                        )
                    ),
                    "max_display_width_points": None,
                    "max_display_height_points": None,
                }

            images[object_id]["page_numbers"].add(
                page_number
            )

    def _build_image_analysis(

        self,
        object_id: str,
        metadata: dict,
    ) -> PdfImageAnalysis:
        max_display_width = metadata[
            "max_display_width_points"
        ]

        max_display_height = metadata[
            "max_display_height_points"
        ]

        width_px = metadata["width_px"] or 0
        height_px = metadata["height_px"] or 0
        return PdfImageAnalysis(
            object_id=object_id,
            page_numbers=tuple(
                sorted(metadata["page_numbers"])
            ),
            width_px=width_px,
            height_px=height_px,
            stream_size_bytes=(
                metadata["stream_size_bytes"]
            ),
            filters=metadata["filters"],
            color_space=metadata["color_space"],
            bits_per_component=(
                metadata["bits_per_component"]
            ),
            has_smask=metadata["has_smask"],
            has_mask=metadata["has_mask"],
            is_image_mask=metadata["is_image_mask"],
            max_display_width_points=(
                max_display_width
            ),
            max_display_height_points=(
                max_display_height
            ),
            effective_dpi_x=self._effective_dpi(
                width_px,
                max_display_width,
            ),
            effective_dpi_y=self._effective_dpi(
                height_px,
                max_display_height,
            ),
        )

    def _analyze_page_content(
        self,
        page,
    ) -> tuple[bool, bool]:
        has_text = False
        has_vector = False

        try:
            instructions = (
                pikepdf.parse_content_stream(page)
            )

            for _operands, operator in instructions:
                operation = str(operator)

                if operation in self._TEXT_OPERATORS:
                    has_text = True

                if operation in self._VECTOR_OPERATORS:
                    has_vector = True

                if has_text and has_vector:
                    break

        except Exception:
            pass

        return has_text, has_vector

    def _object_id(
        self,
        raw_image,
        page_number: int,
        resource_name,
    ) -> str:
        objgen = tuple(raw_image.objgen)

        if objgen != (0, 0):
            return f"{objgen[0]} {objgen[1]} R"

        return (
            f"direct:"
            f"{page_number}:"
            f"{resource_name}"
        )

    def _stream_size(
        self,
        raw_image,
    ) -> int:
        try:
            return len(
                raw_image.read_raw_bytes()
            )
        except Exception:
            return 0

    def _filters(
        self,
        value,
    ) -> tuple[str, ...]:
        if value is None:
            return ()

        if isinstance(value, pikepdf.Array):
            return tuple(
                str(item)
                for item in value
            )

        return (str(value),)

    def _safe_int(
        self,
        value,
    ) -> int | None:
        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _string_or_none(
        self,
        value,
    ) -> str | None:
        if value is None:
            return None

        return str(value)

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                f"PDF bulunamadı: {source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "Kaynak bir dosya olmalıdır."
            )

        if source_path.suffix.lower() != ".pdf":
            raise ValueError(
                "Yalnızca PDF dosyaları analiz edilebilir."
            )

    def _collect_page_image_usage(
        self,
        page,
        page_number: int,
        images: dict[str, dict],
    ) -> None:
        try:
            resources = page.Resources
            xobjects = resources.get(
                "/XObject",
                {},
            )

            instructions = (
                pikepdf.parse_content_stream(page)
            )
        except Exception:
            return

        ctm = (
            1.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
        )

        stack = []

        for operands, operator in instructions:
            operation = str(operator)

            if operation == "q":
                stack.append(ctm)
                continue

            if operation == "Q":
                if stack:
                    ctm = stack.pop()

                continue

            if operation == "cm":
                if len(operands) < 6:
                    continue

                try:
                    matrix = tuple(
                        float(value)
                        for value in operands[:6]
                    )
                except (TypeError, ValueError):
                    continue

                ctm = self._multiply_matrices(
                    ctm,
                    matrix,
                )

                continue

            if operation != "Do":
                continue

            if not operands:
                continue

            try:
                resource_name = str(
                    operands[0]
                )

                raw_xobject = xobjects.get(
                    resource_name
                )

                if raw_xobject is None:
                    continue

                if (
                    raw_xobject.get("/Subtype")
                    != pikepdf.Name.Image
                ):
                    continue

            except Exception:
                continue

            object_id = self._object_id(
                raw_image=raw_xobject,
                page_number=page_number,
                resource_name=resource_name,
            )

            metadata = images.get(
                object_id
            )

            if metadata is None:
                continue

            display_width = math.hypot(
                ctm[0],
                ctm[1],
            )

            display_height = math.hypot(
                ctm[2],
                ctm[3],
            )

            if display_width > 0:
                current_width = metadata[
                    "max_display_width_points"
                ]

                if (
                    current_width is None
                    or display_width > current_width
                ):
                    metadata[
                        "max_display_width_points"
                    ] = display_width

            if display_height > 0:
                current_height = metadata[
                    "max_display_height_points"
                ]

                if (
                    current_height is None
                    or display_height > current_height
                ):
                    metadata[
                        "max_display_height_points"
                    ] = display_height


    def _multiply_matrices(
        self,
        current,
        matrix,
    ):
        a1, b1, c1, d1, e1, f1 = current
        a2, b2, c2, d2, e2, f2 = matrix

        return (
            a1 * a2 + c1 * b2,
            b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2,
            b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1,
            b1 * e2 + d1 * f2 + f1,
        )


    def _effective_dpi(
        self,
        pixel_size: int,
        display_points: float | None,
    ) -> float | None:
        if (
            pixel_size <= 0
            or display_points is None
            or display_points <= 0
        ):
            return None

        return round(
            pixel_size
            * 72.0
            / display_points,
            2,
        )