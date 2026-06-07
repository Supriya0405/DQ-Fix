"""
Email Verification API — External API Integration
==================================================
Validates email addresses using an external API service.
"""

import requests
from typing import Optional

from config.settings import EMAIL_API_URL, EMAIL_API_KEY


class EmailVerifier:
    """
    Verifies email addresses via external API.
    Falls back to regex validation if API is unavailable.
    """

    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = api_url or EMAIL_API_URL
        self.api_key = api_key if api_key is not None else EMAIL_API_KEY

    def verify(self, email: str) -> dict:
        """
        Verify a single email address.

        Returns
        -------
        dict with:
            - email: str
            - is_valid: bool
            - api_status: str (available/unavailable/error)
            - confidence: int (0-100)
            - details: dict (API response details)
        """
        if not email or not isinstance(email, str) or "@" not in email:
            return {
                "email": email,
                "is_valid": False,
                "api_status": "skipped",
                "confidence": 100,
                "details": {"reason": "Invalid email format"},
            }

        if not self.api_key:
            return self._fallback(
                email,
                "EMAIL_API_KEY not set — add it to .env (free key at https://app.emailvalidation.io)",
            )

        try:
            response = requests.get(
                self.api_url,
                params={"email": email.strip()},
                headers={"apikey": self.api_key},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                state = (data.get("state") or "").lower()
                format_valid = data.get("format_valid", True)
                is_valid = state == "deliverable" or (
                    format_valid and state not in ("undeliverable", "invalid")
                )
                score = data.get("score", 0.8)
                confidence = int(score * 100) if isinstance(score, float) else 80
                return {
                    "email": email,
                    "is_valid": is_valid,
                    "api_status": "available",
                    "confidence": min(100, max(0, confidence)),
                    "details": {
                        "domain": data.get("domain", ""),
                        "state": data.get("state", ""),
                        "format_valid": data.get("format_valid"),
                        "mx_found": data.get("mx_found"),
                        "smtp_check": data.get("smtp_check"),
                        "reason": data.get("reason", ""),
                    },
                }
            if response.status_code == 401:
                return self._fallback(email, "HTTP 401 — invalid or missing EMAIL_API_KEY")
            return self._fallback(email, f"HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            return self._fallback(email, "API timeout")
        except requests.exceptions.ConnectionError:
            return self._fallback(email, "Connection error")
        except Exception as e:
            return self._fallback(email, str(e))

    def _fallback(self, email: str, error: str) -> dict:
        """Fallback to regex validation when API is unavailable."""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        is_valid = bool(re.match(pattern, email))
        return {
            "email": email,
            "is_valid": is_valid,
            "api_status": "unavailable",
            "confidence": 60 if is_valid else 40,
            "details": {"reason": f"API unavailable ({error}), used regex fallback"},
        }

    def check_api_status(self) -> dict:
        """Check if the email verification API is available."""
        if not self.api_key:
            return {
                "available": False,
                "status_code": None,
                "message": "EMAIL_API_KEY not set in .env",
            }
        try:
            response = requests.get(
                self.api_url,
                params={"email": "test@example.com"},
                headers={"apikey": self.api_key},
                timeout=5,
            )
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "message": "API is available" if response.status_code == 200 else f"HTTP {response.status_code}",
            }
        except Exception as e:
            return {
                "available": False,
                "status_code": None,
                "message": str(e),
            }
