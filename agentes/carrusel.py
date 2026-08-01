"""
agentes/carrusel.py — Agente de Carruseles Instagram
-----------------------------------------------------
Trigger: "Carrusel [tema]"
Recibe el contenido estructurado del carrusel y genera un HTML
con preview visual de cada slide listo para llevar a Canva.
"""

import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def _nombre_agencia() -> str:
    ruta = Path("agencia.md")
    if not ruta.exists():
        return "Impulse Agency"
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip() and not linea.startswith("#") and not (linea.strip().startswith("(") and linea.strip().endswith(")")):
            return linea.strip()
    return "Impulse Agency"


def parsear_slides(texto: str) -> list[dict]:
    """
    Parsea el markdown del carrusel en una lista de slides.
    Espera bloques separados por --- con:
      ## SLIDE N — Titulo
      **Copy:** texto
      **Visual:** instrucción
    """
    bloques = re.split(r'\n---+\n', texto.strip())
    slides = []
    for bloque in bloques:
        if not bloque.strip():
            continue
        slide = {"numero": len(slides) + 1, "titulo": "", "copy": "", "visual": "", "raw": bloque.strip()}

        # Título del slide
        m = re.search(r'##\s+(?:SLIDE\s+\d+\s*[—-]\s*)?(.+)', bloque, re.I)
        if m:
            slide["titulo"] = m.group(1).strip()

        # Copy
        m = re.search(r'\*\*Copy[:\*]*\*?\*?\s*(.+?)(?=\*\*Visual|\Z)', bloque, re.I | re.S)
        if m:
            slide["copy"] = m.group(1).strip().strip('"')

        # Visual
        m = re.search(r'\*\*Visual[:\*]*\*?\*?\s*(.+?)(?=\n##|\Z)', bloque, re.I | re.S)
        if m:
            slide["visual"] = m.group(1).strip()

        slides.append(slide)
    return slides


# Paleta de fondos para preview (cicla entre slides)
_FONDOS = [
    ("#0a0a0a", "#ffffff"),  # negro / blanco
    ("#1ae82f", "#0a0a0a"),  # verde / negro
    ("#22cfff", "#0a0a0a"),  # celeste / negro
    ("#f8f9fa", "#1a1a1a"),  # blanco / negro
    ("#1a1a1a", "#1ae82f"),  # negro / verde
]


def guardar_doc(tema: str, slides: list[dict], fecha: datetime) -> Path:
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts   = fecha.strftime("%Y%m%d_%H%M%S")
    slug = "".join(c if c.isalnum() else "-" for c in tema[:40].lower()).strip("-")
    ruta = carpeta / f"carrusel_{slug}_{ts}.html"

    nombre = _nombre_agencia()

    slides_html = ""
    for i, s in enumerate(slides):
        bg, fg = _FONDOS[i % len(_FONDOS)]
        accent = "#1ae82f" if fg == "#0a0a0a" or fg == "#1a1a1a" else "#0a0a0a"
        num_label = f"SLIDE {s['numero']}"
        if i == 0:
            num_label += " · PORTADA"
        elif i == len(slides) - 1:
            num_label += " · CIERRE"

        visual_html = f'<div class="visual-note">🎨 {s["visual"]}</div>' if s["visual"] else ""

        slides_html += f"""
<div class="slide" style="background:{bg};color:{fg}">
  <div class="slide-num" style="color:{accent}">{num_label}</div>
  <div class="slide-title">{s['titulo']}</div>
  <div class="slide-copy">{s['copy'].replace(chr(10), '<br>')}</div>
  {visual_html}
</div>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Carrusel — {tema[:50]}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:#f0f0f0;padding:40px 20px 80px}}
    .header{{max-width:900px;margin:0 auto 32px;display:flex;justify-content:space-between;align-items:flex-end}}
    .header-title{{font-size:22px;font-weight:700;color:#1a1a1a}}
    .header-meta{{font-size:13px;color:#80868b}}
    .grid{{max-width:900px;margin:0 auto;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}}
    .slide{{border-radius:12px;padding:32px 28px;aspect-ratio:1/1;display:flex;flex-direction:column;justify-content:space-between;box-shadow:0 2px 12px rgba(0,0,0,.15);position:relative}}
    .slide-num{{font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:16px}}
    .slide-title{{font-size:22px;font-weight:800;line-height:1.2;flex:1;display:flex;align-items:center}}
    .slide-copy{{font-size:13px;line-height:1.6;opacity:.85;margin-top:16px}}
    .visual-note{{margin-top:14px;font-size:11px;opacity:.6;border-top:1px solid rgba(255,255,255,.2);padding-top:10px}}
    .footer{{max-width:900px;margin:32px auto 0;font-size:12px;color:#9aa0a6;display:flex;justify-content:space-between}}
    @media(max-width:600px){{.grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <div class="header-title">{tema}</div>
      <div class="header-meta">{nombre} · Carrusel Instagram · {fecha.strftime('%d/%m/%Y')}</div>
    </div>
    <div class="header-meta">{len(slides)} slides</div>
  </div>
  <div class="grid">
    {slides_html}
  </div>
  <div class="footer">
    <span>{nombre}</span>
    <span>Agente de Carruseles</span>
  </div>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("tema")
    parser.add_argument("--archivo", help="Archivo .md con el contenido del carrusel")
    args = parser.parse_args()

    if args.archivo:
        contenido = Path(args.archivo).read_text(encoding="utf-8")
    else:
        contenido = sys.stdin.read()

    slides = parsear_slides(contenido)
    if not slides:
        print("No se encontraron slides. Revisá el formato del archivo.")
        sys.exit(1)

    fecha = datetime.now()
    ruta  = guardar_doc(args.tema, slides, fecha)
    subprocess.run(["open", str(ruta)], check=False)
    subprocess.run(
        ["osascript", "-e",
         f'display notification "Carrusel listo — {len(slides)} slides" with title "Impulse Agency" sound name "Glass"'],
        check=False, capture_output=True
    )
    print(f"Guardado: {ruta} ({len(slides)} slides)")


if __name__ == "__main__":
    main()
