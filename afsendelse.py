# -*- coding: utf-8 -*-
"""Afsendelse af digesten.

Tre tilstande, styret af config.json -> "afsendelse":
  "brevo"  Brevos transaktions-API (samme tjeneste som klimamonitoren bruger)
  "smtp"   Almindelig SMTP med STARTTLS
  "ingen"  Skriv kun HTML-filen til udbakke/ — ingen afsendelse

Adgangskoder og API-nøgler læses UDELUKKENDE fra miljøvariabler eller .env.
De skrives aldrig i config.json og logges aldrig.
"""
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage

import requests

from config import hent_hemmelighed

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


class AfsendelsesFejl(RuntimeError):
    pass


def _via_brevo(emne: str, html_krop: str, tekst_krop: str, conf: dict) -> str:
    noegle = hent_hemmelighed("brevo_api_noegle")
    if not noegle:
        raise AfsendelsesFejl(
            "Mangler Brevo-nøgle. Sæt BREVO_API_KEY som miljøvariabel "
            "eller i .env-filen ved siden af scriptet."
        )
    if not conf.get("afsender"):
        raise AfsendelsesFejl('Sæt "afsender" i config.json (verificeret Brevo-afsender).')

    svar = requests.post(
        BREVO_URL,
        headers={"api-key": noegle, "content-type": "application/json",
                 "accept": "application/json"},
        json={
            "sender": {"email": conf["afsender"], "name": conf["afsender_navn"]},
            "to": [{"email": m} for m in conf["modtagere"]],
            "subject": emne,
            "htmlContent": html_krop,
            "textContent": tekst_krop,
        },
        timeout=30,
    )
    if svar.status_code >= 300:
        raise AfsendelsesFejl(f"Brevo svarede {svar.status_code}: {svar.text[:300]}")
    return f"sendt via Brevo til {', '.join(conf['modtagere'])}"


def _via_smtp(emne: str, html_krop: str, tekst_krop: str, conf: dict) -> str:
    kode = hent_hemmelighed("smtp_kode")
    if not kode:
        raise AfsendelsesFejl(
            "Mangler SMTP-kode. Sæt TEATERMONITOR_SMTP_KODE som miljøvariabel "
            "eller i .env-filen."
        )
    for felt in ("smtp_vaert", "smtp_bruger", "afsender"):
        if not conf.get(felt):
            raise AfsendelsesFejl(f'Sæt "{felt}" i config.json.')

    besked = EmailMessage()
    besked["Subject"] = emne
    besked["From"] = f"{conf['afsender_navn']} <{conf['afsender']}>"
    besked["To"] = ", ".join(conf["modtagere"])
    besked.set_content(tekst_krop)
    besked.add_alternative(html_krop, subtype="html")

    kontekst = ssl.create_default_context()
    with smtplib.SMTP(conf["smtp_vaert"], int(conf["smtp_port"]), timeout=30) as s:
        s.starttls(context=kontekst)
        s.login(conf["smtp_bruger"], kode)
        s.send_message(besked)
    return f"sendt via SMTP til {', '.join(conf['modtagere'])}"


def send(emne: str, html_krop: str, tekst_krop: str, conf: dict) -> str:
    """Send digesten. Returnerer en statusbesked."""
    tilstand = conf.get("afsendelse", "ingen")
    if tilstand == "ingen":
        return "afsendelse slået fra (skrev kun fil til udbakke/)"
    if not conf.get("modtagere"):
        raise AfsendelsesFejl('Ingen modtagere. Sæt "modtagere" i config.json.')
    if tilstand == "brevo":
        return _via_brevo(emne, html_krop, tekst_krop, conf)
    if tilstand == "smtp":
        return _via_smtp(emne, html_krop, tekst_krop, conf)
    raise AfsendelsesFejl(f'Ukendt afsendelsestilstand: "{tilstand}"')
