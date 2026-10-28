# Verifiering 2026-10-28

## Deterministiska tester

`python -m unittest discover -s tests -v`: 12 tester. Täcker skapande och kontextuell revision via fixture, bevarade identiteter, beslut med två grenar, systembyte, schema och relationsintegritet, atomärt avslag, följdfråga/svar utan modelländring, dialogrevision, persistens, sena/duplicerade anrop, samtidiga transaktioner med en vinnare, undo, saknad AI-konfiguration, vägran/ofullständigt providersvar och HTTP-kedjan inklusive autentisering och Origin-kontroll.

Providertransportens kontrakt kontrolleras med testtransport. HTTP- och browsertester ersätter enbart inferensfunktionen under testkörningen. Produktionskoden använder alltid verklig AI eller returnerar fel.

## Webbläsare

`PYTHONPATH=.:tests python tests/browser_check.py` kördes mot installerad Chromium. Kontrollerade saknad AI-konfiguration, skapande, automatisk beslutslayout och namngiven gren, följdfråga utan modelländring, undo, omladdning samt samma servermodell på dator (1440 px) och mobil (390 px). Inga JavaScript-fel och ingen sidöverbredd på mobil. Bilder granskades separat. Detta var en fixturebaserad kontroll, inte ett live-AI-test.

## Återstår för verklig användning

- `OPENAI_API_KEY` och `OPENAI_MODEL` saknas i den konfigurerade molnmiljön. Inget live-AI-test har körts. Kör de sju acceptansscenarierna mot vald modell efter konfiguration.
- `api.openai.com` behöver tillåtas i molnmiljöns utgående nätverkspolicy för att anrop från denna miljö ska fungera.
- Ingen hostingadress eller beständig driftvolym är konfigurerad. Appen är inte publicerad. HTTPS, arbetsytelösenord, Secure-cookie, gateway och databasbackup behöver sättas upp för en driftsatt gemensam arbetsyta.

Git-kloning och lokala nätverks-/browsertester behövde köras utanför kommandosandboxen. Miljöns ordinarie nätverksproxy behölls. Projektet Florens-2026 har inte ändrats.
