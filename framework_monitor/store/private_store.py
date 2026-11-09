"""Encrypted private store for restricted raw data.

``data/private/`` (restricted Parquet + restricted manual CSVs) is packed into
a tar.gz, encrypted with Fernet (AES-128-CBC + HMAC-SHA256) using the
``PRIVATE_STORE_KEY`` secret, and uploaded as a GitHub Actions artifact.
Artifacts on a public repo can be downloaded by any signed-in GitHub user,
which is why the archive must be encrypted, not just uploaded.

Generate a key once and save it as the repository secret PRIVATE_STORE_KEY::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import io
import os
import tarfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

KEY_ENV = "PRIVATE_STORE_KEY"


class PrivateStoreError(Exception):
    pass


def _fernet(key: str | None) -> Fernet:
    key = key or os.environ.get(KEY_ENV)
    if not key:
        raise PrivateStoreError(f"{KEY_ENV} is not set")
    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except ValueError as exc:
        raise PrivateStoreError(f"{KEY_ENV} is not a valid Fernet key") from exc


def pack(private_dir: Path, out_file: Path, key: str | None = None) -> int:
    """Encrypt `private_dir` into `out_file`. Returns the number of files packed."""
    buf = io.BytesIO()
    n = 0
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if private_dir.exists():
            for f in sorted(private_dir.rglob("*")):
                if f.is_file():
                    tar.add(f, arcname=str(f.relative_to(private_dir)))
                    n += 1
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_bytes(_fernet(key).encrypt(buf.getvalue()))
    return n


def unpack(in_file: Path, private_dir: Path, key: str | None = None) -> int:
    """Decrypt `in_file` into `private_dir`. Returns the number of files restored."""
    try:
        raw = _fernet(key).decrypt(in_file.read_bytes())
    except InvalidToken as exc:
        raise PrivateStoreError("cannot decrypt private store: wrong PRIVATE_STORE_KEY or corrupt file") from exc
    private_dir.mkdir(parents=True, exist_ok=True)
    root = private_dir.resolve()
    n = 0
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        for member in tar.getmembers():
            target = (private_dir / member.name).resolve()
            if not member.isfile() or not target.is_relative_to(root):
                raise PrivateStoreError(f"refusing unsafe archive member {member.name!r}")
        tar.extractall(private_dir, filter="data")
        n = len(tar.getmembers())
    return n
