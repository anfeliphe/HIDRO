"""
Parse CSV or JSON/GeoJSON file into list of parcel dicts.
Expected fields: parcel_id, land_use, population, lat, lng.
land_use must be one of: Residential, Commercial, Mixed-use.
"""
import csv
import math
from app.services.data_quality import key
import json
from io import StringIO
from typing import Any

VALID_LAND_USE = {"Residential", "Commercial", "Mixed-use"}


def _normalize_land_use(s: str) -> str:
    v = (s or "").strip()
    if not v:
        raise ValueError("El uso del predio (land_use) es obligatorio")
    # Allow common variants
    lower = v.lower()
    if lower in ("residential", "res"):
        return "Residential"
    if lower in ("commercial", "comm"):
        return "Commercial"
    if lower in ("mixed-use", "mixed_use", "mixed use", "mixed"):
        return "Mixed-use"
    if v in VALID_LAND_USE:
        return v
    raise ValueError(f"El uso debe ser residencial (Residential), comercial (Commercial) o mixto (Mixed-use); se recibió {v!r}")


def _population_from_row(row: dict[str, Any]) -> Any:
    """Resolve population from common EN/ES column names (handles mixed case in GeoJSON properties)."""
    norm: dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        key = str(k).strip().lower().replace(" ", "_").replace("ó", "o").replace("ñ", "n")
        norm[key] = v
    for candidate in (
        "population",
        "pop",
        "poblacion",
        "habitantes",
        "hab",
        "num_personas",
        "n_personas",
        "personas",
        "numhab",
        "n_hab",
        "no_habitantes",
    ):
        if candidate not in norm:
            continue
        val = norm[candidate]
        if val is not None and str(val).strip() != "":
            return val
    return None


def _row_to_parcel(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a row dict to normalized parcel dict."""
    pid = str(row.get("parcel_id") or row.get("id") or "").strip()
    if not pid:
        raise ValueError("El identificador del predio (parcel_id) es obligatorio")
    land_use = _normalize_land_use(str(row.get("land_use") or row.get("landUse") or ""))
    pop = _population_from_row(row)
    if pop is None:
        pop = row.get("population")
    if pop is None:
        pop = row.get("pop")
    try:
        population = float(pop) if pop is not None else 0
        if not math.isfinite(population) or not population.is_integer():raise ValueError()
        population=int(population)
    except (TypeError, ValueError):
        raise ValueError(f"El número de habitantes debe ser numérico; se recibió {pop!r}")
    if population < 0 or population > 10000:
        raise ValueError(f"Los habitantes deben estar entre 0 y 10000; se recibió {population}")
    try:
        lat = float(row.get("lat") or row.get("latitude") or 0)
        lng = float(row.get("lng") or row.get("lon") or row.get("longitude") or 0)
    except (TypeError, ValueError):
        raise ValueError(f"La latitud y longitud deben ser numéricas; se recibió lat={row.get('lat')}, lng={row.get('lng')}")
    if not (-90 <= lat <= 90):
        raise ValueError(f"La latitud debe estar entre −90 y 90; se recibió {lat}")
    if not (-180 <= lng <= 180):
        raise ValueError(f"La longitud debe estar entre −180 y 180; se recibió {lng}")
    if len(pid)>32:raise ValueError("El identificador admite máximo 32 caracteres en el formato anterior; no se recortará.")
    return {
        "parcel_id": pid,
        "land_use": land_use,
        "population": population,
        "lat": lat,
        "lng": lng,
    }


def parse_csv(content: str) -> list[dict[str, Any]]:
    """Parse CSV string. First row = headers. Columns: parcel_id, land_use, population, lat, lng (names case-insensitive)."""
    reader = csv.DictReader(StringIO(content))
    if reader.fieldnames and len(reader.fieldnames)!=len(set(reader.fieldnames)):raise ValueError("Encabezados duplicados.")
    rows = list(reader)
    if not rows:
        return []
    # Normalize header keys to lowercase for lookup
    normalized = []
    for row in rows:
        if None in row:raise ValueError("Hay columnas adicionales sin encabezado.")
        d = {k.strip().lower().replace(" ", "_"): v for k, v in row.items()}
        # Map common column names
        if "parcel_id" not in d and "id" in d:
            d["parcel_id"] = d["id"]
        if "land_use" not in d and "landuse" in d:
            d["land_use"] = d["landuse"]
        if "population" not in d and "pop" in d:
            d["population"] = d["pop"]
        for alt in (
            "poblacion",
            "población",
            "habitantes",
            "num_personas",
            "n_personas",
            "personas",
            "n_hab",
            "no_habitantes",
        ):
            if "population" not in d and alt in d:
                d["population"] = d[alt]
                break
        if "lat" not in d and "latitude" in d:
            d["lat"] = d["latitude"]
        if "lng" not in d and "longitude" in d:
            d["lng"] = d["longitude"]
        if "lng" not in d and "lon" in d:
            d["lng"] = d["lon"]
        normalized.append(d)
    result=[];seen=set()
    for line,r in enumerate(normalized,2):
        try:
            parsed=_row_to_parcel(r);identity=key(parsed['parcel_id'])
            if identity in seen:raise ValueError('Identificador duplicado en el archivo.')
            seen.add(identity);result.append(parsed)
        except ValueError as e:raise ValueError(f'Fila {line}: {e}')
    return result


def parse_json(content: str) -> list[dict[str, Any]]:
    """Parse JSON array or GeoJSON FeatureCollection into list of parcel dicts."""
    data = json.loads(content)
    parcels = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if item.get("type") == "Feature" and "geometry" in item and "properties" in item:
                    props = item["properties"]
                    geom = item["geometry"]
                    if geom.get("type") == "Point" and geom.get("coordinates"):
                        coords = geom["coordinates"]
                        props["lng"] = coords[0]
                        props["lat"] = coords[1]
                    parcels.append(_row_to_parcel(props))
                else:
                    parcels.append(_row_to_parcel(item))
    elif isinstance(data, dict) and data.get("type") == "FeatureCollection":
        for f in data.get("features", []):
            if f.get("type") != "Feature" or "properties" not in f:
                continue
            props = dict(f["properties"])
            geom = f.get("geometry")
            if geom and geom.get("type") == "Point" and geom.get("coordinates"):
                props["lng"] = geom["coordinates"][0]
                props["lat"] = geom["coordinates"][1]
            parcels.append(_row_to_parcel(props))
    else:
        raise ValueError("El JSON debe contener una lista de predios o una colección GeoJSON (FeatureCollection)")
    seen=set()
    for i,p in enumerate(parcels,1):
        identity=key(p['parcel_id'])
        if identity in seen:raise ValueError(f'Registro {i}: identificador duplicado.')
        seen.add(identity)
    return parcels
