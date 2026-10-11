import os
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None
    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    # auto mode – try real first, then fallback to MailHog
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False
    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délais réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))
    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False
    host, port, use_ssl, need_login = transport
    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None
    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    # auto mode – try real first, then fallback to MailHog
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False
    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délais réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))
    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False
    host, port, use_ssl, need_login = transport
    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None
    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    # auto mode – try real first, then fallback to MailHog
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False
    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délais réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))
    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False
    host, port, use_ssl, need_login = transport
    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None
    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    # auto mode – try real first, then fallback to MailHog
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False
    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délais réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))
    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False
    host, port, use_ssl, need_login = transport
    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False

import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None

    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)

    # auto mode – try real first, fall back to MailHog if needed
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False

    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False

    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délais réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False

    host, port, use_ssl, need_login = transport

    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False

import smtplib

import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – disables all e‑mail alerts when false
EMAIL_ALERTES_ACTIVEES = os.getenv("EMAIL_ALERTES_ACTIVEES", "false").lower() == "true"

# Optional MailHog fallback (useful for local development)
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout (5 s)."""
    timeout = 5  # seconds – fail fast on unreachable network
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False

def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not EMAIL_ALERTES_ACTIVEES or SMTP_MODE == "disable":
        return None

    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)

    # auto mode – try real first, fall back to MailHog if needed
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public async function used by the rest of the code base
# ------------------------------------------------------------
async def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail without blocking the event loop.
    The heavy SMTP work is executed in a thread via ``asyncio.to_thread``.
    Returns True on success, False on any failure (including when alerts are disabled)."""
    if not EMAIL_ALERTES_ACTIVEES:
        print("[EMAIL] Alerts disabled (EMAIL_ALERTES_ACTIVEES=False). Skipping send.")
        return False

    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False

    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délai réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    transport = _select_transport()
    if transport is None:
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False

    host, port, use_ssl, need_login = transport

    def _send_sync():
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)

    try:
        await asyncio.to_thread(_send_sync)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False



from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------------------------------------------------
# Environment configuration (all values read from .env or system)
# ------------------------------------------------------------
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USE_SSL = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# Master switch – completely disables e‑mail sending (useful for CI)
SEND_EMAILS = os.getenv("SEND_EMAILS", "true").lower() == "true"

# Mode selection – auto tries real SMTP first, then falls back to MailHog
SMTP_MODE = os.getenv("SMTP_MODE", "auto").lower()  # auto | mailhog | disable

# MailHog (local dummy server) defaults – used for fallback
MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))

# ------------------------------------------------------------
# Helper to create an SMTP client according to the chosen security
# ------------------------------------------------------------
def _make_smtp_client(host: str, port: int, use_ssl: bool):
    """Return an SMTP client (SSL or STARTTLS) with a short timeout."""
    timeout = 10  # seconds – prevents hanging forever
    if use_ssl:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)
    else:
        client = smtplib.SMTP(host, port, timeout=timeout)
        client.starttls()
        return client

# ------------------------------------------------------------
# Connectivity checks – used when SMTP_MODE=auto
# ------------------------------------------------------------
def _try_real_smtp() -> bool:
    """Attempt a quick login to the configured real SMTP server.
    Returns True on success, False on any error (timeout, auth, network)."""
    try:
        with _make_smtp_client(SMTP_HOST, SMTP_PORT, SMTP_USE_SSL) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
        return True
    except Exception as e:
        print(f"[EMAIL] Real SMTP unreachable or auth failed: {e}")
        return False


def _try_mailhog() -> bool:
    """Check that a local MailHog server is reachable (no auth needed)."""
    try:
        with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=5) as server:
            server.noop()
        return True
    except Exception as e:
        print(f"[EMAIL] MailHog not reachable: {e}")
        return False

# ------------------------------------------------------------
# Choose the transport based on env and connectivity
# ------------------------------------------------------------
def _select_transport():
    """Decide which SMTP endpoint to use.
    Returns a tuple (host, port, use_ssl, need_login) or None to skip.
    """
    if not SEND_EMAILS or SMTP_MODE == "disable":
        return None

    if SMTP_MODE == "mailhog":
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)

    # auto mode – try real first, fall back to MailHog if needed
    if _try_real_smtp():
        return (SMTP_HOST, SMTP_PORT, SMTP_USE_SSL, True)
    elif _try_mailhog():
        print("[EMAIL] Falling back to MailHog (local dummy server).")
        return (MAILHOG_HOST, MAILHOG_PORT, False, False)
    else:
        print("[EMAIL] No SMTP server reachable – e‑mail will be dropped.")
        return None

# ------------------------------------------------------------
# Public function used by the rest of the code base
# ------------------------------------------------------------
def envoyer_email_alerte(destinataire: str, numero_demande: str,
                         direction: str, jours_restants: int) -> bool:
    """Send a priority alert e‑mail.
    Returns True on success, False on any failure (including when sending is disabled).
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("[EMAIL] Missing SMTP_USER or SMTP_PASSWORD – email not sent.")
        return False

    # Build the email message
    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM
    msg["To"] = destinataire
    msg["Subject"] = (
        f"⚠️ Alerte prioritaire — Demande {numero_demande} "
        f"({jours_restants} jours restants)"
    )
    corps = f"""\
Bonjour,

La demande {numero_demande}, affectée à la direction {direction}, arrive à échéance légale\n
dans {jours_restants} jour(s) (délai réglementaire de 60 jours, Décret n° 2.17.265, article 8).\n
Merci de traiter ce dossier en priorité.

-- Plateforme GEDEC
"""
    msg.attach(MIMEText(corps, "plain", "utf-8"))

    transport = _select_transport()
    if transport is None:
        # Sending disabled or no reachable server – log the message for debugging
        print("[EMAIL] *** DROPPED MESSAGE ***")
        print(msg.as_string())
        return False

    host, port, use_ssl, need_login = transport
    try:
        with _make_smtp_client(host, port, use_ssl) as server:
            if need_login:
                server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        print(f"[EMAIL] Alerte envoyée avec succès à {destinataire} pour {numero_demande}.")
        return True
    except Exception as e:
        print(f"[EMAIL] Échec de l'envoi à {destinataire} : {e}")
        return False