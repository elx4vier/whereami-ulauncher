import requests
import time

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction

# Chaves API
IPSTACK_KEY = "51adc2e31921227b91c2fc04190b174e"
GOOGLE_API_KEY = "AIzaSyChY5KA-9Fgzz4o-hvhny0F1YKimAFrbzo"

# Cache de 10 minutos
_last_location = None
_last_timestamp = 0
CACHE_TIMEOUT = 600  # segundos

def extrair_cidade_estado_pais(geo_data):
    """
    Extrai cidade, estado e país do JSON da Google Geocoding API de forma robusta.
    """
    cidade = estado = pais = None
    for result in geo_data.get("results", []):
        for comp in result.get("address_components", []):
            types = comp.get("types", [])
            if not cidade and any(t in types for t in ["locality", "sublocality", "postal_town"]):
                cidade = comp.get("long_name")
            if not estado and "administrative_area_level_1" in types:
                estado = comp.get("long_name")
            if not pais and "country" in types:
                pais = comp.get("long_name")
        if cidade and estado and pais:
            break
    return cidade, estado, pais


class WhereAmIIPstackGoogle(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        global _last_location, _last_timestamp

        # Retorna cache se recente
        if _last_location and (time.time() - _last_timestamp) < CACHE_TIMEOUT:
            return RenderResultListAction(_last_location)

        try:
            # 1️⃣ Obter lat/lon via IPstack
            url_ip = f"https://api.ipstack.com/check?access_key={IPSTACK_KEY}"
            resp = requests.get(url_ip, timeout=5)
            resp.raise_for_status()
            ip_data = resp.json()
            lat = ip_data.get("latitude")
            lon = ip_data.get("longitude")
            if lat is None or lon is None:
                return self._mostrar_erro(extension, "Não foi possível obter latitude/longitude via IPstack")

            # 2️⃣ Geocodificação reversa via Google Maps
            url_geo = f"https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lon}&key={GOOGLE_API_KEY}"
            resp = requests.get(url_geo, timeout=5)
            resp.raise_for_status()
            geo_data = resp.json()

            cidade, estado, pais = extrair_cidade_estado_pais(geo_data)

            if not cidade or not estado or not pais:
                return self._mostrar_erro(extension, "Não foi possível extrair cidade/estado/país")

            texto = f"{cidade}, {estado} — {pais}"

            itens = [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                ),
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="🌐 Abrir no Google Maps",
                    description="Ver localização no mapa",
                    on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                )
            ]

            # Atualiza cache
            _last_location = itens
            _last_timestamp = time.time()

            return RenderResultListAction(itens)

        except Exception as e:
            return self._mostrar_erro(extension, f"Erro ao obter localização: {e}")

    def _mostrar_erro(self, extension, mensagem):
        return RenderResultListAction([
            ExtensionResultItem(
                icon="images/icon.png",
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=None
            )
        ])


if __name__ == "__main__":
    WhereAmIIPstackGoogle().run()
