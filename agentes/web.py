"""
agentes/web.py — Análisis de sitios web
----------------------------------------
Trigger: "Analizá web [URL]" → análisis del sitio del cliente (qué mejorar)
         "Espia web [URL]"   → análisis del competidor (qué robar)
"""

import os
import sys
import re
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _leer_identidad() -> str:
    ruta = Path("agencia.md")
    if not ruta.exists():
        return ""
    lineas = [l for l in ruta.read_text(encoding="utf-8").splitlines()
              if not (l.strip().startswith("(") and l.strip().endswith(")"))]
    return "\n".join(lineas)


def _nombre_agencia() -> str:
    for linea in _leer_identidad().splitlines():
        if linea.strip() and not linea.startswith("#"):
            return linea.strip()
    return "Impulse Agency"


def scrape_url(url: str) -> str:
    """Obtiene el contenido visible de una URL usando Playwright."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        texto = page.evaluate("""() => {
            // Remover scripts, estilos, nav, footer
            ['script','style','nav','footer','noscript'].forEach(t =>
                document.querySelectorAll(t).forEach(e => e.remove())
            );
            return document.body.innerText;
        }""")
        html_meta = page.content()
        browser.close()

    # Extraer meta title y description
    title = re.search(r'<title[^>]*>([^<]+)</title>', html_meta, re.I)
    desc  = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html_meta, re.I)

    encabezado = ""
    if title: encabezado += f"TITLE: {title.group(1).strip()}\n"
    if desc:  encabezado += f"META DESC: {desc.group(1).strip()}\n"

    # Limitar texto a 8000 chars para no saturar el prompt
    texto_limpio = re.sub(r'\n{3,}', '\n\n', texto.strip())[:8000]
    return encabezado + "\n" + texto_limpio


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
            lineas.append(f'<p>{l}</p>')
    return "\n".join(lineas)


def guardar_doc(url: str, modo: str, contenido: str, fecha: datetime) -> Path:
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts   = fecha.strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r'https?://(www\.)?', '', url).split('/')[0].replace('.', '-')[:40]
    ruta = carpeta / f"web_{modo}_{slug}_{ts}.html"

    nombre  = _nombre_agencia()
    cuerpo  = _md_a_html(contenido)
    tag_txt = "Análisis Cliente" if modo == "cliente" else "Espionaje Web"
    tag_color = "#22cfff22" if modo == "cliente" else "#ff6b3522"
    tag_fg    = "#0077aa"   if modo == "cliente" else "#c04000"

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{tag_txt} — {slug}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:#f8f9fa;color:#1a1a1a;line-height:1.75;padding:40px 20px 80px}}
    .doc{{background:#fff;max-width:780px;margin:0 auto;padding:60px 72px;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.12),0 4px 20px rgba(0,0,0,.06)}}
    .doc-header{{border-bottom:1px solid #e8eaed;padding-bottom:24px;margin-bottom:36px}}
    .doc-tag{{display:inline-block;background:{tag_color};color:{tag_fg};font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:4px 10px;border-radius:4px;margin-bottom:12px}}
    .doc-title{{font-size:22px;font-weight:700;margin-bottom:8px;word-break:break-all}}
    .doc-meta{{font-size:13px;color:#80868b}}
    h1{{font-size:20px;font-weight:700;margin:32px 0 12px}}
    h2{{font-size:17px;font-weight:600;margin:28px 0 10px}}
    h3{{font-size:14px;font-weight:600;margin:20px 0 6px;text-transform:uppercase;letter-spacing:.04em;color:#3c4043}}
    p{{font-size:15px;color:#3c4043;margin:6px 0}}
    li{{font-size:15px;color:#3c4043;margin:5px 0 5px 20px;list-style:disc}}
    blockquote{{background:#f0f8ff;border-left:3px solid #22cfff;padding:14px 20px;margin:12px 0;border-radius:0 6px 6px 0;font-size:15px;font-weight:500}}
    hr{{border:none;border-top:1px solid #e8eaed;margin:28px 0}}
    strong{{color:#1a1a1a;font-weight:600}}
    .doc-footer{{margin-top:48px;padding-top:20px;border-top:1px solid #e8eaed;font-size:12px;color:#9aa0a6;display:flex;justify-content:space-between}}
  </style>
</head>
<body>
<div class="doc">
  <div class="doc-header">
    <div class="doc-tag">{tag_txt}</div>
    <div class="doc-title">{url}</div>
    <div class="doc-meta">{nombre} &nbsp;·&nbsp; {fecha.strftime('%d de %B de %Y, %H:%M')}</div>
  </div>
  {cuerpo}
  <div class="doc-footer">
    <span>{nombre}</span>
    <span>Agente Web</span>
  </div>
</div>
</body>
</html>"""

    ruta.write_text(html, encoding="utf-8")
    return ruta


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--modo", choices=["cliente", "competidor"], default="cliente")
    parser.add_argument("--archivo", help="Archivo .md con el análisis ya generado")
    args = parser.parse_args()

    if args.archivo:
        contenido = Path(args.archivo).read_text(encoding="utf-8")
    else:
        contenido = sys.stdin.read()

    fecha = datetime.now()
    ruta  = guardar_doc(args.url, args.modo, contenido, fecha)
    subprocess.run(["open", str(ruta)], check=False)
    subprocess.run(
        ["osascript", "-e",
         f'display notification "Análisis listo — {args.url[:40]}" with title "{_nombre_agencia()}" sound name "Glass"'],
        check=False, capture_output=True
    )
    print(f"Guardado: {ruta}")


if __name__ == "__main__":
    main()
