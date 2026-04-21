"""
agentes/marketing.py — Agente de Marketing
-------------------------------------------
Uso:
    python3 agentes/marketing.py "ideas para vender zapatillas en TikTok"

El agente genera:
  - Ideas de contenido concretas
  - Guion TikTok listo (hook + desarrollo + CTA)
  - Post para Instagram (caption + hashtags)
  - Plan de acción para llevar la idea a cabo
"""

import os
import sys
import anthropic
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

LINEA = "─" * 52


def imprimir_seccion(titulo: str, contenido: str):
    print(f"\n{LINEA}")
    print(f"  {titulo}")
    print(LINEA)
    print(contenido.strip())


def _leer_identidad() -> str:
    """Lee agencia.md para usar como contexto de marca."""
    ruta = Path("agencia.md")
    if ruta.exists():
        contenido = ruta.read_text(encoding="utf-8").strip()
        # Filtrar secciones sin completar (que aún tienen los paréntesis de ejemplo)
        lineas = [l for l in contenido.splitlines() if not (l.strip().startswith("(") and l.strip().endswith(")"))]
        return "\n".join(lineas)
    return ""


def generar(tema: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "⚠️  Falta ANTHROPIC_API_KEY en el archivo .env"

    client = anthropic.Anthropic(api_key=api_key)
    identidad = _leer_identidad()
    contexto_agencia = f"\n\nIDENTIDAD DE LA AGENCIA:\n{identidad}" if identidad else ""

    prompt = f"""Sos el agente de marketing de AgenciaML, una agencia especializada en e-commerce argentino (MercadoLibre, tiendas online, redes sociales).{contexto_agencia}

El dueño de la agencia te pide ayuda con este tema:
"{tema}"

Respondé en español argentino, de forma práctica y directa. Estructurá tu respuesta así:

---

💡 IDEAS DE CONTENIDO
(3 ideas concretas y originales para este tema, explicadas en 2-3 líneas cada una)

---

🎬 GUION TIKTOK
(Un guion listo para grabar con esta estructura:
- HOOK [0-3 seg]: la frase que abre el video y engancha
- DESARROLLO [4-30 seg]: el contenido principal, paso a paso
- CIERRE/CTA [últimos 5 seg]: qué tiene que hacer el que mira)

---

📱 POST INSTAGRAM
(Caption completo listo para copiar y pegar, con emojis y tono natural argentino)
(Hashtags: 10 hashtags relevantes)

---

📋 PLAN PARA LLEVARLO A CABO
(3 pasos concretos para ejecutar esta idea esta semana, con detalle de cada uno)

---

⚡ CONSEJO CLAVE
(Una sola idea que marque la diferencia para este tema específico)

Sé concreto, evitá los genéricos. Pensá en una agencia real que vende servicios a negocios de e-commerce argentinos."""

    mensaje = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return mensaje.content[0].text


def _md_a_html(texto: str) -> str:
    """Convierte markdown básico a HTML limpio."""
    import re
    lineas = []
    for linea in texto.split("\n"):
        l = linea.strip()
        if not l:
            lineas.append("<br>")
        elif l.startswith("### "):
            lineas.append(f'<h3>{l[4:]}</h3>')
        elif l.startswith("## "):
            lineas.append(f'<h2>{l[3:]}</h2>')
        elif l.startswith("# "):
            lineas.append(f'<h1>{l[2:]}</h1>')
        elif l.startswith("---"):
            lineas.append('<hr>')
        elif l.startswith("- ") or l.startswith("• "):
            lineas.append(f'<li>{l[2:]}</li>')
        elif re.match(r'^\d+\.', l):
            lineas.append(f'<li>{l}</li>')
        elif l.startswith("> "):
            lineas.append(f'<blockquote>{l[2:]}</blockquote>')
        else:
            l = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', l)
            l = re.sub(r'\*(.+?)\*', r'<em>\1</em>', l)
            l = re.sub(r'`(.+?)`', r'<code>\1</code>', l)
            lineas.append(f'<p>{l}</p>')
    return "\n".join(lineas)


def guardar_doc(tema: str, contenido: str, fecha: datetime) -> Path:
    """Guarda como documento HTML estilo Google Docs."""
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts = fecha.strftime("%Y%m%d_%H%M%S")
    slug = tema[:40].replace(" ", "-").lower()
    slug = "".join(c for c in slug if c.isalnum() or c == "-")
    ruta = carpeta / f"marketing_{slug}_{ts}.html"

    agencia = _leer_identidad()
    nombre_agencia = "Impulse Agency"
    for linea in agencia.splitlines():
        if linea.startswith("## Nombre"):
            continue
        if linea.strip() and not linea.startswith("#"):
            nombre_agencia = linea.strip()
            break

    cuerpo = _md_a_html(contenido)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{tema[:50]} — {nombre_agencia}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: 'Inter', 'Segoe UI', sans-serif;
      background: #f8f9fa;
      color: #1a1a1a;
      line-height: 1.7;
      padding: 40px 20px 80px;
    }}

    .doc {{
      background: #ffffff;
      max-width: 780px;
      margin: 0 auto;
      padding: 60px 72px;
      border-radius: 4px;
      box-shadow: 0 1px 3px rgba(0,0,0,.12), 0 4px 20px rgba(0,0,0,.06);
    }}

    .doc-header {{
      border-bottom: 1px solid #e8eaed;
      padding-bottom: 24px;
      margin-bottom: 36px;
    }}

    .doc-tag {{
      display: inline-block;
      background: #1ae82f22;
      color: #0d7a1a;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .06em;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 4px;
      margin-bottom: 12px;
    }}

    .doc-title {{
      font-size: 26px;
      font-weight: 700;
      color: #1a1a1a;
      line-height: 1.3;
      margin-bottom: 8px;
    }}

    .doc-meta {{
      font-size: 13px;
      color: #80868b;
    }}

    h1 {{ font-size: 22px; font-weight: 700; margin: 32px 0 12px; color: #1a1a1a; }}
    h2 {{ font-size: 18px; font-weight: 600; margin: 28px 0 10px; color: #1a1a1a; }}
    h3 {{ font-size: 15px; font-weight: 600; margin: 20px 0 8px; color: #3c4043; }}

    p {{
      font-size: 15px;
      color: #3c4043;
      margin: 6px 0;
    }}

    li {{
      font-size: 15px;
      color: #3c4043;
      margin: 6px 0 6px 20px;
      list-style: disc;
    }}

    blockquote {{
      background: #f8fffe;
      border-left: 3px solid #1ae82f;
      padding: 14px 20px;
      margin: 12px 0;
      border-radius: 0 6px 6px 0;
      font-size: 15px;
      font-style: italic;
      color: #3c4043;
    }}

    hr {{
      border: none;
      border-top: 1px solid #e8eaed;
      margin: 28px 0;
    }}

    strong {{ color: #1a1a1a; font-weight: 600; }}
    em {{ color: #3c4043; }}
    code {{
      background: #f1f3f4;
      padding: 2px 6px;
      border-radius: 3px;
      font-size: 13px;
      font-family: 'Courier New', monospace;
    }}

    br {{ display: block; margin: 4px 0; content: ""; }}

    .doc-footer {{
      margin-top: 48px;
      padding-top: 20px;
      border-top: 1px solid #e8eaed;
      font-size: 12px;
      color: #9aa0a6;
      display: flex;
      justify-content: space-between;
    }}
  </style>
</head>
<body>
  <div class="doc">
    <div class="doc-header">
      <div class="doc-tag">Marketing</div>
      <div class="doc-title">{tema}</div>
      <div class="doc-meta">{nombre_agencia} &nbsp;·&nbsp; {fecha.strftime('%d de %B de %Y, %H:%M')}</div>
    </div>

    {cuerpo}

    <div class="doc-footer">
      <span>{nombre_agencia}</span>
      <span>Generado por Agente de Marketing</span>
    </div>
  </div>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 agentes/marketing.py \"tu idea o tema\"")
        sys.exit(1)

    tema = " ".join(sys.argv[1:])
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    print(f"\n{'═'*52}")
    print(f"  AGENTE DE MARKETING — AgenciaML")
    print(f"  {fecha}")
    print(f"{'═'*52}")
    print(f"\n  Tema: {tema}\n")
    print("  Generando...")

    contenido = generar(tema)

    # Imprimir en consola para el chat
    print(f"\n{'═'*52}\n")
    print(contenido)

    # Guardar como documento HTML y abrir
    fecha_obj = datetime.now()
    ruta = guardar_doc(tema, contenido, fecha_obj)
    print(f"\n{'─'*52}")
    print(f"  Documento: {ruta}")
    print(f"{'─'*52}\n")

    # Abrir el documento en el navegador
    import subprocess
    subprocess.run(["open", str(ruta)], check=False)


if __name__ == "__main__":
    main()
