---
status: in-development
progress: 92
version: "0.2.0"
tags: [overlay, kde, wayland, dead-by-daylight, gaming]
scope: "Kleines transparentes Input-Overlay für Dead by Daylight unter KDE Wayland: WASD, E, F, Space, Shift, 1-5, Maustasten inkl. Seitentasten und Bewegungsrichtung, always-on-top, GPU-Screen-Recorder-kompatibel, mit Einstellungs-GUI."
last_updated: "2026-10-19"
next_steps:
  - GitHub-Repo anlegen und main pushen
  - Mausklick auf das Overlay-X und Tastaturfokus im Einstellungsfenster am echten Gerät prüfen
  - gtk4-layer-shell systemweit installieren (aktuell lokaler Fallback in ~/.local/opt)
  - optional: Tray oder globaler Shortcut zum Ein-/Ausschalten
---

# Aktueller Stand
- Overlay oben rechts, klick-durchlässig bis auf das kleine X, über DBD-Vollbild sichtbar
- Einstellungs-GUI für Monitor, 9 Anker, Randabstand, Größe, Akzentfarbe, Panel-Deckkraft und Anzeige-Schalter
- Live-Rebuild ohne Neustart, Config-Speicherung, Reset, Escape/× zum Schließen
- evdev-Reader für Keychron V5 und YJX-Maus, inkl. Seitentasten und Bewegungsrichtung
- 43 Unit-Tests; GUI, Ankerpositionen und GPU-Screen-Recorder-Aufnahme verifiziert
- Offen: GitHub-Push, echter Klick-/Tastaturtest, Systempaket
