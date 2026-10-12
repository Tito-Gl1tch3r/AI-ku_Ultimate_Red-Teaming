"""Unit tests for stealth configuration models."""

from __future__ import annotations

from tengu.stealth.config import (
    DNSPrivacyConfig,
    ProxyConfig,
    StealthConfig,
    TimingConfig,
    UserAgentConfig,
    WrapperConfig,
)

# ---------------------------------------------------------------------------
# TestProxyConfig
# ---------------------------------------------------------------------------


class TestProxyConfig:
    def test_default_disabled(self):
        cfg = ProxyConfig()
        assert cfg.enabled is False

    def test_default_host(self):
        cfg = ProxyConfig()
        assert cfg.host == "127.0.0.1"

    def test_default_port(self):
        cfg = ProxyConfig()
        assert cfg.port == 9050

    def test_default_type(self):
        cfg = ProxyConfig()
        assert cfg.type == "socks5"

    def test_url_property_socks5(self):
        cfg = ProxyConfig(type="socks5", host="127.0.0.1", port=9050)
        assert cfg.url == "socks5://127.0.0.1:9050"

    def test_url_property_http(self):
        cfg = ProxyConfig(type="http", host="proxy.corp.com", port=3128)
        assert cfg.url == "http://proxy.corp.com:3128"

    def test_url_property_custom_host_port(self):
        cfg = ProxyConfig(type="socks4", host="10.0.0.5", port=1080)
        assert cfg.url == "socks4://10.0.0.5:1080"


# ---------------------------------------------------------------------------
# TestTimingConfig
# ---------------------------------------------------------------------------


class TestTimingConfig:
    def test_default_disabled(self):
        cfg = TimingConfig()
        assert cfg.enabled is False

    def test_default_min_delay(self):
        cfg = TimingConfig()
        assert cfg.min_delay_ms == 100

    def test_default_max_delay(self):
        cfg = TimingConfig()
        assert cfg.max_delay_ms == 3000

    def test_default_jitter(self):
        cfg = TimingConfig()
        assert cfg.jitter_percent == 30

    def test_custom_values(self):
        cfg = TimingConfig(enabled=True, min_delay_ms=50, max_delay_ms=500, jitter_percent=10)
        assert cfg.enabled is True
        assert cfg.min_delay_ms == 50
        assert cfg.max_delay_ms == 500
        assert cfg.jitter_percent == 10


# ---------------------------------------------------------------------------
# TestUserAgentConfig
# ---------------------------------------------------------------------------


class TestUserAgentConfig:
    def test_default_disabled(self):
        cfg = UserAgentConfig()
        assert cfg.enabled is False

    def test_default_rotate_every(self):
        cfg = UserAgentConfig()
        assert cfg.rotate_every == 10

    def test_default_browser_type(self):
        cfg = UserAgentConfig()
        assert cfg.browser_type == "random"

    def test_custom_browser_type(self):
        cfg = UserAgentConfig(browser_type="chrome")
        assert cfg.browser_type == "chrome"


# ---------------------------------------------------------------------------
# TestWrapperConfig
# ---------------------------------------------------------------------------


class TestWrapperConfig:
    def test_default_mode(self):
        cfg = WrapperConfig()
        assert cfg.mode == "none"

    def test_proxychains_mode(self):
        cfg = WrapperConfig(mode="proxychains")
        assert cfg.mode == "proxychains"

    def test_torsocks_mode(self):
        cfg = WrapperConfig(mode="torsocks")
        assert cfg.mode == "torsocks"


# ---------------------------------------------------------------------------
# TestDNSPrivacyConfig
# ---------------------------------------------------------------------------


class TestDNSPrivacyConfig:
    def test_default_disabled(self):
        cfg = DNSPrivacyConfig()
        assert cfg.enabled is False

    def test_default_method(self):
        cfg = DNSPrivacyConfig()
        assert cfg.method == "system"

    def test_default_doh_url_has_cloudflare(self):
        cfg = DNSPrivacyConfig()
        assert "cloudflare" in cfg.doh_url


# ---------------------------------------------------------------------------
# TestStealthConfig
# ---------------------------------------------------------------------------


class TestStealthConfig:
    def test_default_disabled(self):
        cfg = StealthConfig()
        assert cfg.enabled is False

    def test_has_proxy_subconfig(self):
        cfg = StealthConfig()
        assert isinstance(cfg.proxy, ProxyConfig)

    def test_has_timing_subconfig(self):
        cfg = StealthConfig()
        assert isinstance(cfg.timing, TimingConfig)

    def test_has_user_agent_subconfig(self):
        cfg = StealthConfig()
        assert isinstance(cfg.user_agent, UserAgentConfig)

    def test_has_wrapper_subconfig(self):
        cfg = StealthConfig()
        assert isinstance(cfg.wrapper, WrapperConfig)

    def test_has_dns_subconfig(self):
        cfg = StealthConfig()
        assert isinstance(cfg.dns, DNSPrivacyConfig)

    def test_fully_enabled_config(self):
        cfg = StealthConfig(
            enabled=True,
            proxy=ProxyConfig(enabled=True),
            timing=TimingConfig(enabled=True),
            user_agent=UserAgentConfig(enabled=True),
        )
        assert cfg.enabled is True
        assert cfg.proxy.enabled is True
        assert cfg.timing.enabled is True
        assert cfg.user_agent.enabled is True
