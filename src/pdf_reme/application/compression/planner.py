from pdf_reme.application.compression.options import (
    PdfCompressionOptions,
)
from pdf_reme.application.compression.plan import (
    ImageCompressionAction,
    ImageCompressionPlan,
    PdfCompressionPlan,
)
from pdf_reme.application.pdf_analysis import (
    PdfAnalysisResult,
    PdfImageAnalysis,
)


class AdaptiveCompressionPlanner:
    def create_plan(
        self,
        analysis: PdfAnalysisResult,
        options: PdfCompressionOptions,
    ) -> PdfCompressionPlan:
        plans = tuple(
            self._plan_image(
                image=image,
                options=options,
            )
            for image in analysis.images
        )

        return PdfCompressionPlan(
            images=plans
        )

    def _plan_image(
        self,
        image: PdfImageAnalysis,
        options: PdfCompressionOptions,
    ) -> ImageCompressionPlan:
        if self._is_unsafe(image):
            return self._keep(
                image=image,
                reason="unsafe_mask_or_transparency",
            )

        if (
            image.width_px <= 0
            or image.height_px <= 0
        ):
            return self._keep(
                image=image,
                reason="invalid_image_dimensions",
            )

        source_dpi = self._effective_dpi(
            image
        )

        if source_dpi is None:
            return self._keep(
                image=image,
                reason="effective_dpi_unknown",
            )

        if source_dpi <= options.max_dpi:
            return self._keep(
                image=image,
                reason="already_within_dpi_limit",
                source_dpi=source_dpi,
            )

        return self._downsample(
            image=image,
            source_dpi=source_dpi,
            options=options,
        )

    def _downsample(
        self,
        image: PdfImageAnalysis,
        source_dpi: float,
        options: PdfCompressionOptions,
    ) -> ImageCompressionPlan:
        target_dpi = float(
            options.max_dpi
        )

        # min_dpi burada doğrudan kullanılmıyor çünkü
        # baseline adaptive plan yalnız max DPI üstündeki
        # görüntüleri güvenli şekilde aşağı çeker.
        #
        # min_dpi, Target Size Optimizer aşamasında
        # ne kadar aşağı inebileceğimizin kalite tabanı olacak.

        scale = (
            target_dpi
            / source_dpi
        )

        target_width = max(
            1,
            round(
                image.width_px * scale
            ),
        )

        target_height = max(
            1,
            round(
                image.height_px * scale
            ),
        )

        return ImageCompressionPlan(
            object_id=image.object_id,
            action=(
                ImageCompressionAction.DOWNSAMPLE
            ),
            source_width_px=image.width_px,
            source_height_px=image.height_px,
            target_width_px=target_width,
            target_height_px=target_height,
            source_dpi=source_dpi,
            target_dpi=target_dpi,
            target_quality=(
                options.image_quality
            ),
            reason="effective_dpi_above_maximum",
        )

    def _keep(
        self,
        image: PdfImageAnalysis,
        reason: str,
        source_dpi: float | None = None,
    ) -> ImageCompressionPlan:
        if source_dpi is None:
            source_dpi = self._effective_dpi(
                image
            )

        return ImageCompressionPlan(
            object_id=image.object_id,
            action=ImageCompressionAction.KEEP,
            source_width_px=image.width_px,
            source_height_px=image.height_px,
            target_width_px=image.width_px,
            target_height_px=image.height_px,
            source_dpi=source_dpi,
            target_dpi=source_dpi,
            target_quality=None,
            reason=reason,
        )

    def _effective_dpi(
        self,
        image: PdfImageAnalysis,
    ) -> float | None:
        values = [
            value
            for value in (
                image.effective_dpi_x,
                image.effective_dpi_y,
            )
            if value is not None
            and value > 0
        ]

        if not values:
            return None

        # En düşük ekseni kullanmak bilinçli:
        # bir eksen zaten düşük DPI ise uniform resize
        # o ekseni gereğinden fazla düşürmemeli.
        return min(values)

    def _is_unsafe(
        self,
        image: PdfImageAnalysis,
    ) -> bool:
        return (
            image.has_smask
            or image.has_mask
            or image.is_image_mask
        )