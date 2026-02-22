import logging
import requests
import time
import os
import locale
import json

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

logger = logging.getLogger(__name__)
CACHE_TTL = 600


# 🌍 Detecta idioma do sistema
def get_lang():
    try:
        lang = locale.getdefaultlocale()[0]
        return lang if lang else "en"
    except Exception:
        return "en"


# 📦 Traduções com fallback inteligente
def load_translation(base_path, lang):
    try:
        translations_path = os.path.join(base_path, "translations")

        langs_to_try = []

        if lang:
            langs_to_try.append(lang)

            if "_" in lang:
                langs_to_try.append(lang.split("_")[0])

        langs_to_try.append("en")

        for l in langs_to_try:
            path = os.path.join(translations_path, f"{l}.json")

            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)

    except Exception:
        pass

    return {
        "title": "Where Am I?",
        "unknown": "Unknown",
        "error": "Error",
        "source": "Source",
        "copy_format": "{city}, {region}, {country} (IP: {ip})"
    }


# 🌐 Sessão HTTP
def create_session():
    session = requests.Session()
    retries = Retry(total=0, backoff_factor=0.1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class WhereAmIExtension(Extension):
    def __init__(self):
        super().__init__()

        self.base_path = os.path.dirname(os.path.abspath(__file__))

        self.lang = get_lang()
        self.t = load_translation(self.base_path, self.lang)

        self.keyword = self.preferences.get("kw") or "l"

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesUpdateEvent, PreferencesEventListener())

        self.session = create_session()
        self.cache = None
        self.cache_time = 0

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        if os.path.exists(path):
            return path
        return os.path.join(self.base_path, "images", "icon.png")


class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.keyword = event.preferences.get("kw") or "l"


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        try:
            if event.get_keyword() != extension.keyword:
                return RenderResultListAction([])

            now = time.time()

            if extension.cache and (now - extension.cache_time < CACHE_TTL):
                geo = extension.cache
            else:
                geo = self.fetch_location(extension)
                extension.cache = geo
                extension.cache_time = now

            t = extension.t

            cidade = geo.get("city") or t["unknown"]
            estado = geo.get("region") or ""
            code = geo.get("country_code") or ""
            ip = geo.get("ip") or "N/A"
            lat = geo.get("lat")
            lon = geo.get("lon")
            provider = geo.get("provider", "API")

            pais_sigla = code.upper() if code else "??"
            bandeira = self.flag(code)

            # 🧾 TEXTO PRINCIPAL (GRANDE)
            linhas = [t["title"], "", f"{cidade}"]

            if estado:
                linhas.append(estado)

            # país
            linhas.append(f"{pais_sigla} {bandeira}")

            # linha vazia após país
            linhas.append("")

            texto_principal = "\n".join(linhas)

            # 🔽 DESCRIÇÃO (MENOR): coord → IP → fonte
            desc_linhas = []

            if lat and lon:
                desc_linhas.append(f"{lat}, {lon}")

            desc_linhas.append(f"IP: {ip}")
            desc_linhas.append(f"{t['source']}: {provider}")

            descricao = " • ".join(desc_linhas)

            # 📋 Texto para copiar
            copia = t.get(
                "copy_format",
                "{city}, {region}, {country} (IP: {ip})"
            ).format(
                city=cidade,
                region=estado,
                country=pais_sigla,
                ip=ip,
                lat=lat or "",
                lon=lon or ""
            )

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=texto_principal,
                    description=descricao,
                    on_enter=CopyToClipboardAction(copia)
                )
            ])

        except Exception as e:
            logger.error(f"Erro: {e}")

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=extension.t["error"],
                    description="",
                    on_enter=None
                )
            ])

    def fetch_location(self, extension):
        apis = [
            ("https://ip-api.com/json/", "ip-api.com", 2),
            ("https://freeipapi.com/api/json", "freeipapi.com", 2),
            ("https://ipapi.co/json/", "ipapi.co", 2),
            ("https://ipinfo.io/json", "ipinfo.io", 3)
        ]

        for url, name, timeout in apis:
            try:
                r = extension.session.get(url, timeout=timeout)

                if r.status_code != 200:
                    continue

                data = r.json()

                if data.get("status") == "fail" or "error" in data:
                    continue

                lat = (
                    data.get("lat")
                    or data.get("latitude")
                    or (data.get("loc").split(",")[0] if data.get("loc") else None)
                )

                lon = (
                    data.get("lon")
                    or data.get("longitude")
                    or (data.get("loc").split(",")[1] if data.get("loc") else None)
                )

                return {
                    "ip": data.get("query") or data.get("ip") or data.get("ipAddress"),
                    "city": data.get("city") or data.get("cityName"),
                    "region": data.get("regionName") or data.get("region"),
                    "country_code": (data.get("countryCode") or data.get("country_code") or "")[:2],
                    "lat": lat,
                    "lon": lon,
                    "provider": name
                }

            except Exception:
                continue

        return {
            "city": None,
            "region": None,
            "ip": "N/A",
            "country_code": "",
            "lat": None,
            "lon": None,
            "provider": "Unavailable"
        }

    def flag(self, code):
        if not code or len(code) != 2:
            return ""
        return chr(ord(code[0].upper()) + 127397) + chr(ord(code[1].upper()) + 127397)


if __name__ == "__main__":
    WhereAmIExtension().run()
