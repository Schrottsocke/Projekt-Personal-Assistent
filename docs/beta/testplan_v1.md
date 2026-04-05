# Beta-Testplan v1 – DualMind Personal Assistant

> **Version:** 1.0
> **Datum:** 2026-04-05
> **Zielgruppe:** Beta-Tester (keine technischen Vorkenntnisse noetig)

---

## Hinweise fuer Tester

- Bitte teste auf mindestens einem Geraet aus der Geraete-Matrix (siehe unten).
- Notiere bei jedem Schritt, ob das erwartete Ergebnis eingetreten ist.
- Wenn etwas nicht funktioniert: kurz beschreiben, was stattdessen passiert ist.
- Screenshots oder Bildschirmaufnahmen sind sehr hilfreich.
- Am Ende bitte den Feedback-Abschnitt ausfuellen.

---

## Geraete-Matrix

| Geraet         | Browser / App        | Mindestversion          |
| -------------- | -------------------- | ----------------------- |
| iPhone         | Safari               | iOS 16.4 oder neuer     |
| iPad           | Safari               | iPadOS 16.4 oder neuer  |
| Android-Handy  | Chrome               | Android 10 oder neuer   |
| Android-Tablet | Chrome               | Android 10 oder neuer   |
| Windows-PC     | Chrome / Edge / Firefox | aktuelle Version      |
| Mac            | Safari / Chrome      | aktuelle Version        |
| Linux-PC       | Chrome / Firefox     | aktuelle Version        |

**Empfehlung:** Wenn moeglich, teste auf einem Handy UND einem Computer.

---

## 1. Einstieg und Onboarding

Das Ziel dieses Abschnitts ist zu pruefen, ob neue Benutzer problemlos starten koennen.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 1.1 | Oeffne die App im Browser ueber den Link, den du erhalten hast. | Die Anmeldeseite wird angezeigt. Die Seite laedt vollstaendig und ohne Fehlermeldungen. |
| 1.2 | Erstelle ein neues Benutzerkonto mit E-Mail und Passwort. | Du erhaeltst eine Bestaetigung und wirst zur App weitergeleitet. |
| 1.3 | Melde dich ab und melde dich erneut an. | Nach der Anmeldung siehst du das Dashboard mit deinen Daten. |
| 1.4 | Pruefe, ob die App dir beim ersten Start eine kurze Einfuehrung zeigt. | Es erscheint ein Onboarding-Dialog oder eine Willkommensnachricht, die die wichtigsten Funktionen erklaert. |
| 1.5 | Installiere die App auf deinem Startbildschirm (Handy: „Zum Startbildschirm hinzufuegen"). | Die App erscheint als eigenes Symbol auf dem Startbildschirm und oeffnet sich ohne Browser-Leiste. |

---

## 2. Finanzen

Das Ziel dieses Abschnitts ist zu pruefen, ob Rechnungen und Finanzdaten korrekt verwaltet werden.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 2.1 | Erstelle eine neue Rechnung mit Betrag, Datum und Beschreibung. | Die Rechnung erscheint in der Rechnungsliste mit allen eingegebenen Daten. |
| 2.2 | Fotografiere eine Papierrechnung mit der Kamera-Funktion (falls vorhanden). | Die App fragt nach Kamera-Berechtigung, oeffnet die Kamera und das Foto wird gespeichert. |
| 2.3 | Bearbeite eine bestehende Rechnung (z.B. Betrag aendern). | Die Aenderung wird gespeichert und korrekt angezeigt. |
| 2.4 | Loesche eine Rechnung. | Die Rechnung verschwindet aus der Liste. Es erscheint vorher eine Sicherheitsabfrage. |
| 2.5 | Pruefe die Rechnungsliste auf einem schmalen Handy-Bildschirm. | Alle Eintraege sind lesbar, nichts wird abgeschnitten oder ueberlappt. |

---

## 3. Dokumente

Das Ziel dieses Abschnitts ist zu pruefen, ob Dokumente hochgeladen, angezeigt und verwaltet werden koennen.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 3.1 | Lade ein PDF-Dokument hoch. | Das Dokument erscheint in der Dokumentenliste mit Dateiname und Datum. |
| 3.2 | Lade ein Bild (JPG oder PNG) als Dokument hoch. | Das Bild wird hochgeladen und eine Vorschau ist sichtbar. |
| 3.3 | Oeffne ein hochgeladenes Dokument. | Das Dokument wird angezeigt oder zum Download angeboten. |
| 3.4 | Suche nach einem Dokument ueber den Dateinamen. | Das richtige Dokument wird in den Suchergebnissen gefunden. |
| 3.5 | Loesche ein Dokument. | Das Dokument wird entfernt. Es erscheint eine Sicherheitsabfrage. |
| 3.6 | Versuche eine sehr grosse Datei hochzuladen (ueber 10 MB). | Es erscheint eine verstaendliche Fehlermeldung oder der Upload funktioniert. |

---

## 4. Inventar

Das Ziel dieses Abschnitts ist zu pruefen, ob Haushaltsgegenstaende und Einkaufslisten funktionieren.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 4.1 | Fuege einen neuen Einkaufslisteneintrag hinzu (z.B. „Milch"). | Der Eintrag erscheint auf der Einkaufsliste. |
| 4.2 | Hake einen Eintrag auf der Einkaufsliste ab. | Der Eintrag wird als erledigt markiert (z.B. durchgestrichen). |
| 4.3 | Loesche einen Eintrag von der Einkaufsliste. | Der Eintrag verschwindet von der Liste. |
| 4.4 | Erstelle ein Rezept und pruefe, ob Zutaten zur Einkaufsliste hinzugefuegt werden koennen. | Die Zutaten des Rezepts werden korrekt zur Einkaufsliste uebernommen. |
| 4.5 | Pruefe die Einkaufsliste auf dem Handy im Hochformat. | Die Liste ist gut bedienbar, Eintraege lassen sich leicht antippen und abhaken. |

---

## 5. Familie und Aufgaben

Das Ziel dieses Abschnitts ist zu pruefen, ob Aufgaben und Kalender im Familienkontext funktionieren.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 5.1 | Erstelle eine neue Aufgabe mit Titel, Faelligkeit und Beschreibung. | Die Aufgabe erscheint in der Aufgabenliste mit allen Details. |
| 5.2 | Markiere eine Aufgabe als erledigt. | Die Aufgabe wird als erledigt dargestellt. |
| 5.3 | Erstelle einen Kalendereintrag fuer morgen. | Der Eintrag erscheint im Kalender am richtigen Tag. |
| 5.4 | Bearbeite einen bestehenden Kalendereintrag (z.B. Uhrzeit aendern). | Die Aenderung wird gespeichert und korrekt angezeigt. |
| 5.5 | Pruefe, ob Aufgaben und Kalendereintraege auf dem Dashboard sichtbar sind. | Anstehende Aufgaben und Termine erscheinen auf der Startseite. |
| 5.6 | Erstelle einen Schichtplan-Eintrag (falls vorhanden). | Der Schichteintrag wird korrekt gespeichert und angezeigt. |

---

## 6. Einstellungen

Das Ziel dieses Abschnitts ist zu pruefen, ob Profil- und App-Einstellungen funktionieren.

### Testaufgaben

| Nr. | Aufgabe | Erwartetes Ergebnis |
| --- | ------- | ------------------- |
| 6.1 | Oeffne die Profil-Seite und aendere deinen Anzeigenamen. | Der neue Name wird gespeichert und ueberall in der App angezeigt. |
| 6.2 | Wechsle zwischen Hell- und Dunkel-Modus (falls vorhanden). | Das Farbschema der App aendert sich sofort. |
| 6.3 | Pruefe die Benachrichtigungs-Einstellungen. | Die Einstellungen sind verstaendlich beschrieben und lassen sich aendern. |
| 6.4 | Aendere dein Passwort. | Du erhaeltst eine Bestaetigung. Die Anmeldung funktioniert mit dem neuen Passwort. |
| 6.5 | Pruefe die App im Offline-Modus: schalte WLAN/Daten kurz aus und navigiere in der App. | Die App zeigt gespeicherte Daten an oder eine verstaendliche Offline-Meldung. Kein weisser Bildschirm. |

---

## 7. Feedback

Das Ziel dieses Abschnitts ist es, deine Gesamterfahrung festzuhalten.

### Bitte beantworte diese Fragen

| Nr. | Frage |
| --- | ----- |
| 7.1 | Wie einfach war der Einstieg in die App? (1 = sehr schwer, 5 = sehr einfach) |
| 7.2 | Welche Funktion hat am besten funktioniert? |
| 7.3 | Welche Funktion hat Probleme gemacht? Was ist passiert? |
| 7.4 | Gab es Texte oder Beschriftungen, die unklar oder verwirrend waren? |
| 7.5 | Wie schnell hat sich die App angefuehlt? (1 = sehr langsam, 5 = sehr schnell) |
| 7.6 | Wuerdest du die App in diesem Zustand regelmaessig nutzen? Warum / warum nicht? |
| 7.7 | Was wuenscht du dir als naechste Funktion oder Verbesserung? |
| 7.8 | Sonstige Anmerkungen oder Beobachtungen: |

### So gibst du Feedback ab

1. Kopiere die Fragen oben und fuege deine Antworten ein.
2. Sende das Feedback an den Kanal oder die Adresse, die dir mitgeteilt wurde.
3. Haenge gerne Screenshots oder Bildschirmaufnahmen an, falls du Probleme zeigen moechtest.

---

## Ergebnis-Protokoll

Fuer jeden Abschnitt das Gesamtergebnis eintragen:

| Abschnitt | Bestanden | Teilweise | Nicht bestanden | Anmerkungen |
| --------- | --------- | --------- | --------------- | ----------- |
| 1. Einstieg/Onboarding | | | | |
| 2. Finanzen | | | | |
| 3. Dokumente | | | | |
| 4. Inventar | | | | |
| 5. Familie/Aufgaben | | | | |
| 6. Einstellungen | | | | |
| 7. Feedback | | | | |

**Getestetes Geraet:** _______________
**Browser/Version:** _______________
**Datum:** _______________
**Tester-Name/Kuerzel:** _______________
