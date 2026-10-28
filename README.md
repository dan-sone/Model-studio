# Model Studio

AI-stödd process- och arkitekturmodellering genom svensk dialog, med automatiskt diagram.

## Första implementationen

Fri text → serveranrop till OpenAI Responses → strukturerat ändringsförslag → oberoende schemavalidering och domänkontroller → atomär SQLite-transaktion → automatiskt SVG-diagram. Fortsatt dialog får aktuell modell och tidigare samtal. AI kan ställa följdfrågor och besvara frågor utan att ändra modellen.

Stöder aktiviteter, beslut, roller, system, namngivna förgreningar, ändringssammanfattningar, versionshistorik och ångra senaste ändringen. Befintliga ID:n används i explicita ändringsoperationer. AI-genererat innehåll markeras som förslag. Systemstöd, exempelvis Dynamics 365 F&O, behöver verifieras separat. Ingen kommandotolk eller simulerad AI används i appen.

**Status:** implementerad och testad med kontrollerade providersvar. Verklig AI-inferens kräver serverkonfiguration och har inte verifierats i denna miljö. Appen är inte driftsatt på en publik adress. Detta är en förenklad metamodel, inte full ArchiMate- eller BPMN-överensstämmelse.

## Start i molnmiljön

Python 3.12 eller senare:

```sh
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python -m model_studio.server
```

Öppna port 8000 via molnplattformens skyddade förhandsvisning eller använd en separat driftsättning. Standardbindningen är `127.0.0.1`. Ingen lokal utveckling på användarens Mac krävs.

Konfigurera följande via driftmiljöns hemlighets- och variabelhantering. Servern läser inte automatiskt `.env`:

| Variabel | Betydelse |
| --- | --- |
| `OPENAI_API_KEY` | Hemlighet på servern; krävs för AI. |
| `OPENAI_MODEL` | Modell-ID med stöd för Responses och strikt JSON Schema; välj en modell tillgänglig i ert API-projekt. |
| `DATABASE_PATH` | Beständig SQLite-fil, standard `data/studio.sqlite3`. |
| `APP_PASSWORD` | Gemensamt hemligt arbetsytelösenord. Minst 16 tecken krävs vid extern bindning. |
| `HOST` | Standard `127.0.0.1`; `0.0.0.0` bakom skyddad HTTPS-gateway. |
| `PORT` | Standard `8000`. |
| `COOKIE_SECURE` | Sätt `1` vid HTTPS-drift. |

Saknad AI-konfiguration visas i gränssnittet och blockerar AI-knappen. Direkta API-anrop ger ett fel och lämnar modellen intakt. Skriv aldrig API-nycklar i källkod, browserkod eller chatt.

## Användning

Beskriv exempelvis ”Skapa en Order to Cash-process med Microsoft Dynamics 365 F&O som system.” Fortsätt med ”Lägg in kreditkontroll och en separat väg när kunden inte blir godkänd” eller ”Låt ett externt WMS hantera plock och pack”. AI:n får modellens aktuella objekt och relationer och ska behålla deras identiteter. Betydelsefull tvetydighet ska leda till en följdfråga.

Diagrammet får automatisk layout utan manuellt ritande. Hela modellen finns också i en textvy. ”Ångra” återställer modellinnehållet före senaste ändring och skapar ett nytt versionsnummer. Dialogen behålls. Knappen avaktiveras efter ångring tills en ny ändring görs. Ingen flerstegs-undo eller redo ingår ännu.

## Lagring och åtkomst

En serverinstans har **en gemensam arbetsyta**. Alla som loggar in med arbetsytans lösenord ser samma modell och dialog, även på andra enheter. Detta är enkel delad åtkomst, inte individuella konton eller separata användarmodeller. Utan lösenord tillåts enbart standardstart på loopback.

SQLite lagrar aktuell modell, modellhistorik, de senaste 40 dialogmeddelandena, anrops-ID:n och hashade inloggningssessioner. Sessioner gäller ett dygn. Historik och anrops-ID:n sparas tills databasen tas bort; UI visar de senaste 50 versionerna. Ingen localStorage används. Beständigheten beror på att databasfilen ligger på en beständig volym; säkerhetskopiering konfigureras i driften. Kör en instans mot en lokal beständig disk.

Verklig drift kräver en Python-process som hålls igång av hostingplattformen, HTTPS med reverse proxy/gateway, åtkomstbegränsning, beständig disk och serverhemligheter. Gateway ska vidarebefordra Host/Origin oförändrade och begränsa inloggningsförsök samt trafik. Appen gör utgående HTTPS-anrop till `api.openai.com`; tillåt värden i molnmiljöns nätverkspolicy. GitHub lagrar kod och driver inte appen eller AI-anropen. Ingen specifik hosting har valts eller aktiverats.

## Verifiering

```sh
python -m unittest discover -s tests -v
```

Domän-, konkurrens- och HTTP-tester använder kontrollerade AI-svar enbart i tester. För separat Chromium-kontroll:

```sh
pip install playwright
playwright install chromium
CHROMIUM_PATH="$(python -c 'from playwright.sync_api import sync_playwright; p=sync_playwright().start(); print(p.chromium.executable_path); p.stop()')" PYTHONPATH=.:tests python tests/browser_check.py
```

Alternativt sätt `CHROMIUM_PATH` till befintlig Chromium-binär. Browserkontrollen använder också testfixtures, aldrig live-inferens. Se [verifieringsrapporten](docs/verification.md) och [arkitekturen](docs/architecture.md).

För liveacceptans: konfigurera AI, starta appen och kör scenarierna i [implementationsplanen](docs/implementation-plan.md). Kontrollera modellens innehåll, relevanta ändringar, följdfrågor och ID:n. Godkända deterministiska tester visar inte att en viss AI-modell klarar dessa scenarier.
