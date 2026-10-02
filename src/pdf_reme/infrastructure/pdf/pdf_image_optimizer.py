from io import BytesIO

from PIL import Image

from pdf_reme.application.compression.optimization import (
    ImageOptimizationResult,
)
from pdf_reme.application.compression.plan import (
    ImageCompressionAction,
    ImageCompressionPlan,
)


class PdfImageOptimizer:
    def optimize_jpeg(
        self,
        source_bytes: bytes,
        plan: ImageCompressionPlan,
    ) -> ImageOptimizationResult:
        if not source_bytes:
            raise ValueError(
                "Kaynak görsel verisi boş olamaz."
            )

        if plan.action == ImageCompressionAction.KEEP:
            return self._keep(
                source_bytes=source_bytes,
                plan=plan,
            )

        if plan.target_quality is None:
            raise ValueError(
                "Görsel değiştirilecekse hedef kalite belirtilmelidir."
            )

        with Image.open(
            BytesIO(source_bytes)
        ) as source_image:
            image = self._normalize_mode(
                source_image
            )

            original_width = image.width
            original_height = image.height

            if (
                original_width
                != plan.source_width_px
                or original_height
                != plan.source_height_px
            ):
                raise ValueError(
                    "Planlanan kaynak görsel boyutu ile "
                    "gerçek görsel boyutu uyuşmuyor."
                )

            resized = False

            if (
                plan.action
                == ImageCompressionAction.DOWNSAMPLE
            ):
                image = self._resize(
                    image=image,
                    width=plan.target_width_px,
                    height=plan.target_height_px,
                )

                resized = True

            output_bytes = self._encode_jpeg(
                image=image,
                quality=plan.target_quality,
            )

            output_width = image.width
            output_height = image.height

            image.close()

        # Optimizasyon sonucu gerçekten daha büyükse
        # kaynak görseli koruyoruz.
        if len(output_bytes) >= len(source_bytes):
            return self._keep(
                source_bytes=source_bytes,
                plan=plan,
            )

        return ImageOptimizationResult(
            data=output_bytes,
            original_size_bytes=len(
                source_bytes
            ),
            optimized_size_bytes=len(
                output_bytes
            ),
            original_width_px=(
                plan.source_width_px
            ),
            original_height_px=(
                plan.source_height_px
            ),
            output_width_px=output_width,
            output_height_px=output_height,
            changed=True,
            resized=resized,
        )

    def _keep(
        self,
        source_bytes: bytes,
        plan: ImageCompressionPlan,
    ) -> ImageOptimizationResult:
        return ImageOptimizationResult(
            data=source_bytes,
            original_size_bytes=len(
                source_bytes
            ),
            optimized_size_bytes=len(
                source_bytes
            ),
            original_width_px=(
                plan.source_width_px
            ),
            original_height_px=(
                plan.source_height_px
            ),
            output_width_px=(
                plan.source_width_px
            ),
            output_height_px=(
                plan.source_height_px
            ),
            changed=False,
            resized=False,
        )

    def _resize(
        self,
        image: Image.Image,
        width: int,
        height: int,
    ) -> Image.Image:
        if width <= 0 or height <= 0:
            raise ValueError(
                "Hedef görsel boyutu sıfırdan büyük olmalıdır."
            )

        resized = image.resize(
            (width, height),
            Image.Resampling.LANCZOS,
        )

        image.close()

        return resized

    def _normalize_mode(
        self,
        image: Image.Image,
    ) -> Image.Image:
        if image.mode == "RGB":
            return image.copy()

        if image.mode == "L":
            return image.convert("L")

        if image.mode == "CMYK":
            return image.convert("RGB")

        return image.convert("RGB")

    def _encode_jpeg(
        self,
        image: Image.Image,
        quality: int,
    ) -> bytes:
        output = BytesIO()

        image.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )

        return output.getvalue()