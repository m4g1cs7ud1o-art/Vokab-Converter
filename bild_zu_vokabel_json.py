import csv
import io
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path


IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DATA_DIRECTORY = Path("datas") / "12T2"
CATALOG_PATH = Path("datas") / "catalog.json"


def slugify(value):
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    if not value:
        raise ValueError("Der Dateiname muss mindestens einen Buchstaben oder eine Zahl enthalten.")
    return value


def find_images(source):
    source = Path(source).expanduser()
    if source.is_file():
        if source.suffix.lower() not in IMAGE_SUFFIXES:
            raise ValueError(f"Nicht unterstütztes Bildformat: {source.suffix}")
        return [source]
    if source.is_dir():
        images = sorted(
            path for path in source.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
        if images:
            return images
        raise ValueError(f"Keine unterstützten Bilddateien in {source} gefunden.")
    raise ValueError(f"Datei oder Ordner nicht gefunden: {source}")


def ocr_rows(image):
    result = subprocess.run(
        ["tesseract", str(image), "stdout", "-l", "eng+deu", "tsv"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        detail = result.stderr.strip() or f"Tesseract wurde mit Code {result.returncode} beendet."
        raise RuntimeError(f"OCR für {image} fehlgeschlagen: {detail}")

    rows = defaultdict(list)
    for word in csv.DictReader(io.StringIO(result.stdout), delimiter="\t"):
        text = word.get("text", "").strip()
        try:
            confidence = float(word.get("conf", "-1"))
            left = int(word["left"])
            width = int(word["width"])
            height = int(word["height"])
        except (ValueError, KeyError):
            continue
        if text and confidence >= 0:
            key = (word["block_num"], word["par_num"], word["line_num"])
            rows[key].append((left, width, height, text))

    candidates = []
    for words in rows.values():
        words.sort(key=lambda word: word[0])
        text = " ".join(word[3] for word in words)
        separated = re.split(r"\s*(?:;|=>|->|–|—|\s-\s)\s*", text, maxsplit=1)
        if len(separated) == 2:
            candidates.append((separated[0].strip(), separated[1].strip()))
            continue

        if len(words) < 2:
            candidates.append((text, ""))
            continue

        gaps = [
            (words[index + 1][0] - (words[index][0] + words[index][1]), index)
            for index in range(len(words) - 1)
        ]
        largest_gap, split_at = max(gaps)
        typical_height = sorted(word[2] for word in words)[len(words) // 2]
        if largest_gap >= max(12, typical_height * 1.5):
            left_text = " ".join(word[3] for word in words[: split_at + 1])
            right_text = " ".join(word[3] for word in words[split_at + 1 :])
            candidates.append((left_text, right_text))
        else:
            candidates.append((text, ""))
    return candidates


def review_pairs(candidates, image):
    accepted = []
    print(f"\nErkannte Zeilen aus {image}:")
    for index, (english, german) in enumerate(candidates, start=1):
        print(f"\n{index}. OCR: {english}" + (f" | {german}" if german else ""))
        if english and german:
            prompt = "Englisch [Enter übernimmt, /skip überspringt]: "
            corrected_english = input(prompt).strip()
            if corrected_english.lower() == "/skip":
                continue
            english = corrected_english or english
            corrected_german = input(f"Deutsch [{german}]: ").strip()
            german = corrected_german or german
        else:
            english = input("Englisch (leer oder /skip zum Überspringen): ").strip()
            if not english or english.lower() == "/skip":
                continue
            german = input("Deutsch: ").strip()

        if english and german:
            accepted.append({"x": english, "y": german})
        else:
            print("Eintrag übersprungen: Beide Übersetzungen müssen ausgefüllt sein.")
    return accepted


def add_to_catalog(catalog, item):
    if isinstance(catalog, dict):
        group = catalog if catalog.get("id") == "12T2" else catalog.get("12T2")
        if isinstance(group, dict):
            lists = group.get("lists")
            if not isinstance(lists, list):
                raise ValueError("Die Gruppe 12T2 im Katalog hat kein gültiges 'lists'-Array.")
            if any(entry.get("id") == item["id"] for entry in lists if isinstance(entry, dict)):
                raise ValueError(f"Die ID '{item['id']}' ist in der Gruppe 12T2 bereits vorhanden.")
            lists.append(item)
            return True
        return any(add_to_catalog(value, item) for value in catalog.values() if isinstance(value, (dict, list)))
    if isinstance(catalog, list):
        for value in catalog:
            if isinstance(value, (dict, list)) and add_to_catalog(value, item):
                return True
    return False


def main():
    if not shutil.which("tesseract"):
        raise RuntimeError(
            "Tesseract OCR wurde nicht gefunden. Installiere Tesseract und die Sprachdaten "
            "für Englisch (eng) und Deutsch (deu), und stelle sicher, dass 'tesseract' im PATH liegt."
        )

    source = input("Pfad zu einem Bild oder einem Ordner mit Bildern: ").strip().strip('"')
    images = find_images(source)
    name = slugify(input("Dateiname für die Vokabelliste (wird zu Kleinbuchstaben-mit-Bindestrichen): "))
    title = input(f"Titel [{name.replace('-', ' ').title()}]: ").strip()
    title = title or name.replace("-", " ").title()
    description = input("Beschreibung (optional): ").strip()

    output_path = DATA_DIRECTORY / f"{name}.json"
    if output_path.exists():
        raise FileExistsError(f"Die Datei existiert bereits und wird nicht überschrieben: {output_path}")

    entries = []
    for image in images:
        entries.extend(review_pairs(ocr_rows(image), image))
    if not entries:
        raise ValueError("Es wurden keine vollständigen Vokabelpaare bestätigt; es wurde nichts gespeichert.")

    DATA_DIRECTORY.mkdir(parents=True, exist_ok=True)
    document = {
        "languageX": "Englisch",
        "languageY": "Deutsch",
        "entries": entries,
    }
    catalog_item = {
        "id": name,
        "title": title,
        "description": description,
        "wordCount": len(entries),
        "file": (DATA_DIRECTORY / f"{name}.json").as_posix(),
    }

    catalog = None
    if CATALOG_PATH.exists():
        with CATALOG_PATH.open("r", encoding="utf-8") as file:
            catalog = json.load(file)
        if not add_to_catalog(catalog, catalog_item):
            raise ValueError("Im Katalog wurde keine Gruppe mit der ID '12T2' und einem 'lists'-Array gefunden.")
    else:
        print(f"Hinweis: {CATALOG_PATH} existiert nicht; es wird nur die JSON-Datei erzeugt.")

    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(document, file, ensure_ascii=False, indent=2)
        file.write("\n")
    if catalog is not None:
        with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as file:
            json.dump(catalog, file, ensure_ascii=False, indent=2)
            file.write("\n")

    print(f"\nGespeichert: {output_path} ({len(entries)} Vokabelpaare)")
    if catalog is not None:
        print(f"Katalog ergänzt: {CATALOG_PATH}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"Fehler: {error}", file=sys.stderr)
        sys.exit(1)
