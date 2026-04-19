"""
espiar_vendedor.py
------------------
Monitorea las publicaciones activas de un vendedor de MercadoLibre Argentina.

Genera dos salidas:
  - Excel (.xlsx): hoja principal + resumen por marca + detalle de variantes
  - Página HTML  : dashboard visual que se abre en el navegador

Uso:
    python espiar_vendedor.py <NICKNAME> [--carpeta NOMBRE]

    Ejemplo:
        python espiar_vendedor.py todoairelibregd --carpeta TODOAIRELIBRE

Dependencias:
    pip install requests openpyxl python-dotenv

Variables de entorno opcionales (archivo .env) para WhatsApp:
    TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM, TWILIO_WHATSAPP_TO
"""

import os
import sys
import glob
import argparse
import textwrap
import requests
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_DISPONIBLE = True
except ImportError:
    TWILIO_DISPONIBLE = False

# ─── Configuración ────────────────────────────────────────────────────────────

TWILIO_SID   = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
WA_FROM      = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
WA_TO        = os.getenv("TWILIO_WHATSAPP_TO")

ML_APP_ID  = os.getenv("ML_APP_ID")
ML_APP_SECRET = os.getenv("ML_APP_SECRET")

REPORTS_ROOT = Path("reportes_ml")
MAX_ITEMS    = 1000
API_BASE     = "https://api.mercadolibre.com"

# Token de acceso a la API de ML (se renueva automáticamente)
_ml_token: dict = {"access_token": None, "expires_at": 0}


# ─── MercadoLibre Auth ────────────────────────────────────────────────────────

import time as _time

def obtener_ml_token() -> str:
    """
    Obtiene un access token de nivel app usando client credentials.
    Lo cachea en memoria y lo renueva cuando expira.
    Requiere ML_APP_ID y ML_APP_SECRET en el .env.
    """
    global _ml_token
    if _ml_token["access_token"] and _time.time() < _ml_token["expires_at"]:
        return _ml_token["access_token"]

    if not ML_APP_ID or not ML_APP_SECRET:
        raise RuntimeError(
            "\n⚠️  La API de MercadoLibre requiere credenciales de app.\n"
            "   1. Registrá tu app gratis en: https://developers.mercadolibre.com.ar\n"
            "   2. Copiá APP_ID y SECRET_KEY al archivo .env:\n"
            "      ML_APP_ID=1234567890\n"
            "      ML_APP_SECRET=tu_secret_key\n"
        )

    resp = requests.post(
        f"{API_BASE}/oauth/token",
        data={
            "grant_type":    "client_credentials",
            "client_id":     ML_APP_ID,
            "client_secret": ML_APP_SECRET,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _ml_token["access_token"] = data["access_token"]
    # Renovar 5 minutos antes de que expire
    _ml_token["expires_at"]   = _time.time() + data.get("expires_in", 21600) - 300
    print(f"      [✓] Token ML obtenido (expira en {data.get('expires_in',0)//3600}hs)")
    return _ml_token["access_token"]


def _headers() -> dict:
    """Retorna los headers con Bearer token para las requests a ML."""
    return {"Authorization": f"Bearer {obtener_ml_token()}"}


# ─── MercadoLibre API ──────────────────────────────────────────────────────────

def obtener_seller_id(nickname: str) -> tuple:
    """Resuelve seller_id y nombre oficial a partir del nickname."""
    resp = requests.get(
        f"{API_BASE}/sites/MLA/search",
        params={"nickname": nickname, "limit": 1},
        headers=_headers(),
        timeout=15,
    )
    resp.raise_for_status()
    resultados = resp.json().get("results", [])
    if not resultados:
        raise ValueError(f"Vendedor '{nickname}' no encontrado.")
    seller = resultados[0]["seller"]
    return seller["id"], seller.get("nickname", nickname)


def obtener_ids_publicaciones(seller_id: int) -> list[str]:
    """Recupera todos los IDs de publicaciones activas con paginación."""
    ids, offset, limit = [], 0, 50
    while True:
        resp = requests.get(
            f"{API_BASE}/sites/MLA/search",
            params={"seller_id": seller_id, "status": "active", "limit": limit, "offset": offset},
            headers=_headers(),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("results", []):
            ids.append(item["id"])
        total  = data.get("paging", {}).get("total", 0)
        offset += limit
        if offset >= min(total, MAX_ITEMS):
            break
    return ids


def _limpiar_tipo(domain_id: str) -> str:
    """Convierte 'MLA-AIR_CONDITIONERS' en 'Air Conditioners'."""
    return domain_id.replace("MLA-", "").replace("_", " ").title() if domain_id else "—"


def obtener_detalle_items(ids: list[str]) -> list[dict]:
    """
    Descarga precio, stock, ventas, marca, tipo de producto y variantes
    usando el endpoint multiget (20 ítems por request).
    """
    items = []
    hoy   = datetime.now(timezone.utc)

    for i in range(0, len(ids), 20):
        chunk = ids[i : i + 20]
        resp  = requests.get(f"{API_BASE}/items", params={"ids": ",".join(chunk)}, headers=_headers(), timeout=15)
        resp.raise_for_status()

        for entry in resp.json():
            if entry.get("code") != 200:
                continue
            b = entry["body"]

            # Marca desde el array de atributos
            marca = next(
                (a["value_name"] for a in b.get("attributes", []) if a.get("id") == "BRAND"),
                "Sin marca",
            )

            # Días activo desde date_created
            fecha_creacion = b.get("date_created", "")
            dias_activo    = 1
            if fecha_creacion:
                try:
                    dt_creacion = datetime.fromisoformat(fecha_creacion)
                    if dt_creacion.tzinfo is None:
                        dt_creacion = dt_creacion.replace(tzinfo=timezone.utc)
                    dias_activo = max(1, (hoy - dt_creacion).days)
                except ValueError:
                    pass

            vendidos      = b.get("sold_quantity", 0)
            ventas_hist   = round(vendidos / dias_activo, 2)
            envio_gratis  = (
                "free_shipping" in b.get("shipping", {}).get("tags", [])
                or b.get("shipping", {}).get("free_shipping", False)
            )

            # Variantes: lista de {descripcion, stock, vendidos}
            variantes = []
            for v in b.get("variations", []):
                desc = " / ".join(
                    f"{a['name']}: {a.get('value_name','?')}"
                    for a in v.get("attribute_combinations", [])
                )
                variantes.append({
                    "descripcion": desc or "Sin variante",
                    "stock":       v.get("available_quantity", 0),
                    "vendidos":    v.get("sold_quantity", 0),
                })

            items.append({
                "id":            b.get("id"),
                "titulo":        b.get("title"),
                "marca":         marca,
                "tipo":          _limpiar_tipo(b.get("domain_id", "")),
                "categoria_id":  b.get("category_id", ""),
                "precio":        b.get("price"),
                "stock":         b.get("available_quantity", 0),
                "vendidos":      vendidos,
                "dias_activo":   dias_activo,
                "ventas_hist_dia": ventas_hist,
                "ventas_rec_dia":  None,   # se completa en comparar_snapshots
                "condicion":     b.get("condition"),
                "envio_gratis":  envio_gratis,
                "permalink":     b.get("permalink"),
                "variantes":     variantes,
            })

    return items


# ─── Snapshot anterior ─────────────────────────────────────────────────────────

def cargar_reporte_anterior(nickname: str, carpeta: Path) -> tuple:
    """
    Lee el penúltimo Excel del vendedor (si existe).
    Retorna ({item_id: {precio, stock, vendidos}}, fecha_snapshot_anterior).
    """
    archivos = sorted(glob.glob(str(carpeta / f"{nickname}_*.xlsx")))
    if len(archivos) < 2:
        return {}, None

    ruta = archivos[-2]
    print(f"[i] Comparando contra: {Path(ruta).name}")

    # Fecha del snapshot anterior desde el nombre de archivo
    stem   = Path(ruta).stem                       # NICKNAME_YYYYMMDD_HHMMSS
    partes = stem.split("_")
    try:
        fecha_ant = datetime.strptime(f"{partes[-2]}_{partes[-1]}", "%Y%m%d_%H%M%S")
    except (ValueError, IndexError):
        fecha_ant = None

    wb = openpyxl.load_workbook(ruta)
    ws = wb.active

    # Leer encabezados para encontrar columnas por nombre
    encabezados = {cell.value: cell.column for cell in ws[1]}
    col_id  = encabezados.get("ID", 1)
    col_pre = encabezados.get("Precio (ARS)", 5)
    col_stk = encabezados.get("Stock Total", 6)
    col_ven = encabezados.get("Vendidos Totales", 7)

    datos = {}
    for fila in ws.iter_rows(min_row=2, values_only=True):
        iid = fila[col_id - 1]
        if iid:
            datos[str(iid)] = {
                "precio":   fila[col_pre - 1],
                "stock":    fila[col_stk - 1],
                "vendidos": fila[col_ven - 1],
            }
    return datos, fecha_ant


# ─── Comparación de snapshots ──────────────────────────────────────────────────

def comparar_snapshots(
    actuales:     list[dict],
    anteriores:   dict,
    fecha_actual: datetime,
    fecha_ant:    Optional[datetime],
) -> dict:
    """
    Detecta cambios de precio y stock, estima ventas y calcula ventas_rec_dia por ítem.
    Modifica actuales in-place para agregar ventas_rec_dia.
    """
    if not anteriores:
        return {
            "cambios_precio":   [],
            "cambios_stock":    [],
            "ventas_estimadas": 0,
            "ventas_rec_dia_total": None,
            "delta_dias":       None,
            "nuevos":           [i["id"] for i in actuales],
            "eliminados":       [],
        }

    delta_dias = (
        max(0.01, (fecha_actual - fecha_ant).total_seconds() / 86400)
        if fecha_ant else None
    )

    ids_actuales  = {i["id"] for i in actuales}
    ids_anteriores = set(anteriores.keys())
    cambios_precio, cambios_stock = [], []
    ventas_est = 0

    for item in actuales:
        iid  = item["id"]
        prev = anteriores.get(iid)
        if not prev:
            continue

        # Cambio de precio
        p_ant, p_act = (prev["precio"] or 0), (item["precio"] or 0)
        if p_ant != p_act:
            pct = ((p_act - p_ant) / p_ant * 100) if p_ant else 0
            cambios_precio.append({
                "id": iid, "titulo": item["titulo"],
                "antes": p_ant, "ahora": p_act, "delta%": round(pct, 1),
            })

        # Cambio de stock
        s_ant, s_act = (prev["stock"] or 0), (item["stock"] or 0)
        if s_ant != s_act:
            cambios_stock.append({
                "id": iid, "titulo": item["titulo"],
                "antes": s_ant, "ahora": s_act,
            })

        # Delta de ventas y tasa diaria reciente
        delta_v = max(0, (item["vendidos"] or 0) - (prev["vendidos"] or 0))
        ventas_est += delta_v
        if delta_dias:
            item["ventas_rec_dia"] = round(delta_v / delta_dias, 2)

    ventas_rec_dia_total = round(ventas_est / delta_dias, 2) if delta_dias else None

    return {
        "cambios_precio":        cambios_precio,
        "cambios_stock":         cambios_stock,
        "ventas_estimadas":      ventas_est,
        "ventas_rec_dia_total":  ventas_rec_dia_total,
        "delta_dias":            round(delta_dias, 1) if delta_dias else None,
        "nuevos":                list(ids_actuales - ids_anteriores),
        "eliminados":            list(ids_anteriores - ids_actuales),
    }


# ─── Excel ─────────────────────────────────────────────────────────────────────

AZUL   = "1A73E8"
VERDE  = "0F9D58"
GRIS   = "F5F5F5"
BLANCO = "FFFFFF"

def _estilo_encabezado(ws, fila: int, cols: list[str], color: str = AZUL):
    fill = PatternFill("solid", fgColor=color)
    font = Font(bold=True, color=BLANCO)
    for col, texto in enumerate(cols, start=1):
        c = ws.cell(row=fila, column=col, value=texto)
        c.fill, c.font = fill, font
        c.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[fila].height = 20

def _autowidth(ws, max_w=70):
    for col in ws.columns:
        w = max((len(str(c.value or "")) for c in col), default=8)
        ws.column_dimensions[get_column_letter(col[0].column)].width = min(w + 2, max_w)


def guardar_excel(
    items: list[dict],
    nickname: str,
    fecha: datetime,
    carpeta: Path,
    cambios: dict,
) -> Path:
    """Crea el Excel con tres hojas: Publicaciones, Por Marca, Variantes."""
    ts   = fecha.strftime("%Y%m%d_%H%M%S")
    ruta = carpeta / f"{nickname}_{ts}.xlsx"
    wb   = openpyxl.Workbook()

    # ── Hoja 1: Publicaciones ─────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Publicaciones"
    cols1 = [
        "ID", "Título", "Marca", "Tipo de Producto",
        "Precio (ARS)", "Stock Total", "Vendidos Totales",
        "Días Activo", "Ventas Hist/Día", "Ventas Rec/Día",
        "Condición", "Envío Gratis", "URL",
    ]
    _estilo_encabezado(ws1, 1, cols1)

    fill_alt = PatternFill("solid", fgColor=GRIS)
    for r, it in enumerate(items, start=2):
        fila = [
            it["id"], it["titulo"], it["marca"], it["tipo"],
            it["precio"], it["stock"], it["vendidos"],
            it["dias_activo"], it["ventas_hist_dia"],
            it["ventas_rec_dia"] if it["ventas_rec_dia"] is not None else "—",
            it["condicion"], "Sí" if it["envio_gratis"] else "No", it["permalink"],
        ]
        for c, val in enumerate(fila, start=1):
            celda = ws1.cell(row=r, column=c, value=val)
            if r % 2 == 0:
                celda.fill = fill_alt

    ws1.freeze_panes = "A2"
    _autowidth(ws1)

    # ── Hoja 2: Por Marca ─────────────────────────────────────────────────────
    ws2 = wb.create_sheet("Por Marca")
    cols2 = ["Marca", "Publicaciones", "Stock Total", "Vendidos Totales",
             "Ventas Hist/Día", "Ventas Rec/Día"]
    _estilo_encabezado(ws2, 1, cols2, VERDE)

    # Agrupar por marca
    marcas: dict[str, dict] = defaultdict(lambda: {
        "pubs": 0, "stock": 0, "vendidos": 0, "hist": 0.0, "rec": 0.0, "rec_count": 0
    })
    for it in items:
        m = it["marca"]
        marcas[m]["pubs"]     += 1
        marcas[m]["stock"]    += it["stock"]
        marcas[m]["vendidos"] += it["vendidos"]
        marcas[m]["hist"]     += it["ventas_hist_dia"]
        if it["ventas_rec_dia"] is not None:
            marcas[m]["rec"]       += it["ventas_rec_dia"]
            marcas[m]["rec_count"] += 1

    # Ordenar por ventas históricas descendente
    for r, (marca, d) in enumerate(
        sorted(marcas.items(), key=lambda x: x[1]["hist"], reverse=True), start=2
    ):
        rec = round(d["rec"], 2) if d["rec_count"] else "—"
        fila = [marca, d["pubs"], d["stock"], d["vendidos"], round(d["hist"], 2), rec]
        for c, val in enumerate(fila, start=1):
            celda = ws2.cell(row=r, column=c, value=val)
            if r % 2 == 0:
                celda.fill = fill_alt

    ws2.freeze_panes = "A2"
    _autowidth(ws2)

    # ── Hoja 3: Variantes ─────────────────────────────────────────────────────
    ws3 = wb.create_sheet("Variantes")
    cols3 = ["Item ID", "Título", "Marca", "Tipo", "Variante", "Stock Variante", "Vendidos Variante"]
    _estilo_encabezado(ws3, 1, cols3, "7B1FA2")

    r = 2
    for it in items:
        if not it["variantes"]:
            # Ítem sin variantes: una sola fila con el stock total
            ws3.append([it["id"], it["titulo"], it["marca"], it["tipo"],
                        "Sin variantes", it["stock"], it["vendidos"]])
            if r % 2 == 0:
                for c in range(1, 8):
                    ws3.cell(row=r, column=c).fill = fill_alt
            r += 1
        else:
            for v in it["variantes"]:
                fila_v = [it["id"], it["titulo"], it["marca"], it["tipo"],
                          v["descripcion"], v["stock"], v["vendidos"]]
                for c, val in enumerate(fila_v, start=1):
                    celda = ws3.cell(row=r, column=c, value=val)
                    if r % 2 == 0:
                        celda.fill = fill_alt
                r += 1

    ws3.freeze_panes = "A2"
    _autowidth(ws3)

    wb.save(ruta)
    print(f"[✓] Excel guardado: {ruta}")
    return ruta


# ─── HTML ──────────────────────────────────────────────────────────────────────

def generar_html(
    items: list[dict],
    nickname: str,
    fecha: datetime,
    cambios: dict,
    carpeta: Path,
) -> Path:
    """Genera un dashboard HTML estático que se abre en el navegador."""
    ts   = fecha.strftime("%Y%m%d_%H%M%S")
    ruta = carpeta / f"{nickname}_{ts}.html"

    total_stock    = sum(i["stock"] for i in items)
    total_vendidos = sum(i["vendidos"] for i in items)
    ventas_hist_total = sum(i["ventas_hist_dia"] for i in items)
    precio_prom    = (
        sum(i["precio"] for i in items if i["precio"]) / len(items) if items else 0
    )

    # ── Top 10 marcas por ventas históricas ──
    marcas: dict[str, dict] = defaultdict(lambda: {"pubs": 0, "hist": 0.0, "rec": 0.0, "rc": 0})
    for it in items:
        m = it["marca"]
        marcas[m]["pubs"] += 1
        marcas[m]["hist"] += it["ventas_hist_dia"]
        if it["ventas_rec_dia"] is not None:
            marcas[m]["rec"] += it["ventas_rec_dia"]
            marcas[m]["rc"]  += 1
    top_marcas = sorted(marcas.items(), key=lambda x: x[1]["hist"], reverse=True)[:10]

    filas_marcas = ""
    for i, (m, d) in enumerate(top_marcas, 1):
        rec = f"{d['rec']:.1f}" if d["rc"] else "—"
        filas_marcas += (
            f"<tr><td>{i}</td><td><strong>{m}</strong></td>"
            f"<td>{d['pubs']}</td>"
            f"<td>{d['hist']:.1f}</td>"
            f"<td>{rec}</td></tr>\n"
        )

    # ── Tabla de publicaciones (top 200 por ventas históricas) ──
    top_items = sorted(items, key=lambda x: x["ventas_hist_dia"], reverse=True)[:200]
    filas_items = ""
    for it in top_items:
        rec  = f"{it['ventas_rec_dia']:.2f}" if it["ventas_rec_dia"] is not None else "—"
        env  = "✅" if it["envio_gratis"] else "❌"
        filas_items += (
            f"<tr>"
            f"<td><a href='{it['permalink']}' target='_blank'>{it['titulo'][:60]}</a></td>"
            f"<td>{it['marca']}</td>"
            f"<td>{it['tipo']}</td>"
            f"<td>${it['precio']:,.0f}</td>"
            f"<td>{it['stock']}</td>"
            f"<td>{it['vendidos']}</td>"
            f"<td>{it['ventas_hist_dia']:.2f}</td>"
            f"<td>{rec}</td>"
            f"<td>{env}</td>"
            f"</tr>\n"
        )

    ventas_est_str = (
        f"{cambios['ventas_estimadas']} uds en {cambios['delta_dias']} días "
        f"(≈ {cambios['ventas_rec_dia_total']}/día)"
        if cambios.get("ventas_rec_dia_total") is not None
        else "Primer snapshot — sin comparación aún"
    )

    html = textwrap.dedent(f"""<!DOCTYPE html>
    <html lang="es">
    <head>
      <meta charset="UTF-8">
      <title>Reporte ML — {nickname}</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #333; }}
        header {{ background: #1A73E8; color: white; padding: 20px 32px; }}
        header h1 {{ font-size: 1.4rem; }}
        header p  {{ font-size: .85rem; opacity: .85; margin-top: 4px; }}
        .cards {{ display: flex; flex-wrap: wrap; gap: 16px; padding: 24px 32px 0; }}
        .card {{ background: white; border-radius: 10px; padding: 16px 24px;
                 box-shadow: 0 1px 4px rgba(0,0,0,.1); flex: 1; min-width: 160px; }}
        .card .val {{ font-size: 1.8rem; font-weight: 700; color: #1A73E8; }}
        .card .lbl {{ font-size: .78rem; color: #888; margin-top: 4px; }}
        section {{ margin: 24px 32px; background: white; border-radius: 10px;
                   box-shadow: 0 1px 4px rgba(0,0,0,.1); overflow: hidden; }}
        section h2 {{ background: #f8f9fa; padding: 14px 20px; font-size: 1rem;
                      border-bottom: 1px solid #e0e0e0; }}
        table {{ width: 100%; border-collapse: collapse; font-size: .82rem; }}
        th {{ background: #1A73E8; color: white; padding: 9px 12px; text-align: left; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }}
        tr:hover td {{ background: #f0f7ff; }}
        tr:nth-child(even) td {{ background: #fafafa; }}
        tr:nth-child(even):hover td {{ background: #f0f7ff; }}
        a {{ color: #1A73E8; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .chip {{ display: inline-block; padding: 2px 8px; border-radius: 12px;
                 font-size: .75rem; background: #e8f0fe; color: #1A73E8; }}
        footer {{ text-align: center; padding: 20px; font-size: .75rem; color: #aaa; }}
        input[type=text] {{ width: 100%; padding: 10px 16px; font-size: .9rem;
                            border: 1px solid #ddd; border-radius: 6px; margin: 12px 20px;
                            width: calc(100% - 40px); }}
      </style>
    </head>
    <body>
    <header>
      <h1>📊 Reporte MercadoLibre — {nickname}</h1>
      <p>Generado el {fecha.strftime('%d/%m/%Y a las %H:%M')}</p>
    </header>

    <div class="cards">
      <div class="card"><div class="val">{len(items)}</div><div class="lbl">Publicaciones activas</div></div>
      <div class="card"><div class="val">{total_stock:,}</div><div class="lbl">Stock total disponible</div></div>
      <div class="card"><div class="val">{total_vendidos:,}</div><div class="lbl">Unidades vendidas (totales)</div></div>
      <div class="card"><div class="val">{ventas_hist_total:.0f}</div><div class="lbl">Ventas históricas/día (suma)</div></div>
      <div class="card"><div class="val">${precio_prom:,.0f}</div><div class="lbl">Precio promedio ARS</div></div>
      <div class="card"><div class="val">{len(cambios.get('cambios_precio',[]))}</div><div class="lbl">Cambios de precio</div></div>
    </div>

    <section>
      <h2>🚀 Ventas estimadas vs. reporte anterior</h2>
      <p style="padding:14px 20px;font-size:.9rem;">{ventas_est_str}</p>
    </section>

    <section>
      <h2>🏷️ Top marcas por ventas históricas/día</h2>
      <table>
        <tr><th>#</th><th>Marca</th><th>Publicaciones</th><th>Ventas Hist/Día</th><th>Ventas Rec/Día</th></tr>
        {filas_marcas}
      </table>
    </section>

    <section>
      <h2>📦 Publicaciones (top 200 por ventas)</h2>
      <input type="text" id="buscar" placeholder="Filtrar por título, marca o tipo…" oninput="filtrar()">
      <table id="tabla">
        <tr>
          <th>Título</th><th>Marca</th><th>Tipo</th><th>Precio</th>
          <th>Stock</th><th>Vendidos</th><th>Hist/Día</th><th>Rec/Día</th><th>Env. Gratis</th>
        </tr>
        {filas_items}
      </table>
    </section>

    <footer>espiar_vendedor.py — AgenciaML</footer>

    <script>
      function filtrar() {{
        const q = document.getElementById('buscar').value.toLowerCase();
        document.querySelectorAll('#tabla tr:not(:first-child)').forEach(tr => {{
          tr.style.display = tr.textContent.toLowerCase().includes(q) ? '' : 'none';
        }});
      }}
    </script>
    </body>
    </html>
    """)

    ruta.write_text(html, encoding="utf-8")
    print(f"[✓] HTML guardado:  {ruta}")
    return ruta


# ─── WhatsApp ──────────────────────────────────────────────────────────────────

def armar_mensaje(nickname: str, items: list[dict], cambios: dict, fecha: datetime) -> str:
    ts = fecha.strftime("%d/%m/%Y %H:%M")

    # Top 5 marcas
    marcas: dict[str, float] = defaultdict(float)
    for it in items:
        marcas[it["marca"]] += it["ventas_hist_dia"]
    top5 = sorted(marcas.items(), key=lambda x: x[1], reverse=True)[:5]

    ventas_rec = (
        f"~{cambios['ventas_rec_dia_total']}/día en últimos {cambios['delta_dias']} días"
        if cambios.get("ventas_rec_dia_total") is not None
        else "Primer snapshot"
    )

    lineas = [
        f"📊 *Reporte ML* — {ts}",
        f"🏪 *{nickname}*",
        f"📦 Publicaciones: {len(items)} | Stock total: {sum(i['stock'] for i in items):,}",
        f"🚀 Ventas estimadas: {ventas_rec}",
        "",
        "🏷️ *Top marcas (ventas hist/día):*",
    ]
    for m, v in top5:
        lineas.append(f"  • {m}: {v:.1f}/día")

    if cambios["cambios_precio"]:
        lineas.append(f"\n💲 Cambios de precio: {len(cambios['cambios_precio'])}")
        for cp in cambios["cambios_precio"][:3]:
            signo = "▲" if cp["delta%"] > 0 else "▼"
            lineas.append(f"  {signo} {cp['titulo'][:35]}… ({cp['delta%']:+.1f}%)")

    if cambios["cambios_stock"]:
        lineas.append(f"\n📉 Cambios de stock: {len(cambios['cambios_stock'])}")

    lineas.append("\n_espiar_vendedor.py_")
    return "\n".join(lineas)


def enviar_whatsapp(mensaje: str) -> None:
    if not TWILIO_DISPONIBLE:
        print("[!] Twilio no instalado — saltando WhatsApp.")
        return
    if not all([TWILIO_SID, TWILIO_TOKEN, WA_TO]):
        print("[!] Credenciales de Twilio incompletas — saltando WhatsApp.")
        return
    client = TwilioClient(TWILIO_SID, TWILIO_TOKEN)
    msg    = client.messages.create(from_=WA_FROM, to=WA_TO, body=mensaje)
    print(f"[✓] WhatsApp enviado. SID: {msg.sid}")


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Espía publicaciones de un vendedor ML Argentina.")
    parser.add_argument("nickname", help="Nickname del vendedor")
    parser.add_argument("--carpeta", default=None, help="Subcarpeta en reportes_ml/")
    args = parser.parse_args()

    nickname_input = args.nickname.strip()
    fecha_ahora    = datetime.now()
    subcarpeta     = args.carpeta if args.carpeta else nickname_input.upper()
    reports_dir    = REPORTS_ROOT / subcarpeta
    reports_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Espiando: {nickname_input} | Carpeta: {reports_dir} ===\n")

    print("[1/6] Buscando seller_id…")
    seller_id, nickname_oficial = obtener_seller_id(nickname_input)
    print(f"      ID={seller_id}  nombre='{nickname_oficial}'")

    print("[2/6] Recuperando publicaciones activas…")
    ids = obtener_ids_publicaciones(seller_id)
    print(f"      {len(ids)} publicaciones.")
    if not ids:
        print("      Sin publicaciones activas. Saliendo.")
        sys.exit(0)

    print("[3/6] Descargando detalle de ítems…")
    items = obtener_detalle_items(ids)
    print(f"      {len(items)} ítems procesados.")

    print("[4/6] Cargando reporte anterior para comparar…")
    anteriores, fecha_ant = cargar_reporte_anterior(nickname_oficial, reports_dir)
    cambios = comparar_snapshots(items, anteriores, fecha_ahora, fecha_ant)

    print("[5/6] Guardando Excel y HTML…")
    guardar_excel(items, nickname_oficial, fecha_ahora, reports_dir, cambios)
    generar_html(items, nickname_oficial, fecha_ahora, cambios, reports_dir)

    # Resumen en consola
    ventas_hist_total = sum(i["ventas_hist_dia"] for i in items)
    print(f"""
── Resumen ──────────────────────────────────────
   Publicaciones activas : {len(items)}
   Stock total           : {sum(i['stock'] for i in items):,}
   Ventas totales (hist) : {sum(i['vendidos'] for i in items):,}
   Ventas hist/día       : {ventas_hist_total:.1f} uds/día
   Ventas rec/día        : {cambios['ventas_rec_dia_total'] or 'Primer snapshot'}
   Cambios de precio     : {len(cambios['cambios_precio'])}
   Cambios de stock      : {len(cambios['cambios_stock'])}
   Nuevas publicaciones  : {len(cambios['nuevos'])}
   Eliminadas            : {len(cambios['eliminados'])}
─────────────────────────────────────────────────""")

    print("[6/6] Enviando WhatsApp…")
    enviar_whatsapp(armar_mensaje(nickname_oficial, items, cambios, fecha_ahora))

    print("\n=== Listo ===\n")


if __name__ == "__main__":
    main()
