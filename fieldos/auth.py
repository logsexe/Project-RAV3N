from __future__ import annotations

from dataclasses import dataclass
import base64
import hashlib
import hmac
import json
import os
from pathlib import Path

from fieldos.operations import _data_root


@dataclass(frozen=True, slots=True)
class AuthStatus:
    configured: bool
    locked: bool
    key_configured: bool


class OperatorAuth:
    """Optional local operator PIN/key authentication using scrypt verifiers."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (_data_root() / "auth.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._locked = True

    def status(self) -> AuthStatus:
        payload = self._read()
        configured = bool(payload.get("pin_verifier"))
        return AuthStatus(configured, self._locked if configured else False, bool(payload.get("key_verifier")))

    def configure_pin(self, pin: str) -> None:
        if len(pin) < 6:
            raise ValueError("PIN must contain at least 6 characters")
        payload = self._read()
        salt = os.urandom(16)
        payload.update({
            "pin_salt": base64.b64encode(salt).decode("ascii"),
            "pin_verifier": base64.b64encode(self._derive(pin.encode("utf-8"), salt)).decode("ascii"),
        })
        self._write(payload)
        self._locked = True

    def verify_pin(self, pin: str) -> bool:
        payload = self._read()
        if not payload.get("pin_verifier"):
            self._locked = False
            return True
        try:
            salt = base64.b64decode(payload["pin_salt"])
            expected = base64.b64decode(payload["pin_verifier"])
        except Exception:
            return False
        valid = hmac.compare_digest(self._derive(pin.encode("utf-8"), salt), expected)
        if valid:
            self._locked = False
        return valid

    def configure_key(self, key_file: Path) -> None:
        data = key_file.read_bytes()
        if len(data) < 16:
            raise ValueError("Operator key file must contain at least 16 bytes")
        payload = self._read()
        salt = os.urandom(16)
        payload.update({
            "key_salt": base64.b64encode(salt).decode("ascii"),
            "key_verifier": base64.b64encode(self._derive(data, salt)).decode("ascii"),
        })
        self._write(payload)

    def verify_key(self, key_file: Path) -> bool:
        payload = self._read()
        if not payload.get("key_verifier"):
            return False
        try:
            salt = base64.b64decode(payload["key_salt"])
            expected = base64.b64decode(payload["key_verifier"])
            valid = hmac.compare_digest(self._derive(key_file.read_bytes(), salt), expected)
        except (OSError, ValueError, KeyError):
            return False
        if valid:
            self._locked = False
        return valid

    def lock(self) -> None:
        self._locked = True

    def vault_key_from_pin(self, pin: str) -> bytes:
        payload = self._read()
        if not payload.get("pin_verifier"):
            raise RuntimeError("PIN authentication is not configured")
        salt_b64 = payload.get("vault_salt")
        if salt_b64:
            salt = base64.b64decode(salt_b64)
        else:
            salt = os.urandom(16)
            payload["vault_salt"] = base64.b64encode(salt).decode("ascii")
            self._write(payload)
        return self._derive(pin.encode("utf-8"), salt)

    @staticmethod
    def _derive(secret: bytes, salt: bytes) -> bytes:
        return hashlib.scrypt(secret, salt=salt, n=2**14, r=8, p=1, dklen=32)

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}

    def _write(self, payload: dict) -> None:
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
