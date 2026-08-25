"""Encrypted OAuth token vault (AES-GCM, versioned keys).

Refresh tokens are encrypted at rest and never logged.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True, slots=True)
class EncryptedToken:
    ciphertext: bytes
    nonce: bytes
    key_version: int


class TokenVault:
    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != 32:
            raise ValueError("master key must be 32 bytes")
        self._key = master_key

    def encrypt(self, plaintext: str, key_version: int) -> EncryptedToken:
        nonce = os.urandom(12)
        aes = AESGCM(self._derive(key_version))
        ciphertext = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
        return EncryptedToken(ciphertext=ciphertext, nonce=nonce, key_version=key_version)

    def decrypt(self, token: EncryptedToken) -> str:
        aes = AESGCM(self._derive(token.key_version))
        plaintext = aes.decrypt(token.nonce, token.ciphertext, None)
        return plaintext.decode("utf-8")

    def _derive(self, key_version: int) -> bytes:
        # Deterministic per-version subkey; real deployments rotate via KMS.
        from cryptography.hazmat.primitives import hashes

        digest = hashes.Hash(hashes.SHA256())
        digest.update(self._key + str(key_version).encode("utf-8"))
        return digest.finalize()


__all__ = ["EncryptedToken", "TokenVault"]
