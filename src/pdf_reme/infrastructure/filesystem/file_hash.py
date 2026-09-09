import hashlib
from pathlib import Path


DEFAULT_CHUNK_SIZE = 1024 * 1024  # 1 MB


def calculate_sha256(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(f"Dosya bulunamadı: {path}")

    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            sha256.update(chunk)

    return sha256.hexdigest()