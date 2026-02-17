import logging
import requests
import os
import tempfile

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


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        try:
            # 🌍 Localização
            geo = requests.get("https://ipapi.co/json/", timeout=4).json()

            cidade = geo.get("city", "")
            estado = geo.get("region", "")
            country_code = geo.get("country_code", "").upper()

            # 🇧🇷 Bandeira dinâmica
            def flag(code):
                if len(code) != 2:
                    return ""
                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

            bandeira = flag(country_code)

            # 🖼 Buscar imagem da cidade
            icon_path = 'map-marker'

            try:
                wiki = requests.get(
                    f"https://pt.wikipedia.org/api/rest_v1/page/summary/{cidade}",
                    timeout=4
                ).json()

                if "thumbnail" in wiki:
                    img_url = wiki["thumbnail"]["source"]
                    img_data = requests.get(img_url, timeout=4).content

                    tmp_dir = tempfile.gettempdir()
                    icon_path = os.path.join(tmp_dir, "cidade.png")

                    with open(icon_path, "wb") as f:
                        f.write(img_data)

            except Exception:
                pass  # se falhar, usa ícone padrão

            # 📝 Montagem visual
            titulo = "Você está em:\n"

            linha_estado = f"{estado}\n" if estado else ""

            texto = (
                f"{titulo}\n"
                f"{cidade}\n"
                f"{linha_estado}"
                f"{country_code} {bandeira}"
            )

            rodape = "Fontes: ipapi.co • Wikimedia"

            return RenderResultListAction([
                ExtensionResultItem(
                    icon=icon_path,
                    name=texto,
                    description=rodape,
                    on_enter=CopyToClipboardAction(f"{cidade}, {estado}, {country_code}")
                )
            ])

        except Exception as e:
            logger.error(e)

            return RenderResultListAction([
                ExtensionResultItem(
                    icon='dialog-error',
                    name="Erro ao obter localização",
                    description="Verifique sua conexão",
                    on_enter=CopyToClipboardAction("Erro")
                )
            ])


if __name__ == "__main__":
    OndeEstouExtension().run()
