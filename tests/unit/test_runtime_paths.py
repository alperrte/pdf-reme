"""Portable LibreOffice runtime keşfi — yalnızca tmp'de sahte klasörler."""

import sys
from pathlib import Path

import pytest

from pdf_reme.presentation import runtime_paths


@pytest.fixture
def frozen_root(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "PDF-REME.exe"))

    return tmp_path


def test_frozen_root_is_executable_folder(frozen_root):
    assert runtime_paths.application_root() == frozen_root.resolve()


def test_development_root_is_project_root(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    root = runtime_paths.application_root()

    assert (root / "src" / "pdf_reme").is_dir()


def test_bundled_libreoffice_missing_returns_none(frozen_root):
    assert runtime_paths.bundled_libreoffice_dir() is None


def test_bundled_libreoffice_found_next_to_executable(frozen_root):
    program = frozen_root / "runtime" / "libreoffice" / "program"
    program.mkdir(parents=True)
    (program / "soffice.exe").write_bytes(b"fake")

    assert runtime_paths.bundled_libreoffice_dir() == (
        frozen_root / "runtime" / "libreoffice"
    )


def test_runtime_folder_without_soffice_is_ignored(frozen_root):
    (frozen_root / "runtime" / "libreoffice" / "program").mkdir(
        parents=True
    )

    assert runtime_paths.bundled_libreoffice_dir() is None


_GATEWAY_PROBE = """
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.frozen = True
sys.executable = str(root / "PDF-REME.exe")

from pdf_reme.presentation import backend_gateway

service = backend_gateway._office_service()
print(service.runtime_path)
print(service._resolve_soffice() if service.runtime_path else "")
"""


def _run_gateway_probe(tmp_path: Path, frozen_root: Path) -> list[str]:
    # backend_gateway içe aktarılırken veri klasörü/veritabanı oluşturulur;
    # bu yüzden gerçek Documents'a dokunmamak için ayrı süreç + tmp profil.
    import os
    import subprocess

    profile = tmp_path / "profile"
    profile.mkdir()

    env = dict(os.environ)
    env["USERPROFILE"] = str(profile)
    env["HOME"] = str(profile)
    env["PDF_REME_DATABASE_URL"] = "sqlite:///" + (
        profile / "t.db"
    ).as_posix()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")
    env["QT_QPA_PLATFORM"] = "offscreen"

    result = subprocess.run(
        [sys.executable, "-c", _GATEWAY_PROBE, str(frozen_root)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr

    return result.stdout.splitlines()


def test_gateway_uses_bundled_runtime_when_present(tmp_path):
    root = tmp_path / "app"
    program = root / "runtime" / "libreoffice" / "program"
    program.mkdir(parents=True)
    (program / "soffice.exe").write_bytes(b"fake")

    lines = _run_gateway_probe(tmp_path, root)

    assert Path(lines[0]) == root / "runtime" / "libreoffice"
    assert Path(lines[1]) == program / "soffice.exe"


def test_gateway_falls_back_to_system_discovery(tmp_path):
    root = tmp_path / "app"
    root.mkdir()

    assert _run_gateway_probe(tmp_path, root)[0] == "None"


def test_office_service_hides_console_window():
    from pdf_reme.infrastructure.conversion.office_to_pdf_service import (
        OfficeToPdfService,
    )

    flags = OfficeToPdfService._creation_flags()

    if sys.platform == "win32":
        import subprocess

        assert flags == subprocess.CREATE_NO_WINDOW
    else:
        assert flags == 0
