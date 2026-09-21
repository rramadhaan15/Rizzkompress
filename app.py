"""Rizzkompress: private, local document compression."""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename


MAX_FILE_SIZE = 200 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}
OFFICE_EXTENSIONS = {".docx", ".pptx", ".xlsx"}
OFFICE_MIME_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
LEVELS = {
    "kuat": {"pdf": "/screen", "quality": 52, "max_side": 1600, "zip": 9},
    "sedang": {"pdf": "/ebook", "quality": 72, "max_side": 2400, "zip": 6},
    "ringan": {"pdf": "/printer", "quality": 86, "max_side": 3600, "zip": 3},
}

app = Flask(__name__)
# Leave room for multipart framing; the actual file limit is checked while streaming.
app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE + CHUNK_SIZE
app.json.ensure_ascii = False


class CompressionError(Exception):
    pass


def find_executable(*names: str) -> str | None:
    local_tools = Path(__file__).resolve().parent / ".tools"
    for name in names:
        candidates = list(local_tools.glob(f"ghostscript/**/{name}.exe"))
        candidates += list(local_tools.glob(f"libreoffice/**/{name}.exe"))
        if candidates:
            return str(candidates[-1])
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    if os.name == "nt":
        roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")]
        for root in filter(None, roots):
            for name in names:
                candidates = list((Path(root) / "gs").glob(f"gs*/bin/{name}.exe"))
                candidates = [candidate for candidate in candidates if candidate.is_file()]
                if candidates:
                    return str(candidates[-1])
    return None


def ghostscript() -> str | None:
    return find_executable("gswin64c", "gswin32c", "gs")


def run_command(command: list[str], label: str, timeout: int = 180) -> None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        raise CompressionError(f"{label} terlalu lama memproses file. Coba file yang lebih kecil.") from exc
    except OSError as exc:
        raise CompressionError(f"{label} tidak dapat dijalankan: {exc}") from exc
    if result.returncode:
        details = (result.stderr or result.stdout).strip().splitlines()
        reason = details[-1][:250] if details else "file mungkin rusak atau tidak didukung"
        raise CompressionError(f"{label} gagal memproses file: {reason}")


def compress_pdf(source: Path, destination: Path, level: str) -> None:
    executable = ghostscript()
    if not executable:
        raise CompressionError("Ghostscript belum terpasang. Instal Ghostscript untuk mengompresi PDF.")
    run_command(
        [
            executable,
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            f"-dPDFSETTINGS={LEVELS[level]['pdf']}",
            f"-sOutputFile={destination}",
            str(source),
        ],
        "Ghostscript",
    )
    if not destination.is_file() or destination.stat().st_size == 0:
        raise CompressionError("Ghostscript tidak menghasilkan PDF. Periksa apakah file masukan valid.")


def compress_image(source: Path, destination: Path, level: str) -> None:
    try:
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened)
            image.thumbnail((LEVELS[level]["max_side"],) * 2, Image.Resampling.LANCZOS)
            # JPEG has no alpha channel; use white for transparent areas.
            if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
                rgba = image.convert("RGBA")
                canvas = Image.new("RGB", rgba.size, "white")
                canvas.paste(rgba, mask=rgba.getchannel("A"))
                image = canvas
            else:
                image = image.convert("RGB")
            image.save(destination, "JPEG", quality=LEVELS[level]["quality"], optimize=True, progressive=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise CompressionError("Gambar tidak dapat dibuka atau formatnya tidak valid.") from exc


def optimize_office_image(data: bytes, suffix: str, level: str) -> bytes:
    """Reduce embedded Office images while retaining their original format."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            image.thumbnail((LEVELS[level]["max_side"],) * 2, Image.Resampling.LANCZOS)
            output = io.BytesIO()
            if suffix in {".jpg", ".jpeg"}:
                image.convert("RGB").save(
                    output, "JPEG", quality=LEVELS[level]["quality"], optimize=True, progressive=True
                )
            elif suffix == ".png":
                image.save(output, "PNG", optimize=True, compress_level=LEVELS[level]["zip"])
            elif suffix == ".webp":
                image.save(output, "WEBP", quality=LEVELS[level]["quality"], method=6)
            else:
                return data
            optimized = output.getvalue()
            return optimized if len(optimized) < len(data) else data
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return data


def compress_office(source: Path, destination: Path, level: str) -> None:
    """Repack an Open XML Office document and optimize its embedded images."""
    media_roots = ("word/media/", "ppt/media/", "xl/media/")
    try:
        with zipfile.ZipFile(source, "r") as incoming:
            entries = incoming.infolist()
            total_uncompressed = sum(entry.file_size for entry in entries)
            if len(entries) > 10000 or total_uncompressed > 1024 * 1024 * 1024:
                raise CompressionError("Dokumen Office terlalu kompleks untuk diproses dengan aman.")
            with zipfile.ZipFile(
                destination,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=LEVELS[level]["zip"],
            ) as outgoing:
                for entry in entries:
                    data = incoming.read(entry)
                    normalized = entry.filename.lower()
                    if normalized.startswith(media_roots):
                        data = optimize_office_image(data, Path(normalized).suffix, level)
                    entry.compress_type = zipfile.ZIP_DEFLATED
                    entry._compresslevel = LEVELS[level]["zip"]
                    outgoing.writestr(entry, data)
    except CompressionError:
        raise
    except (OSError, RuntimeError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
        raise CompressionError("Dokumen Office rusak atau tidak dapat dibuka.") from exc


def compress_generic(source: Path, destination: Path, original_name: str, level: str) -> None:
    try:
        with zipfile.ZipFile(
            destination,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=LEVELS[level]["zip"],
        ) as archive:
            archive.write(source, arcname=original_name)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise CompressionError("File tidak dapat dibuat menjadi arsip ZIP.") from exc


def save_upload(upload, destination: Path) -> int:
    total = 0
    with destination.open("wb") as target:
        while chunk := upload.stream.read(CHUNK_SIZE):
            total += len(chunk)
            if total > MAX_FILE_SIZE:
                raise CompressionError("Ukuran file melebihi batas 200 MB.")
            target.write(chunk)
    if not total:
        raise CompressionError("File kosong. Pilih file lain.")
    return total


def process_file(
    source: Path,
    filename: str,
    extension: str,
    level: str,
    folder: Path,
    original_size: int,
) -> tuple[Path, str]:
    folder.mkdir(parents=True, exist_ok=True)
    if extension == ".pdf":
        with source.open("rb") as document:
            if b"%PDF-" not in document.read(1024):
                raise CompressionError("File PDF tidak valid.")
        output = folder / "compressed.pdf"
        compress_pdf(source, output, level)
        result = output if output.stat().st_size < original_size else source
        result_name = f"{Path(filename).stem}-kompres.pdf" if result == output else filename
    elif extension in IMAGE_EXTENSIONS:
        output = folder / "compressed.jpg"
        compress_image(source, output, level)
        result = output if output.stat().st_size < original_size else source
        result_name = f"{Path(filename).stem}-kompres.jpg" if result == output else filename
    elif extension in OFFICE_EXTENSIONS:
        output = folder / f"compressed{extension}"
        compress_office(source, output, level)
        result = output if output.stat().st_size < original_size else source
        result_name = f"{Path(filename).stem}-kompres{extension}" if result == output else filename
    else:
        output = folder / "compressed.zip"
        compress_generic(source, output, filename, level)
        result = output
        result_name = f"{Path(filename).stem or 'file'}-kompres.zip"
    return result, result_name


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify({"ghostscript": bool(ghostscript())})


@app.errorhandler(RequestEntityTooLarge)
def file_too_large(_error):
    return jsonify({"error": "Ukuran file melebihi batas 200 MB."}), 413


@app.post("/api/estimate")
def estimate():
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return jsonify({"error": "Pilih file yang ingin dikompres."}), 400
    filename = secure_filename(upload.filename)
    if not filename:
        return jsonify({"error": "Nama file tidak valid. Ubah nama file lalu coba lagi."}), 400
    extension = Path(filename).suffix.lower()
    with tempfile.TemporaryDirectory(prefix="rizzkompress-estimate-") as temporary:
        folder = Path(temporary)
        try:
            source = folder / f"source{extension}"
            original_size = save_upload(upload, source)
            estimates = {}
            for level in LEVELS:
                result, _ = process_file(
                    source, filename, extension, level, folder / level, original_size
                )
                result_size = result.stat().st_size
                estimates[level] = {
                    "size": result_size,
                    "saved_percent": round((1 - result_size / original_size) * 100, 1),
                    "used_original": result == source,
                }
            return jsonify({"original_size": original_size, "estimates": estimates})
        except CompressionError as exc:
            return jsonify({"error": str(exc)}), 400
        except Exception:
            app.logger.exception("Unexpected estimate failure")
            return jsonify({"error": "Ukuran hasil tidak dapat dihitung. Coba file lain."}), 500


@app.post("/api/compress")
def compress():
    upload = request.files.get("file")
    level = request.form.get("level", "sedang")
    if not upload or not upload.filename:
        return jsonify({"error": "Pilih file yang ingin dikompres."}), 400
    if level not in LEVELS:
        return jsonify({"error": "Tingkat kompresi tidak valid."}), 400

    filename = secure_filename(upload.filename)
    extension = Path(filename).suffix.lower()
    if not filename:
        return jsonify({"error": "Nama file tidak valid. Ubah nama file lalu coba lagi."}), 400

    temporary = tempfile.TemporaryDirectory(prefix="rizzkompress-")
    folder = Path(temporary.name)
    try:
        source = folder / f"source{extension}"
        original_size = save_upload(upload, source)
        result, result_name = process_file(
            source, filename, extension, level, folder / "result", original_size
        )

        result_size = result.stat().st_size
        mime_type = (
            "application/pdf"
            if result.suffix == ".pdf"
            else "image/jpeg"
            if result.suffix in {".jpg", ".jpeg"}
            else "application/zip"
            if result.suffix == ".zip"
            else OFFICE_MIME_TYPES[result.suffix]
            if result.suffix in OFFICE_MIME_TYPES
            else "application/octet-stream"
        )
        response = Response(stream_file(result, temporary), mimetype=mime_type)
        response.headers["Content-Length"] = str(result_size)
        response.headers["Content-Disposition"] = f"attachment; filename=download{result.suffix}; filename*=UTF-8''{quote(result_name)}"
        response.headers["X-Original-Size"] = str(original_size)
        response.headers["X-Result-Size"] = str(result_size)
        response.headers["X-Result-Name"] = quote(result_name)
        response.headers["X-Used-Original"] = "true" if result == source else "false"
        response.headers["Cache-Control"] = "no-store"
        return response
    except CompressionError as exc:
        temporary.cleanup()
        return jsonify({"error": str(exc)}), 400
    except Exception:
        temporary.cleanup()
        app.logger.exception("Unexpected compression failure")
        return jsonify({"error": "Terjadi kesalahan saat memproses file. Coba file lain."}), 500


def stream_file(path: Path, temporary: tempfile.TemporaryDirectory):
    try:
        with path.open("rb") as file:
            while chunk := file.read(CHUNK_SIZE):
                yield chunk
    finally:
        temporary.cleanup()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
