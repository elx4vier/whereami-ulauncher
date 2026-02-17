import logging
import requests
import threading
import time

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction

logger = logging.getLogger(__name__)

CACHE_TEMPO = 300  # 5 minutos


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.cache = None
        self.cache_timestamp = 0


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        # Se cache válido, retorna imediatamente
        if extension.cache and (time.time() - extension.cache_timestamp < CACHE_TEMPO):
            return RenderResultListAction(extension.cache)

        # Busca em background
        threading.Thread(
            target=self.buscar_localizacao,
            args=(extension,),
            daemon=True
        ).start()

        return RenderResultListAction([
            ExtensionResultItem(
                icon='map-marker',
                name="Obtendo localização...",
                description="Aguarde um instante",
                on_enter=HideWindowAction()
            )
        ])

    def buscar_localizacao(self, extension):

        headers = {"User-Agent": "Ulauncher-OndeEstou"}

        apis = [
            "https://ipapi.co/json/",
            "http://ip-api.com/json/"
        ]

        data = None
        fonte_dados = None
        response = None

        for url in apis:
            try:
                response = requests.get(url, headers=headers, timeout=3)
                if response.status_code == 200:
                    data = response.json()
                    fonte_dados = url
                    break
            except Exception as e:
                logger.warning(f"Falha na API {url}: {e}")

        if not data:
            items = [
                ExtensionResultItem(
                    icon='error',
                    name="Não foi possível obter localização",
                    description="Verifique sua conexão",
                    on_enter=HideWindowAction()
                )
            ]
            extension.publish_event(RenderResultListAction(items))
            return

        # Normalização de campos (compatível com as 2 APIs)
        cidade = data.get('city', 'Desconhecida')
        regiao = data.get('region') or data.get('regionName', '')
        pais_nome = data.get('country_name') or data.get('country', '')
        country_code = data.get('country_code') or data.get('countryCode', '')
        ip = data.get('ip') or data.get('query', '')

        country_code = country_code.upper()

        # Emoji de bandeira
        def country_flag(code):
            if len(code) != 2:
                return ""
            return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

        flag = country_flag(country_code)

        # Linha formatada
        linha_local = cidade

        if regiao:
            linha_local += f", {regiao}"

        if country_code:
            linha_local += f" — {country_code} {flag}"

        # Detecta nome simples da API
        if "ipapi" in fonte_dados:
            fonte_nome = "ipapi.co"
        else:
            fonte_nome = "ip-api.com"

        # Simulação leve de centralização
        titulo = "Você está em:"
        espaco = " " * max(0, (len(linha_local) - len(titulo)) // 2)

        texto_principal = (
            f"{espaco}{titulo}\n\n"
            f"{linha_local}"
        )

        rodape = f"IP: {ip} • Dados: {fonte_nome}"

        items = [
            ExtensionResultItem(
                icon='map-marker',
                name=texto_principal,
                description=rodape,
                on_enter=CopyToClipboardAction(linha_local)
            )
        ]

        # Salva cache
        extension.cache = items
        extension.cache_timestamp = time.time()

        # Atualiza interface
        extension.publish_event(RenderResultListAction(items))


if __name__ == '__main__':
    OndeEstouExtension().run()
