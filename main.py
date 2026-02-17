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

CACHE_TEMPO = 300
OPENWEATHER_KEY = "4e984b8d646f78243e905469f3ebd800"


class OndeEstouExtension(Extension):

    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.cache = None
        self.cache_timestamp = 0


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):

        if extension.cache and (time.time() - extension.cache_timestamp < CACHE_TEMPO):
            return RenderResultListAction(extension.cache)

        threading.Thread(
            target=self.buscar_dados,
            args=(extension,),
            daemon=True
        ).start()

        return RenderResultListAction([
            ExtensionResultItem(
                icon='map-marker',
                name="Carregando informações...",
                description="Aguarde um instante",
                on_enter=HideWindowAction()
            )
        ])

    def buscar_dados(self, extension):

        try:
            # 🌍 Localização + ISP
            geo = requests.get("https://ipapi.co/json/", timeout=3).json()

            cidade = geo.get("city", "Desconhecida")
            estado = geo.get("region", "")
            pais = geo.get("country_name", "")
            country_code = geo.get("country_code", "").upper()
            ip = geo.get("ip", "")
            isp = geo.get("org", "Desconhecido")
            timezone = geo.get("timezone", "")
            lat = geo.get("latitude")
            lon = geo.get("longitude")

            # 🇧🇷 Bandeira dinâmica
            def flag(code):
                if len(code) != 2:
                    return ""
                return chr(ord(code[0]) + 127397) + chr(ord(code[1]) + 127397)

            bandeira = flag(country_code)

            # 🌦 Clima
            clima = "N/D"
            if lat and lon:
                try:
                    weather = requests.get(
                        f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={OPENWEATHER_KEY}",
                        timeout=3
                    ).json()

                    temp = round(weather["main"]["temp"])
                    cond = weather["weather"][0]["main"]

                    emoji_map = {
                        "Clear": "☀️",
                        "Clouds": "☁️",
                        "Rain": "🌧",
                        "Thunderstorm": "⛈",
                        "Drizzle": "🌦",
                        "Snow": "❄️",
                        "Mist": "🌫"
                    }

                    emoji = emoji_map.get(cond, "")
                    clima = f"{temp}°C {emoji}"
                except:
                    pass

            texto = (
                "Você está em:\n\n"
                f"{cidade}\n"
                f"{estado}\n"
                f"{pais} {bandeira}\n\n"
                f"Fuso: {timezone}\n"
                f"Clima: {clima}\n\n"
                f"ISP: {isp}\n"
                f"IP: {ip}"
            )

            items = [
                ExtensionResultItem(
                    icon='map-marker',
                    name=texto,
                    description="Dados: ipapi.co • OpenWeather",
                    on_enter=CopyToClipboardAction(f"{cidade}, {estado}, {pais}")
                )
            ]

            extension.cache = items
            extension.cache_timestamp = time.time()

            extension.publish_event(RenderResultListAction(items))

        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    OndeEstouExtension().run()
