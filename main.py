import requests
from threading import Thread

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction


class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        return RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name='🌍 Descobrir minha localização',
                description='Pressione Enter para buscar sua cidade',
                on_enter=ExtensionCustomAction({'action': 'buscar'}, keep_app_open=True)
            )
        ])


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        data = event.get_data()

        if data.get('action') == 'buscar':
            extension.window.show_results(RenderResultListAction([
                ExtensionResultItem(
                    icon='images/icon.png',
                    name='🔎 Buscando localização...',
                    description='Aguarde um momento...',
                    on_enter=HideWindowAction()
                )
            ]))

            Thread(target=self._buscar_localizacao, args=(extension,)).start()
            return None

        return HideWindowAction()

    def _buscar_localizacao(self, extension):
        try:
            # Serviço simples de geolocalização por IP
            resp = requests.get("https://ipapi.co/json/", timeout=5)

            if resp.status_code == 200:
                dados = resp.json()

                cidade = dados.get("city")
                lat = dados.get("latitude")
                lon = dados.get("longitude")

                if cidade and lat and lon:
                    self._mostrar_resultado(extension, cidade, lat, lon)
                else:
                    self._mostrar_erro(extension, "Cidade não encontrada")
            else:
                self._mostrar_erro(extension, f"Erro HTTP {resp.status_code}")

        except Exception as e:
            self._mostrar_erro(extension, f"Erro: {e}")

    def _mostrar_resultado(self, extension, cidade, lat, lon):
        extension.window.show_results(RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name=f"📍 Você está em: {cidade}",
                description="Clique para copiar o nome da cidade",
                on_enter=CopyToClipboardAction(cidade)
            ),
            ExtensionResultItem(
                icon='images/icon.png',
                name="🌐 Abrir no Google Maps",
                description="Ver localização no mapa",
                on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
            )
        ]))

    def _mostrar_erro(self, extension, mensagem):
        extension.window.show_results(RenderResultListAction([
            ExtensionResultItem(
                icon='images/icon.png',
                name="❌ Erro ao obter localização",
                description=mensagem,
                on_enter=HideWindowAction()
            )
        ]))


if __name__ == '__main__':
    WhereAmI().run()
