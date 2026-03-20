"""
Converte as chaves RSA para formato de uma linha só (para colar no Railway/Render).

Execute após gerar as chaves:
  python export_keys_for_cloud.py

Cole os valores gerados nas variáveis de ambiente da plataforma:
  JWT_PRIVATE_KEY  →  valor da chave privada
  JWT_PUBLIC_KEY   →  valor da chave pública
"""
from pathlib import Path

def to_env_value(path: str) -> str:
    content = Path(path).read_text().strip()
    return content.replace("\n", "\\n")

print("=" * 60)
print("Cole estes valores nas variáveis de ambiente da plataforma:")
print("=" * 60)

try:
    print("\nJWT_PRIVATE_KEY=")
    print(to_env_value("keys/private.pem"))
    print()
except FileNotFoundError:
    print("  ERRO: keys/private.pem não encontrado. Execute generate_keys.py primeiro.")

try:
    print("JWT_PUBLIC_KEY=")
    print(to_env_value("keys/public.pem"))
    print()
except FileNotFoundError:
    print("  ERRO: keys/public.pem não encontrado. Execute generate_keys.py primeiro.")

print("=" * 60)
print("AVISO: JWT_PRIVATE_KEY nunca deve ser exposta publicamente!")
