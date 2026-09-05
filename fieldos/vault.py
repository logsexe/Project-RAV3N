from __future__ import annotations

from pathlib import Path
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"RVNVAULT1"


class Vault:
    """AES-256-GCM encrypted artefact storage for FIELD//OS."""

    def __init__(self, key: bytes) -> None:
        if len(key) != 32:
            raise ValueError("Vault key must be 32 bytes")
        self.key = key

    def encrypt_bytes(self, data: bytes, *, associated_data: bytes = b"FIELD//OS") -> bytes:
        nonce = os.urandom(12)
        return MAGIC + nonce + AESGCM(self.key).encrypt(nonce, data, associated_data)

    def decrypt_bytes(self, payload: bytes, *, associated_data: bytes = b"FIELD//OS") -> bytes:
        if not payload.startswith(MAGIC) or len(payload) < len(MAGIC) + 13:
            raise ValueError("Not a FIELD//OS encrypted artefact")
        start = len(MAGIC)
        nonce = payload[start:start + 12]
        return AESGCM(self.key).decrypt(nonce, payload[start + 12:], associated_data)

    def encrypt_file(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.encrypt_bytes(source.read_bytes()))

    def decrypt_file(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.decrypt_bytes(source.read_bytes()))
