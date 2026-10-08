#!/usr/bin/env python3
"""Prüfer für deutsche Texte in Einfacher Sprache.

Zählt die Regeln, die ein Muster erkennen kann: Satzlänge, Kommazahl,
Passiv, Nominalstil, Genitiv, Amtsdeutsch, Abkürzungen, Füllwörter,
Redewendungen, Konjunktiv, Einschübe und Zahlenformate.

Bekannte Grenze: Das ist ein Musterabgleich, kein Grammatik-Parser. Der
Prüfer übersieht Verstöße und kann bei ungewöhnlicher Formatierung falsch
zählen. Die Zahlen sind zwischen zwei Texten vergleichbar, die durch
dieselbe Version gelaufen sind. Sie sind kein Normurteil. Kein Werkzeug
kann die Einhaltung von DIN 8581-1 garantieren.

Aufruf:
  python3 pruefen.py text.md
  python3 pruefen.py --text "Der Antrag wird geprüft."
  cat text.md | python3 pruefen.py -
  python3 pruefen.py --json text.md
  python3 pruefen.py --selbsttest
"""

from __future__ import annotations

import argparse
import json
import re
import sys

# --- Schutzliste: Punkte, die keinen Satz beenden -------------------------

ABKUERZUNGEN = [
    "z. B.", "z.B.", "u. a.", "u.a.", "d. h.", "d.h.", "o. Ä.", "o.Ä.",
    "i. d. R.", "i.d.R.", "u. U.", "u.U.", "ggf.", "evtl.", "inkl.",
    "bzw.", "usw.", "etc.", "sog.", "ca.", "zzgl.", "lt.", "Abt.", "Az.",
    "Nr.", "vgl.", "bspw.", "max.", "min.", "Dr.", "Prof.", "St.",
    "e. V.", "e.V.", "GmbH", "Abs.", "Art.", "S.", "ff.", "bzw",
]
MONATE = (
    "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|"
    "November|Dezember"
)

ABK_PATTERN = re.compile(
    "|".join(re.escape(a) for a in sorted(ABKUERZUNGEN, key=len, reverse=True))
)
ORDINAL = re.compile(rf"\b\d{{1,2}}\.\s*(?={MONATE})")
TOKEN = re.compile(
    rf"(?:{ABK_PATTERN.pattern}|\b\d{{1,2}}\.\s*(?={MONATE})|\S+)"
)

# --- Einzelne Regelprüfungen ---------------------------------------------

WERDEN = re.compile(r"\b(?:wird|werden|wurde|wurden|worden|werde|werdet)\b", re.I)
PARTIZIP = re.compile(
    r"\b(?:ge\w{2,}(?:t|en)|be\w{2,}(?:t|en)|ver\w{2,}(?:t|en)|er\w{2,}(?:t|en)|"
    r"ent\w{2,}(?:t|en)|zer\w{2,}(?:t|en)|miss\w{2,}(?:t|en)|über\w{3,}(?:t|en)|"
    r"unter\w{3,}(?:t|en)|\w{3,}iert)\b",
    re.I,
)
NOMINAL_SICHER = re.compile(
    r"\b(?:Berücksichtigung|Einhaltung|Durchführung|Inanspruchnahme|Genehmigung|"
    r"Antragstellung|Übernahme|Anerkennung|Erstattung|Auszahlung|Bemessung|"
    r"Begründung|Mitteilung|Aufforderung|Anrechnung|Zuweisung|Nutzung|Anwendung|"
    r"Verwendung|Beachtung|Erfüllung|Vorlage|Inbetriebnahme|Außerbetriebnahme|"
    r"Abwicklung|Beurteilung|Verpflichtung|Terminierung|Fragestellung|"
    r"Problemstellung|Zusendung|Übersendung|Bekanntgabe|Kenntnisnahme|"
    r"Mitwirkungspflicht|Fristversäumnis|Rückantwort|Entscheidungsfindung|"
    r"Zurverfügungstellung|Berichtserstattung|Sachverhaltsdarstellung|"
    r"\w{5,}(?:tion|tät|ismus|ierung))\b",
    re.I,
)
ALLTAGSWORT = {
    "bewegung", "schwellung", "nebenwirkung", "wohnung", "zeitung", "rechnung",
    "ordnung", "meinung", "übung", "kleidung", "wirkung", "hoffnung",
    "erinnerung", "sammlung", "stimmung", "leitung", "sitzung", "ausbildung",
    "weiterbildung", "umgebung", "nahrung", "erfahrung", "anmeldung",
    "erklärung", "zahlung", "prüfung", "richtung", "versicherung", "leistung",
    "verbindung", "abteilung", "ausstattung", "ausstellung", "bedeutung",
    "bedingung", "begleitung", "behandlung", "bestellung", "betreuung",
    "bezeichnung", "darstellung", "einrichtung", "einstellung", "entschädigung",
    "entwicklung", "erholung", "erweiterung", "finanzierung", "förderung",
    "freundschaft", "gebühr", "haltung", "handlung", "herstellung",
    "information", "kleidung", "kündigung", "lieferung", "lösung", "meldung",
    "möglichkeit", "notwendigkeit", "planung", "reinigung", "sammlung",
    "sicherheit", "gesundheit", "krankheit", "wahrheit", "wirklichkeit",
    "spannung", "stellung", "teilnahme", "umstellung", "unterkunft",
    "veranstaltung", "veränderung", "verfügung", "verletzung", "verordnung",
    "versammlung", "verwaltung", "vorbereitung", "vorsorge", "wartung",
    "werbung", "wohnung", "zahlung", "zeitung", "zufriedenheit", "zulassung",
    "zusammenarbeit", "erlaubnis",
}
NOMINAL_PRUEFEN = re.compile(r"\b\w{5,}(?:ung|heit|keit|igkeit)\b", re.I)
FUNKTIONSVERB = re.compile(
    r"\b(?:erfolgt|erfolgen|erfolgte|erfolgten|findet\s+\S+\s+statt|finden\s+\S+\s+statt|"
    r"vornimmt|vornehmen|vorgenommen|durchführt|durchführen|durchgeführt|"
    r"zur\s+Verfügung|in\s+Anspruch|zur\s+Anwendung|zur\s+Kenntnis|"
    r"zur\s+Folge|in\s+Kraft|zur\s+Anwendung\s+kommt)\b",
    re.I,
)
GENITIV = re.compile(r"\b(?:des|dessen|deren)\s+\w{3,}(?:es|s|en)\b", re.I)
KONJUNKTIV = re.compile(
    r"\b(?:wäre|wären|hätte|hätten|würde|würden|könnte|könnten|müsste|müssten|"
    r"dürfte|dürften|sollte|sollten|wollte|wollten|ginge|käme|bräuchte)\b",
    re.I,
)
ES_FORMEL = re.compile(
    r"\bes\s+(?:ist|wird|sind|werden|besteht|bestehen|gilt|gelten|handelt\s+sich|"
    r"erfolgt|erfolgen|wird\s+gebeten|wird\s+empfohlen)\b",
    re.I,
)
NEGATION = re.compile(
    r"\b(?:nicht|kein|keine|keinen|keinem|keiner|keines|niemals|nie|niemand|"
    r"ohne|unzulässig|unmöglich|unterlassen)\b",
    re.I,
)
KLAMMER = re.compile(r"\([^)]{1,80}\)")
SEMIKOLON = re.compile(r";")
GEDANKENSTRICH = re.compile(r"—|(?<!\d)–(?!\d)|(?<= )--(?= )|(?<=[^\s\d]) - (?=[^\s\d])")
LANGS_WORT = re.compile(r"\b[A-Za-zÄÖÜäöüß]{21,}\b")

DATUM_KURZ = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{2}(?!\d)\b")
UHRZEIT_KURZ = re.compile(r"\b\d{1,2}\.\d{2}\s?(?:h|Uhr)\b")
EINHEIT_OHNE_LZ = re.compile(
    r"\b\d+(?:kg|km|cm|mm|ml|mg|kW|MB|GB|TB|kWh)\b", re.I
)

AMTSDEUTSCH = re.compile(
    r"\b(?:aufgrund|auf\s+Grund|zwecks|hinsichtlich|bezüglich|diesbezüglich|insofern|"
    r"sofern|zumal|obliegt|erlassen|gegenständlich|gegenwärtig|unverzüglich|zeitnah|"
    r"seitens|erfolgt|erfolgen|vorzunehmen|vornehmen|durchzuführen|durchführen|"
    r"unentgeltlich|entgeltlich|Aufwendungen|Entgelte|Rückfragen|Rückantwort|"
    r"Zusendung|Übersendung|Einwendung|Sachverhalt|Fragestellung|Problemstellung|"
    r"Thematik|Maßnahme|Vorgang|Mitwirkungspflicht|Fristversäumnis|Bestandskraft|"
    r"Bekanntgabe|Erwerb|Abnahme|Anlieferung|Inbetriebnahme|Außerbetriebnahme|"
    r"Gewährleistung|Zuwendung|Fördermittel|Terminierung|Verpflichtung|Beurteilung|"
    r"Abwicklung|Kenntnisnahme|Inanspruchnahme|Antragstellung|Genehmigung|"
    r"Erfordernis|Notwendigkeit|Berücksichtigung|Zurverfügungstellung|"
    r"Rechtsbehelfsbelehrung|Widerspruchsfrist|Bemessungsgrenze)\b",
    re.I,
)
FACHJARGON = re.compile(
    r"\b(?:administrieren|Applikation|approbieren|evaluieren|implementieren|"
    r"initialisieren|kommunizieren|validieren|Modifikation|Konfiguration|"
    r"Integration|Koordination|Kooperation|Konsequenz|Kategorie|Dimension|"
    r"Distanz|Frequenz|Modul|Parameter|Prozedur|Prozess|Quantität|Reduktion|"
    r"Selektion|Sequenz|Strategie|Transformation|Variante|Kriterium|Priorität|"
    r"Relevanz|Ressource|Terminologie|Kompetenz|Konzeption|Zertifikat|Option|"
    r"Kontext|Fokus|Aspekt|Indikator|Sektor|Synergie|Mehrwert)\b",
    re.I,
)
SLOP = re.compile(
    r"\b(?:nahtlos|reibungslos|mühelos|ganzheitlich|robust|leistungsstark|innovativ|"
    r"umfassend|vielfältig|facettenreich|Optimierung|optimieren|Implementierung|"
    r"Augenhöhe|hierbei|diesbezüglich|ferner|darüber\s+hinaus|des\s+Weiteren|"
    r"zusammenfassend|abschließend|heutzutage|Möglichkeit|ermöglicht|verfügt\s+über|"
    r"zeichnet\s+sich\s+aus|birgt|macht\s+deutlich|unterstreicht|revolutioniert|"
    r"transformativ|wegweisend|bahnbrechend|ermöglicht\s+es|stellt\s+sicher|"
    r"spielt\s+eine\s+(?:wichtige|entscheidende|zentrale)\s+Rolle|"
    r"es\s+ist\s+wichtig|es\s+ist\s+erwähnenswert|es\s+lohnt\s+sich|"
    r"es\s+handelt\s+sich\s+um|in\s+der\s+heutigen\s+Zeit|im\s+Zeitalter|"
    r"eine\s+Vielzahl|eine\s+Reihe\s+von|zum\s+jetzigen\s+Zeitpunkt)\b",
    re.I,
)
FUELLWOERTER = re.compile(
    r"\b(?:wirklich|eigentlich|grundsätzlich|durchaus|gewissermaßen|sozusagen|quasi|"
    r"letztlich|schlichtweg|keineswegs|mitunter|durchweg|im\s+Grunde|"
    r"letzten\s+Endes|mehr\s+oder\s+weniger|an\s+sich|für\s+sich\s+genommen|"
    r"praktisch\s+gesehen|in\s+der\s+Gesamtschau|nicht\s+zuletzt)\b",
    re.I,
)
REDEWENDUNG = re.compile(
    r"\b(?:am\s+Ball\s+bleiben|Weichen\s+stellen|aufs\s+Gleis|ins\s+Rollen|"
    r"Ruder\s+herum|an\s+einem\s+Strang|Handtuch\s+werfen|Zahn\s+zulegen|"
    r"Daumen\s+drücken|an\s+der\s+Quelle\s+sitzen|Luft\s+nach\s+oben|"
    r"im\s+gleichen\s+Boot|Sand\s+ins\s+Getriebe|Eigentor|"
    r"mit\s+Kanonen\s+auf\s+Spatzen|ins\s+Boot\s+holen|Hand\s+in\s+Hand)\b",
    re.I,
)
ABK_IM_TEXT = re.compile(
    r"(?:\bz\.\s?B\.|\bu\.\s?a\.|\bd\.\s?h\.|\bo\.\s?Ä\.|\bi\.\s?d\.\s?R\.|"
    r"\bu\.\s?U\.|\bggf\.|\bevtl\.|\binkl\.|\bbzw\.|\busw\.|\betc\.|\bsog\.|"
    r"\bca\.|\bzzgl\.)"
)

SYNONYMGRUPPEN = [
    ("Antrag", r"\bAntrag\b", r"\bGesuch\b", r"\bErsuchen\b"),
    ("Widerspruch", r"\bWiderspruch\b", r"\bEinspruch\b", r"\bBeschwerde\b"),
    ("Frist", r"\bFrist\b", r"\bTermin\b", r"\bZeitfenster\b"),
    ("Kunde", r"\bKunde\b", r"\bKundin\b", r"\bInteressent\b"),
]

# --- Hilfen ---------------------------------------------------------------


def schuetzen(text: str):
    """Ersetzt Abkürzungspunkte und Ordinalzahlen durch Platzhalter."""
    store: list[str] = []

    def merk(match: re.Match) -> str:
        store.append(match.group(0))
        return f"\x00{len(store) - 1}\x00"

    text = ORDINAL.sub(merk, text)
    text = ABK_PATTERN.sub(merk, text)
    return text, store


def entschuetzen(text: str, store: list[str]) -> str:
    def hol(match: re.Match) -> str:
        return store[int(match.group(1))]

    return re.sub(r"\x00(\d+)\x00", hol, text)


def entferne_code(text: str) -> str:
    """Blendet Code, YAML-Kopf und Trennzeilen aus, ohne Zeilen zu verschieben."""
    text = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)
    text = re.sub(r"`[^`\n]+`", " CODE ", text)
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"^\s*\|[\s:|-]+\|\s*$", "", text, flags=re.M)
    # YAML-Kopfzeile ist Metadaten, kein Fließtext.
    if text.startswith("---"):
        ende = text.find("\n---", 3)
        if ende != -1:
            kopf = text[: ende + 4]
            text = "".join(
                "\n" if z == "\n" else " " for z in kopf
            ) + text[ende + 4 :]
    return text


def tokens(satz: str) -> list[str]:
    geschuetzt, _ = schuetzen(satz)
    return TOKEN.findall(geschuetzt)


def bloecke(text: str) -> list[tuple[int, bool, list[str]]]:
    """Zerlegt den Text in Absätze.

    Ergibt (Startzeile, ist_Überschrift, Zeilen). Ein normaler Absatz wird
    zusammengezogen, damit ein Satz über mehrere Zeilen trotzdem als ein
    Satz gezählt wird. Überschriften, Listenpunkte, Tabellenzeilen und
    Zitate stehen jeweils für sich.
    """
    bloecke: list[tuple[int, bool, list[str]]] = []
    puffer: list[str] = []
    start = 0
    for nr, zeile in enumerate(text.split("\n"), start=1):
        blank = not zeile.strip()
        if blank:
            if puffer:
                bloecke.append((start, False, puffer))
                puffer = []
            continue
        einzeln = (
            zeile.lstrip().startswith(("#", "|", ">", "-", "*", "+"))
            or re.match(r"^\s*\d+[.)]\s", zeile) is not None
        )
        if einzeln:
            if puffer:
                bloecke.append((start, False, puffer))
                puffer = []
            bloecke.append((nr, zeile.lstrip().startswith("#"), [zeile]))
            continue
        if not puffer:
            start = nr
        puffer.append(zeile)
    if puffer:
        bloecke.append((start, False, puffer))
    return bloecke


def saetze(text: str) -> list[tuple[int, str]]:
    """Liste aus (Zeilennummer, Satz). Überschriften bleiben enthalten."""
    geschuetzt, store = schuetzen(text)
    ergebnis: list[tuple[int, str]] = []
    for start, ist_ueberschrift, zeilen in bloecke(geschuetzt):
        teile: list[str] = []
        offsets: list[tuple[int, int]] = []
        pos = 0
        for versatz, zeile in enumerate(zeilen):
            offsets.append((pos, start + versatz if not ist_ueberschrift else start))
            teile.append(zeile.strip())
            pos += len(zeile.strip()) + 1
        zusammen = " ".join(teile)
        for teil in re.split(r"(?<=[.!?:])\s+(?=[A-ZÄÖÜ])", zusammen):
            if len(tokens(teil)) < 2:
                continue
            index = zusammen.find(teil)
            zeile_nr = start
            for offset, nr in offsets:
                if offset <= index:
                    zeile_nr = nr
                else:
                    break
            ergebnis.append((zeile_nr, entschuetzen(teil.strip(), store)))
    return ergebnis


def ist_ueberschrift(zeilen: list[str], zeile_nr: int) -> bool:
    """Überschrift ist eine Zeile mit # oder eine Zeile, die ganz fett ist."""
    if not (1 <= zeile_nr <= len(zeilen)):
        return False
    zeile = zeilen[zeile_nr - 1].strip()
    return zeile.startswith("#") or (zeile.startswith("**") and zeile.endswith("**") and len(zeile) > 4)


class Befund:
    __slots__ = ("kategorie", "text", "zeile")

    def __init__(self, kategorie: str, text: str, zeile: int):
        self.kategorie = kategorie
        self.text = text
        self.zeile = zeile


def kuerzen(text: str, laenge: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= laenge else text[:laenge] + "…"


def pruefe(text: str, max_satzlaenge: int = 20) -> tuple[list[Befund], dict]:
    roh = text
    text = entferne_code(text)
    zeilen = text.split("\n")
    befunde: list[Befund] = []
    belegte_spannen: list[tuple[int, int]] = []

    def add(kategorie: str, inhalt: str, zeile: int) -> None:
        befunde.append(Befund(kategorie, kuerzen(inhalt), zeile))

    def frei(start: int, ende: int) -> bool:
        """Wahr, wenn die Stelle noch keinem anderen Befund zugeordnet ist.

        Ein Wort wie "Rechtsbehelfsbelehrung" trifft mehrere Muster. Ohne
        diese Prüfung erschiene es dreimal und würde die Verstoßzahl
        künstlich aufblasen.
        """
        for s, e in belegte_spannen:
            if start < e and s < ende:
                return False
        return True

    # Satzebene
    for zeile_nr, satz in saetze(text):
        if ist_ueberschrift(zeilen, zeile_nr):
            continue
        woerter = tokens(satz)
        if len(woerter) > max_satzlaenge:
            add("Satzlänge", f"{len(woerter)} Wörter: {satz}", zeile_nr)
        if satz.count(",") > 1:
            add("Kommazahl", f"{satz.count(',')} Kommas: {satz}", zeile_nr)
        if WERDEN.search(satz):
            for m in WERDEN.finditer(satz):
                if PARTIZIP.search(satz[m.end():][:60]):
                    add("Passiv", m.group(0), zeile_nr)
                    break

    # Wort- und Musterebene, in dieser Reihenfolge. Der erste Treffer auf
    # einer Stelle gewinnt, weil er die genauere Erklärung liefert.
    for name, muster in [
        ("Amtsdeutsch", AMTSDEUTSCH),
        ("Fachjargon", FACHJARGON),
        ("AI-Sprech", SLOP),
        ("Funktionsverb", FUNKTIONSVERB),
        ("Nominalstil", NOMINAL_SICHER),
        ("Genitiv", GENITIV),
        ("Konjunktiv", KONJUNKTIV),
        ("Es-Formel", ES_FORMEL),
        ("Klammer", KLAMMER),
        ("Negation", NEGATION),
        ("Füllwort", FUELLWOERTER),
        ("Redewendung", REDEWENDUNG),
        ("Abkürzung", ABK_IM_TEXT),
        ("Langes Wort", LANGS_WORT),
        ("Kurzes Datum", DATUM_KURZ),
        ("Kurze Uhrzeit", UHRZEIT_KURZ),
        ("Einheit ohne Leerzeichen", EINHEIT_OHNE_LZ),
        ("Semikolon", SEMIKOLON),
        ("Gedankenstrich", GEDANKENSTRICH),
    ]:
        for m in muster.finditer(text):
            if not frei(m.start(), m.end()):
                continue
            belegte_spannen.append((m.start(), m.end()))
            zeile = text.count("\n", 0, m.start()) + 1
            add(name, m.group(0), zeile)

    # Nur ein Hinweis, kein Verstoß: gewöhnliche Wörter mit -ung, -heit oder
    # -keit sind kein Nominalstil. Sie werden getrennt gemeldet.
    for m in NOMINAL_PRUEFEN.finditer(text):
        if m.group(0).lower() in ALLTAGSWORT:
            continue
        if not frei(m.start(), m.end()):
            continue
        belegte_spannen.append((m.start(), m.end()))
        zeile = text.count("\n", 0, m.start()) + 1
        add("Substantivierung prüfen", m.group(0), zeile)

    for name, *muster in SYNONYMGRUPPEN:
        treffer = [p.pattern for p in (re.compile(m, re.I) for m in muster) if p.search(text)]
        if len(treffer) > 1:
            befunde.append(
                Befund("Synonymwechsel", f"{name}: {len(treffer)} Bezeichnungen im Text", 0)
            )

    zaehlbar = tokens(text)
    saetze_liste = [s for z, s in saetze(text) if not ist_ueberschrift(zeilen, z)]
    hinweise = sum(1 for b in befunde if b.kategorie in HINWEISE)
    statistik = {
        "woerter": len(zaehlbar),
        "saetze": len(saetze_liste),
        "mittlere_satzlaenge": round(
            sum(len(tokens(s)) for s in saetze_liste) / len(saetze_liste), 1
        )
        if saetze_liste
        else 0.0,
        "laengster_satz": max((len(tokens(s)) for s in saetze_liste), default=0),
        "verstoesse": len(befunde),
        "hinweise": hinweise,
        "verstoesse_hart": len(befunde) - hinweise,
        "verstoesse_pro_100_woerter": round(len(befunde) / len(zaehlbar) * 100, 1)
        if zaehlbar
        else 0.0,
        "harte_pro_100_woerter": round((len(befunde) - hinweise) / len(zaehlbar) * 100, 1)
        if zaehlbar
        else 0.0,
        "zeichen": len(roh),
    }
    return befunde, statistik


HINWEISE = (
    "Negation",
    "Genitiv",
    "Langes Wort",
    "Substantivierung prüfen",
    "Klammer",
    "Kurzes Datum",
    "Kurze Uhrzeit",
)


def bericht(pfad: str, befunde: list[Befund], statistik: dict) -> str:
    zeilen = [
        f"Prüfbericht: {pfad}",
        "",
        f"Wörter: {statistik['woerter']}   Sätze: {statistik['saetze']}   "
        f"Ø Satzlänge: {str(statistik['mittlere_satzlaenge']).replace('.', ',')} Wörter   "
        f"längster Satz: {statistik['laengster_satz']} Wörter",
        f"Verstöße pro 100 Wörter: "
        f"{str(statistik['verstoesse_pro_100_woerter']).replace('.', ',')}   "
        f"davon harte Verstöße: "
        f"{str(statistik['harte_pro_100_woerter']).replace('.', ',')}   "
        f"({statistik['hinweise']} von {statistik['verstoesse']} Treffern sind Hinweise)",
    ]
    if not befunde:
        zeilen += ["", "Keine Musterverstöße gefunden. Das ist kein Normurteil."]
        return "\n".join(zeilen)

    nach_kategorie: dict[str, list[Befund]] = {}
    for b in befunde:
        nach_kategorie.setdefault(b.kategorie, []).append(b)

    zeilen.append("")
    for kategorie, liste in sorted(nach_kategorie.items(), key=lambda kv: -len(kv[1])):
        marke = "  (Hinweis)" if kategorie in HINWEISE else ""
        zeilen.append(f"{kategorie} ({len(liste)}){marke}")
        for b in liste[:6]:
            ort = f"Zeile {b.zeile}: " if b.zeile else ""
            zeilen.append(f"  {ort}{b.text}")
        if len(liste) > 6:
            zeilen.append(f"  … und {len(liste) - 6} weitere")
        zeilen.append("")

    zeilen.append("Zusammenfassung")
    for kategorie, liste in sorted(nach_kategorie.items(), key=lambda kv: -len(kv[1])):
        zeilen.append(f"  {kategorie:<26} {len(liste)}")
    zeilen.append("")
    zeilen.append(
        "Als Hinweis markierte Kategorien sind Prüfstellen, keine Fehler. Eine "
        "Verneinung in einer Warnung, ein Genitiv auf einem Gesetzesnamen und "
        "ein langes Fachwort sind oft richtig."
    )
    zeilen.append(
        "Hinweis: Musterabgleich, kein Normurteil. Kein Werkzeug kann die "
        "Einhaltung von DIN 8581-1 garantieren."
    )
    return "\n".join(zeilen)


SELBSTTEST_GUT = """# Antrag auf einen Kita-Platz

Sie möchten einen Kita-Platz für Ihr Kind? Dann stellen Sie einen Antrag.
Die Frist endet am 3. Juni 2026.

1. Füllen Sie das Formular aus.
2. Legen Sie den Nachweis über Ihr Einkommen bei.
3. Schicken Sie alles an die Adresse unten.

Wir prüfen Ihren Antrag. Sie bekommen innerhalb von vier Wochen eine Antwort.
"""

SELBSTTEST_SCHLECHT = """
Aufgrund der Tatsache, dass die Berücksichtigung der Einkommensverhältnisse
durch die zuständige Stelle im Rahmen der Antragsprüfung erfolgt; die
Genehmigung wird nach Maßgabe des § 22 erteilt, sofern die Unterlagen, die
für die Bearbeitung erforderlich sind, innerhalb einer Frist von zwei Wochen
nachgereicht werden. Es ist zu beachten, dass die Möglichkeit besteht, dass
z. B. weitere Nachweise angefordert werden — diesbezüglich bitten wir um
Kenntnisnahme.
"""


def selbsttest() -> int:
    fehler = 0

    gut, stat_gut = pruefe(SELBSTTEST_GUT)
    if stat_gut["saetze"] < 5:
        print(f"FEHLER: Sätze falsch gezählt: {stat_gut['saetze']}")
        fehler += 1
    if stat_gut["laengster_satz"] > 20:
        print(f"FEHLER: Guter Text meldet langen Satz: {stat_gut['laengster_satz']}")
        fehler += 1
    hart = {"Passiv", "Amtsdeutsch", "Semikolon", "Gedankenstrich"}
    treffer = {b.kategorie for b in gut} & hart
    if treffer:
        print(f"FEHLER: Guter Text meldet {sorted(treffer)}")
        fehler += 1

    schlecht, stat_schlecht = pruefe(SELBSTTEST_SCHLECHT)
    gefunden = {b.kategorie for b in schlecht}
    erwartet = ["Amtsdeutsch", "Semikolon", "Gedankenstrich", "Satzlänge"]
    for kat in erwartet:
        if kat not in gefunden:
            print(f"FEHLER: Schlechter Text meldet {kat} nicht")
            fehler += 1
    if stat_schlecht["verstoesse_pro_100_woerter"] <= stat_gut["verstoesse_pro_100_woerter"]:
        print("FEHLER: Schlechter Text hat nicht mehr Verstöße als der gute")
        fehler += 1

    if fehler == 0:
        print("Selbsttest bestanden.")
        print(f"  guter Text:      {list(gut)}")
        print(f"  schlechter Text: {sorted(gefunden)}")
    return 1 if fehler else 0


def hilfe() -> str:
    return __doc__ or ""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="pruefen.py",
        description="Prüfer für Einfache Sprache nach DIN 8581-1",
        add_help=False,
    )
    p.add_argument("datei", nargs="?", help="Textdatei, oder - für die Standardeingabe")
    p.add_argument("--text", help="Text direkt übergeben")
    p.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    p.add_argument("--satzlaenge", type=int, default=20, help="Obergrenze (Standard 20)")
    p.add_argument("--selbsttest", action="store_true", help="Prüfer selbst testen")
    p.add_argument("--hilfe", "-h", action="store_true", help="Hilfe zeigen")
    args = p.parse_args(argv)

    if args.selbsttest:
        return selbsttest()
    if args.hilfe or (not args.datei and args.text is None):
        print(hilfe())
        return 0 if args.hilfe else 2

    if args.text is not None:
        text, pfad = args.text, "<Text>"
    elif args.datei == "-":
        text, pfad = sys.stdin.read(), "<Standardeingabe>"
    else:
        try:
            text = open(args.datei, encoding="utf-8").read()
        except OSError as exc:
            print(f"Datei nicht lesbar: {exc}", file=sys.stderr)
            return 1
        pfad = args.datei

    befunde, statistik = pruefe(text, args.satzlaenge)

    if args.json:
        print(
            json.dumps(
                {
                    "datei": pfad,
                    "statistik": statistik,
                    "befunde": [
                        {"kategorie": b.kategorie, "text": b.text, "zeile": b.zeile}
                        for b in befunde
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(bericht(pfad, befunde, statistik))
    return 1 if befunde else 0


if __name__ == "__main__":
    raise SystemExit(main())
