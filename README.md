<img src="https://raw.githubusercontent.com/flololan/ha-totalenergies-stations/main/docs/icon.png" alt="Icône de l'intégration (design propre, sans rapport avec la marque)" width="96" align="right">

# TotalEnergies Stations (unofficial) – Intégration Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/flololan/ha-totalenergies-stations)](https://github.com/flololan/ha-totalenergies-stations/releases)
[![License](https://img.shields.io/github/license/flololan/ha-totalenergies-stations)](https://github.com/flololan/ha-totalenergies-stations/blob/main/LICENSE)
[![Validate](https://github.com/flololan/ha-totalenergies-stations/actions/workflows/validate.yml/badge.svg)](https://github.com/flololan/ha-totalenergies-stations/actions/workflows/validate.yml)

**Français** – [Deutsch](#deutsch) – [English](#english)

Intégration HACS **non officielle** qui affiche dans Home Assistant les **prix et la disponibilité**
des carburants dans les stations TotalEnergies en France. Elle utilise la même interface web publique
que la carte officielle des stations <https://services.totalenergies.fr/stations>.

Cas d'usage typique : à cause du plafonnement du prix (1,99 €/L), le SP95-E10 et le SP98 sont
souvent en rupture. Avec cette intégration, vous pouvez être notifié dès que le carburant est de
nouveau disponible dans votre station (voir `examples/`).

> ⚠️ **Avertissement / Clause de non-responsabilité**
>
> - Ce projet n'est **pas** affilié à TotalEnergies ni à Woosmap, et n'est ni soutenu ni autorisé
>   par eux. Toutes les marques appartiennent à leurs propriétaires respectifs. Aucun logo ni
>   élément de marque de TotalEnergies n'est fourni : l'icône de l'intégration est un dessin
>   propre et neutre (pompe à carburant), sans lien avec la marque.
> - Il s'appuie sur une interface web **publique mais non documentée** de la carte des stations.
>   Elle peut changer ou être désactivée à tout moment ; l'intégration peut alors cesser de
>   fonctionner sans préavis.
> - **Usage privé et non commercial uniquement.** Les données récupérées ne doivent **pas être
>   redistribuées**. Merci de respecter les conditions d'utilisation de services.totalenergies.fr.
> - Les intervalles d'interrogation par défaut sont volontairement modérés (30 min, minimum 15 min,
>   10 stations maximum, 2 requêtes parallèles maximum). Merci de ne pas les rendre plus agressifs.
> - Aucun mécanisme de contrôle d'accès n'est contourné et aucun proxy n'est utilisé. L'intégration
>   s'identifie avec un User-Agent honnête (`ha-totalenergies-stations/…`).
> - **Utilisation à vos propres risques.** Aucune garantie quant à l'exactitude ou à l'actualité
>   des données.
> - **Ayants droit :** si vous vous opposez à ce projet, ouvrez une issue ou contactez le
>   mainteneur ; le dépôt sera adapté ou retiré rapidement.

## Fonctionnalités

- Configuration par l'interface : recherche par rayon autour d'un lieu (par défaut : domicile HA,
  1–30 km) **ou** saisie manuelle d'identifiants de station (`NF…`). 10 stations maximum par entrée.
- La recherche par rayon n'a lieu **que** lors de la configuration. Ensuite, seules les stations
  choisies sont interrogées.
- Un appareil par station avec :
  - `sensor` **« Prix <carburant> »** en €/L (attributs : `availability_status`,
    `price_update_date_time`, `product_name`, `location_id`)
  - `binary_sensor` **« <carburant> disponible »** (`on` = AVAILABLE, `off` = UNAVAILABLE,
    `unknown` = UNKNOWN / non renseigné)
  - `sensor` **« Statut d'ouverture »**
- Options : intervalle d'interrogation (30 min par défaut, 15 min minimum), choix des carburants
  et notifications persistantes (désactivées par défaut).
- Événement `totalenergies_stations_fuel_availability_changed` à chaque changement de
  disponibilité + blueprint d'automatisation prêt à l'emploi (voir [Notifications](#notifications)).
- Carburants : SP95-E10, SP98, SP95, Gazole, Excellium Gazole, E85, GPLc, AdBlue.
- Diagnostics avec clés, coordonnées et adresses masquées. Aucune dépendance Python supplémentaire.
- Interface traduite en français, allemand et anglais.

## Installation (HACS)

Prérequis : Home Assistant 2026.3 ou plus récent (icône locale de l'intégration).

1. HACS → Intégrations → ⋮ → **Dépôts personnalisés**
2. URL `https://github.com/flololan/ha-totalenergies-stations`, catégorie **Intégration**
3. Installer « TotalEnergies Stations (unofficial) », redémarrer Home Assistant
4. Paramètres → Appareils et services → **Ajouter une intégration** → « TotalEnergies Stations »

Manuellement : copier le dossier `custom_components/totalenergies_stations` dans
`<config>/custom_components/` puis redémarrer.

## Fonctionnement (transparence)

La carte des stations charge ses clés publiques depuis des fichiers JavaScript librement
accessibles. L'intégration lit ces clés **à l'exécution** depuis ces mêmes fichiers (une fois par
démarrage, puis en cache mémoire). **Aucune clé n'est stockée dans ce dépôt**, pas même en secours.
Si TotalEnergies/Woosmap modifie les scripts, la découverte des clés échoue proprement.

1. **Recherche de stations** (configuration uniquement) : API Woosmap Stores. La clé publique
   Woosmap est liée au domaine, c'est pourquoi cette unique requête envoie les en-têtes `Origin` et
   `Referer` de la carte des stations. Ce n'est pas une imitation de navigateur (le User-Agent reste
   honnête), mais nous le signalons ouvertement.
2. **Données « à chaud »** (prix/disponibilité) : point d'accès de la carte, interrogé avec la clé
   lue dans `front.js`. Un 404 pour une station signifie « pas de données », pas une erreur.
3. Si **toutes** les stations renvoient 401/403/404, les clés sont redécouvertes une fois et la
   requête est répétée. En cas d'erreur, un backoff exponentiel s'applique (jusqu'à 3 h).

## Notifications

Trois façons d'être prévenu quand un carburant redevient disponible :

1. **Blueprint (recommandé)** – importez le blueprint, choisissez les `binary_sensor`
   « … disponible » à surveiller, l'action `notify.…` et un prix maximum optionnel :

   [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fflololan%2Fha-totalenergies-stations%2Fmain%2Fblueprints%2Fautomation%2Ftotalenergies_stations%2Ffuel_available_notify.yaml)

   Le bouton ne fonctionne que si l'adresse de votre instance est renseignée sur
   [my.home-assistant.io](https://my.home-assistant.io). Sinon, importez manuellement :
   **Paramètres → Automatisations et scènes → Blueprints → Importer un blueprint** et collez cette URL :

   ```text
   https://raw.githubusercontent.com/flololan/ha-totalenergies-stations/main/blueprints/automation/totalenergies_stations/fuel_available_notify.yaml
   ```
2. **Notification persistante** – Options de l'intégration → **Notification persistante quand un carburant est de nouveau disponible**.
   Une notification apparaît dans Home Assistant dès qu'un carburant surveillé redevient disponible
   (désactivé par défaut).
3. **Événement** – l'intégration émet `totalenergies_stations_fuel_availability_changed` à chaque
   passage disponible ↔ indisponible (jamais au premier rafraîchissement, jamais pour `unknown`).
   Données : `location_id`, `station_name`, `product_code`, `product_name`, `available`,
   `previous_available`, `availability_status`, `price`. Exemples dans
   `examples/automation_fuel_available.yaml` (déclencheur d'état et déclencheur d'événement).

## Signaler un problème

Ne publiez **jamais** de clés API, de fichiers de diagnostic complets contenant des
coordonnées/adresses, ni de réponses brutes de l'API. Décrivez le comportement, la version de HA, la
version de l'intégration et les lignes de journal pertinentes de
`custom_components.totalenergies_stations`. L'intégration ne journalise jamais les clés ; le fichier
de diagnostic masque clés, coordonnées et adresses mais contient les identifiants de station –
retirez-les si vous ne souhaitez pas révéler votre localisation.

## Sécurité

- Aucun secret dans le code, les tests, les fixtures ni l'historique git. Les fixtures sont synthétiques.
- Aucune connexion sortante autre que vers les trois hôtes nommés dans le code.

## Développement

```bash
pip install pytest ruff
ruff check .
pytest -q
```

Les tests ne couvrent que l'analyse des réponses et la détection des changements (fixtures synthétiques, sans réseau, sans Home Assistant).

CI : `.github/workflows/validate.yml` exécute hassfest, l'action HACS, ruff et pytest à chaque
push/PR (le badge en haut reflète son état). L'icône est générée par `scripts/make_brand.py`.

---

## Deutsch

Inoffizielle HACS-Integration, die **Preise und Verfügbarkeit** von Kraftstoffen an
TotalEnergies-Tankstellen in Frankreich in Home Assistant anzeigt. Sie nutzt dieselbe
öffentliche Web-Schnittstelle wie die offizielle Stationskarte
<https://services.totalenergies.fr/stations>.

Typischer Anwendungsfall: Wegen des Preisdeckels (1,99 €/L) sind SP95-E10 und SP98 häufig
ausverkauft. Mit dieser Integration kannst du dich benachrichtigen lassen, sobald der
Kraftstoff an deiner Station wieder verfügbar ist (siehe `examples/`).

> ⚠️ **Disclaimer / Haftungsausschluss**
>
> - Dieses Projekt ist **nicht** mit TotalEnergies oder Woosmap verbunden, wird von ihnen weder
>   unterstützt noch autorisiert. Alle Marken gehören ihren jeweiligen Inhabern. Es werden keine
>   Logos oder Markenassets von TotalEnergies mitgeliefert: Das Icon der Integration ist ein
>   eigenes, neutrales Design (Zapfsäule) ohne Bezug zur Marke.
> - Es wird eine **öffentliche, aber undokumentierte** Web-Schnittstelle der Stationskarte genutzt.
>   Sie kann sich jederzeit ändern oder abgeschaltet werden; die Integration kann dann ohne
>   Vorwarnung aufhören zu funktionieren.
> - Nutzung **nur privat und nicht-kommerziell**. Die abgerufenen Daten dürfen **nicht
>   weiterverbreitet** werden. Bitte beachte die Nutzungsbedingungen von
>   services.totalenergies.fr.
> - Die Standard-Abfrageintervalle sind bewusst schonend (30 min, Minimum 15 min, maximal
>   10 Stationen, maximal 2 parallele Anfragen). Bitte nicht aggressiver konfigurieren.
> - Es werden keine Zugriffsschutzmechanismen umgangen und keine Proxys verwendet. Die
>   Integration identifiziert sich mit einem ehrlichen User-Agent (`ha-totalenergies-stations/…`).
> - **Nutzung auf eigene Verantwortung.** Keine Gewähr für Richtigkeit oder Aktualität der Daten.
> - **Rechteinhaber:** Falls du als Rechteinhaber Einwände gegen dieses Projekt hast, eröffne bitte
>   ein Issue oder kontaktiere den Maintainer; das Repository wird dann umgehend angepasst
>   oder entfernt.

### Funktionen

- Config-Flow (UI): Umkreissuche um einen Standort (Standard: HA-Home, Radius 1–30 km) **oder**
  manuelle Eingabe von Stations-IDs (`NF…`). Maximal 10 Stationen je Eintrag.
- Die Umkreissuche läuft **nur** im Config-Flow. Im Betrieb werden ausschließlich die gewählten
  Stationen abgefragt.
- Pro Station ein Gerät mit:
  - `sensor` **„<Kraftstoff> Preis“** in €/L (Attribute: `availability_status`,
    `price_update_date_time`, `product_name`, `location_id`)
  - `binary_sensor` **„<Kraftstoff> verfügbar“** (`on` = AVAILABLE, `off` = UNAVAILABLE,
    `unknown` = UNKNOWN/keine Angabe)
  - `sensor` **„Öffnungsstatus“**
- Options-Flow: Abfrageintervall (Standard 30 min, Minimum 15 min), Kraftstoffauswahl und
  persistente Benachrichtigungen (standardmäßig aus).
- Event `totalenergies_stations_fuel_availability_changed` bei jedem Verfügbarkeitswechsel +
  fertiger Automations-Blueprint (siehe [Benachrichtigungen](#benachrichtigungen)).
- Kraftstoffe: SP95-E10, SP98, SP95, Gazole, Excellium Gazole, E85, GPLc, AdBlue.
- Diagnostics mit geschwärzten Schlüsseln, Koordinaten und Adressen.
- Keine zusätzlichen Python-Abhängigkeiten.
- Oberfläche auf Französisch, Deutsch und Englisch übersetzt.

### Installation (HACS)

Voraussetzung: Home Assistant 2026.3 oder neuer (lokales Integrations-Icon).

1. HACS → Integrationen → ⋮ → **Benutzerdefinierte Repositories**
2. URL `https://github.com/flololan/ha-totalenergies-stations`, Typ **Integration**
3. „TotalEnergies Stations (unofficial)“ installieren, Home Assistant neu starten
4. Einstellungen → Geräte & Dienste → **Integration hinzufügen** → „TotalEnergies Stations“

Manuell: Ordner `custom_components/totalenergies_stations` nach `<config>/custom_components/`
kopieren und neu starten.

### Wie es funktioniert (Transparenz)

Die Stationskarte lädt ihre öffentlichen Schlüssel aus frei abrufbaren JavaScript-Dateien.
Die Integration liest diese Schlüssel **zur Laufzeit** aus denselben Dateien (einmal pro
Start, danach im Speicher gecacht). **Im Repository ist kein Schlüssel hinterlegt**, auch kein
Fallback. Ändert TotalEnergies/Woosmap die Skripte, schlägt die Schlüsselerkennung sauber fehl.

1. **Stationssuche** (nur im Config-Flow): Woosmap Stores API. Der öffentliche Woosmap-Schlüssel
   ist domaingebunden, deshalb werden bei dieser einen Anfrage die Header `Origin` und `Referer`
   auf die Stationskarte gesetzt. Das ist keine Browser-Imitation (der User-Agent bleibt ehrlich),
   aber wir benennen es offen.
2. **Hot Data** (Preise/Verfügbarkeit): Endpunkt der Stationskarte, abgefragt mit dem aus
   `front.js` gelesenen Schlüssel. Liefert eine Station 404, gilt das als „keine Daten“, nicht
   als Fehler.
3. Liefern **alle** Stationen 401/403/404, werden die Schlüssel einmal neu ermittelt und die
   Abfrage wiederholt. Bei Fehlern greift ein exponentieller Backoff (bis 3 h).

### Benachrichtigungen

Drei Wege, um benachrichtigt zu werden, wenn ein Kraftstoff wieder verfügbar ist:

1. **Blueprint (empfohlen)** – Blueprint importieren, die zu überwachenden `binary_sensor`
   „… verfügbar“, die `notify.…`-Aktion und optional einen Maximalpreis wählen:

   [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fflololan%2Fha-totalenergies-stations%2Fmain%2Fblueprints%2Fautomation%2Ftotalenergies_stations%2Ffuel_available_notify.yaml)

   Der Button funktioniert nur, wenn die Adresse der eigenen Instanz unter
   [my.home-assistant.io](https://my.home-assistant.io) hinterlegt ist. Alternativ manuell importieren:
   **Einstellungen → Automationen & Szenen → Blueprints → Blueprint importieren** und diese URL einfügen:

   ```text
   https://raw.githubusercontent.com/flololan/ha-totalenergies-stations/main/blueprints/automation/totalenergies_stations/fuel_available_notify.yaml
   ```
2. **Persistente Benachrichtigung** – Integrations-Optionen → **Dauerhafte Benachrichtigung, wenn ein Kraftstoff wieder verfügbar ist**.
   Sobald ein überwachter Kraftstoff wieder verfügbar ist, erscheint eine Benachrichtigung in
   Home Assistant (standardmäßig aus).
3. **Event** – die Integration feuert `totalenergies_stations_fuel_availability_changed` bei jedem
   Wechsel verfügbar ↔ nicht verfügbar (nie beim ersten Abruf, nie bei `unknown`).
   Daten: `location_id`, `station_name`, `product_code`, `product_name`, `available`,
   `previous_available`, `availability_status`, `price`. Beispiele in
   `examples/automation_fuel_available.yaml` (State-Trigger und Event-Trigger).

### Issues melden

Bitte **niemals** API-Schlüssel, vollständige Diagnosedateien mit Koordinaten/Adressen oder
Live-Antworten der API posten. Beschreibe stattdessen das Verhalten, die HA-Version, die
Integrationsversion und relevante Log-Zeilen aus `custom_components.totalenergies_stations`
(Debug-Logging kann über die Geräte-&-Dienste-Seite aktiviert werden). Die Integration loggt
Schlüssel nie; die Diagnostics-Datei schwärzt Schlüssel, Koordinaten und Adressen, enthält aber
Stations-IDs – entferne sie, wenn du deinen Standort nicht preisgeben willst.

### Sicherheit / Security

- Keine Secrets im Code, in Tests, Fixtures oder in der Git-History. Fixtures sind synthetisch.
- Keine ausgehenden Verbindungen außer zu den drei im Code benannten Hosts.
- Siehe Abschnitt **Disclaimer** zu rechtlichen Hinweisen.

### Entwicklung

```bash
pip install pytest ruff
ruff check .
pytest -q
```

Die Tests prüfen nur das Parsing und die Änderungserkennung (synthetische Fixtures, kein Netzwerk,
kein Home Assistant).

CI: `.github/workflows/validate.yml` führt bei jedem Push/PR hassfest, die HACS-Action, ruff und
pytest aus (Badge oben). Das Icon wird mit `scripts/make_brand.py` erzeugt.

---

## English

Unofficial HACS integration that shows **fuel prices and availability** at TotalEnergies
stations in France inside Home Assistant. It uses the same public web interface as the
official station map <https://services.totalenergies.fr/stations>.

Typical use case: due to the French price cap (€1.99/L), SP95-E10 and SP98 are often sold out.
This integration lets you get notified as soon as the fuel is available again (see `examples/`).

> ⚠️ **Disclaimer**
>
> - This project is **not** affiliated with, endorsed by or authorised by TotalEnergies or
>   Woosmap. All trademarks belong to their respective owners. No TotalEnergies logos or brand
>   assets are shipped: the integration icon is an original, neutral design (fuel pump) with no
>   relation to the brand.
> - It relies on a **public but undocumented** web interface of the station map. It may change
>   or be switched off at any time; the integration can stop working without notice.
> - **Private, non-commercial use only.** Do **not** redistribute the retrieved data. Please
>   respect the terms of use of services.totalenergies.fr.
> - Default polling is deliberately gentle (30 min, minimum 15 min, max. 10 stations, max. 2
>   concurrent requests). Please do not configure it more aggressively.
> - No access controls are circumvented and no proxies are used. The integration identifies
>   itself with an honest user agent (`ha-totalenergies-stations/…`).
> - **Use at your own risk.** No warranty for correctness or timeliness of the data.
> - **Rights holders:** if you object to this project, please open an issue or contact the
>   maintainer; the repository will be adjusted or removed promptly.

### Features

- UI config flow: radius search around a location (default: HA home, 1–30 km) **or** manual
  entry of station IDs (`NF…`). Up to 10 stations per entry.
- The radius search only runs in the config flow; afterwards only the selected stations are polled.
- One device per station with:
  - `sensor` **"<fuel> price"** in €/L (attributes: `availability_status`,
    `price_update_date_time`, `product_name`, `location_id`)
  - `binary_sensor` **"<fuel> available"** (`on` = AVAILABLE, `off` = UNAVAILABLE,
    `unknown` = UNKNOWN/null)
  - `sensor` **"Opening status"**
- Options flow: poll interval (default 30 min, minimum 15 min), fuel selection and persistent
  notifications (off by default).
- Event `totalenergies_stations_fuel_availability_changed` on every availability change + a
  ready-made automation blueprint (see [Notifications](#notifications-1)).
- Fuels: SP95-E10, SP98, SP95, Gazole, Excellium Gazole, E85, GPLc, AdBlue.
- Diagnostics with redacted keys, coordinates and addresses. No extra Python requirements.
- UI translated to French, German and English.

### Installation (HACS)

Requires Home Assistant 2026.3 or newer (local integration icon).

1. HACS → Integrations → ⋮ → **Custom repositories**
2. URL `https://github.com/flololan/ha-totalenergies-stations`, category **Integration**
3. Install "TotalEnergies Stations (unofficial)" and restart Home Assistant
4. Settings → Devices & services → **Add integration** → "TotalEnergies Stations"

### How it works (transparency)

The station map loads its public keys from freely served JavaScript files. The integration
reads those keys **at runtime** from the same files (once per start, cached in memory). **No key
is stored in this repository**, not even a fallback. If the scripts change, key discovery fails
cleanly.

1. **Station search** (config flow only): Woosmap Stores API. The public Woosmap key is
   domain-bound, so this single request sets `Origin`/`Referer` to the station map. The user
   agent stays honest; we state this openly.
2. **Hot data** (prices/availability): the map's endpoint, queried with the key read from
   `front.js`. A 404 for a station means "no data", not an error.
3. If **all** stations return 401/403/404 the keys are re-discovered once and the batch is
   retried. Errors trigger exponential backoff (up to 3 h).

### Notifications

Three ways to get notified when a fuel becomes available again:

1. **Blueprint (recommended)** – import the blueprint, pick the "… available" `binary_sensor`
   entities to watch, the `notify.…` action and an optional maximum price:

   [![Open your Home Assistant instance and show the blueprint import dialog with a specific blueprint pre-filled.](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fraw.githubusercontent.com%2Fflololan%2Fha-totalenergies-stations%2Fmain%2Fblueprints%2Fautomation%2Ftotalenergies_stations%2Ffuel_available_notify.yaml)

   The button only works if your instance URL is configured on
   [my.home-assistant.io](https://my.home-assistant.io). Otherwise import manually:
   **Settings → Automations & scenes → Blueprints → Import blueprint** and paste this URL:

   ```text
   https://raw.githubusercontent.com/flololan/ha-totalenergies-stations/main/blueprints/automation/totalenergies_stations/fuel_available_notify.yaml
   ```
2. **Persistent notification** – integration options → **Persistent notification when a fuel is available again**. A
   notification appears in Home Assistant as soon as a watched fuel is available again (off by
   default).
3. **Event** – the integration fires `totalenergies_stations_fuel_availability_changed` on every
   available ↔ unavailable transition (never on the first refresh, never for `unknown`).
   Data: `location_id`, `station_name`, `product_code`, `product_name`, `available`,
   `previous_available`, `availability_status`, `price`. Examples in
   `examples/automation_fuel_available.yaml` (state trigger and event trigger).

### Reporting issues

**Never** post API keys, full diagnostics files containing coordinates/addresses, or raw live API
responses. Describe the behaviour, HA version, integration version and relevant log lines from
`custom_components.totalenergies_stations`. The integration never logs keys; diagnostics redact
keys, coordinates and addresses but include station IDs – remove them if you don't want to reveal
your location.

### Security

- No secrets in code, tests, fixtures or git history. Fixtures are synthetic.
- No outbound connections except to the three hosts named in the code.

### Development

```bash
pip install pytest ruff
ruff check .
pytest -q
```

Tests only cover parsing and change detection (synthetic fixtures, no network, no Home Assistant).

CI: `.github/workflows/validate.yml` runs hassfest, the HACS action, ruff and pytest on every
push/PR (badge at the top). The icon is generated by `scripts/make_brand.py`.

## License

MIT – see [LICENSE](https://github.com/flololan/ha-totalenergies-stations/blob/main/LICENSE).
