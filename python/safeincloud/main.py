from pathlib import Path

from python.safeincloud.decrypter import Decrypter


def main() -> bytes:
    decrypter = Decrypter(
        db_filename="",
        password="",
    )
    decrypted = decrypter.decrypt()
    return decrypted


if __name__ == "__main__":
    res = main()
    out_file = Path("./dump.xml")
    out_file.write_bytes(res)
