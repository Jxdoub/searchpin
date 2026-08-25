#!/usr/bin/env python3
"""
Shared configuration constants for Searchpin.
Import from here instead of duplicating across files.
"""

import os

# ── Product identity ──────────────────────────────────────────
PRODUCT_NAME = os.environ.get("SEARCHPIN_NAME", "Searchpin")
DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ── Google via Serper.dev ─────────────────────────────────────
# Google CAPTCHA-walls shared datacenter IPs (/sorry redirect), so the
# google engine calls the Serper.dev JSON API instead of scraping HTML.
# Get a key at https://serper.dev (free tier: 2500 queries/month) and
# set SEARCHPIN_SERPER_API_KEY; without it the batch runs the four
# free engines and google is skipped silently.
SERPER_API_KEY = os.environ.get("SEARCHPIN_SERPER_API_KEY", "").strip()

# ── DNS-over-HTTPS endpoints (tried in order) ─────────────────
DOH_ENDPOINTS = [
    ("https://dns.google/resolve", "8.8.8.8"),
    ("https://cloudflare-dns.com/dns-query", "1.1.1.1"),
    ("https://dns.quad9.net/dns-query", "9.9.9.9"),
]

# ── Timing log (set SEARCHPIN_TIMING_LOG='' to disable) ──────
TIMING_LOG_PATH = os.environ.get("SEARCHPIN_TIMING_LOG", "/tmp/searchpin_timing.log")
