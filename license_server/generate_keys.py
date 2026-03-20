"""
Gera o par de chaves RSA (privada + pública) para assinatura JWT.

Execute UMA vez antes de subir o servidor:
  python generate_keys.py

  - keys/private.pem  → fica APENAS no servidor (nunca no .exe)
  - keys/public.pem   → pode ser embutida no .exe (sem risco)
"""
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

KEYS_DIR = Path("keys")
KEYS_DIR.mkdir(exist_ok=True)

PRIVATE_PATH = KEYS_DIR / "private.pem"
PUBLIC_PATH  = KEYS_DIR / "public.pem"

if PRIVATE_PATH.exists() or PUBLIC_PATH.exists():
    print("Chaves ja existem. Delete os arquivos em keys/ para regenerar.")
else:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    PRIVATE_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

    PUBLIC_PATH.write_bytes(
        private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )

    print(f"OK! Chaves geradas em:")
    print(f"   {PRIVATE_PATH.resolve()}")
    print(f"   {PUBLIC_PATH.resolve()}")
    print()
    print("IMPORTANTE: NUNCA distribua o arquivo private.pem!")
    print("    Apenas public.pem pode ser embutida no .exe.")
