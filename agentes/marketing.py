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


def guardar(tema: str, contenido: str) -> Path:
    carpeta = Path("reportes_ml") / "AgenciaML"
    carpeta.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = tema[:30].replace(" ", "_").lower()
    ruta = carpeta / f"marketing_{slug}_{ts}.md"
    ruta.write_text(
        f"# Marketing — {tema}\n_{datetime.now().strftime('%d/%m/%Y %H:%M')}_\n\n{contenido}",
        encoding="utf-8"
    )
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

    # Imprimir resultado directo en consola (aparece en el chat)
    print(f"\n{'═'*52}\n")
    print(contenido)

    # Guardar para referencia futura
    ruta = guardar(tema, contenido)
    print(f"\n{'─'*52}")
    print(f"  Guardado en: {ruta}")
    print(f"{'─'*52}\n")


if __name__ == "__main__":
    main()
