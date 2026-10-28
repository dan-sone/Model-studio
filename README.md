# Model Studio

AI-stödd process- och arkitekturmodellering utan manuellt ritande.

## Mål

Beskriv verksamheten och resonera med AI:n. AI:n skapar och ändrar en strukturerad modell. Diagrammet får automatisk layout.

Exempel:

> Skapa en Order to Cash-process med Microsoft Dynamics 365 F&O som system.
>
> Lägg in kreditkontroll och en separat väg när kunden inte blir godkänd.
>
> Låt ett externt WMS hantera plock och pack.
>
> Flytta kontrollen tidigare och visa vem som ansvarar för varje steg.

Ingen särskild kommandosyntax ska krävas. AI:n ska förstå aktuell modell och tidigare dialog, ställa relevanta följdfrågor och redovisa antaganden.

## Status

Projektet är förberett för implementation. Ingen fungerande AI-app finns ännu i detta repository. Den tidigare kommandobaserade prototypen ingår inte, eftersom den inte uppfyllde huvudkravet.

## Första leverans

Fri text → verkligt AI-anrop via server → validerad strukturerad modell → automatiskt diagram → ändring genom fortsatt dialog → ångra.

Saknad AI-konfiguration ska ge ett tydligt fel. Simulerad AI och regelbaserad kommandotolkning är inte ersättningar för AI-stödet.

## Arkitekturprinciper

- Separera applikationslogik, modellinnehåll och diagramvisning.
- Modellen är sanningskällan. Diagrammet är en vy.
- Använd stabila objekt-ID:n och explicita, typade relationer.
- Stöd aktiviteter, beslut, roller, system och förgreningar.
- Validera och applicera ändringar atomärt med versionshistorik och ångra.
- Systemstöd är förslag tills det verifierats mot relevant konfiguration och källa.
- ArchiMate är en önskad modelleringsriktning. Påstå inte full standardöverensstämmelse innan metamodel och relationer implementerats och validerats.

## Utveckling och användning

Koden hanteras i GitHub. Målet är utveckling med Codex i en molnmiljö och en driftsatt webbapp för Mac, iPad och mobil, utan beroende av att användarens Mac är igång. GitHub lagrar kod; AI-drift, apphosting och datalagring konfigureras separat.

Läs [AGENTS.md](AGENTS.md) och [utvecklingsplanen](docs/implementation-plan.md) före implementation.

API-nycklar hanteras endast på serversidan via miljöns hemlighetshantering. Lägg aldrig nycklar i repositoryt, klientkod, loggar eller chattmeddelanden.
