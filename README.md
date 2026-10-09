# `/einfache-sprache`

Ein AI-Skill, der deutsche Texte in **Einfache Sprache nach DIN 8581-1** bringt.

Amtsdeutsch, Fachjargon und Modell-Sprech werden zu Sätzen, die eine Leserin ohne Vorwissen beim ersten Lesen versteht. Dabei bleibt der Inhalt stehen: Fristen, Beträge, Dosierungen und Rechtsfolgen werden nicht vereinfacht, sondern erklärt.

Der Skill ist Prompt + Script welches sicherstellt das ein Agent keine Regel halluziniert.

## Installieren

```bash
npx skills add codingjoe/einfache-sprache
```

oder 

```
/plugin marketplace add codingjoe/claude-plugins
/plugin install einfache-sprache@codingjoe
```

## So sieht das aus

| Ohne Skill (echter Bescheidtext)                                                                                                                                                                                                                                                                                                              | Mit Skill                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Aufgrund der Tatsache, dass die Berücksichtigung der tatsächlichen Unterkunftskosten die nach § 22 Abs. 1 Satz 1 SGB II maßgebliche Angemessenheitsgrenze überschreitet, werden die Kosten der Unterkunft lediglich in Höhe von 640,00 EUR monatlich anerkannt; eine vollständige Übernahme der tatsächlichen Aufwendungen ist nicht möglich. | **Ihre Miete wird nur zum Teil übernommen**<br><br>Für Mieten gibt es eine Grenze. Bei Ihnen liegt diese Grenze bei 640,00 Euro im Monat.<br><br>Ihre Miete ist höher als die Grenze. Deshalb übernehmen wir nur 640,00 Euro. Den Betrag darüber zahlen wir nicht.<br><br>**Was Sie tun können**<br><br>Sie können gegen diesen Bescheid vorgehen. Wie das geht, steht in der Rechtsbehelfsbelehrung. Das ist der letzte Teil des Bescheids. |

Ein Satz von 44 Wörtern mit Semikolon, vier Substantivierungen und einem Passiv. Daraus werden zwölf Sätze, der längste mit 11 Wörtern. Die 640,00 Euro stehen weiterhin da.

Mehr Beispiele, darunter Modelltexte, die nach Werbebroschüre klingen: `skills/einfache-sprache/examples/vorher-nachher.md`.

## Wo das herkommt

`SKILL.md` folgt dem Format von [Agent Skills](https://agentskills.io) und passt in Claude Code, Cursor, VS Code Copilot, OpenAI Codex, Gemini CLI, Goose und OpenCode.

Der Aufbau ist inspiriert von [AminBlg/SimpleEnglish](https://github.com/AminBlg/SimpleEnglish), das dasselbe für Englisch nach ASD-STE100 macht. Der Inhalt dieses Repos stammt aus den öffentlich zugänglichen Quellen zu DIN 8581-1, gesammelt in `skills/einfache-sprache/references/regeln.md`. Der kostenpflichtige Normtext wurde nicht verwendet und wird nicht zitiert.

## Lizenz

AGPL-3.0. Inoffizielles Projekt, nicht mit DIN oder DIN Media verbunden und nicht von ihnen geprüft.
