"""
agentes/guion.py — Agente de Guiones
--------------------------------------
Genera un guion completo para que el dueño de la agencia se grabe.
Formato: TikTok / Reels (60-90 segundos)

Trigger desde el chat: "Guion [tema]"
"""

import re
import subprocess
from datetime import datetime
from pathlib import Path


def _leer_identidad() -> str:
    ruta = Path("agencia.md")
    if not ruta.exists():
        return ""
    lineas = [
        l for l in ruta.read_text(encoding="utf-8").splitlines()
        if not (l.strip().startswith("(") and l.strip().endswith(")"))
    ]
    return "\n".join(lineas)


def _nombre_agencia() -> str:
    for linea in _leer_identidad().splitlines():
        if linea.strip() and not linea.startswith("#"):
            return linea.strip()
    return "Impulse Agency"


def _md_a_html(texto: str) -> str:
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
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts = fecha.strftime("%Y%m%d_%H%M%S")
    slug = "".join(c if c.isalnum() else "-" for c in tema[:40].lower()).strip("-")
    ruta = carpeta / f"guion_{slug}_{ts}.html"

    nombre = _nombre_agencia()
    cuerpo = _md_a_html(contenido)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Guion — {tema[:50]}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Inter', 'Segoe UI', sans-serif;
      background: #f8f9fa;
      color: #1a1a1a;
      line-height: 1.75;
      padding: 40px 20px 80px;
    }}
    .doc {{
      background: #fff;
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
      background: #22cfff22;
      color: #0077aa;
      font-size: 11px;
      font-weight: 600;
      letter-spacing: .06em;
      text-transform: uppercase;
      padding: 4px 10px;
      border-radius: 4px;
      margin-bottom: 12px;
    }}
    .doc-title {{ font-size: 26px; font-weight: 700; margin-bottom: 8px; }}
    .doc-meta {{ font-size: 13px; color: #80868b; }}

    /* Bloques de tiempo del guion */
    .bloque {{
      background: #f8fffe;
      border-left: 4px solid #22cfff;
      border-radius: 0 8px 8px 0;
      padding: 16px 20px;
      margin: 16px 0;
    }}
    .bloque.hook {{ border-color: #1ae82f; background: #f0fff2; }}
    .bloque.cta  {{ border-color: #ff6b35; background: #fff5f0; }}
    .bloque.nota {{ border-color: #9aa0a6; background: #f8f9fa; font-style: italic; }}

    .tiempo {{
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
      color: #80868b;
      margin-bottom: 8px;
    }}

    h1 {{ font-size: 22px; font-weight: 700; margin: 32px 0 12px; }}
    h2 {{ font-size: 17px; font-weight: 600; margin: 28px 0 10px; color: #1a1a1a; }}
    h3 {{ font-size: 14px; font-weight: 600; margin: 20px 0 6px; color: #3c4043;
          text-transform: uppercase; letter-spacing: .04em; }}
    p  {{ font-size: 15px; color: #3c4043; margin: 6px 0; }}
    li {{ font-size: 15px; color: #3c4043; margin: 5px 0 5px 20px; list-style: disc; }}
    blockquote {{
      background: #f0fff2;
      border-left: 3px solid #1ae82f;
      padding: 14px 20px;
      margin: 12px 0;
      border-radius: 0 6px 6px 0;
      font-size: 16px;
      font-weight: 500;
      color: #1a1a1a;
    }}
    hr {{ border: none; border-top: 1px solid #e8eaed; margin: 28px 0; }}
    strong {{ color: #1a1a1a; font-weight: 600; }}
    code {{
      background: #f1f3f4; padding: 2px 6px;
      border-radius: 3px; font-size: 13px;
    }}
    .doc-footer {{
      margin-top: 48px; padding-top: 20px;
      border-top: 1px solid #e8eaed;
      font-size: 12px; color: #9aa0a6;
      display: flex; justify-content: space-between;
    }}
    @media print {{
      body {{ background: white; padding: 0; }}
      .doc {{ box-shadow: none; padding: 40px; }}
    }}
  </style>
</head>
<body>
<div class="doc">
  <div class="doc-header">
    <div class="doc-tag">Guion · TikTok / Reels</div>
    <div class="doc-title">{tema}</div>
    <div class="doc-meta">{nombre} &nbsp;·&nbsp; {fecha.strftime('%d de %B de %Y, %H:%M')}</div>
  </div>

  {cuerpo}

  <div class="doc-footer">
    <span>{nombre}</span>
    <span>Agente de Guiones</span>
  </div>
</div>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta


def generar_y_abrir(tema: str, contenido: str) -> Path:
    """Guarda el guion como documento HTML y lo abre en el navegador."""
    fecha = datetime.now()
    ruta = guardar_doc(tema, contenido, fecha)
    subprocess.run(["open", str(ruta)], check=False)
    subprocess.run(
        ["osascript", "-e",
         f'display notification "Guion listo — {tema[:40]}" with title "Impulse Agency" sound name "Glass"'],
        check=False, capture_output=True
    )
    return ruta


def main():
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="Agente de Guiones — AgenciaML")
    parser.add_argument("tema", help="Tema del guion")
    parser.add_argument("--archivo", help="Archivo .md con el contenido del guion")
    args = parser.parse_args()

    if args.archivo:
        contenido = Path(args.archivo).read_text(encoding="utf-8")
    else:
        contenido = sys.stdin.read()

    ruta = generar_y_abrir(args.tema, contenido)
    print(f"Guion guardado: {ruta}")


if __name__ == "__main__":
    main()
