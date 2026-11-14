"""Generate a secure CityOS admin password hash locally for Render."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.auth import hash_password

print("CityOS admin password setup (password won't display while typing).")
pw = getpass.getpass("Choose an admin password (14+ characters): ")
confirm = getpass.getpass("Repeat the password: ")
if pw != confirm:
    sys.exit("Passwords do not match. No hash generated.")
try:
    digest = hash_password(pw)
except ValueError as exc:
    sys.exit(str(exc))
print("\nSet this value as CITYOS_ADMIN_PASSWORD_HASH in Render → Environment:")
print(digest)
print("\nDo not add this hash or your password to GitHub or share it in chat.")
