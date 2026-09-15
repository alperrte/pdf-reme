from pathlib import Path

from PIL import Image, ImageOps


class ImageToPdfService:
    SUPPORTED_EXTENSIONS = {
        ".jpg",
        ".jpeg",
        ".png",
    }

    def create(
        self,
        image_paths: list[str | Path],
        output_path: str | Path,
    ) -> Path:
        if not image_paths:
            raise ValueError(
                "PDF oluşturmak için en az bir görsel gereklidir."
            )

        source_paths = [
            Path(image_path)
            for image_path in image_paths
        ]

        target_path = Path(output_path)

        self._validate_output_path(
            source_paths=source_paths,
            output_path=target_path,
        )

        for source_path in source_paths:
            self._validate_source(
                source_path
            )

        target_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        prepared_images: list[Image.Image] = []

        try:
            for source_path in source_paths:
                with Image.open(
                    source_path
                ) as image:
                    prepared_images.append(
                        self._prepare_image(
                            image
                        )
                    )

            first_image = prepared_images[0]
            remaining_images = prepared_images[1:]

            first_image.save(
                target_path,
                format="PDF",
                save_all=True,
                append_images=remaining_images,
            )

        except Exception:
            if target_path.exists():
                target_path.unlink()

            raise

        finally:
            for image in prepared_images:
                image.close()

        return target_path

    def _prepare_image(
        self,
        image: Image.Image,
    ) -> Image.Image:
        oriented_image = ImageOps.exif_transpose(
            image
        )

        if self._has_transparency(
            oriented_image
        ):
            rgba_image = oriented_image.convert(
                "RGBA"
            )

            background = Image.new(
                "RGB",
                rgba_image.size,
                (255, 255, 255),
            )

            background.paste(
                rgba_image,
                mask=rgba_image.getchannel(
                    "A"
                ),
            )

            return background

        return oriented_image.convert(
            "RGB"
        )

    def _has_transparency(
        self,
        image: Image.Image,
    ) -> bool:
        if image.mode in {
            "RGBA",
            "LA",
        }:
            return True

        if (
            image.mode == "P"
            and "transparency" in image.info
        ):
            return True

        return False

    def _validate_source(
        self,
        source_path: Path,
    ) -> None:
        if not source_path.exists():
            raise FileNotFoundError(
                "Görsel dosyası bulunamadı: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise ValueError(
                "Görsel kaynağı bir dosya olmalıdır: "
                f"{source_path}"
            )

        if (
            source_path.suffix.lower()
            not in self.SUPPORTED_EXTENSIONS
        ):
            raise ValueError(
                "Yalnızca JPG, JPEG ve PNG "
                "görselleri PDF'e dönüştürülebilir."
            )

        try:
            with Image.open(
                source_path
            ) as image:
                image.verify()

        except Exception as exc:
            raise ValueError(
                "Geçersiz veya bozuk görsel dosyası: "
                f"{source_path.name}"
            ) from exc

    def _validate_output_path(
        self,
        source_paths: list[Path],
        output_path: Path,
    ) -> None:
        if (
            output_path.suffix.lower()
            != ".pdf"
        ):
            raise ValueError(
                "Çıktı dosyası PDF formatında olmalıdır."
            )

        resolved_output = (
            output_path.resolve()
        )

        for source_path in source_paths:
            if (
                source_path.resolve()
                == resolved_output
            ):
                raise ValueError(
                    "Çıktı dosyası kaynak "
                    "görselle aynı olamaz."
                )