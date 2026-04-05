"""
Unit-Tests für OcrService – erweiterte Methoden.

Getestet:
- extract_deadline: diverse deutsche Datumsformate
- classify_document: Keyword-basierte Klassifikation
- extract_text: korrekte dict-Struktur
- extract_text_from_file: Delegation für Bilder
"""

import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixture: OcrService mit deaktiviertem Tesseract-Check
# ---------------------------------------------------------------------------
@pytest.fixture
def ocr_service():
    with patch("src.services.ocr_service.settings") as mock_settings:
        mock_settings.OCR_CONFIDENCE_THRESHOLD = 70
        with patch.object(_ocr_module().OcrService, "_check_tesseract", return_value=False):
            svc = _ocr_module().OcrService()
    return svc


def _ocr_module():
    """Import-Helfer, damit settings-Mock greift."""
    import src.services.ocr_service as m

    return m


# ---------------------------------------------------------------------------
# extract_deadline
# ---------------------------------------------------------------------------
class TestExtractDeadline:
    """Deadline-Extraktion aus OCR-Text."""

    def _run(self, svc, text: str):
        return asyncio.get_event_loop().run_until_complete(svc.extract_deadline(text))

    def test_standard_date(self, ocr_service):
        text = "Bitte überweisen Sie bis zum 31.12.2030 den Betrag."
        result = self._run(ocr_service, text)
        assert result == date(2030, 12, 31)

    def test_frist_bis(self, ocr_service):
        text = "Frist bis 15.06.2030"
        result = self._run(ocr_service, text)
        assert result == date(2030, 6, 15)

    def test_faellig_am(self, ocr_service):
        text = "Fällig am 01.03.2029"
        result = self._run(ocr_service, text)
        assert result == date(2029, 3, 1)

    def test_zahlbar_bis(self, ocr_service):
        text = "Zahlbar bis 28.02.2028"
        result = self._run(ocr_service, text)
        assert result == date(2028, 2, 28)

    def test_two_digit_year(self, ocr_service):
        text = "Frist bis 10.05.30"
        result = self._run(ocr_service, text)
        assert result == date(2030, 5, 10)

    def test_multiple_dates_returns_earliest_future(self, ocr_service):
        text = "Datum: 01.01.2029. Zahlbar bis 15.06.2028."
        result = self._run(ocr_service, text)
        assert result == date(2028, 6, 15)

    def test_past_dates_ignored(self, ocr_service):
        text = "Rechnungsdatum: 01.01.2020. Keine weitere Frist."
        result = self._run(ocr_service, text)
        assert result is None

    def test_no_date_returns_none(self, ocr_service):
        result = self._run(ocr_service, "Kein Datum hier.")
        assert result is None

    def test_empty_text_returns_none(self, ocr_service):
        result = self._run(ocr_service, "")
        assert result is None

    def test_invalid_date_skipped(self, ocr_service):
        text = "Frist bis 32.13.2030 und 15.06.2030"
        result = self._run(ocr_service, text)
        assert result == date(2030, 6, 15)

    def test_dash_separator(self, ocr_service):
        text = "Deadline: 20-08-2029"
        result = self._run(ocr_service, text)
        assert result == date(2029, 8, 20)

    def test_slash_separator(self, ocr_service):
        text = "Due: 10/07/2029"
        result = self._run(ocr_service, text)
        assert result == date(2029, 7, 10)

    def test_faellig_bis(self, ocr_service):
        text = "Fällig bis 05.11.2030"
        result = self._run(ocr_service, text)
        assert result == date(2030, 11, 5)


# ---------------------------------------------------------------------------
# classify_document
# ---------------------------------------------------------------------------
class TestClassifyDocument:
    """Keyword-basierte Dokumenten-Klassifikation."""

    def _run(self, svc, text: str):
        return asyncio.get_event_loop().run_until_complete(svc.classify_document(text))

    def test_invoice(self, ocr_service):
        text = "Rechnung Nr. 12345\nRechnungsdatum: 01.01.2026\nNettobetrag: 100€\nUSt-ID: DE123"
        assert self._run(ocr_service, text) == "invoice"

    def test_receipt(self, ocr_service):
        text = "Kassenbon\nSumme: 12,50€\nBar bezahlt\nDanke für Ihren Einkauf"
        assert self._run(ocr_service, text) == "receipt"

    def test_warranty(self, ocr_service):
        text = "Garantieschein\nGarantiebedingungen gelten ab Kaufdatum\nGarantiezeitraum: 2 Jahre"
        assert self._run(ocr_service, text) == "warranty"

    def test_insurance(self, ocr_service):
        text = "Versicherungsschein Nr. V-2026\nVersicherung: Haftpflicht\nPrämie: 200€/Jahr"
        assert self._run(ocr_service, text) == "insurance"

    def test_contract(self, ocr_service):
        text = "Mietvertrag\nVertragspartner: Max Mustermann\nKündigungsfrist: 3 Monate\nLaufzeit: unbefristet"
        assert self._run(ocr_service, text) == "contract"

    def test_unknown_returns_other(self, ocr_service):
        text = "Lorem ipsum dolor sit amet, consectetur adipiscing elit."
        assert self._run(ocr_service, text) == "other"

    def test_empty_text_returns_other(self, ocr_service):
        assert self._run(ocr_service, "") == "other"

    def test_single_keyword_weak_match(self, ocr_service):
        """Ein einzelnes Keyword reicht für schwache Zuordnung (Fallback)."""
        text = "Dieses Dokument enthält eine Rechnung."
        result = self._run(ocr_service, text)
        assert result == "invoice"


# ---------------------------------------------------------------------------
# extract_text – dict-Struktur
# ---------------------------------------------------------------------------
class TestExtractText:
    """extract_text gibt korrekte dict-Struktur zurück."""

    def test_returns_dict_with_required_keys(self, ocr_service):
        """Ohne Tesseract und ohne AI-Service → 'none'-Fallback."""
        result = asyncio.get_event_loop().run_until_complete(ocr_service.extract_text(b"fake-image-bytes"))
        assert isinstance(result, dict)
        assert "text" in result
        assert "confidence" in result
        assert "method" in result
        assert "words_data" in result
        assert result["method"] == "none"
        assert result["confidence"] == 0.0


# ---------------------------------------------------------------------------
# extract_text_from_file – Image-Delegation
# ---------------------------------------------------------------------------
class TestExtractTextFromFile:
    """extract_text_from_file delegiert korrekt."""

    def test_image_file_delegates(self, ocr_service, tmp_path):
        img_path = tmp_path / "test.png"
        img_path.write_bytes(b"fake-png-bytes")

        with patch.object(ocr_service, "extract_text", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "text": "Hello",
                "confidence": 95.0,
                "method": "tesseract",
                "words_data": None,
            }
            result = asyncio.get_event_loop().run_until_complete(ocr_service.extract_text_from_file(str(img_path)))
            mock_extract.assert_called_once()
            assert result["pages"] == 1
            assert result["text"] == "Hello"

    def test_pdf_without_pdf2image(self, ocr_service, tmp_path):
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 fake")

        with patch.dict("sys.modules", {"pdf2image": None}):
            # Force ImportError inside _extract_from_pdf
            with patch(
                "src.services.ocr_service.OcrService._extract_from_pdf",
                new_callable=AsyncMock,
            ) as mock_pdf:
                mock_pdf.return_value = {
                    "text": "",
                    "confidence": 0.0,
                    "method": "none",
                    "pages": 0,
                    "words_data": None,
                }
                result = asyncio.get_event_loop().run_until_complete(ocr_service.extract_text_from_file(str(pdf_path)))
                assert result["pages"] == 0
