"""Stealth configuration models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProxyConfig(BaseModel):
    enabled: bool = False
    type: str = "socks5"  # socks5, socks4, http, https
    host: str = "127.0.0.1"
    port: int = 9050  # Tor SOCKS default

    @property
    def url(self) -> str:
        return f"{self.type}://{self.host}:{self.port}"


class WrapperConfig(BaseModel):
    mode: str = "none"  # none, proxychains, torsocks


class TimingConfig(BaseModel):
    enabled: bool = False
    min_delay_ms: int = 100
    max_delay_ms: int = 3000
    jitter_percent: int = 30


class UserAgentConfig(BaseModel):
    enabled: bool = False
    rotate_every: int = 10  # rotate every N requests
    browser_type: str = "random"  # chrome, firefox, safari, edge, random


class DNSPrivacyConfig(BaseModel):
    enabled: bool = False
    method: str = "system"  # system, doh, tor
    doh_url: str = "https://cloudflare-dns.com/dns-query"


class StealthConfig(BaseModel):
    enabled: bool = False
    proxy: ProxyConfig = Field(default_factory=ProxyConfig)
    wrapper: WrapperConfig = Field(default_factory=WrapperConfig)
    timing: TimingConfig = Field(default_factory=TimingConfig)
    user_agent: UserAgentConfig = Field(default_factory=UserAgentConfig)
    dns: DNSPrivacyConfig = Field(default_factory=DNSPrivacyConfig)
