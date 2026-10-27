"""Bounded evidence handling shared by collection, diagnostics and reporting."""
import os
import re

MAX_BYTES = 16000


def redact(text):
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", str(text))
    text = re.sub(r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----", "[REDACTED PRIVATE KEY]", text, flags=re.S)
    for name, value in os.environ.items():
        if re.search(r"TOKEN|PASSWORD|SECRET|API_KEY|PRIVATE_KEY|CREDENTIAL", name, re.I) and len(value) >= 4:
            text = text.replace(value, "[REDACTED]")
    text = re.sub(r"(?i)(authorization\s*[:=]\s*)(?:bearer|basic)\s+[^\s\"']+", r"\1[REDACTED]", text)
    text = re.sub(r"(?i)((?:[\w.-]*(?:password|passwd|secret|token|api[_-]?key)[\w.-]*)[\"']?\s*[:=]\s*)[\"']?[^\s,\"'}]+", r"\1[REDACTED]", text)
    text = re.sub(r"(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", text)
    text = re.sub(r"\b(?:gh[pousr]_[A-Za-z0-9_]+|glpat-[A-Za-z0-9_-]+|AKIA[A-Z0-9]{16})\b", "[REDACTED]", text)
    return text


def bounded(text, limit=MAX_BYTES):
    # Redact before truncating so truncation cannot cut a secret in half.
    return redact(text).encode()[-limit:].decode(errors="replace")
