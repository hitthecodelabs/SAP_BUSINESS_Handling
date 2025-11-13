def export_all_itemgroups_csv(session, out_path):
    """
    Exporta todos los registros de ItemGroups a un CSV con layout OITB.

    Columns
    -------
    ItmsGrpCod : Number (código de grupo)
    ItmsGrpNam : GroupName (nombre del grupo)

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    out_path : str
        Ruta completa del archivo CSV de salida.

    Returns
    -------
    int
        Número de filas (grupos) exportadas.
    """
    try:
        total = service_count(session, "ItemGroups")
    except Exception:
        total = None

    if total is not None:
        print("ItemGroups reportados:", total)

    t0, written = time.time(), 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ItmsGrpCod", "ItmsGrpNam"])
        for r in stream_entity(session, "ItemGroups",
                               select="Number,GroupName",
                               orderby="Number"):
            w.writerow([r.get("Number", ""), r.get("GroupName", "")])
            written += 1

    print(f"✅ OITB: {written} filas -> {out_path} ({time.time()-t0:.1f}s)")
    return written

def export_all_items_csv(session, out_path):
    """
    Exporta todos los Items de SAP B1 a un CSV con layout OITM.

    Columns
    -------
    ItemCode   : código de artículo
    ItemName   : descripción
    ItmsGrpCod : código de grupo (ItemsGroupCode)
    UpdateDate : última fecha de actualización
    CreateDate : fecha de creación

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    out_path : str
        Ruta completa del archivo CSV.

    Returns
    -------
    int
        Número de ítems exportados.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    total_reportado = service_count(session, "Items")
    print("Items reportados por /Items/$count:", total_reportado)

    t0 = time.time()
    written = 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ItemCode", "ItemName", "ItmsGrpCod", "UpdateDate", "CreateDate"])

        for row in stream_entity(session, "Items",
                                 select="ItemCode,ItemName,ItemsGroupCode,UpdateDate,CreateDate",
                                 orderby="ItemCode"):
            w.writerow([
                row.get("ItemCode", ""),
                row.get("ItemName", ""),
                row.get("ItemsGroupCode", 0) or 0,
                row.get("UpdateDate", ""),
                row.get("CreateDate", ""),
            ])
            written += 1

            if written % 2000 == 0:
                dt = time.time() - t0
                print(f"  -> {written} filas en {dt:.1f}s")

    dt = time.time() - t0
    print(f"✅ Exportado {written} ítems a: {out_path}  (t={dt:.1f}s)")
    return written

def export_all_salespersons_csv(session, out_path):
    """
    Exporta todos los vendedores (SalesPersons) a un CSV con layout OSLP.

    Columns
    -------
    SlpCode : SalesEmployeeCode
    SlpName : SalesEmployeeName

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    out_path : str
        Ruta completa del CSV de salida.

    Returns
    -------
    int
        Número de vendedores exportados.
    """
    try:
        total = service_count(session, "SalesPersons")
    except Exception:
        total = None

    if total is not None:
        print("SalesPersons reportados:", total)

    t0, written = time.time(), 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["SlpCode", "SlpName"])

        for r in stream_entity(session, "SalesPersons",
                               select="SalesEmployeeCode,SalesEmployeeName",
                               orderby="SalesEmployeeCode"):
            w.writerow([r.get("SalesEmployeeCode", ""), r.get("SalesEmployeeName", "")])
            written += 1

    print(f"✅ OSLP: {written} filas -> {out_path} ({time.time()-t0:.1f}s)")
    return written

def export_all_bp_csv(session, out_path):
    """
    Exporta todos los Business Partners (clientes/proveedores) a un CSV tipo OCRD.

    Columns
    -------
    CardCode   : código interno del BP
    CardName   : nombre del BP
    LicTradNum : FederalTaxID (RUC/identificación fiscal)
    E_Mail     : EmailAddress
    Phone1     : teléfono principal
    Cellular   : celular
    Address    : reservado para dirección (se deja vacío en este flujo)
    U_BirthDate: campo UDF opcional (se deja vacío en este flujo)
    UpdateDate : fecha de última actualización
    CreateDate : fecha de creación

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    out_path : str
        Ruta del CSV.

    Returns
    -------
    int
        Número de BP exportados.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    try:
        total_reportado = service_count(session, "BusinessPartners")
    except Exception:
        total_reportado = None

    if total_reportado is not None:
        print("BP reportados por /BusinessPartners/$count:", total_reportado)

    t0 = time.time()
    written = 0

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "CardCode", "CardName", "LicTradNum", "E_Mail",
            "Phone1", "Cellular", "Address", "U_BirthDate",
            "UpdateDate", "CreateDate",
        ])

        for bp in stream_entity(
            session,
            "BusinessPartners",
            select="CardCode,CardName,FederalTaxID,EmailAddress,Phone1,Cellular,UpdateDate,CreateDate",
            orderby="CardCode",
        ):
            w.writerow([
                bp.get("CardCode", ""),
                bp.get("CardName", ""),
                bp.get("FederalTaxID", ""),
                bp.get("EmailAddress", ""),
                bp.get("Phone1", ""),
                bp.get("Cellular", ""),
                "",  # Address
                "",  # U_BirthDate
                bp.get("UpdateDate", ""),
                bp.get("CreateDate", ""),
            ])
            written += 1

            if written % 2000 == 0:
                dt = time.time() - t0
                print(f"  -> {written} BP en {dt:.1f}s")

    dt = time.time() - t0
    print(f"✅ Exportados {written} BP a: {out_path}  (t={dt:.1f}s)")
    return written

def sl_fetch_invoice_lines(session, base, doc_entry):
    """
    Recupera las líneas (DocumentLines) de una factura OINV de forma robusta.

    Estrategia:
      1) GET /Invoices(docEntry)/DocumentLines?$select=LineNum,ItemCode,ItemDescription,Quantity,UnitPrice,LineTotal
      2) GET /Invoices(docEntry)/DocumentLines  (sin $select)
      3) GET /Invoices(docEntry) y se extrae la key 'DocumentLines'.

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    base : str
        URL base del Service Layer (usual: BASE).
    doc_entry : int or str
        DocEntry de la factura a consultar.

    Returns
    -------
    list[dict]
        Lista de líneas de la factura. Cada dict contiene como mínimo LineNum, ItemCode,
        descripción, cantidad, precio y total de línea (dependiendo de la variante).
    """
    # 1) Con $select (si el Service Layer lo soporta)
    url1 = f"{base}/Invoices({doc_entry})/DocumentLines?$select=LineNum,ItemCode,ItemDescription,Quantity,UnitPrice,LineTotal"
    r = session.get(url1, timeout=120, verify=False)
    if r.ok:
        val = r.json().get("value")
        if isinstance(val, list):
            return val

    # 2) Sin $select
    url2 = f"{base}/Invoices({doc_entry})/DocumentLines"
    r = session.get(url2, timeout=120, verify=False)
    if r.ok:
        val = r.json().get("value")
        if isinstance(val, list):
            return val

    # 3) Factura completa y lectura de DocumentLines
    url3 = f"{base}/Invoices({doc_entry})"
    r = session.get(url3, timeout=120, verify=False)
    r.raise_for_status()
    obj = r.json()
    lines = obj.get("DocumentLines", [])
    return lines

def export_all_invoices_csv(session, out_path, where=None):
    """
    Exporta encabezados de factura (OINV) a CSV y devuelve la lista de facturas
    para reutilizarla en la exportación de líneas (INV1).

    Columns
    -------
    DocEntry : identificador interno de la factura
    DocNum   : número de documento (visible para el usuario)
    CardCode : código del BP
    SlpCode  : código del vendedor (SalesPersonCode)
    DocDate  : fecha de la factura
    DocTotal : total del documento
    VatSum   : total de impuestos

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    out_path : str
        Ruta del CSV de salida.
    where : str, optional
        Filtro OData, ej. "DocDate ge 2025-01-01" para limitar por fecha.

    Returns
    -------
    list[dict]
        Lista de facturas recuperadas, con los mismos campos que se exportan.
    """
    try:
        total = service_count(session, "Invoices")
    except Exception:
        total = None

    if total is not None:
        print("Invoices reportadas:", total)

    t0, written = time.time(), 0
    invoices = []
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["DocEntry", "DocNum", "CardCode", "SlpCode", "DocDate", "DocTotal", "VatSum"])

        for o in stream_entity(
            session,
            "Invoices",
            select="DocEntry,DocNum,CardCode,SalesPersonCode,DocDate,DocTotal,VatSum",
            orderby="DocEntry",
            where=where,
        ):
            w.writerow([
                o.get("DocEntry", ""),
                o.get("DocNum", ""),
                o.get("CardCode", ""),
                o.get("SalesPersonCode", ""),
                o.get("DocDate", ""),
                o.get("DocTotal", ""),
                o.get("VatSum", ""),
            ])
            invoices.append(o)
            written += 1

            if written % 2000 == 0:
                print(f"  -> {written} encabezados OINV")

    print(f"✅ OINV: {written} filas -> {out_path} ({time.time()-t0:.1f}s)")
    return invoices

def export_all_invoice_lines_csv(session, invoices, out_path, progress_every=500):
    """
    Exporta las líneas de las facturas (INV1) a partir de una lista de encabezados OINV.

    Para cada DocEntry:
      - Llama a sl_fetch_invoice_lines para recuperar DocumentLines.
      - Normaliza el campo de precio (UnitPrice o Price).
      - Escribe una fila en CSV por cada línea de factura.

    Columns
    -------
    DocEntry   : identificador interno de la factura
    LineNum    : número de línea
    ItemCode   : código de artículo
    Dscription : descripción del artículo
    Quantity   : cantidad facturada
    Price      : precio unitario
    LineTotal  : total de la línea

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada.
    invoices : list[dict]
        Lista de facturas devuelta por export_all_invoices_csv.
    out_path : str
        Ruta del CSV de salida.
    progress_every : int, optional
        Frecuencia (en número de facturas) para imprimir progreso.

    Returns
    -------
    int
        Número de líneas (rows) exportadas.
    """
    t0, written_docs, written_lines = time.time(), 0, 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["DocEntry", "LineNum", "ItemCode", "Dscription", "Quantity", "Price", "LineTotal"])

        for i, o in enumerate(invoices, 1):
            de = o.get("DocEntry")
            try:
                lines = sl_fetch_invoice_lines(session, BASE, de)
            except HTTPError as e:
                print(f"[WARN] DocEntry {de} sin líneas ({e})")
                lines = []
            except Exception as e:
                print(f"[WARN] DocEntry {de} error: {e}")
                lines = []

            for l in lines:
                price = l.get("UnitPrice", l.get("Price", ""))
                w.writerow([
                    de,
                    l.get("LineNum", ""),
                    l.get("ItemCode", ""),
                    l.get("ItemDescription", l.get("Dscription", "")),
                    l.get("Quantity", ""),
                    price,
                    l.get("LineTotal", ""),
                ])
                written_lines += 1

            written_docs += 1
            if written_docs % progress_every == 0:
                print(
                    f"  -> líneas de {written_docs}/{len(invoices)} "
                    f"facturas (acum {written_lines} líneas)"
                )

    print(f"✅ INV1: {written_lines} líneas de {written_docs} facturas -> {out_path} ({time.time()-t0:.1f}s)")
    return written_lines
