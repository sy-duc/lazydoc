"""Mã hóa/giải mã API key sử dụng Fernet (symmetric encryption)."""

import hashlib
import platform
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from platformdirs import user_data_dir


def _get_machine_id() -> str:
    """Lấy machine-specific identifier để derive encryption key.

    Kết hợp nhiều yếu tố đặc trưng máy để tạo ID ổn định.

    Returns:
        Chuỗi ID duy nhất của máy.
    """
    components = [
        platform.node(),
        platform.machine(),
        platform.processor(),
    ]
    # Thêm MAC address nếu có
    try:
        mac = uuid.getnode()
        components.append(str(mac))
    except Exception:
        pass

    return "|".join(components)


def _derive_key() -> bytes:
    """Derive Fernet key từ machine-specific identifier.

    Returns:
        Fernet-compatible key (base64-encoded 32 bytes).
    """
    import base64

    machine_id = _get_machine_id()
    # Dùng SHA-256 để tạo 32 bytes từ machine_id
    key_bytes = hashlib.sha256(machine_id.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(key_bytes)


class EncryptionManager:
    """Quản lý mã hóa/giải mã API key."""

    def __init__(self) -> None:
        """Khởi tạo EncryptionManager với key derive từ machine ID."""
        self._fernet = Fernet(_derive_key())

    def encrypt(self, plaintext: str) -> str:
        """Mã hóa chuỗi plaintext.

        Args:
            plaintext: Chuỗi cần mã hóa (ví dụ: API key).

        Returns:
            Chuỗi đã mã hóa (base64).
        """
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str) -> str:
        """Giải mã chuỗi đã mã hóa.

        Args:
            encrypted_text: Chuỗi đã mã hóa (base64).

        Returns:
            Chuỗi plaintext gốc.

        Raises:
            InvalidToken: Nếu chuỗi mã hóa không hợp lệ hoặc key sai.
        """
        return self._fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
