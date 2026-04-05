"""Integration-Tests fuer Email-Service SMTP-Versand (Issue #732)."""

import unittest
from unittest.mock import patch, MagicMock


class TestEmailServiceSMTP(unittest.TestCase):
    """Testet die SMTP-Versand-Methoden des EmailService."""

    def setUp(self):
        from src.services.email_service import EmailService

        self.service = EmailService()

    def test_render_invite_template(self):
        """Invite-Template wird korrekt gerendert."""
        html = self.service._render_template(
            "invite.html",
            {
                "invite_link": "https://example.com/invite/abc",
                "display_name": "Max",
            },
        )
        self.assertIn("https://example.com/invite/abc", html)
        self.assertIn("Max", html)
        self.assertIn("DualMind", html)

    def test_render_password_reset_template(self):
        """Password-Reset-Template wird korrekt gerendert."""
        html = self.service._render_template(
            "password_reset.html",
            {
                "reset_link": "https://example.com/reset/xyz",
            },
        )
        self.assertIn("https://example.com/reset/xyz", html)
        self.assertIn("zuruecksetzen", html)

    def test_render_activation_template(self):
        """Activation-Template wird korrekt gerendert."""
        html = self.service._render_template(
            "activation.html",
            {
                "activation_link": "https://example.com/activate/def",
            },
        )
        self.assertIn("https://example.com/activate/def", html)
        self.assertIn("aktivieren", html)

    def test_render_template_not_found(self):
        """Fehlendes Template wirft FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.service._render_template("nonexistent.html", {})

    def test_plaintext_from_html(self):
        """HTML wird zu Plaintext konvertiert."""
        html = "<html><body><p>Hallo Welt</p></body></html>"
        text = self.service._plaintext_from_html(html)
        self.assertIn("Hallo Welt", text)
        self.assertNotIn("<p>", text)

    @patch("src.services.email_service.settings")
    def test_send_smtp_skips_when_not_configured(self, mock_settings):
        """SMTP-Versand wird uebersprungen wenn nicht konfiguriert."""
        mock_settings.SMTP_HOST = ""
        mock_settings.SMTP_USER = ""
        result = self.service._send_smtp("test@example.com", "Test", "<p>Test</p>")
        self.assertFalse(result)

    @patch("src.services.email_service.smtplib.SMTP")
    @patch("src.services.email_service.settings")
    def test_send_smtp_starttls(self, mock_settings, mock_smtp_class):
        """SMTP-Versand mit STARTTLS (Port 587)."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "secret"
        mock_settings.SMTP_FROM_NAME = "DualMind"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = self.service._send_smtp("test@example.com", "Betreff", "<p>Inhalt</p>")
        self.assertTrue(result)

    @patch("src.services.email_service.smtplib.SMTP_SSL")
    @patch("src.services.email_service.settings")
    def test_send_smtp_ssl(self, mock_settings, mock_smtp_class):
        """SMTP-Versand mit SSL (Port 465)."""
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 465
        mock_settings.SMTP_USER = "user@example.com"
        mock_settings.SMTP_PASSWORD = "secret"
        mock_settings.SMTP_FROM_NAME = "DualMind"
        mock_settings.SMTP_FROM_EMAIL = "noreply@example.com"

        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_class.return_value.__exit__ = MagicMock(return_value=False)

        result = self.service._send_smtp("test@example.com", "Betreff", "<p>Inhalt</p>")
        self.assertTrue(result)

    @patch("src.services.email_service.EmailService._send_smtp")
    def test_send_invite_email(self, mock_send):
        """send_invite_email ruft _send_smtp mit korrekten Parametern auf."""
        mock_send.return_value = True
        result = self.service.send_invite_email("a@b.com", "https://link", "Max")
        self.assertTrue(result)
        mock_send.assert_called_once()
        args = mock_send.call_args
        self.assertEqual(args[0][0], "a@b.com")
        self.assertIn("Max", args[0][1])

    @patch("src.services.email_service.EmailService._send_smtp")
    def test_send_password_reset_email(self, mock_send):
        """send_password_reset_email ruft _send_smtp korrekt auf."""
        mock_send.return_value = True
        result = self.service.send_password_reset_email("a@b.com", "https://reset")
        self.assertTrue(result)
        mock_send.assert_called_once()

    @patch("src.services.email_service.EmailService._send_smtp")
    def test_send_activation_email(self, mock_send):
        """send_activation_email ruft _send_smtp korrekt auf."""
        mock_send.return_value = True
        result = self.service.send_activation_email("a@b.com", "https://activate")
        self.assertTrue(result)
        mock_send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
