"""
espiar_vendedor.py
------------------
Monitorea las publicaciones activas de un vendedor de MercadoLibre Argentina.
- Obtiene título, precio, stock y ventas vía la API pública de MercadoLibre.
- Guarda un snapshot en Excel con fecha.
- Compara con el snapshot anterior para detectar cambios y estimar ventas.
- Envía un resumen por WhatsApp usando Twilio.

Dependencias:
    pip install requests openpyxl twilio python-dotenv

Variables de entorno necesarias (archivo .env):
    TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
    TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
    TWILIO_WHATSAPP_FROM=whatsapp:+14155238886   # número sandbox de Twilio
    TWILIO_WHATSAPP_TO=whatsapp:+549XXXXXXXXXX   # tu número con código de país
"""

import os
import sys
import json
import glob
import requests
from datetime import datetime
from pathlib import Path

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
from twilio.rest import Client

# ─── Configuración ────────────────────────────────────────────────────────────

load_dotenv()

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WA_FROM      = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
WA_TO        = os.getenv("TWILIO_WHATSAPP_TO")

# Directorio donde se guardan los reportes Excel
REPORTS_DIR = Path("reportes_ml")
REPORTS_DIR.mkdir(exist_ok=True)

# Cantidad máxima de publicaciones a recuperar por vendedor
MAX_ITEMS = 1000

# Base URL de la API pública de MercadoLibre
API_BASE = "https://api.mercadolibre.com"


# ─── Funciones de MercadoLibre ─────────────────────────────────────────────────

def obtener_seller_id(nickname: str) -> tuple[int, str]:
    """
    Resuelve el seller_id a partir del nickname del vendedor.
    Retorna (seller_id, nombre_oficial).
    """
    url = f"{API_BASE}/sites/MLA/search"
    params = {"nickname": nickname, "limit": 1}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    resultados = data.get("results", [])
    if not resultados:
        raise ValueError(f"No se encontró ningún vendedor con el nickname '{nickname}'.")

    seller = resultados[0]["seller"]
    return seller["id"], seller.get("nickname", nickname)


def obtener_ids_publicaciones(seller_id: int) -> list[str]:
    """
    Recupera todos los IDs de publicaciones activas del vendedor
    usando paginación de 50 en 50 (límite de la API).
    """
    ids = []
    offset = 0
    limit = 50

    while True:
        url = f"{API_BASE}/sites/MLA/search"
        params = {
            "seller_id": seller_id,
            "status": "active",
            "limit": limit,
            "offset": offset,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        resultados = data.get("results", [])
        for item in resultados:
            ids.append(item["id"])

        total = data.get("paging", {}).get("total", 0)
        offset += limit

        # Detenemos cuando ya recuperamos todos o llegamos al máximo configurado
        if offset >= min(total, MAX_ITEMS):
            break

    return ids


def obtener_detalle_items(ids: list[str]) -> list[dict]:
    """
    Consulta el endpoint multiget de MercadoLibre (hasta 20 IDs por request)
    para obtener precio, stock, ventas y envío de cada publicación.
    """
    items_detalle = []
    chunk_size = 20  # límite del endpoint /items?ids=

    for i in range(0, len(ids), chunk_size):
        chunk = ids[i : i + chunk_size]
        url = f"{API_BASE}/items"
        params = {"ids": ",".join(chunk)}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()

        for entry in resp.json():
            if entry.get("code") != 200:
                continue  # ítem no disponible, lo saltamos
            body = entry["body"]

            # Envío gratis: el ítem tiene tag "free_shipping" o modo de envío gratis
            envio_gratis = "free_shipping" in body.get("shipping", {}).get("tags", []) or \
                           body.get("shipping", {}).get("free_shipping", False)

            items_detalle.append({
                "id":          body.get("id"),
                "titulo":      body.get("title"),
                "precio":      body.get("price"),
                "moneda":      body.get("currency_id", "ARS"),
                "stock":       body.get("available_quantity", 0),
                "vendidos":    body.get("sold_quantity", 0),
                "condicion":   body.get("condition"),
                "envio_gratis": envio_gratis,
                "permalink":   body.get("permalink"),
            })

    return items_detalle


# ─── Funciones de Excel ────────────────────────────────────────────────────────

def nombre_archivo(nickname: str, fecha: datetime) -> Path:
    """Genera el nombre del archivo Excel con fecha y hora."""
    ts = fecha.strftime("%Y%m%d_%H%M%S")
    return REPORTS_DIR / f"{nickname}_{ts}.xlsx"


def guardar_excel(items: list[dict], nickname: str, fecha: datetime) -> Path:
    """
    Crea un archivo Excel con los datos del vendedor.
    Retorna la ruta del archivo creado.
    """
    ruta = nombre_archivo(nickname, fecha)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Publicaciones"

    # ── Encabezados ──
    encabezados = [
        "ID", "Título", "Precio (ARS)", "Stock disponible",
        "Vendidos totales", "Condición", "Envío gratis", "URL",
    ]
    header_fill = PatternFill("solid", fgColor="1A73E8")
    header_font = Font(bold=True, color="FFFFFF")

    for col, texto in enumerate(encabezados, start=1):
        celda = ws.cell(row=1, column=col, value=texto)
        celda.fill = header_fill
        celda.font = header_font
        celda.alignment = Alignment(horizontal="center")

    # ── Datos ──
    for fila, item in enumerate(items, start=2):
        ws.cell(row=fila, column=1, value=item["id"])
        ws.cell(row=fila, column=2, value=item["titulo"])
        ws.cell(row=fila, column=3, value=item["precio"])
        ws.cell(row=fila, column=4, value=item["stock"])
        ws.cell(row=fila, column=5, value=item["vendidos"])
        ws.cell(row=fila, column=6, value=item["condicion"])
        ws.cell(row=fila, column=7, value="Sí" if item["envio_gratis"] else "No")
        ws.cell(row=fila, column=8, value=item["permalink"])

    # ── Ancho automático de columnas ──
    for col in ws.columns:
        max_len = max((len(str(c.value or "")) for c in col), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 2, 80)

    wb.save(ruta)
    print(f"[✓] Reporte guardado: {ruta}")
    return ruta


def cargar_reporte_anterior(nickname: str) -> dict[str, dict] | None:
    """
    Busca el reporte Excel más reciente del vendedor (excluyendo el actual)
    y retorna un dict {item_id: {precio, stock, vendidos}}.
    Retorna None si no existe reporte previo.
    """
    patron = str(REPORTS_DIR / f"{nickname}_*.xlsx")
    archivos = sorted(glob.glob(patron))

    if len(archivos) < 2:
        return None  # no hay reporte anterior con qué comparar

    # El penúltimo es el más reciente anterior al que acabamos de crear
    ruta_anterior = archivos[-2]
    print(f"[i] Comparando contra reporte anterior: {Path(ruta_anterior).name}")

    wb = openpyxl.load_workbook(ruta_anterior)
    ws = wb.active
    datos = {}

    # Fila 1 = encabezados, datos desde fila 2
    for fila in ws.iter_rows(min_row=2, values_only=True):
        item_id, _, precio, stock, vendidos = fila[0], fila[1], fila[2], fila[3], fila[4]
        if item_id:
            datos[str(item_id)] = {
                "precio":   precio,
                "stock":    stock,
                "vendidos": vendidos,
            }

    return datos


# ─── Lógica de comparación ─────────────────────────────────────────────────────

def comparar_snapshots(
    actuales: list[dict],
    anteriores: dict[str, dict] | None,
) -> dict:
    """
    Compara el snapshot actual con el anterior y retorna un resumen con:
    - cambios_precio: lista de ítems con cambio de precio
    - cambios_stock:  lista de ítems con cambio de stock
    - ventas_estimadas: unidades vendidas estimadas (caída de vendidos_totales sería
      imposible; se suma el delta positivo de sold_quantity)
    - nuevos: publicaciones nuevas (no estaban antes)
    - eliminados: publicaciones que desaparecieron
    """
    if anteriores is None:
        return {
            "cambios_precio": [],
            "cambios_stock": [],
            "ventas_estimadas": 0,
            "nuevos": [i["id"] for i in actuales],
            "eliminados": [],
        }

    ids_actuales = {i["id"] for i in actuales}
    ids_anteriores = set(anteriores.keys())

    cambios_precio = []
    cambios_stock  = []
    ventas_est     = 0

    for item in actuales:
        iid = item["id"]
        if iid not in anteriores:
            continue  # ítem nuevo, sin base de comparación

        prev = anteriores[iid]

        # Cambio de precio
        precio_ant = prev["precio"] or 0
        precio_act = item["precio"] or 0
        if precio_ant != precio_act:
            variacion_pct = ((precio_act - precio_ant) / precio_ant * 100) if precio_ant else 0
            cambios_precio.append({
                "id":     iid,
                "titulo": item["titulo"],
                "antes":  precio_ant,
                "ahora":  precio_act,
                "delta%": round(variacion_pct, 1),
            })

        # Cambio de stock
        stock_ant = prev["stock"] or 0
        stock_act = item["stock"] or 0
        if stock_ant != stock_act:
            cambios_stock.append({
                "id":     iid,
                "titulo": item["titulo"],
                "antes":  stock_ant,
                "ahora":  stock_act,
            })

        # Ventas estimadas: incremento en sold_quantity entre snapshots
        vendidos_ant = prev["vendidos"] or 0
        vendidos_act = item["vendidos"] or 0
        delta_ventas = max(0, vendidos_act - vendidos_ant)
        ventas_est  += delta_ventas

    return {
        "cambios_precio":    cambios_precio,
        "cambios_stock":     cambios_stock,
        "ventas_estimadas":  ventas_est,
        "nuevos":            list(ids_actuales - ids_anteriores),
        "eliminados":        list(ids_anteriores - ids_actuales),
    }


# ─── WhatsApp con Twilio ───────────────────────────────────────────────────────

def armar_mensaje(
    nickname: str,
    items: list[dict],
    cambios: dict,
    fecha: datetime,
) -> str:
    """Construye el texto del mensaje de WhatsApp."""
    ts = fecha.strftime("%d/%m/%Y %H:%M")

    precios_promedio = (
        sum(i["precio"] for i in items if i["precio"]) / len(items)
        if items else 0
    )

    lineas = [
        f"📊 *Reporte MercadoLibre* — {ts}",
        f"🏪 Vendedor: *{nickname}*",
        f"📦 Publicaciones activas: {len(items)}",
        f"💰 Precio promedio: ${precios_promedio:,.0f} ARS",
        f"🚀 Ventas estimadas (vs. reporte anterior): {cambios['ventas_estimadas']} unid.",
        "",
    ]

    # Nuevas publicaciones
    if cambios["nuevos"]:
        lineas.append(f"🆕 Nuevas publicaciones: {len(cambios['nuevos'])}")

    # Publicaciones eliminadas
    if cambios["eliminados"]:
        lineas.append(f"🗑️ Publicaciones eliminadas: {len(cambios['eliminados'])}")

    # Cambios de precio (máx. 5 para no saturar el mensaje)
    if cambios["cambios_precio"]:
        lineas.append(f"\n💲 Cambios de precio ({len(cambios['cambios_precio'])} total):")
        for cp in cambios["cambios_precio"][:5]:
            signo = "▲" if cp["delta%"] > 0 else "▼"
            lineas.append(
                f"  {signo} {cp['titulo'][:40]}…\n"
                f"     ${cp['antes']:,.0f} → ${cp['ahora']:,.0f} ({cp['delta%']:+.1f}%)"
            )

    # Cambios de stock (máx. 5)
    if cambios["cambios_stock"]:
        lineas.append(f"\n📉 Cambios de stock ({len(cambios['cambios_stock'])} total):")
        for cs in cambios["cambios_stock"][:5]:
            signo = "▲" if cs["ahora"] > cs["antes"] else "▼"
            lineas.append(
                f"  {signo} {cs['titulo'][:40]}…\n"
                f"     {cs['antes']} → {cs['ahora']} unid."
            )

    lineas.append("\n_Generado por espiar_vendedor.py_")
    return "\n".join(lineas)


def enviar_whatsapp(mensaje: str) -> None:
    """Envía el mensaje de texto por WhatsApp a través de la API de Twilio."""
    if not all([TWILIO_SID, TWILIO_TOKEN, WA_TO]):
        print(
            "[!] Credenciales de Twilio incompletas. "
            "Configurá TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN y TWILIO_WHATSAPP_TO en el .env"
        )
        return

    client = Client(TWILIO_SID, TWILIO_TOKEN)
    msg = client.messages.create(
        from_=WA_FROM,
        to=WA_TO,
        body=mensaje,
    )
    print(f"[✓] WhatsApp enviado. SID: {msg.sid}")


# ─── Punto de entrada ──────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Uso: python espiar_vendedor.py <NICKNAME_VENDEDOR>")
        sys.exit(1)

    nickname_input = sys.argv[1].strip()
    fecha_ahora    = datetime.now()

    print(f"\n=== Espiando vendedor: {nickname_input} ===\n")

    # 1. Resolver seller_id
    print("[1/5] Buscando seller_id…")
    seller_id, nickname_oficial = obtener_seller_id(nickname_input)
    print(f"      seller_id={seller_id}, nombre oficial='{nickname_oficial}'")

    # 2. Obtener IDs de publicaciones activas
    print("[2/5] Recuperando IDs de publicaciones activas…")
    ids = obtener_ids_publicaciones(seller_id)
    print(f"      {len(ids)} publicaciones encontradas.")

    if not ids:
        print("      El vendedor no tiene publicaciones activas. Saliendo.")
        sys.exit(0)

    # 3. Obtener detalle de cada ítem
    print("[3/5] Descargando detalle de ítems (precio, stock, ventas)…")
    items = obtener_detalle_items(ids)
    print(f"      {len(items)} ítems procesados.")

    # 4. Guardar snapshot en Excel (antes de cargar el anterior para que quede en disco)
    print("[4/5] Guardando reporte en Excel…")
    ruta_excel = guardar_excel(items, nickname_oficial, fecha_ahora)

    # 5. Comparar con reporte anterior
    anteriores = cargar_reporte_anterior(nickname_oficial)
    cambios    = comparar_snapshots(items, anteriores)

    print(f"\n── Resumen de cambios ──")
    print(f"   Ventas estimadas:     {cambios['ventas_estimadas']} unidades")
    print(f"   Cambios de precio:    {len(cambios['cambios_precio'])}")
    print(f"   Cambios de stock:     {len(cambios['cambios_stock'])}")
    print(f"   Nuevas publicaciones: {len(cambios['nuevos'])}")
    print(f"   Eliminadas:           {len(cambios['eliminados'])}")

    # 6. Enviar resumen por WhatsApp
    print("\n[5/5] Enviando resumen por WhatsApp…")
    mensaje = armar_mensaje(nickname_oficial, items, cambios, fecha_ahora)
    enviar_whatsapp(mensaje)

    print("\n=== Proceso finalizado correctamente ===\n")


if __name__ == "__main__":
    main()
