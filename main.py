import gi
gi.require_version("Geoclue", "2.0")
from gi.repository import Geoclue, GLib
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.OpenAction import OpenAction


class WhereAmI(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())


class KeywordQueryEventListener(EventListener):
    TIMEOUT_SECONDS = 5

    def on_event(self, event, extension):
        try:
            # Cria cliente Geoclue
            client = Geoclue.Simple.new_sync(
                "io.ulauncher.Ulauncher",
                Geoclue.AccuracyLevel.CITY,
                None
            )

            # Pega localização imediatamente
            loc = client.props.location

            if loc:
                lat = loc.get_property("latitude")
                lon = loc.get_property("longitude")
                if lat is not None and lon is not None:
                    # tenta geocodificação reversa
                    resultado = self._geocode(lat, lon)
                    if resultado:
                        return self._mostrar_resultado(extension, resultado, lat, lon)

            # Se falhou Geoclue/Nominatim, usa fallback via IP
            resultado = self._fallback_ip()
            return self._mostrar_resultado(extension, resultado)

        except Exception as e:
            # Qualquer erro, tenta fallback
            resultado = self._fallback_ip()
            return self._mostrar_resultado(extension, resultado, error=str(e))

    def _geocode(self, lat, lon):
        """Tenta Nominatim para cidade, estado, país"""
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1"
            headers = {"User-Agent": "UlauncherWhereAmI/1.0"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code != 200:
                return None

            data = resp.json()
            addr = data.get("address", {})
            cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
            estado = addr.get("state")
            pais = addr.get("country")

            if cidade and estado and pais:
                return f"{cidade}, {estado} - {pais}"
            return None

        except:
            return None

    def _fallback_ip(self):
        """Usa IP como fallback para garantir cidade/estado/país"""
        try:
            resp = requests.get("https://ipinfo.io/json", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return f"{data.get('city')}, {data.get('region')} - {data.get('country')}"
        except:
            pass
        return "Localização não disponível"

    def _mostrar_resultado(self, extension, texto, lat=None, lon=None, error=None):
        """Cria itens do Ulauncher"""
        items = []
        if texto:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name=f"📍 {texto}",
                    description="Clique para copiar",
                    on_enter=CopyToClipboardAction(texto)
                )
            )
            if lat and lon:
                items.append(
                    ExtensionResultItem(
                        icon="images/icon.png",
                        name="🌐 Abrir no Google Maps",
                        description="Ver localização no mapa",
                        on_enter=OpenAction(f"https://www.google.com/maps?q={lat},{lon}")
                    )
                )
        else:
            items.append(
                ExtensionResultItem(
                    icon="images/icon.png",
                    name="❌ Erro ao obter localização",
                    description=error or "Localização não disponível",
                    on_enter=None
                )
            )
        return RenderResultListAction(items)


if __name__ == "__main__":
    WhereAmI().run()
