"""
PDF-Service: Erstellt durchsuchbare PDFs aus Bildern + OCR-Text.
Strategie: img2pdf (Bild-Layer) + reportlab (unsichtbarer Text-Layer) + pypdf (merge).
Fallback: Pillow-basiertes PDF (image only) wenn img2pdf/reportlab fehlen.
"""

import io
import logging
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class PdfService:
    """Erstellt durchsuchbare PDFs aus Bild + OCR-Ergebnis."""

    def create_searchable_pdf(
        self,
        image_bytes: bytes,
        ocr_text: str,
        words_data: Optional[dict],
        filename: str,
        save_local: bool = True,
    ) -> Path:
        """
        Erstellt ein durchsuchbares PDF.

        Args:
            image_bytes: Originalbild als Bytes
            ocr_text: Extrahierter Volltext
            words_data: pytesseract image_to_data Output (für Wort-Koordinaten) oder None
            filename: Dateiname (YYYY-MM-DD_Typ.pdf)
            save_local: Datei in data/scans/ speichern

        Returns:
            Path zum erstellten PDF
        """
        save_dir = settings.SCANS_DIR
        save_dir.mkdir(parents=True, exist_ok=True)
        output_path = save_dir / filename

        pdf_bytes = self._build_pdf(image_bytes, ocr_text, words_data)

        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"PDF erstellt: {output_path} ({len(pdf_bytes)} Bytes)")
        return output_path

    def _build_pdf(
        self,
        image_bytes: bytes,
        ocr_text: str,
        words_data: Optional[dict],
    ) -> bytes:
        """Versucht img2pdf + reportlab + pypdf, fällt auf Pillow zurück."""
        try:
            return self._build_searchable_pdf(image_bytes, ocr_text, words_data)
        except ImportError as e:
            logger.warning(f"Dependency fehlt ({e}), nutze Pillow-Fallback.")
            return self._build_pillow_pdf(image_bytes)
        except Exception as e:
            logger.error(f"PDF-Erstellung fehlgeschlagen ({e}), nutze Pillow-Fallback.")
            return self._build_pillow_pdf(image_bytes)

    def _build_searchable_pdf(
        self,
        image_bytes: bytes,
        ocr_text: str,
        words_data: Optional[dict],
    ) -> bytes:
        import img2pdf
        from pypdf import PdfWriter, PdfReader

        # Schritt 1: Bild → PDF (lossless via img2pdf)
        image_pdf_bytes = img2pdf.convert(image_bytes)
        image_pdf = PdfReader(io.BytesIO(image_pdf_bytes))
        page = image_pdf.pages[0]

        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)

        # Schritt 2: Text-Layer mit reportlab
        text_pdf_bytes = self._build_text_layer(ocr_text, words_data, page_width, page_height, image_bytes)

        # Schritt 3: Beide Layer zusammenführen
        writer = PdfWriter()
        text_pdf = PdfReader(io.BytesIO(text_pdf_bytes))
        image_page = image_pdf.pages[0]
        text_page = text_pdf.pages[0]

        # Text-Layer über Bild-Layer legen
        image_page.merge_page(text_page)
        writer.add_page(image_page)

        output = io.BytesIO()
        writer.write(output)
        return output.getvalue()

    def _build_text_layer(
        self,
        ocr_text: str,
        words_data: Optional[dict],
        page_width: float,
        page_height: float,
        image_bytes: bytes,
    ) -> bytes:
        """Erstellt unsichtbaren Text-Layer als PDF-Bytes."""
        from reportlab.pdfgen import canvas
        from reportlab.lib.colors import white

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=(page_width, page_height))

        # Schrift: unsichtbar (weiß auf weißem Hintergrund)
        c.setFillColor(white)
        c.setStrokeColor(white)

        if words_data and self._has_word_positions(words_data):
            self._add_words_with_positions(c, words_data, page_width, page_height, image_bytes)
        else:
            # Nur Volltext, links-oben platziert (unsichtbar)
            self._add_plain_text(c, ocr_text, page_width, page_height)

        c.save()
        packet.seek(0)
        return packet.getvalue()

    def _has_word_positions(self, words_data: dict) -> bool:
        return words_data and "text" in words_data and "left" in words_data and len(words_data["text"]) > 0

    def _add_words_with_positions(
        self,
        c,
        words_data: dict,
        page_width: float,
        page_height: float,
        image_bytes: bytes,
    ):
        """Platziert Wörter an pytesseract-Koordinaten (skaliert auf PDF-Größe)."""
        try:
            from PIL import Image as PILImage

            img = PILImage.open(io.BytesIO(image_bytes))
            img_width, img_height = img.size
        except Exception:
            img_width, img_height = page_width, page_height

        scale_x = page_width / img_width
        scale_y = page_height / img_height

        texts = words_data.get("text", [])
        lefts = words_data.get("left", [])
        tops = words_data.get("top", [])
        _widths = words_data.get("width", [])
        heights = words_data.get("height", [])
        confs = words_data.get("conf", [])

        for i, word in enumerate(texts):
            if not word or not word.strip():
                continue
            conf = confs[i] if i < len(confs) else -1
            if conf == -1:
                continue

            x = lefts[i] * scale_x
            h = heights[i] * scale_y if i < len(heights) else 12
            # PDF-Koordinaten: Y von unten (reportlab) vs. oben (Tesseract)
            y = page_height - (tops[i] * scale_y) - h

            font_size = max(h * 0.8, 6)
            try:
                c.setFont("Helvetica", font_size)
                c.drawString(x, y, word)
            except Exception:
                pass

    def _add_plain_text(self, c, text: str, page_width: float, page_height: float):
        """Fügt Volltext als unsichtbaren Block oben-links ein."""

        c.setFont("Helvetica", 8)
        y = page_height - 20
        for line in text.split("\n"):
            if y < 10:
                break
            try:
                c.drawString(10, y, line[:200])  # Zeilenlänge begrenzen
            except Exception:
                pass
            y -= 9

    def _build_pillow_pdf(self, image_bytes: bytes) -> bytes:
        """Pillow-basiertes PDF (image only, nicht durchsuchbar)."""
        try:
            from PIL import Image as PILImage

            image = PILImage.open(io.BytesIO(image_bytes))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")

            output = io.BytesIO()
            image.save(output, format="PDF", resolution=150)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Pillow-PDF-Fallback fehlgeschlagen: {e}")
            raise
