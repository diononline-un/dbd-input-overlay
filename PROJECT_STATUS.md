---
status: in-development
progress: 85
version: "0.1.0"
tags: [overlay, kde, wayland, dead-by-daylight, gaming]
scope: "Kleines transparentes Input-Overlay für Dead by Daylight unter KDE Wayland: WASD, E, F, Space, Shift, 1-5, Maustasten inkl. Seitentasten und Bewegungsrichtung, always-on-top und GPU-Screen-Recorder-kompatibel."
last_updated: "2026-10-19"
next_steps:
  - gtk4-layer-shell systemweit installieren (aktuell lokaler Fallback in ~/.local/opt)
  - echten Tastatur- und Maus-Input in DBD gegen den laufenden Reader prüfen
  - GPU-Screen-Recorder-Aufnahme mit Default-Transparenz gegenprüfen
  - optional: Tray oder globaler Shortcut zum Ein-/Ausschalten
---

# Aktueller Stand
- Layer-Shell-Overlay oben rechts, klick-durchlässig, über DBD-Vollbild sichtbar (KWin 6.8)
- evdev-Reader für Keychron V5 und YJX-Maus, inkl. Seitentasten und Bewegungsrichtung
- Demo-Modus, Konfiguration, Geräteauswahl, 35 Unit-Tests
- GPU Screen Recorder Monitor-Capture enthält das Overlay
- Offen: Systempaket, Live-Input-Test, finale Abnahme
