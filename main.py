import requests
import time
from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

GOOGLE_API_KEY = "AIzaSyChY5KA-9Fgzz4o-hvhny0F1YKimAFrbzo"
_last_result_itens = None
_last_timestamp = 0
CACHE_TIMEOUT = 600  # 10 minutos

ICONE_PADRAO = "images/icon.png"
ICONE_ERRO = "images/error.png"


def extrair_cidade_estado_pais(geo_data):
    cidade = estado = pais = codigo_pais = None
    for result in geo_data.get("results", []):
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if not cidade and any(t in types for t in ["locality", "postal_town", "administrative_area_level_2"]):
                cidade = comp.get("long_name")
            if not estado and "administrative_area_level_1" in types:
                estado = comp.get("long_name")
            if not pais and "country" in types:
                pais = comp.get("long_name")
                codigo_pais = comp.get("short_name")
        if cidade and pais:
            break
    return cidade, estado, pais, codigo_pais


def country_code_to_emoji(code):
    if not code or len(code) != 2:
        return ""
    return chr(ord(code[0].upper()) + 127397) + chr(ord(code[1].upper()) + 127397)


class OndeEstouExtension(Extension):
    def __init__(self):
        super().__init__()
        self.keyword = self.preferences.get("keyword") or "ondeestou"
        self.subscribe(KeywordQueryEvent, OndeEstouKeywordListener(self.keyword))


class OndeEstouKeywordListener(EventListener):
    def __init__(self, keyword):
        self.keyword = keyword

    def on_event(self, event, extension):
        global _last_result_itens, _last_timestamp

        # Sempre mostra o item inicial quando a query está vazia ou parcial
        if not event.get_argument().strip():
            item_inicial = ExtensionResultItem(
                icon=ICONE_PADRAO,
                name="Onde eu estou?",
                description="Mostra sua localização atual",
                on_enter=None  # ou pode colocar uma ação se quiser
            )
            return RenderResultListAction([item_inicial])

        # Se tem cache válido → mostra só o resultado
        if _last_result_itens and (time.time() - _last_timestamp) < CACHE_TIMEOUT:
            return RenderResultListAction(_last_result_itens)

        # Busca nova localização
        try:
            # 1. Geolocalização via IP
            url_geo = f"https://www.googleapis.com/geolocation/v1/geolocate?key={GOOGLE_API_KEY}"
            resp = requests.post(url_geo, json={"considerIp": True}, timeout=5)
            resp.raise_for_status()
            loc = resp.json().get("location")
            if not loc:
                return self._mostrar_erro(extension, "Não foi possível obter lat/lon")

            lat, lon = loc["lat"], loc["lng"]

            # 2. Reverse geocoding
            url_rev = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
            resp = requests.get(url_rev, timeout=5)
            resp.raise_for_status()
            geo_data = resp.json()

            cidade, estado, pais, codigo_pais = extrair_cidade_estado_pais(geo_data)
            if not cidade or not pais:
                return self._mostrar_erro(extension, "Não foi possível extrair cidade/país")

            bandeira = country_code_to_emoji(codigo_pais)

            # Formatação com Markdown do Ulauncher
            nome = f"<b>{cidade}</b>"
            desc = f"<i>{estado}, {pais} {bandeira}</i>" if estado else f"<i>{pais} {bandeira}</i>"

            texto_clipboard = f"{cidade}, {estado} — {pais}" if estado else f"{cidade} — {pais}"

            itens = [
                ExtensionResultItem(
                    icon=ICONE_PADRAO,
                    name=nome,
                    description=desc,
                    on_enter=CopyToClipboardAction(texto_clipboard)
                )
            ]

            _last_result_itens = itens
            _last_timestamp = time.time()

            return RenderResultListAction(itens)

        except Exception as e:
            return self._mostrar_erro(extension, f"Erro: {str(e)}")

    def _mostrar_erro(self, extension, mensagem):
        return RenderResultListAction([
            ExtensionResultItem(
                icon=ICONE_ERRO,
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ])


if __name__ == "__main__":
    OndeEstouExtension().run()
