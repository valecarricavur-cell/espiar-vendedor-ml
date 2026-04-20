"""
ml_auth.py — OAuth con PKCE para MercadoLibre Argentina.

Paso 1: python3 ml_auth.py
         (abre el navegador y guarda el code_verifier)

Paso 2: Autorizá en el navegador, copiá el código TG-... de httpbin

Paso 3: python3 ml_auth.py TG-XXXXXXXXXX-XXXXXXXXX
         (intercambia el código y guarda el token en .env)
"""
import os, sys, secrets, hashlib, base64, webbrowser, requests, json, re
from pathlib import Path
from urllib.parse import urlencode

try:
    from dotenv import load_dotenv, set_key
    load_dotenv()
except ImportError:
    print("pip3 install python-dotenv"); sys.exit(1)

APP_ID     = os.getenv("ML_APP_ID")
APP_SECRET = os.getenv("ML_APP_SECRET")
REDIRECT   = "https://httpbin.org/get"
ENV_FILE   = str(Path(__file__).parent / ".env")
VERIFIER_FILE = Path(__file__).parent / ".ml_verifier"   # guarda el verifier entre pasos

if not APP_ID or not APP_SECRET:
    print("Falta ML_APP_ID o ML_APP_SECRET en .env"); sys.exit(1)

# ── PASO 2: intercambiar código ───────────────────────────────────────────────
if len(sys.argv) > 1:
    code = sys.argv[1].strip()
    m = re.search(r'TG-[\w-]+', code)
    if m:
        code = m.group(0)

    if not VERIFIER_FILE.exists():
        print("No encontré el code_verifier. Corré primero: python3 ml_auth.py (sin argumentos)")
        sys.exit(1)

    code_verifier = VERIFIER_FILE.read_text().strip()

    print(f"Intercambiando código: {code[:25]}...")
    resp = requests.post("https://api.mercadolibre.com/oauth/token", data={
        "grant_type":    "authorization_code",
        "client_id":     APP_ID,
        "client_secret": APP_SECRET,
        "code":          code,
        "redirect_uri":  REDIRECT,
        "code_verifier": code_verifier,
    }, timeout=15)

    d = resp.json()
    if "access_token" not in d:
        print("Error:", json.dumps(d, indent=2))
        sys.exit(1)

    set_key(ENV_FILE, "ML_ACCESS_TOKEN",  d["access_token"])
    set_key(ENV_FILE, "ML_REFRESH_TOKEN", d.get("refresh_token", ""))
    set_key(ENV_FILE, "ML_USER_ID",       str(d.get("user_id", "")))
    VERIFIER_FILE.unlink(missing_ok=True)

    print(f"\n[✓] Token guardado correctamente")
    print(f"    Expira en: {d.get('expires_in',0)//3600}hs")
    print(f"\nAhora corré:")
    print(f"    python3 espiar_vendedor.py todoairelibregd --carpeta TODOAIRELIBRE\n")
    sys.exit(0)

# ── PASO 1: generar URL de autorización ───────────────────────────────────────
code_verifier  = secrets.token_urlsafe(64)
digest         = hashlib.sha256(code_verifier.encode()).digest()
code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

# Guardar verifier para usarlo en el paso 2
VERIFIER_FILE.write_text(code_verifier)

auth_url = "https://auth.mercadolibre.com.ar/authorization?" + urlencode({
    "response_type":         "code",
    "client_id":             APP_ID,
    "redirect_uri":          REDIRECT,
    "code_challenge":        code_challenge,
    "code_challenge_method": "S256",
})

print("\n=== Autenticación MercadoLibre ===\n")
print("1. Abriendo navegador para autorizar la app...")
print(f"\n   Si no se abre, copiá esta URL en Chrome:\n   {auth_url}\n")
webbrowser.open(auth_url)
print("2. Hacé clic en 'Permitir' en MercadoLibre")
print("3. httpbin.org muestra un JSON — buscá el campo 'code' dentro de 'args'")
print("4. Copiá el valor TG-... y corré:\n")
print('   python3 ml_auth.py TG-XXXXXXXXXXXXXXXXXX-XXXXXXXXX\n')
