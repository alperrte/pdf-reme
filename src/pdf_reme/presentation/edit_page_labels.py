"""`PageIdentity`'yi küçük resmin altındaki ikinci (soluk) satır metnine çevirir.

`edit_page_map.py` Qt/i18n'den bağımsız kalır; bu modül çeviri fonksiyonuna
(`tr`) bağımlı olduğu için ayrı tutulur.
"""

from typing import Callable

from pdf_reme.presentation.edit_page_map import PageIdentity


def identity_label(
    identity: PageIdentity,
    position: int,
    tr: Callable[[str], str],
) -> str:
    """Sayfanın altında gösterilecek ikincil metin; kaymamış orijinalde boş."""
    if identity.kind == "original":
        if identity.original_page == position:
            return ""

        return tr("edit.identity.original").format(page=identity.original_page)

    if identity.kind == "blank":
        return tr("edit.identity.blank")

    if identity.kind == "inserted":
        return tr("edit.identity.inserted").format(page=identity.source_pdf_page)

    if identity.kind == "duplicate":
        return tr("edit.identity.duplicate").format(
            page=identity.source_display_page
        )

    return ""
