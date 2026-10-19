# Changelog

## 2026-10-19 — Einstellungs-GUI und Beenden-X
- Layer-Shell-Einstellungsfenster mit Monitorwahl, 9 Ankerpositionen, Randabstand, Scale, Akzentfarbe und Panel-Deckkraft
- Live-Übernahme aller Änderungen, automatisches Speichern, Zurücksetzen und Escape/× zum Schließen
- Kleines klickbares X im Overlay beendet die App; der Rest bleibt klick-durchlässig
- Overlay-Position wird aus Monitorfläche, Fenstergröße und Anker berechnet
- 43 Unit-Tests; GUI und Live-Rebuild mit DBD verifiziert
- Offen: echter Klick-/Tastaturtest, gtk4-layer-shell systemweit

## 2026-10-19 — Initiales DBD-Input-Overlay
- GTK4-Layer-Shell-Overlay oben rechts, klick-durchlässig und ohne Fokusklau
- evdev-Reader für Keychron V5 und YJX-Maus, inkl. Seitentasten und Bewegungsrichtung
- Kompakte Glaskarte mit Keycaps, Mauscluster, Scroll-Indikator und Demo-Modus
- CLI- und TOML-Konfiguration, Geräteauswahl, Systempaket-Prüfung, Installer
- 36 Unit-Tests; Sichtbarkeit über DBD-Vollbild und GPU Screen Recorder verifiziert
- Offen: gtk4-layer-shell systemweit installieren, echter Live-Input-Test
