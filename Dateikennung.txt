# Vokabeln für 12T2

## Dateiformat

Jeder Vokabelsatz wird als eigene JSON-Datei in diesem Ordner gespeichert. Verwende UTF-8 und gültiges JSON: keine Kommentare und kein Komma nach dem letzten Eintrag.

Beispiel für `climate-debate.json`:

```json
{
  "languageX": "Englisch",
  "languageY": "Deutsch",
  "entries": [
    { "x": "climate change", "y": "Klimawandel" },
    { "x": "renewable energy", "y": "erneuerbare Energie" },
    { "x": "to reduce", "y": "verringern" }
  ]
}
```

Jeder Eintrag enthält genau zwei Textfelder: `x` für Englisch und `y` für Deutsch. Die Anzahl der Einträge in `entries` ist die Wortanzahl des Satzes.

## Neue Liste eintragen

1. Lege die JSON-Datei in `datas/12T2/` ab. Verwende für den Dateinamen Kleinbuchstaben und Bindestriche, zum Beispiel `climate-debate.json`.
2. Öffne `datas/catalog.json` und ergänze die Liste im `lists`-Abschnitt der Gruppe `12T2`:

```json
{
  "id": "climate-debate",
  "title": "Climate and society",
  "description": "Klima und Gesellschaft",
  "wordCount": 3,
  "file": "datas/12T2/climate-debate.json"
}
```

3. `wordCount` muss der Anzahl der Einträge in der Datei entsprechen. Die `id` muss innerhalb der Gruppe eindeutig sein.
4. Committe beide Dateien. Bei GitHub Pages wird die Änderung nach der Veröffentlichung des Commits sichtbar.

Die Klassenkennung lautet `12T2`, der Jahrgang `12`. Der Klassencode ist sechs Ziffern lang und beginnt ebenfalls mit `12`.
