import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction

# Sua chave API do IPstack
API_KEY = "51adc2e31921227b91c2fc04190b174e"

# Cache para reduzir requisições
_last_location = None
_last_timestamp = 0
CACHE_TIMEOUT = 600  # segundos = 10 minutos

import time

class WhereAmIIPstack(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        global _last_location, _last_timestamp

        # Verifica cache
        if _last_location and (time.time() - _last_timestamp) < CACHE_TIMEOUT:
            return RenderResultListAction(_last_location)

        try:
            # Requisição ao IPstack
            url = f"https://api.ipstack.com/check?access_key={API_KEY}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()

            cidade = data.get("city")
            estado = data.get("region_name")
            pais = data.get("country_name")
            lat = data.get("latitude")
            lon = data.get("longitude")

            if not cidade or not estado or not pais:
                return self._mostrar_erro(extension, "Dados de localização incompletos")

            texto = f"{cidade}, {estado} — {pais}"

            itens = [
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                )
            ]

            if lat is not None and lon is not None:
                itens.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name="🌐 Abrir no Google Maps",
                        description="Ver localização no mapa",
                        on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                    )
                )

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
    WhereAmIIPstack().run()
