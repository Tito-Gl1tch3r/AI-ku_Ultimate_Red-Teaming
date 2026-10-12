#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lookalike / Homograph Domain Scanner (IDN-aware)
- Generates ASCII typos + optical ASCII look-alikes
- Generates Unicode homoglyph variants (Cyrillic/Greek/Han/Hiragana/Katakana, etc.)
- Validates & queries via IDNA2008 (Punycode) for DNS / CT / WHOIS
- Risk labeling aligned with Unicode UTS #39 (confusables) and Chromium IDN policy heuristics
- Scoring & export to JSON/CSV
- Fast mode: enrich (CT/WHOIS) only DNS-active candidates

Examples:
  python DLaL.py ttl.zip --max 180 --fast --top 10 --out results.json
  python DLaL.py google.de --max 200 --fast --top 50 --out results.csv --dns-timeout 1.0
  python DLaL.py example.com --no-ct --no-whois --no-idn    # ASCII-only quick pass

New flags:
  --idn / --no-idn              Enable/disable IDN homoglyph generation (default: ON)
  --scripts S1,S2,...           Restrict IDN generation to these scripts (Cyrillic,Greek,Han,Hiragana,Katakana)
  --idn-max N                   Cap IDN variants before pruning (default: 2000)
  --optical-max N               Cap ASCII optical variants before pruning (default: 2000)
  --dmarc                       Probe DMARC; missing DMARC + MX raises score

Output fields (per candidate):
  domain_unicode, domain_ascii, A, AAAA, MX, NS, has_ct, whois_created,
  risk, reason_exists, score
"""

from __future__ import annotations
import argparse
import csv
import json
import math
import sys
import time
import unicodedata
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple

import tldextract
import requests
import idna
import regex as re_u

# DNS
import dns.resolver
import dns.exception

# WHOIS (best effort)
try:
    import whois as pywhois
except Exception:
    pywhois = None

HTTP_TIMEOUT_DEFAULT = 10.0
DNS_TIMEOUT_DEFAULT = 2.0

# ----------------- ASCII optical lookalikes (minimal, extend as needed) -----------------
OPTICAL_ASCII: Dict[str, List[str]] = {
    "l": ["1", "I"],
    "1": ["l", "I"],
    "0": ["O"],
    "O": ["0"],
    "S": ["5"],
    "5": ["S"],
    "B": ["8"],
    "8": ["B"],
    "c": ["e", "o"],
    "e": ["c", "o"],
    "o": ["0", "c", "e"],
    "a": ["o"],
    "i": ["l"],
    "t": ["f"],
    "w": ["vv"],
    "m": ["rn", "nn"],
    "u": ["v"],
    "v": ["u"],
}

# ----------------- Unicode confusables (IDN core set) -----------------
# Minimal reverse mapping for Latin → {Cyrillic/Greek look-alikes}. Extend safely later or load from JSON.
# NOTE: This is intentionally conservative to avoid blow-ups.
HOMOGLYPH_REV_CORE: Dict[str, List[str]] = {
    # Latin : [Cyrillic, Greek]
    "a": ["а", "ɑ", "α"],
    "c": ["с"],
    "e": ["е", "ε"],
    "i": ["і", "ί", "ι"],
    "j": ["ј"],
    "o": ["о", "ο", "ο̱"],
    "p": ["р"],
    "s": ["ѕ"],
    "x": ["х", "χ"],
    "y": ["у", "γ"],
    "h": ["һ", "һ"],
    "k": ["κ"],
    "m": ["м"],
    "n": ["п"],  # visually arguable; keep capped by generator
    "t": ["τ"],
    "r": ["г"],  # arguable; conservative capping helps
    "u": ["υ"],
    # Uppercase
    "A": ["А", "Α"],
    "B": ["В", "Β"],
    "C": ["С"],
    "E": ["Е", "Ε"],
    "H": ["Н", "Η"],
    "I": ["І", "Ι"],
    "J": ["Ј"],
    "K": ["К", "Κ"],
    "M": ["М"],
    "O": ["О", "Ο"],
    "P": ["Р", "Ρ"],
    "T": ["Т", "Τ"],
    "X": ["Х", "Χ"],
    "Y": ["У", "Υ"],
}

# Scripts we support for quick restriction (best-effort)
SUPPORTED_SCRIPTS = {"Latin", "Cyrillic", "Greek", "Han", "Hiragana", "Katakana"}

# Regex spans for script detection
SCRIPT_SPAN_RE = re_u.compile(
    r"(\p{Script=Latin}+)|(\p{Script=Cyrillic}+)|(\p{Script=Greek}+)|(\p{Script=Han}+)|(\p{Script=Hiragana}+)|(\p{Script=Katakana}+)"
)

# ----------------- Helpers -----------------
ascii_art = r"""
        %%%%                                            *@%%%%@-                                %%%%
       %%%%%                                        %%%%%%%%%%%%%%%%%-                         @%%%%
      *%%*%%%                                     %%%%%%%%%%%%%%%%%%%%%%%                      %%%%%
      %%%:%%%                                   %%%%%%%%::::   ::::: %%%%%%%                  %%%: %
     %%% :-%%%                                %%%%%%%%  ::::::::::::: ::%%%%%%%               %%%- %
    %%%%::-*%%@                             %%%%%%%%*::::::::::::::::: ::  %%%%%%            %%%:-::
    %%%: :-:%%%                            %%%%%%%% :::::: ::::: ::::::: :: :%%%%%          -%%%- ::
   %%% :  :--%%@                          %%%%%%%%  ::::::::::::*-*-- ::::::::-%%%%%        %%%:-::
  %%%%: :: --%%%                         %%%%%%%%*:::::::::::::----------: :::: %%%%%      %%%*-::::
  %%%: ::::---%%%                       %%%%%%%%%::  :::::::  -----**----*-::::::*@%%%     %%%--::::
 %%% :::::::--*%%%%%%%%%%%%%%%%%%%-    *%%%%%%%% : :: :: ::::-----%-----------:::::%%%%   %%%*--::::
%%%: :::::: :%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%:::: :::  : -----%%%%%%%%%%%---*::: *%%%  %%%-- ::::
%%%::::::  %%%%%%%%:: ::   :-%%%%%%%%%%%%%%%%%%: :::::::::: ----%%%%%%%%%%%%%%*--*:: %%%%%%%---::: :
%%::::: :*%%%%%%:::: :::::::: :::: %%%%%%%%%%%%::   :::::: ----%%%%%%%%%%%%%%%%%%-- : %%%%%*--::::::
%:::::::%%%%%*:::::::: ::::: ::::::::%%%%%%%%%*:::::: ::: ----%%%%%%%%%%%%%%%%%%%%*-*:*%%%%---::: ::
%::: : %%%%%: ::: :::::  : ::: : :::::%%%%%%%% : ::::::::----%%%%%%%%%%%%%%%%%%%%%%%--:%%%%---:: :::
::::: %%%%%:  :: -----* ::  :: ::::::::%%%%%%% :::  ::::----%%%%%%%%%%%%%%*    *%%%%%%- %%%%-::: : :
: :: %%%%*:::: -----*----*: :::::::::: :%%%%%%::::: :::----%%%%%%%%%%%%%%*        %%%%%*-%%%-  :::::
::::%%%%%:  :------*%%%----*:: ::: ::::::%%%%*:::: : ----*%%%%%%%%%%%%%%%%:         %%%%%%%%% : : :
:  %%%%%::::-------%%%%%%----- :::::::::::*%%::::::*---*%%%%%%%%%%%%%%%%%%%%        %%%%%%%%%%%% :::
:: %%%% :::-----%%%%%%%%%%%----::::: :: ::::% :::::::: :: %%%%%%%%%%%%%%%%%%*      *%%%%%    %*%% :
::*%%%%:: ----%%%%%%%%%%%%%%*----::::::::::::: ::: ::: %%%%%%%%%%%%%%%%%%%%%%      %%%%%     *%%%%
::%%%% ::---*%%%%%%%%%%%%%%%%%%----:::  :: :  ::::::%%%%%%%%%%%%%%%%%%%%%%%%%%    %%%%%%    :%@%%%::
: %%%%::---%%%%%%%%%%%%%%%%%%--%%%%%%%%- ::::::: -%%%%%%%%%%%%%%%%%%%%%%%%%%%%   %%%%%%%%-   %%%% ::
  %%%%::--%%%%%%%%%%%%%%%%%%-%%%%%%%%%%%%%-::: %%%%%%%@          %%%%%%%%%%%%%   %%%%-*%%%%%%%%%::::
::%%%%:--%%%%%%*: :::::%%%%%%%%:      %%%%%%%%%%%%*                 %%%%%%%%%%  %%%%-----***-:::::::
  %%%% -%%%%%%:  :: :::-%%%%%*           @%%%%%%*                    %%%%*%%%% %%%%-------: ::: : ::
::%%%%:%%%%% :: ::::: : %%%%@               %%            %%%%%%      %%%%%%%%%%%%-------::::::  :%%
::*%%%%%%%%:: ::::: :: :%%%%  %%%                       %%%%%%**%-    %%%%%%%%%%%-------- ::::::::*%
:: %%%%%%*::: ::::::::::%%%%%%%%%%%                   %%%%%%          %%%%%%%%%%--------:::::: :  %%
::%%%%%%%%%::::  ::: ::: %%%% -%%%%%*               @%%%%%-%%*        %%%%%%%%%--------::::::: :  ::
:%%%%   *%%%% :::::: ::::*%%%: @%%%%%%%       %   @%%%%%   %%%        %%%%%%%%%-------::::: :: : :::
%%%-      %%% ::::::::::::%%%%  %  %%%%%*%:   %%%%%%%%    %%%%        @%%%%%%%%------ ::::::: ::::::
%%%*    : %%%%%**:  ::::::%%%%% %%   %%%%%    -%%%%%    %%%%%         %%%%%%%%%-----  :::  ::-**%%%%
%%%%% :  %%%%%%%%%%%%%%%%%%%%%   %%%%@%%%*     %%%%%%%%%%%%           %%%%%%%%-*%%%%%%%*%%%%%%%%%%%%
  %%%%%%%%%%: ::  :*%%%%%%%%%:     @*%%%%:     @                      %%%%%%%%%%%%%%%%%%%%%-   :::::
::: -%%%* :::::::::::----%%%%          @%                             %%%%%%%%%---------::::  ::::::
 :::%%% :::: :::: :: ----%%%%%         %%       %@%*                 *%%%%%%%%%-----:%%:: :::  :::::
:::%%%%%:::::::::: : -----%%%%        %            %%  @%%%%%%%      %%%%%%%%%%-----%%%%::: : : :::
 : %%%%%:::: ::::    -----*%%%%   %  %%           %%-     %%% :     -%%%%%%%%%%-----%%%%::: :  :-:::
: :%%%%% :::: :::%%%:------%%%%%  *%  %%      %%%%      %%%%        %%%%%%%%%%%----:%%%%-:::: ::::
:  %%%%% ::::: ::%%%:------%%%%%%@ - %*%%*@@%%%     @%%@ %%        %%%%%%%%%%%%-----%%%%-:::: :  :::
:::::::::::::::::  ::------%%%%%%%%   %%%%%%%%%%%%%%*   %%        %%%%%%%%%%%%%---------:::  :::::::
: ::::: ::::: :: ::: ------%%%%%%%%%   %%             @:%%       %%%%%%%%%%%%%*---------::::::::::::
:::: ::::::::::::: ::------%%%%%%%%%%  @%%             %%      %%%%%%%%%%%%%%%%%%%*-:---: ::::::::::
::  ::: ::: : :::::::------%%%%%%%%%%%  *%           *%%      %%%%%%%%%%%%-*%%%%%%%%%%%%%%%%%%%%%%%-
%%%%%%%%%%%%%%%%%%%%***---*%%%%%%%%%%%@  %%        @%%%      %%%%%%%%%%%%%%%:--:*%%%%%%%%%%%%%%%%%%%
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%   %%%%%%%%%%%       %%%%%%%%%%%%%%%%%%---:-----::-%%%%%%%%%%
: : : ::::  :::::%%%%%%%%%%% :::%%%%%%%*                  %%%%%%%%%%%%%%%%%%%%%%*-----:-%%%%*%% : ::
%%%%%%%%%%%%%%%%%%%%%%%:::::::%%%%%%%%%%*       *%       %%%%%%%%%%%*-::--****-::--:-%%%%%%%%%%%%%%%
::::: :::    %%*%%%%  :::::  ::  :  %%%%%               %%%%%%%%%%%%%------------------:-%%%%%%%%%%%
:: : ::::: %%%%%%%%%%%%%%%%%::::::::*%%%%%            :%%%%%%%%%%%%%%%--:-----:------:------:*%%%%%%
:: : :: :-%%%%%%%- %%%%%%*%%%:: :: ::%%*%%%          %%%%%%%%%%%%%%%%%----:-:----:----:-*%%%%%%%%%%%
::::: ::%%%%%%:::%%%%%%%%%%%%:::::: %%%%%%%%%%%%%%%%%%%%%%%%%%*%%%%%%%%:-:-:%%%%%%%%%%%%%%%%%%%%%%%%
::%%%: %%%%%:   %%%%%%%%%%%%% : :::%%%%%%%%%%%%%%%%%%%%%%%%%%-----*%%%%%----%%%%%%*%%%%%%%%%%%%%:---
 :%%%%%%%%%::::%%%%%%%%%%%%%*:::::%%%%%%%%%:%%%%%%%%%%%%%%%%-----::--:*%%---*%%%%%%%%%%%%%%%:---:---
::%%%%%%%% ::-%%%%%%%%%%%%%% ::::%%%%%% :: ::%%%%*%%%%%%%%%-----:-----------:%%%%%%%%%%%:-----:---::
::%%%%%%*:::-%%%%%%%%%%%%%%%:: :%*:::: :::::::%%%%%%%%%%%*----:%%%%--------:-%%%%%%%------------: ::
: %%%%%*:::-%%%%%%%%%%%%%%%%  ::::::::*%%% ::::%%%%%%%%%----:*%%%%%%%%%%*:---:%%%%---:--:---:% :::::
 %%%%%::: :%%%%%%%%%%%%%%%% :::: :%%%%%%%%%*::::*%%%%%%-----%%%%%%%%%%%%%%%%%%%%%%--------:%%:::::::
%%%%%-::: %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%% ::: %%%*:----%%%%%%%%%%%%%%%%%%%%%%%%:--:--%%% :::::::
%%%%%: : %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%*%%%%%%%::::% ::--%%%%%%%%%%%%%%%%%%%--**%**-----%%% ::::::::

Happy hacking!
— The Trave Tricksters Legion CTF Team
"""

def parse_domain(domain: str) -> Tuple[str, str]:
    ext = tldextract.extract(domain.strip())
    if not ext.suffix or not ext.domain:
        raise ValueError(f"Not a registrable domain: {domain!r}")
    return ext.domain, ext.suffix

def normalize_nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", s)

def idna_ascii(label_unicode: str) -> Optional[str]:
    """Return ASCII (Punycode) form or None if not IDNA-valid."""
    try:
        return idna.encode(label_unicode).decode("ascii")
    except idna.IDNAError:
        return None

def get_scripts(label: str) -> List[str]:
    scripts: Set[str] = set()
    for m in SCRIPT_SPAN_RE.finditer(label):
        span = m.group(0)
        if span:
            # best-effort via first char
            ch = span[0]
            try:
                name = unicodedata.name(ch)
            except Exception:
                continue
            # Map Unicode name prefix to rough script label
            if "CYRILLIC" in name:
                scripts.add("Cyrillic")
            elif "GREEK" in name:
                scripts.add("Greek")
            elif "HIRAGANA" in name:
                scripts.add("Hiragana")
            elif "KATAKANA" in name:
                scripts.add("Katakana")
            elif "CJK" in name or "IDEOGRAPH" in name or "HAN" in name:
                scripts.add("Han")
            else:
                scripts.add("Latin")
    if not scripts:
        scripts.add("Latin")
    return sorted(scripts)

# ----------------- UTS #39-like skeleton (minimal) -----------------
def skeleton(s: str, mapping: Dict[str, str]) -> str:
    out = []
    for ch in normalize_nfkc(s):
        out.append(mapping.get(ch, ch))
    return "".join(out)

def is_confusable(a: str, b: str, mapping: Dict[str, str]) -> bool:
    return skeleton(a, mapping) == skeleton(b, mapping)

def build_mapping_from_rev(rev: Dict[str, List[str]]) -> Dict[str, str]:
    """Build forward mapping for skeleton() from reverse confusable map."""
    m: Dict[str, str] = {}
    for base, confs in rev.items():
        for c in confs:
            m[c] = base
        # Also map base to itself to stabilize
        m[base] = base
    return m

# ----------------- Generation -----------------
def _is_valid_dns_label(label: str) -> bool:
    return 1 <= len(label) <= 63 and all(32 < ord(c) < 127 for c in label.replace("-", "")) and not (label.startswith("-") or label.endswith("-"))

def _is_valid_label(label: str) -> bool:
    # Looser: allow Unicode, but limit control/space; DNS will be punycoded later.
    if not (1 <= len(label) <= 63):
        return False
    for ch in label:
        cat = unicodedata.category(ch)
        if cat.startswith("C") or ch.isspace():
            return False
    return True

def gen_ascii_opticals(s: str, max_per_char=2, max_replacements=2, cap=2000) -> List[str]:
    out: Set[str] = set()
    # single replacement
    for i, ch in enumerate(s):
        if ch in OPTICAL_ASCII:
            for rep in OPTICAL_ASCII[ch][:max_per_char]:
                cand = s[:i] + rep + s[i + 1 :]
                if _is_valid_label(cand):
                    out.add(cand)
                    if len(out) >= cap:
                        return list(out)
    # double replacement
    if max_replacements >= 2:
        base_level = list(out) or [s]
        for base in base_level:
            for j, ch in enumerate(base):
                if ch in OPTICAL_ASCII:
                    for rep in OPTICAL_ASCII[ch][:max_per_char]:
                        cand = base[:j] + rep + base[j + 1 :]
                        if _is_valid_label(cand):
                            out.add(cand)
                            if len(out) >= cap:
                                return list(out)
    return list(out)

def gen_idn_homoglyphs(
    s: str,
    mapping_rev: Dict[str, List[str]],
    allowed_scripts: Optional[Set[str]] = None,
    max_per_char=2,
    max_replacements=2,
    cap=2000,
) -> List[str]:
    """
    Generate Unicode homoglyph variants using a reverse-confusable map.
    allowed_scripts restricts output to those containing only allowed scripts (best-effort).
    """
    out: Set[str] = set()
    # single replacement
    for i, ch in enumerate(s):
        cands = mapping_rev.get(ch, [])
        for rep in cands[:max_per_char]:
            cand = s[:i] + rep + s[i + 1 :]
            if _is_valid_label(cand):
                if allowed_scripts:
                    if not set(get_scripts(cand)).issubset(allowed_scripts.union({"Latin"})):
                        continue
                out.add(cand)
                if len(out) >= cap:
                    return list(out)
    # double replacement
    if max_replacements >= 2:
        base_level = list(out) or [s]
        for base in base_level:
            for j, ch in enumerate(base):
                cands = mapping_rev.get(ch, [])
                for rep in cands[:max_per_char]:
                    cand = base[:j] + rep + base[j + 1 :]
                    if _is_valid_label(cand):
                        if allowed_scripts:
                            if not set(get_scripts(cand)).issubset(allowed_scripts.union({"Latin"})):
                                continue
                        out.add(cand)
                        if len(out) >= cap:
                            return list(out)
    return list(out)

def gen_edit_typos(s: str, cap=1000) -> List[str]:
    # Simple deletion + transposition + substitution with neighbors (basic)
    neighbors = {
        'q': 'w', 'w': 'qe', 'e': 'wr', 'r': 'et', 't': 'ry', 'y': 'tu', 'u': 'yi', 'i': 'uo', 'o': 'ip', 'p': 'o',
        'a': 's', 's': 'ad', 'd': 'sf', 'f': 'dg', 'g': 'fh', 'h': 'gj', 'j': 'hk', 'k': 'jl', 'l': 'k',
        'z': 'x', 'x': 'zc', 'c': 'xv', 'v': 'cb', 'b': 'vn', 'n': 'bm', 'm': 'n'
    }
    out: Set[str] = set()
    # deletion
    for i in range(len(s)):
        cand = s[:i] + s[i+1:]
        if _is_valid_label(cand):
            out.add(cand)
            if len(out) >= cap: return list(out)
    # transpose
    for i in range(len(s)-1):
        cand = s[:i] + s[i+1] + s[i] + s[i+2:]
        if _is_valid_label(cand):
            out.add(cand)
            if len(out) >= cap: return list(out)
    # substitution
    for i,ch in enumerate(s):
        for rep in neighbors.get(ch, ''):
            cand = s[:i] + rep + s[i+1:]
            if _is_valid_label(cand):
                out.add(cand)
                if len(out) >= cap: return list(out)
    return list(out)

def gen_candidates(domain: str, max_count=400, enable_idn=True, scripts: Optional[Set[str]]=None,
                   idn_cap=2000, optical_cap=2000) -> List[str]:
    sld, tld = parse_domain(domain.lower())
    base: Set[str] = set()

    # ASCII edits and opticals first
    for cand_sld in gen_edit_typos(sld, cap=min(1000, max(200, max_count*5))):
        base.add(f"{cand_sld}.{tld}")
        if len(base) >= max_count * 4: break
    for cand_sld in gen_ascii_opticals(sld, cap=min(optical_cap, max_count*10)):
        base.add(f"{cand_sld}.{tld}")
        if len(base) >= max_count * 6: break

    # IDN homoglyphs (bounded)
    if enable_idn:
        allowed = None
        if scripts:
            allowed = {s for s in scripts if s in SUPPORTED_SCRIPTS}
        for cand_sld in gen_idn_homoglyphs(sld, HOMOGLYPH_REV_CORE, allowed_scripts=allowed, cap=idn_cap):
            ulabel = f"{cand_sld}.{tld}"
            # Keep only IDNA-valid
            alabel = idna_ascii(ulabel)
            if alabel:
                base.add(ulabel)
                if len(base) >= max_count * 8: break

    base.discard(domain)
    # light pruning: keep labels whose SLD len is ~close to original
    target_len = len(sld)
    pruned = [d for d in base if abs(len(tldextract.extract(d).domain) - target_len) <= 2]
    pruned = pruned or list(base)
    pruned.sort()
    return pruned[:max_count]

# ----------------- DNS / CT / WHOIS / DMARC -----------------
_resolver = dns.resolver.Resolver(configure=True)
_resolver.timeout = DNS_TIMEOUT_DEFAULT
_resolver.lifetime = DNS_TIMEOUT_DEFAULT

def dns_has(record: str, qtype: str, timeout: float) -> bool:
    try:
        _resolver.timeout = timeout
        _resolver.lifetime = timeout
        _resolver.resolve(record, qtype)
        return True
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.Timeout, dns.exception.DNSException):
        return False

def probe_dns(domain_unicode: str, timeout: float) -> Tuple[bool, bool, bool, bool, str]:
    """Return A, AAAA, MX, NS + ascii label used (punycode or ascii)."""
    ascii_label = idna_ascii(domain_unicode) or domain_unicode
    return (
        dns_has(ascii_label, "A", timeout),
        dns_has(ascii_label, "AAAA", timeout),
        dns_has(ascii_label, "MX", timeout),
        dns_has(ascii_label, "NS", timeout),
        ascii_label,
    )

def probe_dmarc(domain_unicode: str, timeout: float) -> Optional[bool]:
    try:
        ascii_label = idna_ascii(domain_unicode) or domain_unicode
        name = f"_dmarc.{ascii_label}"
        _resolver.timeout = timeout
        _resolver.lifetime = timeout
        ans = _resolver.resolve(name, "TXT")
        txts = [b"".join(r.strings).decode("utf-8", "ignore") for r in ans]
        for txt in txts:
            if txt.lower().startswith("v=dmarc1"):
                return True
        return False
    except Exception:
        return None  # unknown

def crt_has(client: requests.Session, domain_unicode: str, timeout: float) -> bool:
    """Query crt.sh for both Unicode and Punycode representations."""
    urls = [f"https://crt.sh/?q={domain_unicode}&output=json"]
    puny = idna_ascii(domain_unicode)
    if puny and puny != domain_unicode:
        urls.append(f"https://crt.sh/?q={puny}&output=json")
    found = False
    for url in urls:
        try:
            r = client.get(url, timeout=timeout, headers={"User-Agent": "DLaL/IDN-Scanner"})
            if r.status_code == 200:
                # sometimes returns HTML for "no results"; JSON parse guarded
                try:
                    data = r.json()
                    if isinstance(data, list) and len(data) > 0:
                        found = True
                        break
                except Exception:
                    continue
        except Exception:
            continue
    return found

def whois_created(domain_unicode: str, timeout: float) -> Optional[str]:
    if not pywhois:
        return None
    try:
        ascii_label = idna_ascii(domain_unicode) or domain_unicode
        # whois lib has no explicit timeout; rely on default socket timeouts of env
        w = pywhois.whois(ascii_label)
        date = None
        if isinstance(w.creation_date, list):
            date = w.creation_date[0]
        else:
            date = w.creation_date
        if isinstance(date, datetime):
            return date.replace(tzinfo=timezone.utc).isoformat()
        return None
    except Exception:
        return None

# ----------------- Risk classification & scoring -----------------
SKELETON_MAP = build_mapping_from_rev(HOMOGLYPH_REV_CORE)

def classify_risk(origin_sld: str, cand_sld: str) -> str:
    """
    Returns:
      whole_script_confusable | mixed_script_confusable | single_script_confusable |
      visual_near_miss | ""  (none)
    """
    if is_confusable(origin_sld, cand_sld, SKELETON_MAP):
        scripts = get_scripts(cand_sld)
        if len(scripts) == 1 and scripts[0] != "Latin":
            return "whole_script_confusable"
        if len(scripts) > 1:
            return "mixed_script_confusable"
        return "single_script_confusable"
    # very light near miss by normalized edit distance
    a, b = normalize_nfkc(origin_sld), normalize_nfkc(cand_sld)
    d = _levenshtein(a, b)
    mx = max(len(a), len(b)) or 1
    sim = 1.0 - (d / mx)
    return "visual_near_miss" if sim >= 0.85 else ""

def _levenshtein(a: str, b: str) -> int:
    if a == b: return 0
    if not a: return len(b)
    if not b: return len(a)
    prev = list(range(len(b)+1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            ins = cur[j-1] + 1
            dele = prev[j] + 1
            sub = prev[j-1] + (ca != cb)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]

def score_record(base_sld: str, cand_sld: str, a: bool, aaaa: bool, mx: bool, ns: bool,
                 has_ct: bool, created_iso: Optional[str], risk: str,
                 dmarc: Optional[bool]) -> float:
    score = 0.0
    # DNS presence
    if a or aaaa: score += 0.35
    if mx: score += 0.15
    if ns: score += 0.05
    # CT visibility
    if has_ct: score += 0.15
    # WHOIS recency
    if created_iso:
        try:
            dt = datetime.fromisoformat(created_iso.replace("Z","+00:00"))
            days = (datetime.now(timezone.utc) - dt).days
            if days <= 30: score += 0.20
            elif days <= 120: score += 0.10
        except Exception:
            pass
    # Risk
    if risk in ("whole_script_confusable", "mixed_script_confusable", "single_script_confusable"):
        score += 0.25
    elif risk == "visual_near_miss":
        score += 0.10
    # DMARC heuristic
    if dmarc is False and mx:  # MX present but DMARC missing
        score += 0.10
    return round(min(score, 1.0), 3)

# ----------------- Data model -----------------
@dataclass
class Record:
    domain_unicode: str
    domain_ascii: str
    A: bool
    AAAA: bool
    MX: bool
    NS: bool
    has_ct: bool
    whois_created: Optional[str]
    risk: str
    reason_exists: str
    score: float

# ----------------- Main scanning -----------------
def scan(domain: str, max_count: int, fast: bool, dns_timeout: float, http_timeout: float,
         use_ct: bool, use_whois: bool, use_idn: bool, scripts: Optional[Set[str]],
         idn_cap: int, optical_cap: int, use_dmarc: bool,
         top: Optional[int] = None) -> List[Record]:

    base_sld, base_tld = parse_domain(domain)
    candidates = gen_candidates(domain, max_count=max_count, enable_idn=use_idn, scripts=scripts,
                                idn_cap=idn_cap, optical_cap=optical_cap)

    sess = requests.Session()
    results: List[Record] = []

    for ulabel in candidates:
        # DNS probe (punycode inside)
        a, aaaa, mx, ns, ascii_label = probe_dns(ulabel, dns_timeout)
        dns_active = a or aaaa or mx or ns

        # fast mode: only enrich active
        has_ct = False
        created = None
        if (not fast) or dns_active:
            if use_ct:
                has_ct = crt_has(sess, ulabel, http_timeout)
            if use_whois:
                created = whois_created(ulabel, http_timeout)

        # dmarc
        dmarc = None
        if use_dmarc and ((not fast) or dns_active) and mx:
            dmarc = probe_dmarc(ulabel, dns_timeout)

        cand_sld, _ = parse_domain(ulabel)
        risk = classify_risk(base_sld, cand_sld)

        reasons = []
        if dns_active: reasons.append("dns_active")
        if has_ct: reasons.append("ct_seen")
        if created: reasons.append("whois_created")
        if risk: reasons.append("confusable")
        if dmarc is False: reasons.append("no_dmarc")

        score = score_record(base_sld, cand_sld, a, aaaa, mx, ns, has_ct, created, risk, dmarc)

        results.append(Record(
            domain_unicode=ulabel,
            domain_ascii=ascii_label,
            A=a, AAAA=aaaa, MX=mx, NS=ns,
            has_ct=has_ct,
            whois_created=created,
            risk=risk,
            reason_exists=",".join(reasons) if reasons else "",
            score=score
        ))

    # sort by score desc then by domain
    results.sort(key=lambda r: (-r.score, r.domain_unicode))
    if top:
        results = results[:top]
    return results

# ----------------- Export -----------------
def export_json(records: List[Record], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)

def export_csv(records: List[Record], path: str):
    if not records:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")  # empty
        return
    fields = list(asdict(records[0]).keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            w.writerow(asdict(r))

# ----------------- CLI -----------------
def main():
    print(ascii_art)
    ap = argparse.ArgumentParser(description="Lookalike/Homograph Domain Scanner (IDN-aware)")
    ap.add_argument("domain", help="Base domain, e.g., example.com")
    ap.add_argument("--max", type=int, default=200, help="Max candidate count (default 200)")
    ap.add_argument("--top", type=int, default=0, help="Keep top N by score (0 = keep all)")
    ap.add_argument("--fast", action="store_true", help="Only enrich (CT/WHOIS/DMARC) if DNS-active")
    ap.add_argument("--out", default="", help="Export to .json or .csv (auto format)")
    ap.add_argument("--dns-timeout", type=float, default=DNS_TIMEOUT_DEFAULT)
    ap.add_argument("--http-timeout", type=float, default=HTTP_TIMEOUT_DEFAULT)
    ap.add_argument("--no-ct", action="store_true", help="Disable CT lookups")
    ap.add_argument("--no-whois", action="store_true", help="Disable WHOIS lookups")
    ap.add_argument("--dmarc", action="store_true", help="Probe DMARC TXT (optional heuristic)")
    # IDN controls
    ap.add_argument("--idn", dest="idn", action=argparse.BooleanOptionalAction, default=True,
                    help="Enable/disable IDN homoglyph generation (default: enabled)")
    ap.add_argument("--scripts", default="", help="Comma-separated subset of scripts for IDN variants (Cyrillic,Greek,Han,Hiragana,Katakana)")
    ap.add_argument("--idn-max", type=int, default=2000, help="Cap of IDN variants before pruning")
    ap.add_argument("--optical-max", type=int, default=2000, help="Cap of ASCII optical variants before pruning")

    args = ap.parse_args()

    scripts = {s.strip() for s in args.scripts.split(",") if s.strip()} if args.scripts else None

    try:
        records = scan(
            domain=args.domain,
            max_count=args.max,
            fast=args.fast,
            dns_timeout=args.dns_timeout,
            http_timeout=args.http_timeout,
            use_ct=not args.no_ct,
            use_whois=not args.no_whois,
            use_idn=args.idn,
            scripts=scripts,
            idn_cap=args.idn_max,
            optical_cap=args.optical_max,
            use_dmarc=args.dmarc,
            top=(args.top or None),
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)

    # Print quick summary to stdout
    for r in records[: min(10, len(records))]:
        print(f"{r.domain_unicode} [{r.domain_ascii}] score={r.score} risk={r.risk} dns={'Y' if (r.A or r.AAAA or r.MX or r.NS) else 'N'} ct={'Y' if r.has_ct else 'N'}")

    if args.out:
        if args.out.lower().endswith(".json"):
            export_json(records, args.out)
            print(f"Wrote JSON -> {args.out}")
        elif args.out.lower().endswith(".csv"):
            export_csv(records, args.out)
            print(f"Wrote CSV -> {args.out}")
        else:
            print("Unknown output format (use .json or .csv)", file=sys.stderr)
            sys.exit(2)

if __name__ == "__main__":
    main()
