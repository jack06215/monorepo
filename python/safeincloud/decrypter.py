import struct
import zlib
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class Decrypter:
    def __init__(self, db_filename: str | Path, password: str | bytes) -> None:
        # Normalize to bytes (UTF-8) to feed the KDF
        self.password = (
            password.encode("utf-8") if isinstance(password, str) else password
        )
        self.db = Path(db_filename) if isinstance(db_filename, str) else db_filename
        self.input: BinaryIO | None = None

    # ---- binary readers -----------------------------------------------------
    def _read_byte(self, fp: BinaryIO) -> int:
        return struct.unpack("B", fp.read(1))[0]

    def _read_short(self, fp: BinaryIO) -> int:
        return struct.unpack("H", fp.read(2))[0]

    def _read_bytearray(self, fp: BinaryIO) -> bytes:
        size = self._read_byte(fp)
        return struct.unpack(f"{size}s", fp.read(size))[0]

    # ---- crypto helpers -----------------------------------------------------
    def _derive(
        self,
        password: bytes,
        salt: bytes,
        iters: int = 10000,
        length: int = 32,
    ) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=length,
            salt=salt,
            iterations=iters,
        )
        return kdf.derive(password)

    def _aes_cbc_decrypt(
        self,
        key: bytes,
        iv: bytes,
        data: bytes,
    ) -> bytes:
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
        decryptor = cipher.decryptor()
        return decryptor.update(data) + decryptor.finalize()

    def decrypt(self) -> bytes:
        with self.db.open("rb") as input:
            # Header / parameters
            magic = self._read_short(input)
            sver = self._read_byte(input)
            salt = self._read_bytearray(input)

            # First-stage key/IV and block
            skey = self._derive(self.password, salt, 10000, 32)
            iv = self._read_bytearray(input)
            salt2 = self._read_bytearray(input)
            block = self._read_bytearray(input)

            # Decrypt the small parameter block to get iv2/pass2/check
            decr_block = self._aes_cbc_decrypt(skey, iv, block)
            sub_fd = BytesIO(decr_block)
            iv2 = self._read_bytearray(sub_fd)
            pass2 = self._read_bytearray(sub_fd)
            check = self._read_bytearray(sub_fd)

            # Second-stage key (note: original used pass2 directly as AES key but also derived skey2)
            # Preserve behavior: derive (not used directly below) and use pass2 as the AES key
            _skey2 = self._derive(pass2, salt2, 1000, 32)

            # Decrypt the remainder of the file with AES-CBC using pass2/iv2
            remaining_ciphertext: bytes = input.read()
            data = self._aes_cbc_decrypt(pass2, iv2, remaining_ciphertext)

            # Decompress (zlib will ignore any trailing padding bytes)
            decompressor = zlib.decompressobj()
            return decompressor.decompress(data) + decompressor.flush()

    def decrypt_to_file(self, output: str) -> None:
        data = self.decrypt()
        Path(output).write_bytes(data)
