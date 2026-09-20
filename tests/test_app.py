import io
import unittest
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

    def test_rejects_invalid_format_and_level(self):
        invalid_format = self.client.post("/api/compress", data={"file": (io.BytesIO(b"hello"), "note.txt"), "level": "sedang"})
        invalid_level = self.client.post("/api/compress", data={"file": (io.BytesIO(b"hello"), "note.pdf"), "level": "custom"})
        self.assertEqual(invalid_format.status_code, 400)
        self.assertEqual(invalid_level.status_code, 400)

    def test_pdf_dependency_error_is_clear(self):
        with patch("app.ghostscript", return_value=None):
            response = self.client.post("/api/compress", data={"file": (io.BytesIO(b"%PDF-1.7\n"), "dokumen.pdf"), "level": "sedang"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Ghostscript", response.json["error"])


if __name__ == "__main__":
    unittest.main()
