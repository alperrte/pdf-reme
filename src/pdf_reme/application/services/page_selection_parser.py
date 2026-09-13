class PageSelectionParser:
    def parse(
        self,
        expression: str,
        total_pages: int,
    ) -> list[int]:
        if total_pages <= 0:
            raise ValueError(
                "Toplam sayfa sayısı sıfırdan büyük olmalıdır."
            )

        clean_expression = expression.strip()

        if not clean_expression:
            raise ValueError(
                "Sayfa seçimi boş bırakılamaz."
            )

        selected_pages: list[int] = []

        parts = clean_expression.split(",")

        for raw_part in parts:
            part = raw_part.strip()

            if not part:
                raise ValueError(
                    "Geçersiz sayfa seçim ifadesi."
                )

            if "-" in part:
                self._add_range(
                    part=part,
                    total_pages=total_pages,
                    selected_pages=selected_pages,
                )
            else:
                page_number = self._parse_page_number(
                    value=part,
                    total_pages=total_pages,
                )

                selected_pages.append(
                    page_number
                )

        return self._remove_duplicates_preserving_order(
            selected_pages
        )

    def _add_range(
        self,
        part: str,
        total_pages: int,
        selected_pages: list[int],
    ) -> None:
        range_parts = part.split("-")

        if len(range_parts) != 2:
            raise ValueError(
                f"Geçersiz sayfa aralığı: {part}"
            )

        start_text = range_parts[0].strip()
        end_text = range_parts[1].strip()

        start = self._parse_page_number(
            start_text,
            total_pages,
        )

        end = self._parse_page_number(
            end_text,
            total_pages,
        )

        if start > end:
            raise ValueError(
                f"Sayfa aralığının başlangıcı "
                f"bitişten büyük olamaz: {part}"
            )

        selected_pages.extend(
            range(start, end + 1)
        )

    def _parse_page_number(
        self,
        value: str,
        total_pages: int,
    ) -> int:
        if not value.isdigit():
            raise ValueError(
                f"Geçersiz sayfa numarası: {value}"
            )

        page_number = int(value)

        if page_number < 1:
            raise ValueError(
                "Sayfa numarası 1 veya daha büyük olmalıdır."
            )

        if page_number > total_pages:
            raise ValueError(
                f"Sayfa numarası belge sınırını aşıyor: "
                f"{page_number}"
            )

        return page_number

    def _remove_duplicates_preserving_order(
        self,
        pages: list[int],
    ) -> list[int]:
        seen: set[int] = set()
        result: list[int] = []

        for page in pages:
            if page not in seen:
                seen.add(page)
                result.append(page)

        return result