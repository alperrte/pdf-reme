from pdf_reme.application.compression.estimate import (
    PdfCompressionEstimate,
)
from pdf_reme.application.compression.options import (
    PdfCompressionOptions,
)
from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)


class PdfCompressionEstimator:
    def estimate(
        self,
        analysis: PdfAnalysisResult,
        options: PdfCompressionOptions,
    ) -> PdfCompressionEstimate:
        original_size = analysis.file_size_bytes

        if original_size <= 0:
            raise ValueError(
                "PDF dosya boyutu sıfırdan büyük olmalıdır."
            )

        image_bytes = min(
            analysis.total_image_stream_bytes,
            original_size,
        )

        non_image_bytes = max(
            0,
            original_size - image_bytes,
        )

        estimated_min_images = 0
        estimated_max_images = 0

        for image in analysis.images:
            minimum, maximum = (
                self._estimate_image_size(
                    image=image,
                    options=options,
                )
            )

            estimated_min_images += minimum
            estimated_max_images += maximum

        estimated_min = (
            non_image_bytes
            + estimated_min_images
        )

        estimated_max = (
            non_image_bytes
            + estimated_max_images
        )

        estimated_min = max(
            1,
            round(estimated_min),
        )

        estimated_max = max(
            estimated_min,
            round(estimated_max),
        )

        return PdfCompressionEstimate(
            original_size_bytes=original_size,
            estimated_min_size_bytes=estimated_min,
            estimated_max_size_bytes=estimated_max,
        )

    def _estimate_image_size(
        self,
        image: PdfImageAnalysis,
        options: PdfCompressionOptions,
    ) -> tuple[int, int]:
        original_size = image.stream_size_bytes

        if original_size <= 0:
            return 0, 0

        if not self._is_safe_candidate(image):
            return original_size, original_size

        resize_factor = self._resize_area_factor(
            image=image,
            options=options,
        )

        quality_min, quality_max = (
            self._quality_factor_range(
                image=image,
                image_quality=options.image_quality,
            )
        )

        minimum_ratio = min(
            1.0,
            resize_factor * quality_min,
        )

        maximum_ratio = min(
            1.0,
            resize_factor * quality_max,
        )

        estimated_min = max(
            1,
            round(
                original_size
                * minimum_ratio
            ),
        )

        estimated_max = max(
            estimated_min,
            round(
                original_size
                * maximum_ratio
            ),
        )

        return (
            estimated_min,
            estimated_max,
        )

    def _resize_area_factor(
        self,
        image: PdfImageAnalysis,
        options: PdfCompressionOptions,
    ) -> float:
        dpi_values = [
            value
            for value in (
                image.effective_dpi_x,
                image.effective_dpi_y,
            )
            if value is not None
            and value > 0
        ]

        if not dpi_values:
            return 1.0

        # Uniform resize yapacağımız için en düşük eksen DPI'sını
        # esas almak, diğer ekseni gereğinden fazla düşürmemizi engeller.
        effective_dpi = min(dpi_values)

        if effective_dpi <= options.max_dpi:
            return 1.0

        target_dpi = max(
            options.min_dpi,
            min(
                options.max_dpi,
                effective_dpi,
            ),
        )

        scale = (
            target_dpi
            / effective_dpi
        )

        # En ve boy aynı oranda küçüleceği için piksel miktarı
        # scale² oranında değişir.
        return scale * scale

    def _quality_factor_range(
        self,
        image: PdfImageAnalysis,
        image_quality: int,
    ) -> tuple[float, float]:
        quality = image_quality / 100.0

        filters = set(
            image.filters
        )

        if "/DCTDecode" in filters:
            center = (
                0.35
                + 0.65 * quality
            )

            minimum = center * 0.28
            maximum = center * 1.10

        elif "/FlateDecode" in filters:
            # Flate tabanlı fotoğraf/görüntüler JPEG'e geçtiğinde
            # daha yüksek küçülme potansiyeline sahip olabilir.
            center = (
                0.25
                + 0.55 * quality
            )

            minimum = center * 0.70
            maximum = center * 1.20

        else:
            # Bilinmeyen veya farklı filtrelerde daha konservatif
            # bir tahmin kullan.
            center = (
                0.70
                + 0.30 * quality
            )

            minimum = center * 0.85
            maximum = center * 1.10

        return (
            self._clamp_ratio(minimum),
            self._clamp_ratio(maximum),
        )

    def _is_safe_candidate(
        self,
        image: PdfImageAnalysis,
    ) -> bool:
        if image.is_image_mask:
            return False

        if image.has_mask:
            return False

        # SMask/transparency desteğini ImageOptimizer aşamasında
        # ayrıca ele alacağız. Estimator şimdilik bunun için
        # agresif kazanç vaat etmesin.
        if image.has_smask:
            return False

        return True

    def _clamp_ratio(
        self,
        value: float,
    ) -> float:
        return max(
            0.05,
            min(1.0, value),
        )