import logging
import requests
import time
import os

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action import RenderResultListAction, CopyToClipboardAction

logger = logging.getLogger(__name__)
CACHE_TTL = 300


# --------------------------------------------------
# 🔥 Session otimizada
# --------------------------------------------------
def create_session():
    session = requests.Session()
    retry = Retry(total=2, backoff_factor=0.3,
                  status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# --------------------------------------------------
# 🚀 EXTENSION
# --------------------------------------------------
class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, Query())
        self.session = create_session()
        self.cache = None
        self.cache_time = 0
        self.base = os.path.dirname(os.path.abspath(__file__))

    def icon(self, name):
        path = os.path.join(self.base, "images", name)
        return path if os.path.exists(path) else ""


# --------------------------------------------------
# 🎯 LISTENER
# --------------------------------------------------
class Query(EventListener):

    def on_event(self, event, ext):

        try:
            geo = self.get_geo(ext)
            text = self.build_text(ext, geo)
            copy_value = self.build_copy(ext, geo)

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ext.icon("icon.png"),
                    name=text,
                    description="Fonte: ipapi.co | ip-api.com",
                    on_enter=CopyToClipboardAction(copy_value)
                )
            ])

        except Exception as e:
            logger.error(e)
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=ext.icon("error.png"),
                    name="Erro ao obter localização",
                    description="Verifique sua conexão",
                    on_enter=CopyToClipboardAction("Erro")
                )
            ])

    # --------------------------------------------------
    # 🌍 Geo com cache + normalização
    # --------------------------------------------------
    def get_geo(self, ext):

        if ext.cache and time.time() - ext.cache_time < CACHE_TTL:
            return ext.cache

        for url in ("https://ipapi.co/json/", "http://ip-api.com/json/"):
            try:
                r = ext.session.get(url, timeout=2)
                if r.status_code == 200:
                    data = self.normalize(r.json())
                    ext.cache = data
                    ext.cache_time = time.time()
                    return data
            except Exception:
                continue

        raise Exception("Falha nas APIs")

    # --------------------------------------------------
    # 🔄 Normalização padrão
    # --------------------------------------------------
    def normalize(self, data):
        return {
            "city": data.get("city", "Desconhecida"),
            "region": data.get("region", ""),
            "country": data.get("country_name") or data.get("country", ""),
            "code": (data.get("country_code") or data.get("countryCode") or "").upper(),
            "ip": data.get("ip") or data.get("query", "")
        }

    # --------------------------------------------------
    # 🎨 Layout
    # --------------------------------------------------
    def build_text(self, ext, geo):

        prefs = ext.preferences

        show_state = prefs.get("mostrar_estado", "sim") == "sim"
        show_flag = prefs.get("mostrar_bandeira", "sim") == "sim"
        show_ip = prefs.get("mostrar_ip", "sim") == "sim"

        flag = self.flag(geo["code"]) if show_flag else ""

        lines = [
            "Sua localização atual é:",
            "",
            geo["city"],
        ]

        if geo["region"] and show_state:
            lines.append(geo["region"])

        lines.append(f"{geo['country']} {flag}".strip())

        if show_ip and geo["ip"]:
            lines.append("")
            lines.append(f"IP: {geo['ip']}")

        return "\n".join(lines)

    # --------------------------------------------------
    # 📋 Copy format
    # --------------------------------------------------
    def build_copy(self, ext, geo):

        fmt = ext.preferences.get("formato_copia", "cidade_estado_pais")

        if fmt == "cidade":
            return geo["city"]
        if fmt == "cidade_pais":
            return f"{geo['city']}, {geo['country']}"
        if fmt == "ip":
            return geo["ip"]

        return f"{geo['city']}, {geo['region']}, {geo['country']}"

    # --------------------------------------------------
    # 🇧🇷 Emoji bandeira
    # --------------------------------------------------
    def flag(self, code):
        if len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


if __name__ == "__main__":
    OndeEstouExtension().run()
