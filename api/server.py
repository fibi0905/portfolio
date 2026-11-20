#!/usr/bin/env python3
"""API del form contatti: riceve il messaggio e lo inoltra via SMTP. Nessuna dipendenza esterna."""

import json
import os
import re
import smtplib
import ssl
import threading
import time
from email.message import EmailMessage
from email.utils import formataddr, formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "").strip()
SMTP_PASS = os.environ.get("SMTP_PASS", "").replace(" ", "")
MAIL_TO = os.environ.get("MAIL_TO", "").strip() or SMTP_USER
MAIL_FROM = os.environ.get("MAIL_FROM", "").strip() or SMTP_USER
SUBJECT_PREFIX = os.environ.get("SUBJECT_PREFIX", "[Portfolio]").strip() or "[Portfolio]"
RATE_MAX = int(os.environ.get("RATE_LIMIT_MAX", "5"))
RATE_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "600"))

PORT = 8000
MAX_BODY = 32 * 1024
EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")

_hits = {}
_lock = threading.Lock()


def rate_limited(ip):
    now = time.time()
    with _lock:
        recent = [t for t in _hits.get(ip, []) if now - t < RATE_WINDOW]
        if len(recent) >= RATE_MAX:
            _hits[ip] = recent
            return True
        recent.append(now)
        _hits[ip] = recent
        if len(_hits) > 5000:
            for key in [k for k, v in _hits.items() if not v or now - v[-1] >= RATE_WINDOW]:
                _hits.pop(key, None)
        return False


def one_line(value, limit):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def multi_line(value, limit):
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()[:limit]


def build_message(name, email, subject, message, ip):
    msg = EmailMessage()
    msg["Subject"] = f"{SUBJECT_PREFIX} {subject}"
    msg["From"] = formataddr((f"{name} (Portfolio)", MAIL_FROM))
    msg["To"] = MAIL_TO
    msg["Reply-To"] = formataddr((name, email))
    msg["Date"] = formatdate(localtime=True)
    msg.set_content(
        f"Nome: {name}\nEmail: {email}\nIP: {ip}\n\n{message}\n"
    )
    return msg


def smtp_send(msg):
    context = ssl.create_default_context()
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=20, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)


class Handler(BaseHTTPRequestHandler):
    server_version = "portfolio-api"

    def log_message(self, fmt, *args):
        pass

    def reply(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            return self.reply(200, {"ok": True})
        return self.reply(404, {"ok": False})

    def do_POST(self):
        if self.path != "/api/contact":
            return self.reply(404, {"ok": False})

        ip = self.headers.get("X-Real-IP") or self.client_address[0]

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return self.reply(400, {"ok": False, "error": "Richiesta non valida."})
        if length > MAX_BODY:
            return self.reply(413, {"ok": False, "error": "Messaggio troppo lungo."})

        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self.reply(400, {"ok": False, "error": "Richiesta non valida."})
        if not isinstance(data, dict):
            return self.reply(400, {"ok": False, "error": "Richiesta non valida."})

        if str(data.get("website") or "").strip():
            return self.reply(200, {"ok": True})  # honeypot

        if rate_limited(ip):
            return self.reply(429, {"ok": False, "error": "Troppi invii ravvicinati. Riprova tra qualche minuto."})

        name = one_line(data.get("name"), 100)
        email = one_line(data.get("email"), 254)
        subject = one_line(data.get("subject"), 150)
        message = multi_line(data.get("message"), 5000)

        if not (name and subject and EMAIL_RE.match(email) and len(message) >= 10):
            return self.reply(400, {"ok": False, "error": "Compila correttamente tutti i campi."})

        if not (SMTP_USER and SMTP_PASS and MAIL_TO):
            print("SMTP non configurato: imposta SMTP_USER, SMTP_PASS e MAIL_TO nel file .env", flush=True)
            return self.reply(503, {"ok": False, "error": "Servizio email non disponibile."})

        try:
            smtp_send(build_message(name, email, subject, message, ip))
        except Exception as exc:  # noqa: BLE001
            print(f"Invio email fallito: {type(exc).__name__}: {exc}", flush=True)
            return self.reply(502, {"ok": False, "error": "Invio non riuscito. Riprova tra poco."})

        print(f"Messaggio inviato (IP {ip})", flush=True)
        return self.reply(200, {"ok": True})


if __name__ == "__main__":
    if not (SMTP_USER and SMTP_PASS):
        print("Attenzione: SMTP_USER / SMTP_PASS non impostati, il form non potrà inviare email.", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
