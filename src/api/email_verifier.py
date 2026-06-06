"""
Email Verification API — External API Integration
==================================================
Validates email addresses using an external API service.
"""

import requests
from typing import Optional


class EmailVerifier:
    """
    Verifies email addresses via external API.
    Falls back to regex validation if API is unavailable.
    """

    def __init__(self, api_url: str = "https://api.emailvalidation.io/v1/info"):
        self.api_url = api_url

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

        try:
            response = requests.get(
                self.api_url,
                params={"email": email.strip()},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                is_valid = data.get("state", "").lower() in ("deliverable", "valid", "ok", "")
                return {
                    "email": email,
                    "is_valid": True if is_valid else data.get("state", "") != "undeliverable",
                    "api_status": "available",
                    "confidence": min(100, max(0, int(data.get("score", 80) * 100 if isinstance(data.get("score"), float) else 80))),
                    "details": {
                        "domain": data.get("domain", ""),
                        "state": data.get("state", ""),
                        "raw_response": data,
                    },
                }
            else:
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
        try:
            response = requests.get(self.api_url, params={"email": "test@example.com"}, timeout=5)
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
