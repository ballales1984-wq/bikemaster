"""Tests for backend.api.utils."""


from fastapi import Request

from bike_analyzer.backend.api.utils import (
    _forwarded_value,
    _is_trusted_proxy,
    _trusted_forwarded_value,
)


class TestForwardedValue:
    def test_none_returns_empty(self):
        assert _forwarded_value(None) == ""

    def test_empty_string_returns_empty(self):
        assert _forwarded_value("") == ""

    def test_single_value(self):
        assert _forwarded_value("1.2.3.4") == "1.2.3.4"

    def test_first_value_of_comma_list(self):
        assert _forwarded_value("1.2.3.4, 5.6.7.8, 9.10.11.12") == "1.2.3.4"

    def test_strips_whitespace(self):
        assert _forwarded_value("  1.2.3.4  ") == "1.2.3.4"


class TestIsTrustedProxy:
    def test_loopback_ipv4(self):
        assert _is_trusted_proxy("127.0.0.1") is True

    def test_loopback_ipv6(self):
        assert _is_trusted_proxy("::1") is True

    def test_private_10(self):
        assert _is_trusted_proxy("10.0.0.1") is True
        assert _is_trusted_proxy("10.255.255.255") is True

    def test_private_172(self):
        assert _is_trusted_proxy("172.16.0.1") is True
        assert _is_trusted_proxy("172.31.255.255") is True

    def test_private_192(self):
        assert _is_trusted_proxy("192.168.0.1") is True
        assert _is_trusted_proxy("192.168.1.100") is True

    def test_test_client_host(self):
        assert _is_trusted_proxy("testclient") is True

    def test_public_ip_not_trusted(self):
        assert _is_trusted_proxy("8.8.8.8") is False
        assert _is_trusted_proxy("1.1.1.1") is False

    def test_invalid_ip_returns_false(self):
        assert _is_trusted_proxy("not-an-ip") is False
        assert _is_trusted_proxy("") is False
        assert _is_trusted_proxy("999.999.999.999") is False

    def test_ipv6_not_loopback_not_trusted(self):
        assert _is_trusted_proxy("2001:db8::1") is False


class TestTrustedForwardedValue:
    def _make_request(self, client_host: str, forwarded_for: str = ""):
        scope = {
            "type": "http",
            "client": (client_host, 12345),
            "headers": [(b"x-forwarded-for", forwarded_for.encode())] if forwarded_for else [],
        }
        return Request(scope)

    def test_trusted_proxy_returns_forwarded(self):
        req = self._make_request("127.0.0.1", "1.2.3.4, 5.6.7.8")
        assert _trusted_forwarded_value(req, "x-forwarded-for") == "1.2.3.4"

    def test_untrusted_proxy_returns_empty(self):
        req = self._make_request("8.8.8.8", "1.2.3.4")
        assert _trusted_forwarded_value(req, "x-forwarded-for") == ""

    def test_no_forwarded_header_returns_empty_even_if_trusted(self):
        req = self._make_request("127.0.0.1")
        assert _trusted_forwarded_value(req, "x-forwarded-for") == ""

    def test_test_client_host_is_trusted(self):
        req = self._make_request("testclient", "1.2.3.4")
        assert _trusted_forwarded_value(req, "x-forwarded-for") == "1.2.3.4"

    def test_private_network_client_is_trusted(self):
        req = self._make_request("192.168.1.1", "1.2.3.4")
        assert _trusted_forwarded_value(req, "x-forwarded-for") == "1.2.3.4"

    def test_different_header_name(self):
        scope = {
            "type": "http",
            "client": ("127.0.0.1", 12345),
            "headers": [(b"x-real-ip", b"1.2.3.4")],
        }
        req = Request(scope)
        assert _trusted_forwarded_value(req, "x-real-ip") == "1.2.3.4"

    def test_none_client_returns_empty(self):
        scope = {
            "type": "http",
            "client": None,
            "headers": [(b"x-forwarded-for", b"1.2.3.4")],
        }
        req = Request(scope)
        assert _trusted_forwarded_value(req, "x-forwarded-for") == ""
