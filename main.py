import logging
import requests
import os

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction

logger = logging.getLogger(__name__)


class OndeEstouExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())

        # 📁 Caminho absoluto da pasta da extensão
        self.base_path = os.path.dirname(os.path.abspath(__file__))

    def icon(self, name):
        return os.path.join(self.base_path, "images", name)


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        try:
            geo = requests.get("https://ipapi.co/json/", timeout=4).json()

            if not geo or "city" not in geo:
                return self.alert(extension, "Não foi possível obter localização")

            cidade = geo.get("city", "")
            estado = geo.get("region", "")
            country_code = geo.get("country_code", "").upper()

            # 🔧 Preferências
            mostrar_estado = extension.preferences.get("mostrar_estado", "sim")
            mostrar_bandeira = extension.preferences.get("mostrar_bandeira", "sim")
            copiar_formato = extension.preferences.get("formato_copia", "cidade_estado_pais")

            # 🇧🇷 Bandeira
            def flag(code):
                if len(code) != 2:
                    return ""
                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

            bandeira = flag(country_code) if mostrar_bandeira == "sim" else ""

            linha_estado = ""
            if estado and mostrar_estado == "sim":
                linha_estado = f"{estado}\n"

            titulo = "Você está em:\n"

            texto = (
                f"{titulo}\n"
                f"{cidade}\n"
                f"{linha_estado}"
                f"{country_code} {bandeira}"
                f"\n"  # 👈 Espaçamento leve antes das fontes
            )

            rodape = "Fontes: ipapi.co"

            # 📋 Texto copiado
            if copiar_formato == "cidade":
                copia = cidade
            elif copiar_formato == "cidade_pais":
                copia = f"{cidade}, {country_code}"
            else:
                copia = f"{cidade}, {estado}, {country_code}"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("icon.png"),
                    name=texto,
                    description=rodape,
                    on_enter=CopyToClipboardAction(copia)
                )
            ])

        except requests.exceptions.Timeout:
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("alert.png"),
                    name="Tempo de conexão excedido",
                    description="Verifique sua internet",
                    on_enter=CopyToClipboardAction("")
                )
            ])

        except Exception as e:
            logger.error(e)
            return RenderResultListAction([
                ExtensionResultItem(
                    icon=extension.icon("error.png"),
                    name="Erro inesperado",
                    description="Não foi possível obter localização",
                    on_enter=CopyToClipboardAction("")
                )
            ])

    def alert(self, extension, mensagem):
        return RenderResultListAction([
            ExtensionResultItem(
                icon=extension.icon("alert.png"),
                name=mensagem,
                description="",
                on_enter=CopyToClipboardAction("")
            )
        ])


if __name__ == "__main__":
    OndeEstouExtension().run()
