"""Discover and download selected NASA PSI files into data/raw.

Uses only Python's standard library. The manifest selects investigations and
file categories; individual file URLs are discovered from PSI at runtime.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import time
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "manifest.csv"
RAW_ROOT = ROOT / "data" / "raw"
API_ROOT = "https://psi.nasa.gov/geode-py/ws/"
SITE_ROOT = "https://psi.nasa.gov/physci/repo/"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
BUFFER_SIZE = 1024 * 1024
MAX_RETRIES = 3
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def http_request(url: str, *, data: bytes | None = None, headers: dict | None = None):
    request_headers = {
        "User-Agent": USER_AGENT,
        "Origin": "https://psi.nasa.gov",
        "Referer": "https://psi.nasa.gov/physci/repo/",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, data=data, headers=request_headers)
    return urlopen(request, timeout=90)


def get_json(url: str):
    with http_request(url, headers={"Accept": "application/json"}) as response:
        return json.loads(response.read().decode("utf-8"))


def load_targets() -> list[dict]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"No encuentro {MANIFEST_PATH}")
    with MANIFEST_PATH.open(newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))
    return [row for row in rows if row.get("enabled", "").strip().lower() in {"true", "1", "yes", "si", "sí"}]


def find_value(obj, keys: set[str]):
    """Find a named value in nested PSI responses, ignoring key case."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in keys and value not in (None, ""):
                return value
        for value in obj.values():
            found = find_value(value, keys)
            if found not in (None, ""):
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = find_value(value, keys)
            if found not in (None, ""):
                return found
    return None


def investigation_record(investigation_id: str) -> dict:
    """Read the public PSI record and its current file list."""
    url = urljoin(API_ROOT, f"repo/investigations/{quote(investigation_id)}")
    record = get_json(url)
    if str(record.get("accession", "")).upper() != investigation_id.upper():
        raise RuntimeError(f"La respuesta de PSI no corresponde a {investigation_id}.")
    return record


def discover_files(target: dict, record: dict) -> list[dict]:
    """Convert the PSI record's file metadata into local manifest rows."""
    investigation_id = target["investigation_id"].strip()
    version = str(record.get("version", ""))
    results = []
    for node in record.get("added") or []:
        if not isinstance(node, dict) or not node.get("file_name"):
            continue
        if node.get("visible") is False or node.get("restricted") is True:
            continue
        remote_path = str(node.get("remote_path") or "")
        parts = PurePosixPath(remote_path).parts
        try:
            study_index = parts.index(investigation_id)
            relative_path = str(PurePosixPath(*parts[study_index + 1:]))
        except ValueError:
            relative_path = str(PurePosixPath(node.get("file_name", "")))
        try:
            size_bytes = int(float(node.get("file_size")))
        except (TypeError, ValueError):
            size_bytes = None
        results.append(
            {
                "investigation_id": investigation_id,
                "title": target.get("title", ""),
                "version": version,
                "file_version": str(node.get("version", "")),
                "relative_path": relative_path,
                "filename": str(node["file_name"]),
                "size_bytes": size_bytes,
                "source_url": str(node.get("remote_url", "")),
            }
        )
    return results


def matches_target(file: dict, target: dict) -> bool:
    path_lower = file["relative_path"].lower()
    categories = {
        part.strip().lower()
        for part in target.get("include_categories", "").split(";")
        if part.strip()
    }
    extension = Path(file["filename"].lower()).suffix
    folder = PurePosixPath(path_lower).parts[0] if PurePosixPath(path_lower).parts else ""
    category_aliases = {
        "investigation metadata files": {"metadata", "investigation metadata files"},
        "experimental table": {"experimental table", "experimentaltable"},
    }
    permitted_folders = set()
    for category in categories:
        permitted_folders.update(category_aliases.get(category, {category}))
    category_match = folder in permitted_folders
    extension_match = extension in ALLOWED_EXTENSIONS

    if not category_match:
        return False
    if not extension_match:
        return False
    size = file.get("size_bytes")
    max_mb = float(target.get("max_file_mb", "900") or 900)
    file["max_file_mb"] = max_mb
    if size is not None and size > max_mb * 1024 * 1024:
        file["status"] = "skipped_large"
        return True
    file["status"] = "selected"
    return True


def safe_destination(investigation_id: str, relative_path: str) -> Path:
    parts = [re.sub(r"[^A-Za-z0-9._ -]", "_", part) for part in PurePosixPath(relative_path).parts]
    return RAW_ROOT / investigation_id / Path(*parts)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def presigned_download_url(file: dict) -> str:
    query = urlencode(
        {
            "file": file["filename"],
            "version": file.get("file_version", ""),
            "studyVersion": file["version"],
            "redirect": "false",
        }
    )
    return urljoin(
        API_ROOT,
        f"studies/{quote(file['investigation_id'])}/download?{query}",
    )


def resolve_download_url(file: dict) -> str:
    url = presigned_download_url(file)
    with http_request(url, headers={"Accept": "text/plain, application/json, */*"}) as response:
        body = response.read().decode("utf-8", errors="replace").strip()
        if response.geturl() != url and response.geturl().startswith("https://"):
            return response.geturl()
    if body.startswith(("https://", "http://")):
        return body.strip('"')
    try:
        decoded = json.loads(body)
        if isinstance(decoded, str) and decoded.startswith(("https://", "http://")):
            return decoded
        if isinstance(decoded, dict):
            value = find_value(decoded, {"url", "downloadurl", "download_url", "presignedurl"})
            if value:
                return str(value)
    except json.JSONDecodeError:
        pass
    raise RuntimeError(f"PSI no devolvió un enlace de descarga para {file['investigation_id']}/{file['relative_path']}.")


def download_file(file: dict) -> None:
    if Path(file.get("filename", "").lower()).suffix not in ALLOWED_EXTENSIONS:
        file["status"] = "skipped_extension"
        return
    destination = safe_destination(file["investigation_id"], file["relative_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        expected_size = int(file.get("size_bytes") or 0)
    except (TypeError, ValueError):
        expected_size = 0
    if destination.exists() and expected_size and expected_size == destination.stat().st_size:
        file["status"] = "already_downloaded"
        return

    part_file = destination.with_name(destination.name + ".part")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            url = resolve_download_url(file)
            with http_request(url) as response:
                content_length = response.headers.get("Content-Length")
                max_bytes = float(file.get("max_file_mb") or 900) * 1024 * 1024
                if content_length and int(content_length) > max_bytes:
                    file["size_bytes"] = int(content_length)
                    file["status"] = "skipped_large"
                    return
                with part_file.open("wb") as output:
                    shutil.copyfileobj(response, output, length=BUFFER_SIZE)
            part_file.replace(destination)
            file["status"] = "downloaded"
            file["size_bytes"] = destination.stat().st_size
            file["local_path"] = str(destination.relative_to(ROOT))
            return
        except (HTTPError, URLError, TimeoutError, OSError, RuntimeError) as error:
            if attempt == MAX_RETRIES:
                file["status"] = "download_error"
                file["error"] = str(error)
                if part_file.exists():
                    part_file.unlink()
                return
            time.sleep(attempt * 2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Descubre y descarga archivos seleccionados de NASA PSI.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--discover-only", action="store_true", help="Crea el inventario sin descargar archivos.")
    mode.add_argument("--download-only", action="store_true", help="Descarga desde el inventario ya generado.")
    args = parser.parse_args()

    output_manifest = RAW_ROOT / "psi_download_manifest.csv"
    fields = [
        "investigation_id", "title", "version", "file_version", "relative_path", "filename",
        "size_bytes", "source_url", "max_file_mb", "status", "local_path", "error",
    ]

    if args.download_only:
        if not output_manifest.exists():
            print(f"No existe {output_manifest}. Ejecuta primero el descubrimiento.", file=sys.stderr)
            return 2
        with output_manifest.open(newline="", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))
        selected = [
            row for row in rows
            if row.get("status") in {"selected", "download_error"}
            and Path(row.get("filename", "").lower()).suffix in ALLOWED_EXTENSIONS
        ]
    else:
        targets = load_targets()
        selected = []
        for target in targets:
            investigation_id = target["investigation_id"].strip()
            title = target.get("title", "").strip()
            print(f"Buscando {investigation_id}: {title}")
            try:
                record = investigation_record(investigation_id)
                version = str(record.get("version", ""))
                discovered = discover_files(target, record)
            except Exception as error:
                print(
                    f"  No se pudo consultar PSI para {investigation_id}: {error}",
                    file=sys.stderr,
                )
                if isinstance(error, HTTPError) and error.code in {403, 404}:
                    print(
                        f"  PSI rechazó la ruta del catálogo (HTTP {error.code}). Se detiene para evitar repetir el error.",
                        file=sys.stderr,
                    )
                    return 1
                continue
            matches = [item for item in discovered if matches_target(item, target)]
            for item in matches:
                item.setdefault("status", "selected")
                item["title"] = title
            selected.extend(matches)
            downloadable = sum(item.get("status") == "selected" for item in matches)
            print(f"  {len(discovered)} archivos listados; {downloadable} seleccionados; {len(matches) - downloadable} omitidos por tamaño.")
            time.sleep(0.5)

        RAW_ROOT.mkdir(parents=True, exist_ok=True)
        write_csv(output_manifest, selected, fields)
        print(f"Inventario guardado en {output_manifest.relative_to(ROOT)} ({len(selected)} archivos).")
        if args.discover_only:
            print("No se descargó ningún archivo. Revisa el inventario y ejecuta --download-only cuando quieras.")
            return 0

    large = [row for row in selected if row.get("status") == "skipped_large"]
    if large:
        write_csv(RAW_ROOT / "psi_large_files_skipped.csv", large, fields)
        print(f"{len(large)} archivos superan el límite del manifiesto; lista guardada en data/raw/psi_large_files_skipped.csv.")

    todo = [row for row in selected if row.get("status") in {"selected", "download_error"}]
    for index, row in enumerate(todo, start=1):
        print(f"[{index}/{len(todo)}] {row['investigation_id']} — {row['relative_path']}")
        download_file(row)
        print(f"  {row.get('status')}")
        write_csv(output_manifest, selected, fields)

    write_csv(output_manifest, selected, fields)
    large = [row for row in selected if row.get("status") == "skipped_large"]
    if large:
        write_csv(RAW_ROOT / "psi_large_files_skipped.csv", large, fields)
    print(f"Descarga terminada. Manifiesto actualizado: {output_manifest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrumpido por el usuario. Los archivos completos se conservan; los parciales llevan extensión .part.", file=sys.stderr)
        raise SystemExit(130)
