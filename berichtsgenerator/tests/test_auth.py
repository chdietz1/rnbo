import hashlib

from app import auth


def test_password_roundtrip_without_scrypt(monkeypatch):
    monkeypatch.delattr(hashlib, "scrypt", raising=False)
    stored = auth.hash_password("geheim12345")
    assert stored.startswith("pbkdf2_sha256$")
    assert auth.verify_password("geheim12345", stored)
    assert not auth.verify_password("falsch12345", stored)
    assert not auth.verify_password("geheim12345", "kaputt")
