# Vorher / Nachher

Jedes "Vorher" ist echter Behörden- oder Modelltext. Jedes "Nachher" ist derselbe Inhalt in Einfacher Sprache. Die Angaben in Klammern sind der Rohzählung von `scripts/pruefen.py`, nachprüfbar mit:

```bash
python3 scripts/pruefen.py --text "…"
```

Der Prüfer sieht Muster, keine Bedeutung. Ein einzelner Verstoß in einem guten Text ist meistens eine notwendige Ausnahme, etwa eine Verneinung, die inhaltlich stimmt.

## 1. Bescheid (Textebene, Amtsdeutsch)

**Vorher — 12 Verstöße auf 33 Wörter:**

> Aufgrund der Tatsache, dass die Berücksichtigung der Einkommensverhältnisse im Rahmen der Antragsprüfung durch die zuständige Stelle erfolgt, sind entsprechende Nachweise, die für die Bearbeitung erforderlich sind, beizufügen; andernfalls kann eine Entscheidung nicht erfolgen.

**Nachher — 1 Verstoß auf 32 Wörter:**

> Wir prüfen Ihren Antrag. Dafür brauchen wir einen Nachweis über Ihr Einkommen. Das ist Ihr letzter Lohnzettel.
>
> Legen Sie den Nachweis mit dem Antrag vor. Fehlt der Nachweis, können wir nicht entscheiden.

Der eine Treffer ist die Verneinung "können nicht entscheiden". Sie stimmt inhaltlich und bleibt deshalb stehen. So sieht eine begründete Ausnahme aus.

Was passiert ist: Die Substantivierungen sind Verben geworden (Berücksichtigung → berücksichtigen, Entscheidung → entscheiden). Das Passiv ist Aktiv geworden (die Stelle prüft). Das Semikolon ist ein Satzende geworden. Nichts fehlt, nur die Verpackung ist weg.

## 2. Formularhilfe (Satzebene)

**Vorher:**

> Nachweise über Einkünfte und Einkommensverhältnisse aller im Haushalt lebenden Personen sind der Antragstellung beizufügen, wobei die Vorlage auch in Kopie zulässig ist.

**Nachher:**

> **Diese Unterlagen brauchen wir**
>
> - Ihren letzten Lohnzettel
> - Den letzten Lohnzettel aller Personen in Ihrem Haushalt
>
> Eine Kopie reicht. Sie müssen uns nicht die Originale schicken.
>
> Wir brauchen die Nachweise, um Ihren Anspruch zu berechnen.

Was passiert ist: Aus der Vorschrift ist eine Liste geworden. "Einkommensverhältnisse" ist durch das konkrete Dokument ersetzt (Lohnzettel). Die Erlaubnis, eine Kopie zu schicken, steht jetzt als eigener Satz, weil sie die Frage im Kopf beantwortet.

## 3. Passiv und Funktionsverb (Satzebene)

**Vorher:**

> Die Inbetriebnahme des Geräts erfolgt nach Entfernung der Transportsicherung durch den Nutzer.

**Nachher:**

> 1. Nehmen Sie die Transportsicherung ab. Sie ist hinten am Gerät.
> 1. Stecken Sie den Stecker in eine Steckdose mit Schutzkontakt.
>
> **Achtung:** Stecken Sie den Stecker erst ein, wenn die Spannung passt. Sonst geht das Gerät kaputt.

Was passiert ist: "erfolgt durch den Nutzer" war eine Handlung ohne handelnde Person. Jetzt ist die Person "Sie", und aus einem Satz sind die Schritte geworden, die die Person wirklich tut.

## 4. Patienteninformation (Sicherheit zuerst)

**Vorher:**

> Bei Auftreten von Symptomen, die auf eine Überempfindlichkeitsreaktion hindeuten, ist die Anwendung unverzüglich zu beenden und ein Arzt zu konsultieren.

**Nachher:**

> **Wann Sie sofort aufhören und Hilfe holen**
>
> Eine Überempfindlichkeitsreaktion erkennen Sie zum Beispiel an einem Ausschlag, an Schwellungen im Gesicht oder an Atemnot.
>
> Hören Sie dann sofort auf, das Mittel zu nehmen. Rufen Sie Ihre Ärztin oder Ihren Arzt an. Bei Atemnot rufen Sie den Notruf 112.

Was passiert ist: "Symptome, die auf eine Überempfindlichkeitsreaktion hindeuten" hat die Symptome hinter dem Fachwort versteckt. Die Symptome stehen jetzt vorne, weil sie das sind, was die Person merken kann. Die Handlung ist konkret und steht nach der Bedingung.

## 5. AGB-Klausel (Vertrag)

**Vorher:**

> Eine Kündigung des Vertragsverhältnisses ist unter Einhaltung einer Frist von drei Monaten zum Ende des jeweiligen Vertragsjahres schriftlich gegenüber dem Anbieter zu erklären, widrigenfalls sich das Vertragsverhältnis um jeweils ein weiteres Jahr verlängert.

**Nachher:**

> **Kündigen**
>
> Der Vertrag läuft ein Jahr. Er verlängert sich automatisch um ein weiteres Jahr.
>
> Sie können bis drei Monate vor dem Jahresende kündigen. Schreiben Sie uns dazu einen Brief oder eine E-Mail.
>
> Ein Beispiel: Der Vertrag läuft bis zum 31.12.2026. Dann muss Ihre Kündigung bis zum 30.09.2026 bei uns eintreten.

Was passiert ist: "unter Einhaltung einer Frist von drei Monaten zum Ende des jeweiligen Vertragsjahres" ist rechnerisch richtig und praktisch unbrauchbar. Ein Datumsbeispiel erledigt die Rechnung. Das "widrigenfalls" ist ein eigenes kurzes Stichwort geworden.

## 6. Modelltext ohne Skill (AI-Sprech)

Vorher ein typisches Modell-Ergebnis, ohne diesen Skill erzeugt.

**Vorher — 10 Verstöße auf 66 Wörter:**

> Die Digitalisierung spielt eine entscheidende Rolle für moderne Verwaltungen. Durch die nahtlose Integration digitaler Lösungen können Behörden ihre Prozesse optimieren und einen echten Mehrwert für die Bürger schaffen. Es ist wichtig zu beachten, dass eine ganzheitliche Strategie erforderlich ist, die nicht nur technische, sondern auch organisatorische Aspekte berücksichtigt. Zusammenfassend lässt sich sagen, dass ein solcher Ansatz die Effizienz maßgeblich steigert und die Zufriedenheit der Nutzer erhöht.

**Nachher:**

> Behörden können ihre Arbeit mit digitalen Programmen schneller machen. Ein Beispiel: Ein Antrag, der früher zwei Wochen gebraucht hat, ist heute nach zwei Tagen fertig.
>
> Damit das klappt, müssen zwei Dinge zusammenpassen. Das Programm muss funktionieren, und die Mitarbeitenden müssen es bedienen können.
>
> Weniger Wartezeit ist der Vorteil für die Bürgerinnen und Bürger.

Was passiert ist: Die erste Version enthielt zwei Tatsachen und acht Urteile. Die zweite Version behält die zwei Tatsachen und ersetzt jedes Urteil durch etwas Prüfbares, nämlich die Zahl und die zwei Bedingungen. Der Modelltext klingt gebildet und sagt nichts. Das ist der Grund, warum `wortliste.md` einen eigenen Abschnitt für AI-Sprech hat.

## Was in allen Beispielen gleich bleibt

Zahlen, Fristen, Beträge, Dosierungen, Rechtsfolgen und die Aussage selbst. Einfachere Sprache darf die Zahl nicht ändern, die Frist nicht verschieben und die Rechtsfolge nicht abschwächen. Wenn eine Regel und die Genauigkeit sich widersprechen, gewinnt die Genauigkeit.
