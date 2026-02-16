import gi
gi.require_version('Geoclue', '2.0')
from gi.repository import Geoclue, GLib
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
        # Inscreve-se para escutar quando o usuário digitar a keyword
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        # Inscreve-se para escutar quando um item for clicado
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        """Chamado quando o usuário digita a palavra-chave."""
        return [
            ExtensionResultItem(
                icon='images/icon.png',
                name='Obtendo localização...',
                description='Aguarde enquanto buscamos sua cidade.',
                on_enter=HideWindowAction()
            )
        ]

    def obter_e_mostrar_localizacao(self, extension):
        """Função auxiliar para buscar a localização e criar os resultados."""
        try:
            cliente = Geoclue.Simple.new_sync(
                "ulauncher.whereami",
                Geoclue.AccuracyLevel.EXACT,
                None, None
            )
            loc = cliente.get_location()
            if loc:
                lat = loc.get_property('latitude')
                lon = loc.get_property('longitude')
                if lat and lon:
                    # Faz a geocodificação reversa (em uma thread separada)
                    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
                    headers = {'User-Agent': 'UlauncherWhereAmI/1.0'}
                    resp = requests.get(url, headers=headers, timeout=5)
                    if resp.status_code == 200:
                        data = resp.json()
                        cidade = data.get('address', {}).get('city') or \
                                 data.get('address', {}).get('town') or \
                                 data.get('address', {}).get('village') or \
                                 data.get('address', {}).get('county')
                        if cidade:
                            return [
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
                                    on_enter=OpenAction(
                                        f"https://www.google.com/maps?q={lat},{lon}"
                                    )
                                )
                            ]
        except Exception as e:
            print(f"Erro: {e}")

        # Se algo falhar, retorna uma mensagem de erro
        return [ExtensionResultItem(
            icon='images/icon.png',
            name="❌ Erro ao obter localização",
            description="Tente novamente mais tarde.",
            on_enter=HideWindowAction()
        )]

class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        """Chamado quando um item é clicado (para ações personalizadas)."""
        # Por enquanto, não precisamos de ações complexas, mas este listener
        # é necessário se você quiser usar ExtensionCustomAction no futuro.
        return HideWindowAction()

if __name__ == '__main__':
    WhereAmI().run()
