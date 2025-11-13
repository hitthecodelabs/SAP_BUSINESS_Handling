def req_get(session, url, timeout=120, **kwargs):
    """
    Ejecuta un GET con reintentos ante errores temporales del Service Layer.

    Se aplican reintentos con backoff exponencial para los códigos:
    429, 500, 502, 503, 504.

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    url : str
        URL completa a invocar.
    timeout : int, optional
        Timeout en segundos por intento. Por defecto 120.
    **kwargs :
        Parámetros adicionales que se pasan a session.get (params, headers, etc.).

    Returns
    -------
    requests.Response
        Respuesta exitosa con status_code < 400.

    Raises
    ------
    requests.HTTPError
        Si luego de los reintentos la respuesta sigue siendo de error.
    """
    for attempt in range(4):
        r = session.get(url, timeout=timeout, verify=VERIFY, **kwargs)
        if r.status_code < 400:
            return r

        if r.status_code in (429, 500, 502, 503, 504):
            # Errores transitorios: backoff exponencial
            time.sleep(1.5 * (2 ** attempt))
            continue

        # Otros errores: no tiene sentido reintentar
        r.raise_for_status()

    # Si se llega aquí, todos los intentos fallaron
    r.raise_for_status()

def stream_entity(session, entity, select=None, where=None, orderby=None):
    """
    Generador que recorre TODAS las páginas de una entidad OData.

    Usa dos estrategias de paginación:
      1) Si el Service Layer devuelve @odata.nextLink, se sigue ese enlace.
      2) Si no hay nextLink, se reconstruye manualmente $skip += len(value).

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    entity : str
        Nombre de la entidad OData, ej. "Items", "BusinessPartners", "Invoices".
    select : str, optional
        Campos para $select.
    where : str, optional
        Filtro $filter.
    orderby : str, optional
        Orden para $orderby.

    Yields
    ------
    dict
        Registro devuelto por el servicio.
    """
    qs = []
    if select:
        qs.append(f"$select={select}")
    if where:
        qs.append(f"$filter={where}")
    if orderby:
        qs.append(f"$orderby={orderby}")
    qs.append(f"$top={PAGESIZE}")
    qs.append("$skip=0")

    url = f"{BASE}/{entity}?" + "&".join(qs)
    total = 0

    while True:
        r = req_get(session, url)
        js = r.json()
        rows = js.get("value", [])

        for row in rows:
            yield row

        total += len(rows)

        # 1) Intentar nextLink
        nextlink = js.get("@odata.nextLink") or js.get("odata.nextLink") or js.get("nextLink")
        if nextlink:
            url = nextlink if nextlink.startswith("http") else (BASE.rstrip("/") + "/" + nextlink.lstrip("/"))
            continue

        # 2) Sin nextLink, usar skip
        if not rows:
            break

        base_path, params = url.split("?", 1)
        new_params = []
        for p in params.split("&"):
            if p.startswith("$skip="):
                try:
                    current = int(p.split("=")[1])
                except Exception:
                    current = 0
                p = f"$skip={current + len(rows)}"
            new_params.append(p)

        url = base_path + "?" + "&".join(new_params)

def service_count(session, entity):
    """
    Obtiene el conteo total de registros de una entidad, usando /$count.

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    entity : str
        Nombre de la entidad (ej. "Items", "Invoices").

    Returns
    -------
    int or None
        Conteo total de la entidad, o None si la respuesta no se pudo parsear.
    """
    r = req_get(session, f"{BASE}/{entity}/$count")
    try:
        return int(r.text)
    except Exception:
        return None
