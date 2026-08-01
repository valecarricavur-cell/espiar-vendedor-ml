"""
agentes/carrusel_imagenes.py — Genera PNGs 1080x1080 listos para Instagram
---------------------------------------------------------------------------
Trigger: "Carrusel [tema]"

Uso básico (Claude genera el contenido):
  python3 agentes/carrusel_imagenes.py "Cómo vender más en Meli"

Uso con contenido pre-aprobado (flujo de 2 pasos desde el chat):
  python3 agentes/carrusel_imagenes.py "tema" --slides-json /tmp/slides.json

Variantes de diseño:
  --variante dark      (default) Oscuro profesional
  --variante bold      Tipografía gigante, máximo impacto
  --variante gradient  Fondos con gradientes ricos
  --variante light     Fondo blanco/claro, editorial

Flujo recomendado desde el chat:
  1. Decí "Carrusel [tema]" → Claude genera el contenido en el chat
  2. Revisás, ajustás slides si querés
  3. Decís "ejecutalo" → Claude corre el agente con ese contenido + variante elegida
"""

import json
import sys
import zipfile
import subprocess
from html import escape
from pathlib import Path
from datetime import datetime

import anthropic
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv(Path(__file__).parent.parent / ".env")


# ── MARCA ───────────────────────────────────────────────────────────────────────
VERDE   = "#1ae82f"
CELESTE = "#22cfff"
NEGRO   = "#0a0a0a"
BLANCO  = "#f5f5f5"
W, H    = 1080, 1350

FONT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&display=swap');"


# ── IDENTIDAD ───────────────────────────────────────────────────────────────────
def _leer_agencia() -> str:
    ruta = Path("agencia.md")
    return ruta.read_text(encoding="utf-8") if ruta.exists() else "Agencia: Impulse Agency."


# ── CLAUDE: GENERAR CONTENIDO ───────────────────────────────────────────────────
def generar_slides(tema: str) -> list[dict]:
    """Llama a Claude API y devuelve lista de slides estructurados."""
    cliente = anthropic.Anthropic()
    agencia = _leer_agencia()

    prompt = f"""Sos experto en e-commerce y contenido para Instagram.
Generá un carrusel de 7 slides sobre: "{tema}"

Identidad:
{agencia}

Reglas:
- Español argentino, tono profesional y directo
- Sin emojis en el copy (son imágenes)
- Titulares: máximo 8 palabras, concretos y específicos (nada de "Tips para vender más")
- Copy conciso: máximo 200 caracteres por slide, cada palabra tiene que ganarse su lugar
- Cada slide comunica UNA sola idea
- Usá números, datos y ejemplos concretos siempre que puedas
- Usá variedad de tipos visuales para hacer el carrusel más impactante

Arco narrativo del carrusel:
- Portada: gancho que genere curiosidad o toque un dolor real del vendedor
- Slides 2-3: el problema y por qué le está costando plata
- Slides 4-6: la solución, paso a paso o con datos que la respalden
- Cierre: resumen accionable + CTA

TIPOS DE SLIDE disponibles (elegí el más adecuado para cada punto):

"portada" — siempre el slide 1
  {{"tipo":"portada","titulo":"...","copy":"subtítulo gancho (1 línea)"}}

"contenido" — texto con titular y copy
  {{"tipo":"contenido","numero":N,"titulo":"...","copy":"..."}}

"stat" — número o métrica gigante (usalo cuando tenés un dato impactante: "3x", "68%", "+120 ventas")
  {{"tipo":"stat","numero":"3x","label":"más visitas en 30 días","copy":"Solo cambiando el título de la publicación."}}

"chart" — gráfico de barras SVG ascendente (usalo para mostrar progresión, crecimiento, antes/después)
  {{"tipo":"chart","titulo":"Evolución de visitas","copy":"Sin cambiar el precio ni las fotos.",
    "barras":[
      {{"label":"Antes","valor":20}},
      {{"label":"Sem 1","valor":45}},
      {{"label":"Sem 2","valor":72}},
      {{"label":"Sem 3","valor":95}}
    ]}}

"lista" — lista de 3-5 ítems con íconos (usalo para tips, errores comunes, pasos de acción)
  {{"tipo":"lista","titulo":"Los 4 errores más comunes","items":["Repetir palabras en el título","Poner precio en el título","No usar los 60 caracteres","Orden incorrecto de palabras"]}}

"cierre" — siempre el último slide
  {{"tipo":"cierre","titulo":"...","copy":"...","cta":"Seguime para más estrategias de e-commerce."}}

Estructura del carrusel:
- Slide 1: portada (siempre)
- Slides 2-6: mezcla inteligente de contenido / stat / chart / lista según el tema
- Slide 7: cierre (siempre)

Si el tema tiene datos o métricas → usá al menos 1 "stat" y 1 "chart".
Si el tema tiene errores o pasos → usá al menos 1 "lista".
En "chart", las barras pueden ser porcentajes (0-100) o números absolutos (visitas, ventas, pesos) — usá lo que mejor cuente la historia.

Respondé ÚNICAMENTE con un objeto JSON válido con la clave "slides", sin markdown."""

    resp = cliente.messages.create(
        model="claude-fable-5",
        max_tokens=2000,
        system="Respondés solo con JSON válido, sin markdown, sin texto adicional.",
        messages=[{"role": "user", "content": prompt}],
    )

    texto = next((b.text for b in resp.content if b.type == "text"), "").strip()
    # Limpiar posible markdown
    if "```" in texto:
        partes = texto.split("```")
        for parte in partes:
            parte = parte.strip()
            if parte.startswith("json"):
                parte = parte[4:]
            if parte.startswith("[") or parte.startswith("{"):
                texto = parte
                break

    data = json.loads(texto)
    if isinstance(data, list):
        return data
    return data.get("slides", data.get("carrusel", list(data.values())[0]))


# ── HELPERS ──────────────────────────────────────────────────────────────────────
def _e(s: str) -> str:
    return escape(str(s))

def _base(extra: str = "") -> str:
    return f"{FONT}\n* {{ margin:0; padding:0; box-sizing:border-box; }}\n{extra}"


# ════════════════════════════════════════════════════════════════════════════════
#  VARIANTE: DARK (oscuro profesional — default)
# ════════════════════════════════════════════════════════════════════════════════

def dark_portada(titulo: str, copy: str) -> str:
    t, c = _e(titulo), _e(copy)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;background:{NEGRO};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
body::before{{content:'';position:absolute;top:-80px;left:-80px;width:480px;height:480px;border-radius:50%;
  background:radial-gradient(circle,rgba(26,232,47,.13) 0%,transparent 65%);pointer-events:none;}}
body::after{{content:'';position:absolute;bottom:-80px;right:-80px;width:480px;height:480px;border-radius:50%;
  background:radial-gradient(circle,rgba(34,207,255,.10) 0%,transparent 65%);pointer-events:none;}}
.top{{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:center;}}
.tag{{font-size:13px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{VERDE};margin-bottom:28px;}}
.linea{{width:56px;height:4px;background:linear-gradient(90deg,{VERDE},{CELESTE});border-radius:2px;margin-bottom:32px;}}
.titulo{{font-size:80px;font-weight:900;line-height:1.03;color:{BLANCO};word-break:break-word;max-width:900px;}}
.copy{{font-size:24px;font-weight:400;line-height:1.5;color:rgba(245,245,245,.55);margin-top:28px;max-width:680px;}}
.footer{{position:relative;z-index:1;display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid rgba(255,255,255,.1);padding-top:28px;}}
.marca{{font-size:15px;font-weight:700;color:{VERDE};letter-spacing:1px;}}
.desliza{{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:rgba(245,245,245,.3);}}
</style></head><body>
  <div class="top">
    <div class="tag">Impulse Agency</div>
    <div class="linea"></div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
  </div>
  <div class="footer">
    <div class="marca">@impulsagency</div>
    <div class="desliza">Deslizá →</div>
  </div>
</body></html>"""


def dark_contenido(numero: int, titulo: str, copy: str, total: int) -> str:
    t, c = _e(titulo), _e(copy)
    accent = CELESTE if numero % 2 == 0 else VERDE
    dots = "".join(
        f'<div style="width:7px;height:7px;border-radius:50%;background:{"" + accent if i+1==numero else "rgba(255,255,255,.15)"}"></div>'
        for i in range(total - 2)
    )
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;background:{NEGRO};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
.bg{{position:absolute;inset:0;background:linear-gradient(145deg,#0a0a0a 0%,#0d1014 100%);}}
.corner{{position:absolute;top:60px;right:60px;width:180px;height:180px;border-radius:50%;
  background:radial-gradient(circle,rgba(26,232,47,.07) 0%,transparent 70%);}}
.content{{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:space-between;}}
.body-inner{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.num-area{{display:flex;align-items:flex-end;gap:16px;margin-bottom:40px;}}
.num-big{{font-size:96px;font-weight:900;line-height:1;color:{accent};opacity:.12;}}
.num-label{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{accent};padding-bottom:12px;}}
.titulo{{font-size:54px;font-weight:800;line-height:1.08;color:{BLANCO};margin-bottom:28px;max-width:880px;}}
.copy{{font-size:25px;font-weight:400;line-height:1.6;color:rgba(245,245,245,.65);max-width:820px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid rgba(255,255,255,.07);padding-top:28px;}}
.marca{{font-size:13px;font-weight:600;color:rgba(245,245,245,.25);letter-spacing:1px;}}
.dots{{display:flex;gap:7px;align-items:center;}}
</style></head><body>
  <div class="bg"></div><div class="corner"></div>
  <div class="content">
    <div class="body-inner">
      <div class="num-area">
        <div class="num-big">0{numero}</div>
        <div class="num-label">Punto {numero}</div>
      </div>
      <div class="titulo">{t}</div>
      <div class="copy">{c}</div>
    </div>
    <div class="footer">
      <div class="marca">@impulsagency</div>
      <div class="dots">{dots}</div>
    </div>
  </div>
</body></html>"""


def dark_cierre(titulo: str, copy: str, cta: str) -> str:
    t, c, a = _e(titulo), _e(copy), _e(cta)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;background:{NEGRO};
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:72px 80px;text-align:center;position:relative;
}}
body::before{{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at center,rgba(26,232,47,.09) 0%,transparent 60%);}}
.content{{position:relative;z-index:1;}}
.dots{{display:flex;gap:10px;justify-content:center;margin-bottom:48px;}}
.dot{{width:10px;height:10px;border-radius:50%;}}
.titulo{{font-size:62px;font-weight:900;line-height:1.08;color:{BLANCO};margin-bottom:24px;}}
.copy{{font-size:23px;font-weight:400;line-height:1.6;color:rgba(245,245,245,.55);margin-bottom:52px;max-width:720px;}}
.cta-box{{display:inline-block;border:1px solid rgba(26,232,47,.35);background:rgba(26,232,47,.08);
  border-radius:14px;padding:22px 44px;font-size:19px;font-weight:600;color:{VERDE};
  margin-bottom:44px;line-height:1.4;}}
.handle{{font-size:20px;font-weight:700;color:rgba(245,245,245,.3);letter-spacing:1px;}}
</style></head><body>
  <div class="content">
    <div class="dots">
      <div class="dot" style="background:{VERDE}"></div>
      <div class="dot" style="background:{CELESTE}"></div>
      <div class="dot" style="background:{VERDE};opacity:.35"></div>
    </div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
    <div class="cta-box">{a}</div>
    <div class="handle">@impulsagency</div>
  </div>
</body></html>"""


# ════════════════════════════════════════════════════════════════════════════════
#  VARIANTE: BOLD (tipografía gigante, máximo impacto)
# ════════════════════════════════════════════════════════════════════════════════

def bold_portada(titulo: str, copy: str) -> str:
    t, c = _e(titulo), _e(copy)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:#111111;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:80px 72px;
}}
.top-bar{{display:flex;justify-content:space-between;align-items:center;margin-bottom:auto;}}
.marca-tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{VERDE};}}
.numero{{font-size:12px;font-weight:500;letter-spacing:2px;color:rgba(255,255,255,.25);}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center;padding:40px 0;}}
.titulo{{font-size:96px;font-weight:900;line-height:.97;color:#ffffff;
  text-transform:uppercase;letter-spacing:-3px;word-break:break-word;}}
.titulo em{{color:{VERDE};font-style:normal;}}
.divider{{width:100%;height:2px;background:{VERDE};margin:36px 0;opacity:.4;}}
.copy{{font-size:22px;font-weight:500;line-height:1.5;color:rgba(255,255,255,.5);max-width:700px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;}}
.handle{{font-size:14px;font-weight:700;color:rgba(255,255,255,.3);letter-spacing:1px;}}
.desliza{{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:{VERDE};opacity:.7;}}
</style></head><body>
  <div class="top-bar">
    <div class="marca-tag">Impulse Agency</div>
    <div class="numero">01 / 07</div>
  </div>
  <div class="main">
    <div class="titulo">{t}</div>
    <div class="divider"></div>
    <div class="copy">{c}</div>
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
    <div class="desliza">→</div>
  </div>
</body></html>"""


def bold_contenido(numero: int, titulo: str, copy: str, total: int) -> str:
    t, c = _e(titulo), _e(copy)
    num_str = f"0{numero}" if numero < 10 else str(numero)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:#0f0f0f;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px;position:relative;
}}
.num-giant{{
  position:absolute;right:-20px;top:-20px;
  font-size:320px;font-weight:900;line-height:1;
  color:{VERDE};opacity:.04;letter-spacing:-10px;
  pointer-events:none;user-select:none;
}}
.top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:60px;}}
.counter{{font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{VERDE};}}
.marca{{font-size:12px;font-weight:500;color:rgba(255,255,255,.2);letter-spacing:1px;}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.titulo{{font-size:68px;font-weight:900;line-height:1.02;color:#ffffff;
  text-transform:uppercase;letter-spacing:-2px;margin-bottom:32px;}}
.barra{{width:48px;height:3px;background:{VERDE};border-radius:2px;margin-bottom:28px;}}
.copy{{font-size:24px;font-weight:400;line-height:1.6;color:rgba(255,255,255,.55);max-width:820px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;}}
.handle{{font-size:12px;font-weight:600;color:rgba(255,255,255,.2);letter-spacing:1px;}}
.prog{{font-size:12px;font-weight:700;color:rgba(255,255,255,.2);letter-spacing:1px;}}
</style></head><body>
  <div class="num-giant">{num_str}</div>
  <div class="top">
    <div class="counter">PUNTO {num_str}</div>
    <div class="marca">Impulse Agency</div>
  </div>
  <div class="main">
    <div class="titulo">{t}</div>
    <div class="barra"></div>
    <div class="copy">{c}</div>
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
    <div class="prog">{numero + 1} / {total}</div>
  </div>
</body></html>"""


def bold_cierre(titulo: str, copy: str, cta: str) -> str:
    t, c, a = _e(titulo), _e(copy), _e(cta)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{VERDE};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px;
}}
.top{{display:flex;justify-content:space-between;align-items:center;}}
.tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:rgba(0,0,0,.5);}}
.main{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.titulo{{font-size:80px;font-weight:900;line-height:1.0;color:#000000;
  text-transform:uppercase;letter-spacing:-3px;margin-bottom:36px;}}
.copy{{font-size:24px;font-weight:500;line-height:1.5;color:rgba(0,0,0,.6);max-width:780px;margin-bottom:44px;}}
.cta-btn{{display:inline-block;background:#000;color:{VERDE};
  font-size:18px;font-weight:700;letter-spacing:1px;
  padding:20px 40px;border-radius:8px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;}}
.handle{{font-size:15px;font-weight:700;color:rgba(0,0,0,.5);letter-spacing:1px;}}
.arrow{{font-size:28px;color:rgba(0,0,0,.4);}}
</style></head><body>
  <div class="top">
    <div class="tag">Impulse Agency</div>
  </div>
  <div class="main">
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
    <div class="cta-btn">{a}</div>
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
  </div>
</body></html>"""


# ════════════════════════════════════════════════════════════════════════════════
#  VARIANTE: GRADIENT (fondos con gradientes ricos)
# ════════════════════════════════════════════════════════════════════════════════

_GRAD_BG = [
    "linear-gradient(135deg, #0a1a0d 0%, #0d2a12 50%, #071a0a 100%)",   # verde profundo
    "linear-gradient(135deg, #070d1a 0%, #0d1a2a 50%, #070d1a 100%)",   # azul profundo
    "linear-gradient(145deg, #1a0a0d 0%, #2a0d14 50%, #1a0a0d 100%)",   # granate
    "linear-gradient(135deg, #0a0d1a 0%, #12152a 50%, #0a0d1a 100%)",   # índigo
    "linear-gradient(150deg, #0d1a0a 0%, #1a2a0d 50%, #0d1a0a 100%)",   # selva
]


def gradient_portada(titulo: str, copy: str) -> str:
    t, c = _e(titulo), _e(copy)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{_GRAD_BG[0]};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:76px 80px;position:relative;
}}
.glow-tl{{position:absolute;top:-60px;left:-60px;width:420px;height:420px;border-radius:50%;
  background:radial-gradient(circle,rgba(26,232,47,.18) 0%,transparent 65%);pointer-events:none;}}
.glow-br{{position:absolute;bottom:-60px;right:-60px;width:360px;height:360px;border-radius:50%;
  background:radial-gradient(circle,rgba(34,207,255,.14) 0%,transparent 65%);pointer-events:none;}}
.content{{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:space-between;}}
.body-inner{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.badge{{display:inline-flex;align-items:center;gap:10px;
  background:rgba(26,232,47,.12);border:1px solid rgba(26,232,47,.3);
  border-radius:100px;padding:8px 20px;width:fit-content;margin-bottom:40px;}}
.badge-dot{{width:7px;height:7px;border-radius:50%;background:{VERDE};}}
.badge-text{{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{VERDE};}}
.titulo{{font-size:78px;font-weight:900;line-height:1.03;color:#ffffff;max-width:900px;}}
.copy{{font-size:23px;font-weight:400;line-height:1.5;color:rgba(255,255,255,.5);max-width:660px;margin-top:28px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid rgba(255,255,255,.08);padding-top:28px;}}
.handle{{font-size:14px;font-weight:700;color:{VERDE};letter-spacing:1px;}}
.slide-tag{{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:rgba(255,255,255,.25);}}
</style></head><body>
  <div class="glow-tl"></div><div class="glow-br"></div>
  <div class="content">
    <div class="body-inner">
      <div class="badge"><div class="badge-dot"></div><div class="badge-text">Impulse Agency</div></div>
      <div class="titulo">{t}</div>
      <div class="copy">{c}</div>
    </div>
    <div class="footer">
      <div class="handle">@impulsagency</div>
      <div class="slide-tag">Deslizá →</div>
    </div>
  </div>
</body></html>"""


def gradient_contenido(numero: int, titulo: str, copy: str, total: int) -> str:
    t, c = _e(titulo), _e(copy)
    bg    = _GRAD_BG[numero % len(_GRAD_BG)]
    accent = CELESTE if numero % 2 == 0 else VERDE
    num_str = f"0{numero}" if numero < 10 else str(numero)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{bg};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
.glow{{position:absolute;top:40%;right:-80px;width:400px;height:400px;border-radius:50%;
  background:radial-gradient(circle,rgba(26,232,47,.10) 0%,transparent 60%);pointer-events:none;}}
.content{{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:space-between;}}
.body-inner{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.top-row{{display:flex;align-items:center;gap:16px;margin-bottom:56px;}}
.chip{{background:rgba(26,232,47,.12);border:1px solid rgba(26,232,47,.25);
  border-radius:100px;padding:6px 18px;
  font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{accent};}}
.num-ghost{{font-size:64px;font-weight:900;line-height:1;color:{accent};opacity:.18;}}
.titulo{{font-size:58px;font-weight:800;line-height:1.06;color:#ffffff;margin-bottom:28px;max-width:880px;}}
.separador{{width:40px;height:3px;background:linear-gradient(90deg,{accent},transparent);
  border-radius:2px;margin-bottom:28px;}}
.copy{{font-size:25px;font-weight:400;line-height:1.6;color:rgba(255,255,255,.6);max-width:820px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid rgba(255,255,255,.07);padding-top:26px;}}
.handle{{font-size:12px;font-weight:600;color:rgba(255,255,255,.25);letter-spacing:1px;}}
.progress{{font-size:12px;font-weight:600;color:{accent};opacity:.6;letter-spacing:1px;}}
</style></head><body>
  <div class="glow"></div>
  <div class="content">
    <div class="body-inner">
      <div class="top-row">
        <div class="chip">Punto {num_str}</div>
        <div class="num-ghost">{num_str}</div>
      </div>
      <div class="titulo">{t}</div>
      <div class="separador"></div>
      <div class="copy">{c}</div>
    </div>
    <div class="footer">
      <div class="handle">@impulsagency</div>
      <div class="progress">{numero} / {total - 2}</div>
    </div>
  </div>
</body></html>"""


def gradient_cierre(titulo: str, copy: str, cta: str) -> str:
    t, c, a = _e(titulo), _e(copy), _e(cta)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:linear-gradient(145deg,#071a0a 0%,#0d2a12 40%,#071a0d 100%);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:72px 80px;text-align:center;position:relative;
}}
.glow-center{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:700px;height:700px;border-radius:50%;
  background:radial-gradient(circle,rgba(26,232,47,.11) 0%,transparent 55%);pointer-events:none;}}
.content{{position:relative;z-index:1;}}
.ring{{
  width:80px;height:80px;border-radius:50%;
  border:2px solid rgba(26,232,47,.35);
  display:flex;align-items:center;justify-content:center;
  margin:0 auto 44px;
}}
.ring-inner{{width:50px;height:50px;border-radius:50%;background:rgba(26,232,47,.15);}}
.titulo{{font-size:60px;font-weight:900;line-height:1.06;color:#ffffff;margin-bottom:24px;}}
.copy{{font-size:22px;font-weight:400;line-height:1.6;
  color:rgba(255,255,255,.5);margin-bottom:52px;max-width:720px;}}
.cta-pill{{display:inline-block;
  background:linear-gradient(135deg,{VERDE},{CELESTE});
  color:#000;font-size:17px;font-weight:700;letter-spacing:.5px;
  padding:20px 48px;border-radius:100px;margin-bottom:44px;}}
.handle{{font-size:18px;font-weight:700;color:rgba(255,255,255,.3);letter-spacing:1px;}}
</style></head><body>
  <div class="glow-center"></div>
  <div class="content">
    <div class="ring"><div class="ring-inner"></div></div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
    <div class="cta-pill">{a}</div>
    <div class="handle">@impulsagency</div>
  </div>
</body></html>"""


# ════════════════════════════════════════════════════════════════════════════════
#  VARIANTE: LIGHT (editorial, fondo blanco)
# ════════════════════════════════════════════════════════════════════════════════

def light_portada(titulo: str, copy: str) -> str:
    t, c = _e(titulo), _e(copy)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:#f8f8f6;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
.accent-block{{
  position:absolute;top:0;left:0;right:0;height:6px;
  background:linear-gradient(90deg,{VERDE},{CELESTE});
}}
.top{{margin-top:20px;flex:1;display:flex;flex-direction:column;justify-content:center;}}
.tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:rgba(0,0,0,.35);margin-bottom:44px;}}
.titulo{{font-size:80px;font-weight:900;line-height:1.03;color:#0a0a0a;
  word-break:break-word;max-width:900px;}}
.titulo span{{color:{VERDE};}}
.copy{{font-size:24px;font-weight:400;line-height:1.5;color:rgba(0,0,0,.45);
  margin-top:28px;max-width:680px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:2px solid rgba(0,0,0,.08);padding-top:28px;}}
.marca{{font-size:15px;font-weight:700;color:#0a0a0a;letter-spacing:.5px;}}
.marca span{{color:{VERDE};}}
.desliza{{font-size:13px;letter-spacing:2px;text-transform:uppercase;color:rgba(0,0,0,.3);}}
</style></head><body>
  <div class="accent-block"></div>
  <div class="top">
    <div class="tag">Impulse Agency</div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
  </div>
  <div class="footer">
    <div class="marca">@impulse<span>agency</span></div>
    <div class="desliza">Deslizá →</div>
  </div>
</body></html>"""


def light_contenido(numero: int, titulo: str, copy: str, total: int) -> str:
    t, c = _e(titulo), _e(copy)
    num_str = f"0{numero}" if numero < 10 else str(numero)
    accent  = VERDE
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:#f8f8f6;
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
.stripe{{position:absolute;top:0;left:0;right:0;height:6px;
  background:linear-gradient(90deg,{VERDE},{CELESTE});}}
.content{{flex:1;display:flex;flex-direction:column;justify-content:space-between;margin-top:20px;}}
.body-inner{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.top{{display:flex;align-items:center;gap:20px;margin-bottom:56px;}}
.num-pill{{
  background:{accent};color:#000;
  font-size:13px;font-weight:800;letter-spacing:2px;
  padding:7px 16px;border-radius:100px;
}}
.label{{font-size:13px;font-weight:600;color:rgba(0,0,0,.35);letter-spacing:1px;text-transform:uppercase;}}
.titulo{{font-size:58px;font-weight:800;line-height:1.06;color:#0a0a0a;margin-bottom:24px;max-width:880px;}}
.linea{{width:40px;height:3px;background:{accent};border-radius:2px;margin-bottom:28px;}}
.copy{{font-size:26px;font-weight:400;line-height:1.6;color:rgba(0,0,0,.55);max-width:820px;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid rgba(0,0,0,.1);padding-top:26px;}}
.marca{{font-size:12px;font-weight:600;color:rgba(0,0,0,.3);letter-spacing:1px;}}
.prog{{font-size:12px;font-weight:700;color:{accent};}}
</style></head><body>
  <div class="stripe"></div>
  <div class="content">
    <div class="body-inner">
      <div class="top">
        <div class="num-pill">{num_str}</div>
        <div class="label">Punto {numero} de {total - 2}</div>
      </div>
      <div class="titulo">{t}</div>
      <div class="linea"></div>
      <div class="copy">{c}</div>
    </div>
    <div class="footer">
      <div class="marca">@impulsagency</div>
      <div class="prog">{numero}/{total-2}</div>
    </div>
  </div>
</body></html>"""


def light_cierre(titulo: str, copy: str, cta: str) -> str:
    t, c, a = _e(titulo), _e(copy), _e(cta)
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:#0a0a0a;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:72px 80px;text-align:center;position:relative;
}}
.stripe{{position:absolute;bottom:0;left:0;right:0;height:6px;
  background:linear-gradient(90deg,{VERDE},{CELESTE});}}
body::before{{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse at 50% 40%,rgba(26,232,47,.07) 0%,transparent 55%);}}
.content{{position:relative;z-index:1;}}
.tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:rgba(255,255,255,.25);margin-bottom:48px;}}
.titulo{{font-size:64px;font-weight:900;line-height:1.06;color:#ffffff;margin-bottom:24px;}}
.copy{{font-size:22px;font-weight:400;line-height:1.6;
  color:rgba(255,255,255,.45);margin-bottom:52px;max-width:700px;}}
.cta-box{{display:inline-block;background:{VERDE};color:#000;
  font-size:18px;font-weight:700;padding:22px 48px;border-radius:10px;
  margin-bottom:44px;}}
.handle{{font-size:18px;font-weight:700;color:rgba(255,255,255,.25);letter-spacing:1px;}}
</style></head><body>
  <div class="stripe"></div>
  <div class="content">
    <div class="tag">Impulse Agency</div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
    <div class="cta-box">{a}</div>
    <div class="handle">@impulsagency</div>
  </div>
</body></html>"""


# ════════════════════════════════════════════════════════════════════════════════
#  SLIDES VISUALES — funcionan con cualquier variante via tema de colores
# ════════════════════════════════════════════════════════════════════════════════

# Colores por variante para los slides visuales
_TEMAS = {
    "dark":     {"bg": NEGRO,    "fg": BLANCO,  "accent": VERDE,   "muted": "rgba(245,245,245,.5)",  "border": "rgba(255,255,255,.08)", "is_light": False},
    "bold":     {"bg": "#111111","fg": "#ffffff","accent": VERDE,   "muted": "rgba(255,255,255,.45)", "border": "rgba(255,255,255,.08)", "is_light": False},
    "gradient": {"bg": _GRAD_BG[1],"fg":"#ffffff","accent": VERDE,  "muted": "rgba(255,255,255,.5)",  "border": "rgba(255,255,255,.07)", "is_light": False},
    "light":    {"bg": "#f8f8f6","fg": "#0a0a0a","accent": VERDE,   "muted": "rgba(0,0,0,.45)",       "border": "rgba(0,0,0,.1)",        "is_light": True},
}


def slide_stat(numero: str, label: str, copy: str, variante: str) -> str:
    """Slide con número/métrica gigante centrado."""
    tema   = _TEMAS.get(variante, _TEMAS["dark"])
    bg, fg = tema["bg"], tema["fg"]
    accent = tema["accent"]
    muted  = tema["muted"]
    n, l, c = _e(numero), _e(label), _e(copy)
    glow_color = "rgba(26,232,47,.12)" if not tema["is_light"] else "rgba(26,232,47,.06)"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{bg};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
body::before{{content:'';position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  width:700px;height:700px;border-radius:50%;
  background:radial-gradient(circle,{glow_color} 0%,transparent 55%);pointer-events:none;}}
.content{{position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:center;align-items:flex-start;}}
.tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:{accent};margin-bottom:64px;}}
.stat-num{{
  font-size:200px;font-weight:900;line-height:.85;
  color:{accent};letter-spacing:-6px;
  text-shadow:0 0 80px rgba(26,232,47,.25);
}}
.stat-label{{
  font-size:32px;font-weight:600;line-height:1.3;
  color:{fg};margin-top:28px;max-width:700px;
}}
.stat-copy{{
  font-size:22px;font-weight:400;line-height:1.5;
  color:{muted};margin-top:16px;max-width:680px;
}}
.footer{{position:relative;z-index:1;
  display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid {tema["border"]};padding-top:26px;}}
.handle{{font-size:13px;font-weight:600;color:{muted};letter-spacing:1px;}}
.marca{{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{accent};opacity:.6;}}
</style></head><body>
  <div class="content">
    <div class="tag">Impulse Agency</div>
    <div class="stat-num">{n}</div>
    <div class="stat-label">{l}</div>
    {"<div class='stat-copy'>" + c + "</div>" if c else ""}
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
    <div class="marca">Dato</div>
  </div>
</body></html>"""


def slide_chart(titulo: str, barras: list[dict], copy: str, variante: str) -> str:
    """Slide con gráfico de barras SVG ascendente."""
    tema   = _TEMAS.get(variante, _TEMAS["dark"])
    bg, fg = tema["bg"], tema["fg"]
    accent = tema["accent"]
    muted  = tema["muted"]
    t, c = _e(titulo), _e(copy)

    # Normalizar valores a porcentaje del alto máximo
    max_val = max((b.get("valor", 0) for b in barras), default=100)
    es_porcentaje = all(b.get("valor", 0) <= 100 for b in barras)
    n_bars  = len(barras)
    svg_w, svg_h = 860, 400
    bar_w   = min(140, (svg_w - 40) // n_bars - 20)
    gap     = (svg_w - bar_w * n_bars) // (n_bars + 1)
    max_bar_h = 320

    bars_svg = ""
    for i, b in enumerate(barras):
        val   = b.get("valor", 0)
        h     = int(max_bar_h * val / max_val) if max_val > 0 else 0
        x     = gap + i * (bar_w + gap)
        y     = svg_h - h - 44  # 44px para labels
        label = _e(str(b.get("label", "")))
        is_last = (i == n_bars - 1)

        # Última barra = accent, resto más suaves
        bar_color = accent if is_last else ("rgba(26,232,47,.35)" if not tema["is_light"] else "rgba(26,232,47,.4)")
        txt_color = fg if not tema["is_light"] else "#0a0a0a"

        bars_svg += f"""
  <rect x="{x}" y="{y}" width="{bar_w}" height="{h}"
        fill="{bar_color}" rx="6"/>
  <text x="{x + bar_w//2}" y="{svg_h - 10}" text-anchor="middle"
        font-size="20" font-family="Inter,system-ui,sans-serif"
        font-weight="600" fill="{muted}">{label}</text>"""
        if is_last:
            etiqueta = f"{val}%" if es_porcentaje else f"{val:,}".replace(",", ".")
            bars_svg += f"""
  <text x="{x + bar_w//2}" y="{y - 12}" text-anchor="middle"
        font-size="22" font-family="Inter,system-ui,sans-serif"
        font-weight="800" fill="{accent}">{etiqueta}</text>"""

    glow_color = "rgba(26,232,47,.08)" if not tema["is_light"] else "transparent"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{bg};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:64px 80px;position:relative;
}}
body::before{{content:'';position:absolute;bottom:-100px;right:-100px;width:500px;height:500px;border-radius:50%;
  background:radial-gradient(circle,{glow_color} 0%,transparent 60%);pointer-events:none;}}
.titulo{{font-size:48px;font-weight:800;line-height:1.1;color:{fg};margin-bottom:8px;}}
.copy{{font-size:20px;font-weight:400;color:{muted};margin-bottom:32px;}}
.chart-wrap{{flex:1;display:flex;align-items:flex-end;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid {tema["border"]};padding-top:22px;}}
.handle{{font-size:13px;font-weight:600;color:{muted};letter-spacing:1px;}}
.marca{{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{accent};opacity:.6;}}
</style></head><body>
  <div>
    <div class="titulo">{t}</div>
    <div class="copy">{c}</div>
  </div>
  <div class="chart-wrap">
    <svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}">
      {bars_svg}
    </svg>
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
    <div class="marca">Datos</div>
  </div>
</body></html>"""


def slide_lista(titulo: str, items: list[str], variante: str) -> str:
    """Slide con lista de ítems numerados."""
    tema   = _TEMAS.get(variante, _TEMAS["dark"])
    bg, fg = tema["bg"], tema["fg"]
    accent = tema["accent"]
    muted  = tema["muted"]
    t = _e(titulo)

    items_html = ""
    for i, item in enumerate(items[:5]):
        num_bg  = accent if i == 0 else ("rgba(26,232,47,.15)" if not tema["is_light"] else "rgba(26,232,47,.2)")
        num_fg  = "#000" if i == 0 else accent
        items_html += f"""
    <div style="display:flex;align-items:flex-start;gap:24px;padding:22px 0;
                border-bottom:1px solid {tema['border']};">
      <div style="min-width:44px;height:44px;border-radius:50%;background:{num_bg};
                  display:flex;align-items:center;justify-content:center;
                  font-size:16px;font-weight:800;color:{num_fg};flex-shrink:0;">{i+1}</div>
      <div style="font-size:26px;font-weight:600;line-height:1.35;color:{fg};padding-top:8px;">{_e(item)}</div>
    </div>"""

    glow_color = "rgba(26,232,47,.08)" if not tema["is_light"] else "transparent"

    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><style>
{_base()}
body {{
  width:{W}px;height:{H}px;overflow:hidden;
  font-family:'Inter',system-ui,sans-serif;
  background:{bg};
  display:flex;flex-direction:column;justify-content:space-between;
  padding:72px 80px;position:relative;
}}
body::before{{content:'';position:absolute;top:-80px;left:-80px;width:400px;height:400px;border-radius:50%;
  background:radial-gradient(circle,{glow_color} 0%,transparent 65%);pointer-events:none;}}
.tag{{font-size:12px;font-weight:700;letter-spacing:3px;text-transform:uppercase;
  color:{accent};margin-bottom:20px;}}
.titulo{{font-size:44px;font-weight:800;line-height:1.1;color:{fg};margin-bottom:32px;}}
.lista{{}}
.body-inner{{flex:1;display:flex;flex-direction:column;justify-content:center;}}
.footer{{display:flex;justify-content:space-between;align-items:center;
  border-top:1px solid {tema["border"]};padding-top:22px;margin-top:20px;}}
.handle{{font-size:13px;font-weight:600;color:{muted};letter-spacing:1px;}}
.marca{{font-size:12px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{accent};opacity:.6;}}
</style></head><body>
  <div class="body-inner">
    <div class="tag">Impulse Agency</div>
    <div class="titulo">{t}</div>
    <div class="lista">{items_html}</div>
  </div>
  <div class="footer">
    <div class="handle">@impulsagency</div>
    <div class="marca">Tips</div>
  </div>
</body></html>"""


# ── ROUTER DE VARIANTES ───────────────────────────────────────────────────────────
VARIANTES = {
    "dark":     (dark_portada,     dark_contenido,     dark_cierre),
    "bold":     (bold_portada,     bold_contenido,     bold_cierre),
    "gradient": (gradient_portada, gradient_contenido, gradient_cierre),
    "light":    (light_portada,    light_contenido,    light_cierre),
}


def _html_slide(slide: dict, variante: str, total: int) -> str:
    fn_portada, fn_contenido, fn_cierre = VARIANTES.get(variante, VARIANTES["dark"])
    tipo = slide.get("tipo", "contenido")

    if tipo == "portada":
        return fn_portada(slide.get("titulo", ""), slide.get("copy", ""))
    elif tipo == "cierre":
        return fn_cierre(
            slide.get("titulo", ""),
            slide.get("copy", ""),
            slide.get("cta", "Seguime para más estrategias."),
        )
    elif tipo == "stat":
        return slide_stat(
            slide.get("numero", ""),
            slide.get("label", ""),
            slide.get("copy", ""),
            variante,
        )
    elif tipo == "chart":
        return slide_chart(
            slide.get("titulo", ""),
            slide.get("barras", []),
            slide.get("copy", ""),
            variante,
        )
    elif tipo == "lista":
        return slide_lista(
            slide.get("titulo", ""),
            slide.get("items", []),
            variante,
        )
    else:
        return fn_contenido(
            slide.get("numero", 1),
            slide.get("titulo", ""),
            slide.get("copy", ""),
            total,
        )


# ── RENDER ───────────────────────────────────────────────────────────────────────
def renderizar(slides: list[dict], carpeta: Path, variante: str) -> list[Path]:
    total    = len(slides)
    archivos = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H})

        for i, slide in enumerate(slides):
            html = _html_slide(slide, variante, total)
            page.set_content(html, wait_until="networkidle")

            ruta = carpeta / f"slide_{i + 1:02d}.png"
            page.screenshot(path=str(ruta), clip={"x": 0, "y": 0, "width": W, "height": H})

            archivos.append(ruta)
            print(f"  [{i + 1}/{total}] {slide.get('titulo', '')[:50]}")

        browser.close()

    return archivos


# ── ZIP ──────────────────────────────────────────────────────────────────────────
def empaquetar(archivos: list[Path], carpeta: Path) -> Path:
    zip_path = carpeta / "carrusel_instagram.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in archivos:
            zf.write(f, f.name)
    return zip_path


# ── MAIN ─────────────────────────────────────────────────────────────────────────
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Genera carrusel de imágenes PNG para Instagram")
    parser.add_argument("tema", help='Tema del carrusel. Ej: "Cómo vender más en Meli"')
    parser.add_argument(
        "--variante",
        choices=["dark", "bold", "gradient", "light"],
        default="dark",
        help="Estilo visual del carrusel (default: dark)",
    )
    parser.add_argument(
        "--slides-json",
        dest="slides_json",
        help="Ruta a un JSON con los slides pre-generados (omite la llamada a Claude API)",
    )
    args = parser.parse_args()

    tema     = args.tema
    variante = args.variante
    fecha    = datetime.now()
    slug     = "".join(c if c.isalnum() else "-" for c in tema[:40].lower()).strip("-")
    carpeta  = Path("reportes_ml") / "AgenciaML" / f"carrusel_{slug}_{fecha.strftime('%Y%m%d_%H%M%S')}"
    carpeta.mkdir(parents=True, exist_ok=True)

    print(f"\nTema:     {tema}")
    print(f"Variante: {variante}")

    if args.slides_json:
        print(f"\n[1/3] Cargando slides desde {args.slides_json}...")
        slides = json.loads(Path(args.slides_json).read_text(encoding="utf-8"))
        if isinstance(slides, dict) and "slides" in slides:
            slides = slides["slides"]
        print(f"  → {len(slides)} slides cargados")
    else:
        print("\n[1/3] Generando contenido con Claude...")
        slides = generar_slides(tema)
        print(f"  → {len(slides)} slides generados")

    print(f"\n[2/3] Renderizando imágenes {W}×{H} ({variante})...")
    archivos = renderizar(slides, carpeta, variante)

    print("\n[3/3] Empaquetando ZIP...")
    zip_path = empaquetar(archivos, carpeta)

    subprocess.run(["open", str(carpeta)], check=False)
    subprocess.run(
        ["osascript", "-e",
         f'display notification "{len(slides)} imágenes listas — variante {variante}" '
         f'with title "Impulse Agency — Carrusel" sound name "Glass"'],
        check=False, capture_output=True,
    )

    print(f"\n Carpeta:  {carpeta}")
    print(f" ZIP:      {zip_path}")
    print(f" Slides:   {len(archivos)} PNGs 1080×1080")


if __name__ == "__main__":
    main()
