from __future__ import annotations

import base64
import os
from typing import Annotated, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BeforeValidator, PlainSerializer


def derive_key(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=600_000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key, salt


class EncryptedField:

    def __init__(self, passphrase: str) -> None:
        self._key, self._salt = derive_key(passphrase)

    def encrypt(self, value: str) -> str:
        f = Fernet(self._key)
        return f.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str:
        f = Fernet(self._key)
        return f.decrypt(value.encode()).decode()


_FERNET_PREFIX = "gAAAAA"


def encrypted_field(passphrase: str) -> Any:
    ef = EncryptedField(passphrase)

    def decrypt_validator(v: Any) -> str:
        if isinstance(v, str) and v.startswith(_FERNET_PREFIX):
            return ef.decrypt(v)
        return v

    def encrypt_serializer(v: str) -> str:
        if v.startswith(_FERNET_PREFIX):
            return v
        return ef.encrypt(v)

    return Annotated[
        str,
        BeforeValidator(decrypt_validator),
        PlainSerializer(encrypt_serializer, return_type=str, when_used="always"),
    ]


__all__ = ["EncryptedField", "encrypted_field"]
