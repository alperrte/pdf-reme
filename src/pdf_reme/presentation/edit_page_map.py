"""Bir düzenleme adımında sayfa kimliğinin eski ↔ yeni numaralara eşlenmesi.

PDF Düzenle ekranı, işlem sonrası kullanıcının bağlamını (görünümdeki sayfa,
seçim) sayfa numaralarının kaymasına rağmen koruyabilmek için her adımı bir
`PageMap` ile kaydeder. Qt'ye bağımlı değildir.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PageMap:
    """`mapping[i]`: eski (i+1). sayfanın yeni numarası; silindiyse None.

    `inserted`: işlemin yarattığı (eski hâlde karşılığı olmayan) yeni sayfa
    numaraları.
    """

    old_count: int
    new_count: int
    mapping: tuple[int | None, ...]
    inserted: tuple[int, ...] = ()

    def forward(self, page: int) -> int:
        """Eski sayfanın yeni numarası.

        Sayfa silindiyse ondan sonra gelen ilk sağ kalan sayfa, o da yoksa
        önceki sağ kalan sayfa döner.
        """
        if not self.mapping or self.new_count <= 0:
            return 1

        index = min(max(1, page), self.old_count) - 1

        target = self.mapping[index]

        if target is not None:
            return self._clamp(target)

        for later in self.mapping[index + 1:]:
            if later is not None:
                return self._clamp(later)

        for earlier in reversed(self.mapping[:index]):
            if earlier is not None:
                return self._clamp(earlier)

        return 1

    def backward(self, page: int) -> int:
        """Yeni sayfanın eski numarası (undo yönü).

        İşlemin eklediği sayfa için en yakın sağ kalan sayfa kullanılır.
        """
        if self.old_count <= 0:
            return 1

        page = min(max(1, page), max(1, self.new_count))

        reverse = {
            new: old
            for old, new in enumerate(self.mapping, start=1)
            if new is not None
        }

        if page in reverse:
            return reverse[page]

        inserted = set(self.inserted)

        for later in range(page + 1, self.new_count + 1):
            if later not in inserted and later in reverse:
                return reverse[later]

        for earlier in range(page - 1, 0, -1):
            if earlier not in inserted and earlier in reverse:
                return reverse[earlier]

        return 1

    def _clamp(self, page: int) -> int:
        return min(max(1, page), max(1, self.new_count))

    def neighbour_after_delete(self, deleted: set[int]) -> int | None:
        """Silme sonrası seçilecek sayfa: silinenlerden sonrası, yoksa öncesi."""
        if not deleted or self.new_count <= 0:
            return None

        return self.forward(max(deleted))


def build_page_map(
    operation_name: str,
    args: dict,
    page_count: int,
) -> PageMap:
    """`EditOperation` (ad + argümanlar) için sayfa eşlemesini üretir."""
    identity = tuple(range(1, page_count + 1))

    if operation_name == "rotate_pages":
        return PageMap(page_count, page_count, identity)

    if operation_name == "delete_pages":
        deleted = set(args["page_numbers"])

        mapping: list[int | None] = []
        position = 0

        for page in range(1, page_count + 1):
            if page in deleted:
                mapping.append(None)
            else:
                position += 1
                mapping.append(position)

        return PageMap(page_count, position, tuple(mapping))

    if operation_name == "duplicate_pages":
        duplicated = set(args["page_numbers"])

        mapping = []
        inserted: list[int] = []
        position = 0

        for page in range(1, page_count + 1):
            position += 1
            mapping.append(position)

            if page in duplicated:
                position += 1
                inserted.append(position)

        return PageMap(page_count, position, tuple(mapping), tuple(inserted))

    if operation_name in ("insert_blank_page", "insert_pages"):
        after = args["after_page"]

        added = (
            1
            if operation_name == "insert_blank_page"
            else len(set(args["source_page_numbers"]))
        )

        mapping = [
            page if page <= after else page + added
            for page in range(1, page_count + 1)
        ]

        return PageMap(
            page_count,
            page_count + added,
            tuple(mapping),
            tuple(range(after + 1, after + added + 1)),
        )

    if operation_name == "reorder_pages":
        order = list(args["page_order"])

        new_position = {page: index for index, page in enumerate(order, 1)}

        return PageMap(
            page_count,
            len(order),
            tuple(new_position.get(page) for page in identity),
        )

    return PageMap(page_count, page_count, identity)


@dataclass(frozen=True)
class PageIdentity:
    """Bir sayfanın kalıcı kimliği; pozisyonu (sayfa no) değişse de kalır.

    `kind`:
      - "original": kaynak dosyanın ilk açıldığı andaki bir sayfası.
      - "blank": sonradan eklenen boş sayfa.
      - "inserted": başka bir PDF'ten eklenen sayfa.
      - "duplicate": mevcut bir sayfanın kopyası.

    `original_page`: yalnız `kind == "original"` için, kaynak dosyadaki 1
    tabanlı sayfa numarası.
    `source_pdf_page`: yalnız `kind == "inserted"` için, eklenen PDF'teki 1
    tabanlı sayfa numarası.
    `source_display_page`: yalnız `kind == "duplicate"` için, kopyalandığı
    anda ekranda görünen en yakın kaynağın sayfa numarası (zincir kısa
    tutulur; kopyanın kopyası alınırsa köke değil bir önceki kopyaya işaret
    eder).
    """

    kind: str
    original_page: int | None = None
    source_pdf_page: int | None = None
    source_display_page: int | None = None


def initial_identities(page_count: int) -> tuple[PageIdentity, ...]:
    """Kaynak dosya ilk açıldığında her sayfa kendi orijinal kimliğini taşır."""
    return tuple(
        PageIdentity("original", original_page=page)
        for page in range(1, page_count + 1)
    )


def apply_identity_step(
    identities: tuple[PageIdentity, ...],
    operation_name: str,
    args: dict,
) -> tuple[PageIdentity, ...]:
    """`build_page_map` ile aynı dallanma sırasını izleyerek kimlikleri taşır."""
    if operation_name == "rotate_pages":
        return identities

    if operation_name == "delete_pages":
        deleted = set(args["page_numbers"])

        return tuple(
            identity
            for page, identity in enumerate(identities, start=1)
            if page not in deleted
        )

    if operation_name == "duplicate_pages":
        duplicated = set(args["page_numbers"])

        result: list[PageIdentity] = []

        for page, identity in enumerate(identities, start=1):
            result.append(identity)

            if page in duplicated:
                result.append(
                    PageIdentity("duplicate", source_display_page=page)
                )

        return tuple(result)

    if operation_name == "insert_blank_page":
        after = args["after_page"]

        result = list(identities[:after])
        result.append(PageIdentity("blank"))
        result.extend(identities[after:])

        return tuple(result)

    if operation_name == "insert_pages":
        after = args["after_page"]
        source_pages = sorted(set(args["source_page_numbers"]))

        result = list(identities[:after])
        result.extend(
            PageIdentity("inserted", source_pdf_page=source_page)
            for source_page in source_pages
        )
        result.extend(identities[after:])

        return tuple(result)

    if operation_name == "reorder_pages":
        order = list(args["page_order"])

        return tuple(identities[page - 1] for page in order)

    return identities
