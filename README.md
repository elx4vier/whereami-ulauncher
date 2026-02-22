# Where Am I? – Ulauncher Extension

Quickly shows your public location via IP (city, region, country, coordinates, IP).  
Press Enter to copy a compact summary.

---

## Features

- 🌍 IP-based geolocation (multiple fallback APIs)
- 🏳️ Country flag (Unicode)
- 📋 One-click copy
- 🌐 Auto language (fallback: English)
- ⚡ Cached for 10 minutes
- 🔧 Custom keyword (`l` default)

---

## Installation

- Via Ulauncher → Extensions → Add:
  `https://github.com/yourusername/ulauncher-whereami`

- Or clone into:
  `~/.local/share/ulauncher/extensions/`

---

## Usage

1. Open Ulauncher (`Ctrl+Space`)
2. Type `l`
3. Press Enter to copy result

**Example:**
Berlin, Berlin, Germany (IP: 123.45.67.89)

---

## Config

Change keyword in:
Ulauncher → Preferences → Extensions

---

## How it works

- Uses: ip-api, freeipapi, ipapi, ipinfo
- First valid response is cached (10 min)
- Auto-detects system language

---

## Translation

Add files in `translations/`:

```json
{
  "title": "Where Am I?",
  "unknown": "Unknown",
  "error": "Error",
  "source": "Source",
  "copy_format": "{city}, {region}, {country} (IP: {ip})"
}
```

---

## License

MIT

## Credits

Xavier  
Feather Icons  
Geolocation APIs
