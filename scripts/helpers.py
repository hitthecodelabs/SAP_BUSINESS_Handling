import os
import csv
import time
import tempfile
import requests
import urllib3
from requests import HTTPError
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE = os.environ.get("SAP_SL_BASE")
COMPANY = os.environ.get("SAP_SL_COMPANY")
USER = os.environ.get("SAP_SL_USER")
PASS = os.environ.get("SAP_SL_PASS")

VERIFY = False
PAGESIZE = 1000
TMPDIR = tempfile.gettempdir()

def sl_login():
    """
    Inicia sesión en SAP Business One Service Layer y devuelve
    una sesión HTTP autenticada para reutilizar en las demás llamadas.

    Usa las variables globales:
        BASE    -> URL base del Service Layer (ej. https://host:50000/b1s/v1)
        COMPANY -> CompanyDB
        USER    -> Usuario SAP
        PASS    -> Contraseña del usuario SAP

    Returns
    -------
    requests.Session
        Sesión autenticada contra el Service Layer. Lanza HTTPError en caso de fallo.
    """
    s = requests.Session()
    r = s.post(
        f"{BASE}/Login",
        json={"CompanyDB": COMPANY, "UserName": USER, "Password": PASS},
        timeout=60,
        verify=False,   # En producción: configurar certificados y usar verify=True
    )
    try:
        r.raise_for_status()
    except HTTPError:
        print("ERROR en Login:", r.status_code, r.text[:1000])
        raise
    return s

def login():
    """
    Variante de login pensada para procesos masivos.

    - Autentica contra el Service Layer.
    - Configura cabeceras OData para:
        * Prefer: odata.maxpagesize = PAGESIZE
        * OData-Version / OData-MaxVersion
        * B1S-CaseInsensitive = true (búsqueda case-insensitive en SAP B1)

    Returns
    -------
    requests.Session
        Sesión autenticada con cabeceras OData adecuadas para paginación masiva.
    """
    s = requests.Session()
    s.headers.update({
        "Prefer": f"odata.maxpagesize={PAGESIZE}",
        "OData-Version": "4.0",
        "OData-MaxVersion": "4.0",
        "B1S-CaseInsensitive": "true",
    })
    r = s.post(
        f"{BASE}/Login",
        json={"CompanyDB": COMPANY, "UserName": USER, "Password": PASS},
        timeout=60,
        verify=VERIFY,
    )
    r.raise_for_status()
    return s

def sl_fetch(session, entity, select=None, expand=None, where=None, pagesize=1000):
    """
    Descarga una entidad completa desde el Service Layer usando paginación simple
    basada en $top/$skip. Devuelve una lista en memoria.

    Parameters
    ----------
    session : requests.Session
        Sesión autenticada contra el Service Layer.
    entity : str
        Nombre de la entidad OData (ej. "Items", "ItemGroups", "BusinessPartners").
    select : str, optional
        Lista de campos para $select, ej. "ItemCode,ItemName".
    expand : str, optional
        Expresión para $expand, ej. "NavProp($select=FieldX,FieldY)".
    where : str, optional
        Filtro OData para $filter, ej. "DocDate ge 2025-01-01".
    pagesize : int, optional
        Tamaño de página usado en $top. Por defecto 1000.

    Returns
    -------
    list[dict]
        Lista de registros devueltos por la entidad.
    """
    data, skip = [], 0
    while True:
        params = [f"$top={pagesize}", f"$skip={skip}"]
        if select:
            params.append(f"$select={select}")
        if expand:
            params.append(f"$expand={expand}")
        if where:
            params.append(f"$filter={where}")
        url = f"{BASE}/{entity}?" + "&".join(params)

        r = session.get(url, timeout=120, verify=False)
        if r.status_code >= 400:
            print("ERROR", r.status_code, "en", entity, "=>", r.text[:1000])
            r.raise_for_status()

        chunk = r.json().get("value", [])
        if not chunk:
            break

        data.extend(chunk)
        if len(chunk) < pagesize:
            break

        skip += pagesize

    return data

def save_csv(path, rows, headers):
    """
    Escribe una lista de diccionarios en un archivo CSV con encabezados fijos.

    Parameters
    ----------
    path : str
        Ruta completa del archivo de salida.
    rows : Iterable[dict]
        Cada dict representa una fila. Las claves deben coincidir con `headers`.
    headers : list[str]
        Lista de nombres de columnas en el orden deseado.

    Side Effects
    ------------
    Crea el directorio padre de `path` si no existe y sobrescribe el archivo.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow({h: r.get(h, "") for h in headers})
