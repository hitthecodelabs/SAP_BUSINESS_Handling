def odata_escape_literal(val: str) -> str:
    """
    Escapa un literal de texto para ser usado en filtros OData.

    Reemplaza comillas simples ' por '' para evitar errores de sintaxis OData.

    Parameters
    ----------
    val : str
        Literal original.

    Returns
    -------
    str
        Literal con comillas simples duplicadas.
    """
    return (val or "").replace("'", "''")

def stream_items(s):
    """
    Genera todos los códigos de artículo (ItemCode) existentes en SAP B1,
    sin repeticiones, usando paginación.

    Parameters
    ----------
    s : requests.Session
        Sesión autenticada.

    Yields
    ------
    str
        ItemCode único.
    """
    url = f"{BASE}/Items?$select=ItemCode&$top={PAGESIZE}&$skip=0&$orderby=ItemCode"
    total = 0
    seen = set()

    while True:
        js = req_get(s, url).json()
        rows = js.get("value", [])

        for r in rows:
            code = r.get("ItemCode")
            if code and code not in seen:
                seen.add(code)
                yield code

        total += len(rows)

        nextlink = js.get("@odata.nextLink") or js.get("odata.nextLink") or js.get("nextLink")
        if nextlink:
            url = nextlink if nextlink.startswith("http") else (BASE.rstrip("/") + "/" + nextlink.lstrip("/"))
            continue

        if not rows:
            break

        base_path, params = url.split("?", 1)
        parts = []
        for p in params.split("&"):
            if p.startswith("$skip="):
                try:
                    cur = int(p.split("=")[1])
                except Exception:
                    cur = 0
                p = f"$skip={cur + len(rows)}"
            parts.append(p)
        url = base_path + "?" + "&".join(parts)

def fetch_item_price(s, code, pricelist_no):
    """
    Obtiene el precio de un ítem en una lista de precios específica.

    Estrategia:
      1) GET /Items('ItemCode') y lectura de la colección ItemPrices.
      2) Si falla por caracteres especiales o 404, fallback a:
         GET /Items?$filter=ItemCode eq '...'

    Parameters
    ----------
    s : requests.Session
        Sesión autenticada.
    code : str
        ItemCode del artículo.
    pricelist_no : int
        Número de lista de precios (PriceList).

    Returns
    -------
    tuple[str or None, float or None, str or None]
        (ItemCode, Price, Currency). Si no se encuentra precio, Price y Currency
        pueden ser None.
    """
    if not code:
        return (None, None, None)

    # 1) Intento por clave directa
    try:
        key_literal = quote(odata_escape_literal(code), safe="")
        js = req_get(s, f"{BASE}/Items('{key_literal}')").json()
        ip = js.get("ItemPrices") or []
        if isinstance(ip, dict):
            ip = [ip]
        for pi in ip:
            try:
                if int(pi.get("PriceList", -1)) == int(pricelist_no):
                    return (code, pi.get("Price"), pi.get("Currency"))
            except Exception:
                continue
    except requests.HTTPError:
        # Sólo aplicar fallback, no relanzar para no bloquear el pipeline
        pass
    except Exception:
        pass

    # 2) Fallback con $filter
    try:
        lit = odata_escape_literal(code)
        params = {
            "$select": "ItemCode,ItemPrices",
            "$filter": f"ItemCode eq '{lit}'",
        }
        r = req_get(s, f"{BASE}/Items", params=params)
        vals = r.json().get("value", [])
        if vals:
            ip = vals[0].get("ItemPrices") or []
            if isinstance(ip, dict):
                ip = [ip]
            for pi in ip:
                try:
                    if int(pi.get("PriceList", -1)) == int(pricelist_no):
                        return (code, pi.get("Price"), pi.get("Currency"))
                except Exception:
                    continue
    except Exception:
        pass

    # 3) Sin precio
    return (code, None, None)

def export_prices_csv(s, pricelist_no, out_path, max_workers=16, progress_every=2000):
    """
    Exporta los precios de todos los ítems para una lista de precios específica.

    - Recorre todos los ItemCode via stream_items.
    - Usa concurrencia (ThreadPoolExecutor) para consultar precios en paralelo.
    - Escribe un CSV con un registro por ítem, para la lista indicada.

    Columns
    -------
    ItemCode : código de artículo
    PriceList: número de lista de precios
    Price    : precio en esa lista
    Currency : moneda asociada

    Parameters
    ----------
    s : requests.Session
        Sesión autenticada.
    pricelist_no : int
        Número de la lista de precios a exportar.
    out_path : str
        Ruta del CSV de salida.
    max_workers : int, optional
        Número de workers en el ThreadPoolExecutor.
    progress_every : int, optional
        Cada cuántos ítems escribir una línea de progreso.

    Returns
    -------
    str
        Ruta del archivo CSV generado.
    """
    codes = list(stream_items(s))
    t0 = time.time()
    wrote = 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ItemCode", "PriceList", "Price", "Currency"])

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(fetch_item_price, s, c, pricelist_no) for c in codes]

            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    code, price, curr = fut.result()
                except Exception:
                    # No bloquear por un ítem aislado
                    continue

                if code is None:
                    continue

                w.writerow([
                    code,
                    pricelist_no,
                    price if price is not None else "",
                    curr or "",
                ])
                wrote += 1

                if wrote % progress_every == 0:
                    print(f"  -> {wrote} items procesados en {time.time()-t0:.1f}s")

    print(f"✅ Precios exportados: {wrote} filas -> {out_path}")
    return out_path
