import logging
import requests
import time
import json
import os
import threading
import uuid

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action import RenderResultListAction, CopyToClipboardAction

logger = logging.getLogger(__name__)

CACHE_TTL = 300
CACHE_FILE = os.path.expanduser("~/.cache/onde_estou_cache.json")


def create_session():
    session = requests.Session()
    retries = Retry(total=2, backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.session = create_session()
        self.cache = None
        self.cache_time = 0
        self.base_path = os.path.dirname(os.path.abspath(__file__))

        # 🔥 Controle de concorrência
        self.current_request_id = None
        self.lock = threading.Lock()

    def icon(self, filename):
        path = os.path.join(self.base_path, "images", filename)
        return path if os.path.exists(path) else ""


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        # 🔐 Gera novo ID de requisição
        request_id = str(uuid.uuid4())

        with extension.lock:
            extension.current_request_id = request_id

        # 🚀 Thread única controlada
        thread = threading.Thread(
            target=self.background_fetch,
            args=(extension, request_id),
            daemon=True
        )
        thread.start()

        return RenderResultListAction([
            ExtensionResultItem(
                icon=extension.icon("loading.png"),
                name="Obtendo localização...",
                description="Consultando serviço..."
            )
        ])

    # ----------------------------------
    # 🔄 THREAD CONTROLADA
    # ----------------------------------
    def background_fetch(self, extension, request_id):

        try:
            geo = self.fetch_location(extension)

            # ❌ Se não for mais a requisição ativa → cancela silenciosamente
            if not self.is_active(extension, request_id):
                return

            cidade = geo.get("city", "Desconhecida")
            estado = geo.get("region", "")
            pais = geo.get("country_code", geo.get("countryCode", "")).upper()
            ip = geo.get("ip", geo.get("query", ""))

            bandeira = self.flag(pais)

            texto = (
                "Você está em:\n\n"
                f"{cidade}\n"
                f"{estado}\n"
                f"{pais} {bandeira}\n\n"
                f"IP: {ip}"
            ).strip()

            item = ExtensionResultItem(
                icon=extension.icon("icon.png"),
                name=texto,
                description="Fonte: ipapi.co | ip-api.com",
                on_enter=CopyToClipboardAction(f"{cidade}, {estado}, {pais}")
            )

        except Exception as e:

            if not self.is_active(extension, request_id):
                return

            logger.error(f"Erro async: {e}")

            item = ExtensionResultItem(
                icon=extension.icon("error.png"),
                name="Erro ao obter localização",
                description="Offline ou serviço indisponível",
                on_enter=CopyToClipboardAction("Erro")
            )

        # 🔁 Só atualiza se ainda for ativo
        if self.is_active(extension, request_id):
            extension._emit(RenderResultListAction([item]))

    # ----------------------------------
    # 🔐 Verifica se ainda é requisição válida
    # ----------------------------------
    def is_active(self, extension, request_id):
        with extension.lock:
            return extension.current_request_id == request_id

    # ----------------------------------
    # 🌍 Busca com cache
    # ----------------------------------
    def fetch_location(self, extension):

        now = time.time()

        if extension.cache and (now - extension.cache_time < CACHE_TTL):
            return extension.cache

        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r") as f:
                    data = json.load(f)
                    if now - data["timestamp"] < CACHE_TTL:
                        extension.cache = data["geo"]
                        extension.cache_time = now
                        return data["geo"]
            except Exception:
                pass

        try:
            r = extension.session.get("https://ipapi.co/json/", timeout=2)
            geo = r.json()
        except Exception:
            r = extension.session.get("http://ip-api.com/json/", timeout=2)
            geo = r.json()

        extension.cache = geo
        extension.cache_time = now

        try:
            os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
            with open(CACHE_FILE, "w") as f:
                json.dump({"timestamp": now, "geo": geo}, f)
        except Exception:
            pass

        return geo

    def flag(self, code):
        if len(code) != 2:
            return ""
        return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)


if __name__ == "__main__":
    OndeEstouExtension().run()
