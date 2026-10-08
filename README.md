# /einfache-sprache

Ein AI-Skill, der deutsche Texte in **Einfache Sprache nach DIN 8581-1** bringt.

Amtsdeutsch, Fachjargon und Modell-Sprech werden zu Sätzen, die eine Leserin ohne Vorwissen beim ersten Lesen versteht. Dabei bleibt der Inhalt stehen: Fristen, Beträge, Dosierungen und Rechtsfolgen werden nicht vereinfacht, sondern erklärt.

Der Skill kann drei Dinge:

- **Umschreiben.** Bestehenden Text in Einfache Sprache übertragen.
- **Neuschreiben.** Bescheide, Anleitungen, Formulare, Patienteninfos, AGB, E-Mails, Websites und Reden von Grund auf verfassen.
- **Prüfen.** Einen Text gegen die Regeln bewerten und jeden Fund mit Korrekturvorschlag melden.

## Installieren

```bash
npx skills add codingjoe/einfache-sprache
```

Ohne Skill-Unterstützung: die Regeln aus `skills/einfache-sprache/SKILL.md` in die Systemanweisung, `AGENTS.md` oder `.cursorrules` kopieren.

Dann einen beliebigen Text geben und sagen: "bitte in Einfacher Sprache".

## So sieht das aus

| Ohne Skill (echter Bescheidtext)                                                                                                                                                                                                                                                                                                              | Mit Skill                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Aufgrund der Tatsache, dass die Berücksichtigung der tatsächlichen Unterkunftskosten die nach § 22 Abs. 1 Satz 1 SGB II maßgebliche Angemessenheitsgrenze überschreitet, werden die Kosten der Unterkunft lediglich in Höhe von 640,00 EUR monatlich anerkannt; eine vollständige Übernahme der tatsächlichen Aufwendungen ist nicht möglich. | **Ihre Miete wird nur zum Teil übernommen**<br><br>Für Mieten gibt es eine Grenze. Bei Ihnen liegt diese Grenze bei 640,00 Euro im Monat.<br><br>Ihre Miete ist höher als die Grenze. Deshalb übernehmen wir nur 640,00 Euro. Den Betrag darüber zahlen wir nicht.<br><br>**Was Sie tun können**<br><br>Sie können gegen diesen Bescheid vorgehen. Wie das geht, steht in der Rechtsbehelfsbelehrung. Das ist der letzte Teil des Bescheids. |

Ein Satz von 44 Wörtern mit Semikolon, vier Substantivierungen und einem Passiv. Daraus werden zwölf Sätze, der längste mit 11 Wörtern. Die 640,00 Euro stehen weiterhin da.

Mehr Beispiele, darunter Modelltexte, die nach Werbebroschüre klingen: `skills/einfache-sprache/examples/vorher-nachher.md`.

## Die Regeln

Der Skill hat zwei Register. Das eine gilt für den Text, den du schreibst. Das andere gilt für die Antwort im Chat, damit die Erklärung nicht selbst im Behördendeutsch landet.

**Der Text**

| Regel                                       | Was sie verhindert                                           |
| ------------------------------------------- | ------------------------------------------------------------ |
| 15 Wörter anstreben, 20 nicht überschreiten | Den Schachtelsatz, in dem die Frist untergeht                |
| Höchstens ein Komma pro Satz                | Die Verschachtelung, die man zweimal lesen muss              |
| Verben statt Substantivierungen             | "die Prüfung erfolgt" statt "wir prüfen"                     |
| Aktiv statt Passiv                          | Die Handlung ohne handelnde Person                           |
| Sag, was zu tun ist                         | Den Text, nach dem man nicht weiß, was morgen zu tun ist     |
| Zahlen konkret, keine Abkürzung             | "zeitnah" und "z. B." statt "innerhalb von 14 Tagen"         |
| Ein Begriff pro Sache                       | Antrag, Gesuch und Ersuchen für dieselbe Sache               |
| Fachbegriff beim ersten Mal erklären        | Das Wort, das man nachschlagen müsste                        |
| Füllwörter streichen                        | "ganzheitlich", "nahtlos", "spielt eine entscheidende Rolle" |

**Die Antwort**

| Regel                                   | Was sie verhindert                            |
| --------------------------------------- | --------------------------------------------- |
| Erster Satz ist die Antwort             | Die Vorrede                                   |
| Kein Gedankenstrich, kein Semikolon     | Den zusammengeschobenen Gedanken              |
| Fachbegriff in wenigen Wörtern erklären | Die Erklärung, die selbst erklärt werden muss |
| Keine Floskeln                          | "Ich hoffe, das hilft"                        |

Die vollständige Sammlung liegt in `skills/einfache-sprache/references/`. Die Regeln sind dort mit **[N]** für Norminhalt, **[B]** für bewährte Praxis und **[H]** für Hausregel gekennzeichnet. Wer einen Text prüft, kann so erkennen, ob eine Regel aus der Norm kommt oder aus dem Handwerk.

## Der Prüfer

`skills/einfache-sprache/scripts/pruefen.py` zählt die Regeln, die ein Muster erkennen kann. Keine Abhängigkeiten, nur Python 3.

```bash
python3 skills/einfache-sprache/scripts/pruefen.py bescheid.md
python3 skills/einfache-sprache/scripts/pruefen.py --text "Der Antrag wird geprüft."
cat bescheid.md | python3 skills/einfache-sprache/scripts/pruefen.py -
python3 skills/einfache-sprache/scripts/pruefen.py --json bescheid.md
python3 skills/einfache-sprache/scripts/pruefen.py --selbsttest
```

Er findet Satzlänge, Kommazahl, Passiv, Nominalstil, Genitiv, Amtsdeutsch, Fachjargon, AI-Sprech, Abkürzungen, Füllwörter, Redewendungen, Konjunktiv, Einschübe und Zahlenformate. Ausgegeben werden Verstöße pro 100 Wörter und die Fundstellen mit Zeilennummer.

**Die Grenze des Verfahrens:** Das ist ein Musterabgleich, kein Grammatik-Parser. Der Prüfer übersieht Verstöße und meldet bei ungewöhnlicher Formatierung falsch. Kategorien wie Negation, Genitiv und langes Wort werden als Hinweis markiert, weil eine Verneinung in einer Warnung richtig sein kann. Kein Werkzeug kann die Einhaltung von DIN 8581-1 garantieren.

## Gemessen

Sieben Testfälle, jeder gegen den Ausgangstext gestellt und mit demselben Prüfer bewertet. Der Ausgangstext ist die Baseline, denn das ist der Text, den ein Nutzer ohne Skill hat.

Der Prüfer trennt harte Verstöße von Hinweisen. Ein harter Verstoß ist ein Satz über 20 Wörtern, ein Semikolon, ein Passiv oder ein Amtswort. Ein Hinweis ist eine Prüfstelle, die oft richtig ist, etwa eine Verneinung in einer Warnung. Die Tabelle zeigt nur die harten Verstöße, weil sie die belastbare Zahl sind.

| Aufgabe                     | Ausgangstext | Mit Skill |                      Veränderung |
| --------------------------- | -----------: | --------: | -------------------------------: |
| Bescheid umschreiben        |         18,2 |       0,0 |                           −100 % |
| Patienteninfo neu schreiben |          0,0 |       0,0 | keine, die Quelle war schon klar |
| Modelltext entkitschen      |         14,6 |       0,0 |                           −100 % |
| AGB-Kündigungsklausel       |          5,7 |       0,0 |                           −100 % |
| Interne E-Mail              |          8,1 |       0,0 |                           −100 % |
| **Mittel**                  |     **10,7** |   **0,0** |                       **−100 %** |

Werte sind harte Verstöße pro 100 Wörter. Nachrechnen:

```bash
python3 skills/einfache-sprache/scripts/pruefen.py einfache-sprache-workspace/iteration-2/eval-0-behoerdenbescheid-umschreiben/with_skill/outputs/antwort.md
```

Die Patienteninfo ist der ehrliche Gegenfall. Ihr Ausgangstext bestand schon aus kurzen Sätzen ohne Amtswörter, deshalb gab es nichts zu verbessern. Einfache Sprache lässt sich nicht an jeder Quelle beweisen.

Dazu kommt eine ausführbare Suite in `cases/`. Sie läuft in GitHub Actions gegen `gemma4:cloud` auf Ollama Cloud, schreibt eine kurze Zusammenfassung als Kommentar an den Pull Request und legt den vollen Bericht als Artefakt ab.

Jedes Modell läuft über dieselben sieben Fälle und gegen denselben Richter, damit die Zeilen vergleichbar sind. Der Standardlauf misst nur mit Skill. Wer wissen will, was der Skill beiträgt, fährt `--vergleich` und bekommt zusätzlich einen Lauf ohne Skill. Das kostet doppelt so viel Kontingent, deshalb läuft es nicht bei jedem Pull Request. In einem solchen Vergleichslauf trennten sich die beiden vor allem bei der Inhaltstreue, der Struktur und der Erfindungsfreiheit, während sich die Regelquote kaum unterschied, weil das Testmodell ohnehin etwa einmal pro 100 Wörter strauchelt.

Ein Beispiel aus dem Lauf. Ohne Skill erfindet das Modell gern eine Frist. Mit Skill schreibt es: "Hier fehlt die Information, bis wann Sie den Einspruch schreiben müssen." Genau das verlangt die Regel, die nach dem ersten Testlauf entstanden ist.

Die Tabelle zeigt drei Dinge nicht.

Erstens lief für sie kein Modellversuch ohne Skill, weil in der Entwicklungsumgebung keine Unteragenten zur Verfügung standen. Die Baseline ist dort der Ausgangstext. Die ausführbare Suite holt das nach.

Zweitens ist der siebte Testfall ein Grenzfall ohne Prüferzahl. Er prüft, ob der Skill erkennt, dass eine Leserin mit Demenz Leichte Sprache braucht, und ob er das sagt, statt still das Falsche zu liefern.

Drittens bleiben im Skill-Ergebnis nur noch Hinweise übrig, keine harten Verstöße. Der Genitiv in "im § 22 des Sozialgesetzbuchs II" ist eine Fundstelle, die die Leserin zum Widerspruch braucht, und bleibt deshalb stehen.

## Was Einfache Sprache nicht ist

**Es ist nicht Leichte Sprache.** Leichte Sprache richtet sich an Menschen mit Lernschwierigkeiten und folgt eigenen Regeln, unter anderem DIN SPEC 33429. DIN 8581-1 grenzt diese Zielgruppe ausdrücklich aus. Wenn ein Text in Leichte Sprache muss, sagt der Skill das und arbeitet nicht heimlich weiter. Siehe `skills/einfache-sprache/references/leichte-sprache.md`.

**Es ist nichts für Werbung.** Einfache Sprache löscht Überzeugungsarbeit. Beschreibung ja, Verkaufsprosa nein.

**Es ist kein Rechtsrat.** Bei Bescheiden, Verträgen und AGB bleibt der Inhalt gesetzt. Einfachere Sprache darf keine Frist verschieben und keine Rechtsfolge abschwächen.

**Es ersetzt keinen Test.** Die Norm sieht Tests mit echten Lesenden vor. Kein Modell und kein Skript ersetzt das.

## Wo das herkommt

`SKILL.md` folgt dem Format von [Agent Skills](https://agentskills.io) und passt in Claude Code, Cursor, VS Code Copilot, OpenAI Codex, Gemini CLI, Goose und OpenCode.

Der Aufbau ist inspiriert von [AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish), das dasselbe für Englisch nach ASD-STE100 macht. Der Inhalt dieses Repos stammt aus den öffentlich zugänglichen Quellen zu DIN 8581-1, gesammelt in `skills/einfache-sprache/references/regeln.md`. Der kostenpflichtige Normtext wurde nicht verwendet und wird nicht zitiert.

## Lizenz

AGPL-3.0. Inoffizielles Projekt, nicht mit DIN oder DIN Media verbunden und nicht von ihnen geprüft.
