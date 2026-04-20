"""
orquestador.py — AgenciaML
--------------------------
Corre todos los agentes para todos los clientes activos.

Uso:
    python3 orquestador.py                  # corre todo
    python3 orquestador.py --cliente zapatillas_perez   # solo un cliente
    python3 orquestador.py --agente espionaje           # solo un agente

Estructura esperada:
    clientes/
    └── nombre_cliente/
        ├── config.json
        └── watchlist.txt
"""

import os
import sys
import json
import argparse
import subprocess
import time
from datetime import datetime
from pathlib import Path

# ─── Notificaciones macOS ─────────────────────────────────────────────────────

SONIDOS = {
    "inicio":    "Tink",
    "ok":        "Glass",
    "error":     "Basso",
    "completo":  "Hero",
}

def notificar(titulo: str, mensaje: str, tipo: str = "ok") -> None:
    """Muestra una notificación macOS con sonido."""
    sonido = SONIDOS.get(tipo, "Glass")
    script = (
        f'display notification "{mensaje}" '
        f'with title "AgenciaML — {titulo}" '
        f'sound name "{sonido}"'
    )
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except Exception:
        pass  # Si falla la notif, no interrumpir el flujo

def sonido(tipo: str = "ok") -> None:
    """Reproduce un sonido del sistema."""
    archivos = {
        "inicio":   "/System/Library/Sounds/Tink.aiff",
        "ok":       "/System/Library/Sounds/Glass.aiff",
        "error":    "/System/Library/Sounds/Basso.aiff",
        "completo": "/System/Library/Sounds/Hero.aiff",
    }
    ruta = archivos.get(tipo, archivos["ok"])
    try:
        subprocess.run(["afplay", ruta], check=False, capture_output=True)
    except Exception:
        pass


# ─── Carga de clientes ────────────────────────────────────────────────────────

def cargar_clientes(solo_cliente: str = None) -> list[dict]:
    """Lee todas las carpetas de clientes/. Retorna lista de configs activas."""
    raiz = Path("clientes")
    clientes = []

    for carpeta in sorted(raiz.iterdir()):
        if not carpeta.is_dir() or carpeta.name == "template":
            continue
        if solo_cliente and carpeta.name != solo_cliente:
            continue

        config_path = carpeta / "config.json"
        if not config_path.exists():
            continue

        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not config.get("activo", True):
            continue

        config["_carpeta"] = carpeta
        clientes.append(config)

    return clientes


# ─── Runners de agentes ───────────────────────────────────────────────────────

def correr_espionaje(cliente: dict) -> bool:
    """
    Corre el agente de espionaje ML para todos los vendedores configurados.
    """
    cfg_ml = cliente.get("plataformas", {}).get("mercadolibre", {})
    if not cfg_ml.get("activo", False):
        return True

    vendedores = cfg_ml.get("vendedores_a_espiar", [])
    nombre = cliente["cliente"]
    carpeta_base = Path("reportes_ml") / cliente["_carpeta"].name.upper()
    carpeta_base.mkdir(parents=True, exist_ok=True)

    # Copiar watchlist si existe en la carpeta del cliente
    wl_src = cliente["_carpeta"] / "watchlist.txt"
    wl_dst = carpeta_base / "watchlist.txt"
    if wl_src.exists() and not wl_dst.exists():
        wl_dst.write_text(wl_src.read_text(encoding="utf-8"), encoding="utf-8")

    exito = True
    for vendedor in vendedores:
        notificar(nombre, f"Espiando {vendedor}…", "inicio")
        sonido("inicio")

        resultado = subprocess.run(
            [sys.executable, "espiar_vendedor.py", vendedor,
             "--carpeta", cliente["_carpeta"].name.upper()],
            capture_output=False,
        )

        if resultado.returncode == 0:
            notificar(nombre, f"✓ {vendedor} — reporte listo", "ok")
            sonido("ok")
        else:
            notificar(nombre, f"✗ Error espiando {vendedor}", "error")
            sonido("error")
            exito = False

    return exito


def correr_contenido(cliente: dict) -> bool:
    """Agente de contenido — generación con IA (próximamente)."""
    print("      [contenido] Agente en construcción.")
    return True


def correr_fotos(cliente: dict) -> bool:
    """Agente de fotos/creativos (próximamente)."""
    print("      [fotos] Agente en construcción.")
    return True


# Mapa nombre → función
AGENTES = {
    "espionaje": correr_espionaje,
    "contenido": correr_contenido,
    "fotos":     correr_fotos,
}


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="AgenciaML — Orquestador de agentes")
    parser.add_argument("--cliente", help="Correr solo este cliente (nombre de carpeta)")
    parser.add_argument("--agente",  help="Correr solo este agente (espionaje|contenido|fotos)")
    args = parser.parse_args()

    inicio = datetime.now()
    print(f"\n{'='*55}")
    print(f"  AgenciaML — Orquestador")
    print(f"  {inicio.strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*55}\n")

    notificar("Orquestador", "Iniciando tareas…", "inicio")
    sonido("inicio")

    clientes = cargar_clientes(solo_cliente=args.cliente)
    if not clientes:
        print("No se encontraron clientes activos.")
        sys.exit(0)

    print(f"Clientes a procesar: {len(clientes)}\n")

    errores = 0
    for cliente in clientes:
        nombre = cliente["cliente"]
        agentes_cfg = cliente.get("agentes", {})
        print(f"── {nombre} {'─'*(45 - len(nombre))}")

        for nombre_agente, fn in AGENTES.items():
            # Saltar si se pidió un agente específico
            if args.agente and nombre_agente != args.agente:
                continue
            # Saltar si el cliente no tiene este agente activado
            if not agentes_cfg.get(nombre_agente, False):
                continue

            print(f"   [{nombre_agente}] corriendo…")
            t0 = time.time()
            ok = fn(cliente)
            elapsed = time.time() - t0
            estado = "✓" if ok else "✗"
            print(f"   [{nombre_agente}] {estado} ({elapsed:.0f}s)\n")
            if not ok:
                errores += 1

    # Resumen final
    elapsed_total = (datetime.now() - inicio).total_seconds()
    print(f"\n{'='*55}")
    print(f"  Listo en {elapsed_total:.0f}s — Errores: {errores}")
    print(f"{'='*55}\n")

    if errores == 0:
        notificar("Orquestador", f"Todo listo en {elapsed_total:.0f}s", "completo")
        sonido("completo")
    else:
        notificar("Orquestador", f"Terminó con {errores} error(es)", "error")
        sonido("error")


if __name__ == "__main__":
    main()
