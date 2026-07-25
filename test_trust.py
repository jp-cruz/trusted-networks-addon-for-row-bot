# Copyright 2026 JP Cruz
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Deterministic tests for trust.py -- no network calls, no external services."""

from __future__ import annotations

import pytest

from trust import ENV_VAR, _trusted_networks, is_trusted_client_ip


@pytest.fixture(autouse=True)
def _clear_trust_cache(monkeypatch):
    """Ensure each test sees a fresh, uncached read of ROW_BOT_TRUSTED_NETWORKS."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    _trusted_networks.cache_clear()
    yield
    _trusted_networks.cache_clear()


def test_loopback_ipv4_always_trusted():
    assert is_trusted_client_ip("127.0.0.1") is True


def test_loopback_ipv6_always_trusted():
    assert is_trusted_client_ip("::1") is True


def test_localhost_string_always_trusted():
    assert is_trusted_client_ip("localhost") is True


def test_unconfigured_env_var_only_trusts_loopback(monkeypatch):
    # ENV_VAR unset (autouse fixture already clears it) -- behavior must be unchanged
    # from strict loopback-only, i.e. the feature is off by default.
    assert is_trusted_client_ip("192.0.2.5") is False


def test_ip_in_configured_range_is_trusted(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "192.0.2.0/24")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("192.0.2.5") is True


def test_ip_outside_configured_range_is_not_trusted(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "192.0.2.0/24")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("198.51.100.5") is False


def test_multiple_comma_separated_ranges(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "192.0.2.0/24,198.51.100.0/24")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("192.0.2.5") is True
    assert is_trusted_client_ip("198.51.100.5") is True
    assert is_trusted_client_ip("203.0.113.5") is False


def test_malformed_entry_is_skipped_not_fatal(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "not-a-cidr,192.0.2.0/24")
    _trusted_networks.cache_clear()
    # Malformed first entry must not prevent the valid second entry from working,
    # and must not raise.
    assert is_trusted_client_ip("192.0.2.5") is True


def test_empty_and_whitespace_entries_are_skipped(monkeypatch):
    monkeypatch.setenv(ENV_VAR, " , 192.0.2.0/24 , ")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("192.0.2.5") is True


def test_unparseable_client_host_is_not_trusted():
    assert is_trusted_client_ip("not-an-ip-address") is False


def test_empty_client_host_is_not_trusted():
    assert is_trusted_client_ip("") is False


def test_ipv6_range_matches_ipv6_client():
    import os

    os.environ[ENV_VAR] = "2001:db8::/32"
    _trusted_networks.cache_clear()
    try:
        assert is_trusted_client_ip("2001:db8::1") is True
        assert is_trusted_client_ip("2001:db9::1") is False
    finally:
        del os.environ[ENV_VAR]
        _trusted_networks.cache_clear()


def test_ipv4_mapped_ipv6_client_matches_ipv4_range(monkeypatch):
    """Some ASGI servers report an IPv4 client as ::ffff:x.x.x.x depending on socket
    configuration -- this must still match an IPv4 CIDR, not silently fail."""
    monkeypatch.setenv(ENV_VAR, "192.0.2.0/24")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("::ffff:192.0.2.5") is True


def test_ipv4_mapped_ipv6_client_outside_range_still_rejected(monkeypatch):
    monkeypatch.setenv(ENV_VAR, "192.0.2.0/24")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("::ffff:198.51.100.5") is False


def test_ipv4_client_against_ipv6_only_range_is_not_trusted(monkeypatch):
    """Mismatched address families must fail closed, not raise."""
    monkeypatch.setenv(ENV_VAR, "2001:db8::/32")
    _trusted_networks.cache_clear()
    assert is_trusted_client_ip("192.0.2.5") is False
