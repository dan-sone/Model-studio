# Utvecklingsplan

## Nästa uppgift i Codex

Bygg den första fungerande kedjan från fri dialog till validerad modell och automatiskt diagram. Undersök tillgänglig molnmiljö och runtime, välj en enkel teknisk lösning och dokumentera beslutet. AI-tjänsten ska anropas från serverdelen. Konfigurera hemligheter separat.

## Ansvarsområden

- Domänmodell: objekt, explicita relationer, modellversion och kunskapsstatus.
- AI-adapter: modelleringsinstruktioner, konversationskontext och strukturerade ändringsförslag eller följdfrågor.
- Modellmotor: validering, atomär applicering mot basversion, historik och ångra.
- Diagramvy: automatisk layout och olika perspektiv över samma modell.
- Webbgränssnitt: dialog bredvid diagrammet, ändringssammanfattning och återkoppling.
- Lagring: modeller och dialog med dokumenterat beständighets- och åtkomstbeteende. Synk mellan enheter kräver serverlagring och identitet, inte bara localStorage.

## Acceptansscenarier

1. ”Skapa en Order to Cash-process med Microsoft Dynamics 365 F&O som system.” Verklig AI skapar ett processförslag med aktiviteter och systemrelationer. Antaganden framgår.
2. ”Lägg in kreditkontroll och en separat väg när kunden inte blir godkänd.” Modellen får beslut och alternativa vägar utan manuell ritning.
3. ”Låt ett externt WMS hantera plock och pack.” Endast relevanta kopplingar ändras. Befintliga identiteter bevaras.
4. ”Vem ansvarar för kontrollen?” AI:n förklarar modellens faktiska innehåll och skiljer det från förslag.
5. Vid tvetydighet ber AI:n om förtydligande utan osäker modelländring.
6. Ångra återställer föregående modell. Felaktiga AI-svar och sena svar på äldre modellversioner får inte förstöra modellen.
7. Saknad AI-konfiguration visas tydligt och ger inget falskt lyckat resultat.

## Leverans

Dokumentera installation, start, nödvändiga miljövariabler och faktisk lagring. Kör domäntester och relevanta integrationskontroller. Rapportera live-AI-test och webbläsarverifiering separat från tester med mockade svar. En driftsatt app ska kunna öppnas från flera enheter utan beroende av användarens Mac.

## Senare steg

Fullständig ArchiMate-metamodell och standardexport, avancerade vyer, modelleringsbibliotek, verifierat källstöd för systemkunskap och samarbete ska inte fördröja den första fungerande AI-kedjan.
