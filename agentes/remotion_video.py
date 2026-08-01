#!/usr/bin/env python3
"""
Genera un video .mp4 animado a partir de un JSON de slides (mismo formato que carrusel_imagenes.py).
Uso: python3 agentes/remotion_video.py "[tema]" --slides-json /ruta/slides.json
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTION_DIR = os.path.join(BASE_DIR, "remotion")
OUTPUT_BASE = os.path.join(BASE_DIR, "reportes_ml", "AgenciaML", "videos")


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[áàä]", "a", text)
    text = re.sub(r"[éèë]", "e", text)
    text = re.sub(r"[íìï]", "i", text)
    text = re.sub(r"[óòö]", "o", text)
    text = re.sub(r"[úùü]", "u", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:50]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tema", help="Tema del video")
    parser.add_argument("--slides-json", required=True, help="Ruta al JSON de slides")
    args = parser.parse_args()

    # Leer slides
    with open(args.slides_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    slides = data.get("slides", [])
    if not slides:
        print("Error: el JSON no contiene slides.")
        sys.exit(1)

    slug = slugify(args.tema)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta_nombre = f"video_{slug}_{fecha}"
    carpeta_salida = os.path.join(OUTPUT_BASE, carpeta_nombre)
    os.makedirs(carpeta_salida, exist_ok=True)

    output_mp4 = os.path.join(carpeta_salida, "reel_instagram.mp4")

    # Props para Remotion
    props = json.dumps({"slides": slides, "tema": args.tema})

    print(f"\nTema:   {args.tema}")
    print(f"Slides: {len(slides)}")
    print(f"Duración estimada: {len(slides) * 3} segundos\n")
    print("[1/2] Renderizando video con Remotion...")

    remotion_bin = os.path.join(REMOTION_DIR, "node_modules", ".bin", "remotion")
    cmd = [
        remotion_bin, "render",
        "src/index.ts",
        "AgenciaReel",
        f"--output={output_mp4}",
        f"--props={props}",
        "--concurrency=1",
        "--log=warn",
    ]

    result = subprocess.run(cmd, cwd=REMOTION_DIR, capture_output=True, text=True)

    if result.returncode != 0:
        print("Error al renderizar:")
        print(result.stderr)
        sys.exit(1)

    print(f"[2/2] Video guardado.\n")
    print(f" Carpeta: {os.path.relpath(carpeta_salida, BASE_DIR)}")
    print(f" Video:   {os.path.relpath(output_mp4, BASE_DIR)}")
    print(f" Tamaño:  {os.path.getsize(output_mp4) // 1024} KB")

    # Abrir en Finder
    subprocess.run(["open", carpeta_salida])


if __name__ == "__main__":
    main()
