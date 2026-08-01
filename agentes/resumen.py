"""
agentes/resumen.py — Resumen semanal por cliente
-------------------------------------------------
Trigger: "Resumen semanal"
Lee los reportes de la semana y genera un HTML consolidado por cliente.
"""

import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


def _nombre_agencia() -> str:
    ruta = Path("agencia.md")
    if not ruta.exists():
        return "Impulse Agency"
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        if linea.strip() and not linea.startswith("#") and not (linea.strip().startswith("(") and linea.strip().endswith(")")):
            return linea.strip()
    return "Impulse Agency"


def _reportes_semana() -> list[dict]:
    """Devuelve los archivos HTML generados en los últimos 7 días."""
    hace_7 = datetime.now() - timedelta(days=7)
    reportes = []
    for f in Path("reportes_ml").rglob("*.html"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= hace_7:
                reportes.append({"ruta": f, "fecha": mtime, "tipo": f.stem.split("_")[0]})
        except Exception:
            continue
    return sorted(reportes, key=lambda x: x["fecha"], reverse=True)


def guardar_resumen(contenido_html: str, fecha: datetime) -> Path:
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts   = fecha.strftime("%Y%m%d_%H%M%S")
    ruta = carpeta / f"resumen_semanal_{ts}.html"
    ruta.write_text(contenido_html, encoding="utf-8")
    return ruta


def generar_html(resumen_md: str, reportes: list[dict], fecha: datetime) -> str:
    import re as _re
    nombre = _nombre_agencia()

    def md_html(texto):
        lineas = []
        for linea in texto.split("\n"):
            l = linea.strip()
            if not l: lineas.append("<br>")
            elif l.startswith("## "): lineas.append(f'<h2>{l[3:]}</h2>')
            elif l.startswith("# "): lineas.append(f'<h1>{l[2:]}</h1>')
            elif l.startswith("---"): lineas.append('<hr>')
            elif l.startswith("- "): lineas.append(f'<li>{l[2:]}</li>')
            elif l.startswith("> "): lineas.append(f'<blockquote>{l[2:]}</blockquote>')
            else:
                l = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', l)
                lineas.append(f'<p>{l}</p>')
        return "\n".join(lineas)

    semana_inicio = (fecha - timedelta(days=7)).strftime('%d/%m')
    semana_fin    = fecha.strftime('%d/%m/%Y')

    items_lista = "".join(
        f'<li><a href="{r["ruta"].resolve()}" target="_blank">'
        f'{r["tipo"].capitalize()} — {r["ruta"].parent.name} '
        f'<span style="color:#9aa0a6">({r["fecha"].strftime("%d/%m %H:%M")})</span>'
        f'</a></li>'
        for r in reportes
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Resumen Semanal — {nombre}</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:'Inter',sans-serif;background:#f8f9fa;color:#1a1a1a;line-height:1.75;padding:40px 20px 80px}}
    .doc{{background:#fff;max-width:820px;margin:0 auto;padding:60px 72px;border-radius:4px;box-shadow:0 1px 3px rgba(0,0,0,.12),0 4px 20px rgba(0,0,0,.06)}}
    .doc-header{{border-bottom:1px solid #e8eaed;padding-bottom:24px;margin-bottom:36px}}
    .doc-tag{{display:inline-block;background:#22cfff22;color:#0077aa;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;padding:4px 10px;border-radius:4px;margin-bottom:12px}}
    .doc-title{{font-size:26px;font-weight:700;margin-bottom:8px}}
    .doc-meta{{font-size:13px;color:#80868b}}
    h1{{font-size:20px;font-weight:700;margin:32px 0 12px}}
    h2{{font-size:17px;font-weight:600;margin:28px 0 10px;color:#1a1a1a}}
    p{{font-size:15px;color:#3c4043;margin:6px 0}}
    li{{font-size:15px;color:#3c4043;margin:5px 0 5px 20px}}
    li a{{color:#1a73e8;text-decoration:none}}
    li a:hover{{text-decoration:underline}}
    blockquote{{background:#f0fff2;border-left:3px solid #1ae82f;padding:14px 20px;margin:12px 0;border-radius:0 6px 6px 0;font-size:15px;font-weight:500}}
    hr{{border:none;border-top:1px solid #e8eaed;margin:28px 0}}
    strong{{color:#1a1a1a;font-weight:600}}
    .doc-footer{{margin-top:48px;padding-top:20px;border-top:1px solid #e8eaed;font-size:12px;color:#9aa0a6;display:flex;justify-content:space-between}}
  </style>
</head>
<body>
<div class="doc">
  <div class="doc-header">
    <div class="doc-tag">Resumen Semanal</div>
    <div class="doc-title">Semana {semana_inicio} — {semana_fin}</div>
    <div class="doc-meta">{nombre} &nbsp;·&nbsp; {fecha.strftime('%d de %B de %Y, %H:%M')}</div>
  </div>

  {md_html(resumen_md)}

  <hr>
  <h2>Reportes generados esta semana</h2>
  <ul style="margin-top:12px">{items_lista or '<li>Sin reportes esta semana.</li>'}</ul>

  <div class="doc-footer">
    <span>{nombre}</span>
    <span>Resumen Semanal</span>
  </div>
</div>
</body>
</html>"""


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--archivo", help="Archivo .md con el resumen generado")
    args = parser.parse_args()

    reportes = _reportes_semana()

    if args.archivo:
        contenido = Path(args.archivo).read_text(encoding="utf-8")
    else:
        contenido = sys.stdin.read()

    fecha   = datetime.now()
    html    = generar_html(contenido, reportes, fecha)
    ruta    = guardar_resumen(html, fecha)
    subprocess.run(["open", str(ruta)], check=False)
    subprocess.run(
        ["osascript", "-e",
         f'display notification "Resumen semanal listo" with title "{_nombre_agencia()}" sound name "Hero"'],
        check=False, capture_output=True
    )
    print(f"Guardado: {ruta}")


if __name__ == "__main__":
    main()
