import io
import unittest
import zipfile
from unittest.mock import patch

from PIL import Image

from app import app


class CompressionFlowTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def image_bytes(self, size=(1800, 1200), mode="RGB"):
        image = Image.new(mode, size, (100, 150, 200) if mode == "RGB" else (100, 150, 200, 130))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    def test_image_compression_and_download_headers(self):
        original = self.image_bytes()
        response = self.client.post("/api/compress", data={"file": (io.BytesIO(original), "foto.png"), "level": "kuat"})
        self.assertEqual(response.status_code, 200)
        result = response.get_data()
        self.assertEqual(response.headers["X-Original-Size"], str(len(original)))
        self.assertEqual(response.headers["X-Result-Size"], str(len(result)))
        self.assertTrue(result.startswith((b"\xff\xd8", b"\x89PNG")))
        self.assertLessEqual(len(result), len(original))

    def test_transparent_image_becomes_jpeg(self):
        response = self.client.post("/api/compress", data={"file": (io.BytesIO(self.image_bytes(mode="RGBA")), "logo.png"), "level": "kuat"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(response.get_data())).mode, "RGB")

    def test_generic_format_is_returned_as_zip(self):
        response = self.client.post("/api/compress", data={"file": (io.BytesIO(b"hello world" * 100), "note.txt"), "level": "sedang"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "application/zip")
        with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
            self.assertEqual(archive.read("note.txt"), b"hello world" * 100)

    def test_office_document_is_compressed_without_external_app(self):
        source = io.BytesIO()
        with zipfile.ZipFile(source, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("[Content_Types].xml", "<Types>" + "document " * 5000 + "</Types>")
            archive.writestr("word/document.xml", "<document>" + "content " * 5000 + "</document>")
        original = source.getvalue()
        response = self.client.post(
            "/api/compress",
            data={"file": (io.BytesIO(original), "laporan.docx"), "level": "kuat"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.mimetype,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        self.assertLess(len(response.get_data()), len(original))
        with zipfile.ZipFile(io.BytesIO(response.get_data())) as archive:
            self.assertIn("word/document.xml", archive.namelist())

    def test_rejects_invalid_level(self):
        invalid_level = self.client.post("/api/compress", data={"file": (io.BytesIO(b"hello"), "note.pdf"), "level": "custom"})
        self.assertEqual(invalid_level.status_code, 400)

    def test_pdf_dependency_error_is_clear(self):
        with patch("app.ghostscript", return_value=None):
            response = self.client.post("/api/compress", data={"file": (io.BytesIO(b"%PDF-1.7\n"), "dokumen.pdf"), "level": "sedang"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ghostscript", response.json["error"])


if __name__ == "__main__":
    unittest.main()
