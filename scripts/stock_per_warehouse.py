def get_page(endpoint, params=None):
    """
    Ejecuta un GET contra el Service Layer, normalizando el endpoint
    si proviene de odata.nextLink en forma absoluta.

    Parameters
    ----------
    endpoint : str
        Ruta relativa (ej. "Items") o un nextLink completo.
    params : dict, optional
        Parámetros de query adicionales para la llamada inicial.

    Returns
    -------
    dict
        JSON decodificado de la respuesta.
    """
    if endpoint.startswith("http"):
        endpoint = endpoint.split("/b1s/v1/")[-1]

    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    r = session.get(url, params=params, timeout=TIMEOUT_S, verify=VERIFY_SSL)
    r.raise_for_status()
    return r.json()

def safe_float(x, default=0.0):
    """
    Convierte un valor arbitrario a float de forma segura.

    - Si x es None o no convertible, devuelve `default`.
    - Acepta strings con espacios y separadores estándar.

    Parameters
    ----------
    x : Any
        Valor a convertir.
    default : float, optional
        Valor por defecto si la conversión falla.

    Returns
    -------
    float
        Valor convertido o default.
    """
    try:
        if x is None:
            return float(default)
        return float(str(x).strip())
    except Exception:
        return float(default)


def main():
    """
    Exporta stock por bodega y stock total de todos los ítems de inventario.

    Flujo:
      1) Inicia sesión en el Service Layer (sl_login).
      2) Recorre Items con:
           - InventoryItem eq 'tYES'
           - QuantityOnStock gt 0
      3) Por cada Item, procesa ItemWarehouseInfoCollection:
           - Aplica WAREHOUSE_FILTER (si está definido).
           - Escribe detalles en sl_stock_por_bodega.csv
           - Acumula totales por ItemCode en sl_stock_totales.csv
      4) Imprime progreso cada N ítems procesados.

    Utiliza las constantes:
      OUT_BODEGA : nombre del CSV por bodega.
      OUT_TOTAL  : nombre del CSV de totales.

    Returns
    -------
    None
        (Efecto colateral: genera los archivos CSV mencionados).
    """
    # 1) Login
    sl_login()

    # 2) Archivos de salida
    fb = open(OUT_BODEGA, "w", newline="", encoding="utf-8")
    ft = open(OUT_TOTAL, "w", newline="", encoding="utf-8")
    wb = csv.writer(fb)
    wt = csv.writer(ft)

    wb.writerow(["ItemCode", "Warehouse", "InStock"])
    wt.writerow(["ItemCode", "InStockTotal"])

    totales = {}
    count = 0
    escritos = 0

    endpoint = "Items"
    params = {
        "$select": "ItemCode,ItemName,InventoryItem,QuantityOnStock,ItemWarehouseInfoCollection",
        "$filter": "InventoryItem eq 'tYES' and QuantityOnStock gt 0",
    }

    while endpoint:
        data = get_page(endpoint, params=params)
        endpoint, params = None, None  # params sólo se usan en la primera página

        items = data.get("value", [])
        for it in items:
            code = (it.get("ItemCode") or "").strip()
            iwc = it.get("ItemWarehouseInfoCollection") or []

            if not iwc:
                continue

            item_total = 0.0
            for row in iwc:
                whs = (row.get("WarehouseCode") or "").strip()
                stock = safe_float(row.get("InStock"))

                if WAREHOUSE_FILTER and whs != WAREHOUSE_FILTER:
                    continue
                if stock <= 0:
                    continue

                wb.writerow([code, whs, f"{stock:.4f}"])
                escritos += 1
                item_total += stock

            if item_total > 0:
                totales[code] = totales.get(code, 0.0) + item_total

            count += 1
            if count % 200 == 0:
                print(f"- Procesados {count} ítems... (filas CSV por bodega: {escritos})")
                time.sleep(0.05)

        nxt = data.get("odata.nextLink")
        if nxt:
            endpoint = nxt
        else:
            break

    # 4) Totales
    for code, total in totales.items():
        wt.writerow([code, f"{total:.4f}"])

    fb.close()
    ft.close()

    print(f"OK. CSVs generados: {OUT_BODEGA} y {OUT_TOTAL}")
    if WAREHOUSE_FILTER:
        print(f"(Filtrado por bodega {WAREHOUSE_FILTER})")

