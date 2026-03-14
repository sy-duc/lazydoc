"""Test cho EncryptionManager."""

from src.core.encryption import EncryptionManager


def test_encrypt_decrypt_roundtrip() -> None:
    """Mã hóa rồi giải mã phải trả về giá trị gốc."""
    enc = EncryptionManager()
    original = "sk-test-api-key-12345"
    encrypted = enc.encrypt(original)
    assert encrypted != original
    decrypted = enc.decrypt(encrypted)
    assert decrypted == original


def test_encrypted_output_is_different() -> None:
    """Cùng plaintext nhưng encrypt 2 lần cho kết quả khác nhau (Fernet dùng timestamp)."""
    enc = EncryptionManager()
    text = "my-secret-key"
    enc1 = enc.encrypt(text)
    enc2 = enc.encrypt(text)
    assert enc1 != enc2  # Fernet thêm timestamp nên khác nhau
    assert enc.decrypt(enc1) == text
    assert enc.decrypt(enc2) == text
