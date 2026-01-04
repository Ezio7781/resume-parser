import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken

STORAGE_DIR = Path(__file__).parent / "secrets"
API_KEY_PATH = STORAGE_DIR / "api_key.enc"

def _ensure_storage_dir():
    STORAGE_DIR.mkdir(exist_ok=True)

def _get_fernet():
    master = os.environ.get("MASTER_KEY")
    if not master:
        return None
    # MASTER_KEY should be a urlsafe_b64-encoded 32-byte key (Fernet)
    return Fernet(master.encode())

def store_api_key(api_key: str):
    """Encrypt and store API key to disk. Requires MASTER_KEY env var."""
    f = _get_fernet()
    if f is None:
        raise RuntimeError("MASTER_KEY not set; persistent storage is disabled.")
    _ensure_storage_dir()
    token = f.encrypt(api_key.encode())
    # write file with restrictive permissions where possible
    with open(API_KEY_PATH, "wb") as fh:
        fh.write(token)
    try:
        API_KEY_PATH.chmod(0o600)
    except Exception:
        pass

def get_api_key() -> str | None:
    """Return decrypted API key if available, else None."""
    if not API_KEY_PATH.exists():
        return None
    f = _get_fernet()
    if f is None:
        raise RuntimeError("MASTER_KEY not set; cannot decrypt stored API key.")
    data = API_KEY_PATH.read_bytes()
    try:
        return f.decrypt(data).decode()
    except InvalidToken:
        raise RuntimeError("Decryption failed. Check MASTER_KEY and stored data.")

def delete_api_key():
    if API_KEY_PATH.exists():
        API_KEY_PATH.unlink()
