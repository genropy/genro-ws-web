# genro-ws-web — `WsWebSpaApplication` e lo strato pagine vive

**Version**: 0.1.0
**Last Updated**: 2026-06-01
**Status**: 🔴 DA REVISIONARE — documento non ancora approvato

> Sotto-documento tecnico di `VISION.md`. Referto di cosa il web server
> genro-asgi già fornisce in materia di sessione / connessione / push, e
> proposta dell'unico strato mancante: un'applicazione SPA che tiene vive le
> pagine. Tutto è proposta finché non approvato.

---

## 1. Scopo e relazione con VISION.md

`VISION.md` è la visione: SPA in puro Python, server-driven via WebSocket. Cita
fra i gap "componenti con stato locale" (§7.3), "push server→client" (§7.5) e
"isolamento errori per-connessione" (§7.8), ma non disegna **dove vivono le
pagine** né **come una pagina sopravvive nel tempo** legata a un client.

Questo documento risponde a quella domanda. Disegna lo *strato
applicazione/sessione/pagine vive*: il livello su cui poggeranno poi gli eventi
(Tema A), il render parziale (Tema B) e i widget (Tema C) di VISION.md. Non li
riapre.

Il punto di partenza concreto è la palestra `contrib/live` di genro-builders:
oggi è un'app ASGI con un dizionario di pagine-demo **fisse e condivise** da
tutti i client (`self.demos`, `self.current`), servite via `<iframe>`. Una SPA
vera ha pagine **per-client** che **vivono nel tempo**. Lo scarto fra i due è
esattamente ciò che questo documento colma.

---

## 2. Referto — cosa genro-asgi già fornisce

Indagine condotta sul sorgente installato
(`sub-projects/genro-asgi/src/genro_asgi/`).

| Layer | Esiste? | Identità / chiave | Vita |
| --- | --- | --- | --- |
| Sessione HTTP | sì | `Session`, keyed per session_id (cookie) | server-side, TTL (default 3600s) |
| Connessione WSX | sì | `WsxConnectionInfo`, keyed per `connection_id` (uuid) | dura quanto il socket |
| Stato per-connessione | **no** | — (ogni messaggio è una request a sé) | nessuno |
| Registry connessioni + push | sì | `WsxRegistry._connections: {cid → info}` | per-server |
| Istanza applicazione | **singleton** | una per mount | vita del server |

- **Sessione HTTP.** `Session` porta un `_data: Bag` per lo stato applicativo,
  oltre a `_auth`/`_avatar` e a un `_meta` con `created_at`/`last_access`/`ttl`
  (`session/session.py:24-91`; `data` property ~riga 54; `touch()` e
  `is_expired()` ~righe 84-90). Le sessioni vivono in `MemorySessionStore`,
  keyed per session_id (`session/store.py:41-115`). Il `SessionMiddleware` legge
  il token dal cookie, recupera o crea la sessione e la inietta in
  `scope["session"]` (`middleware/session.py:87-117`). HTTP e WSX condividono la
  **stessa** sessione via cookie.

- **Connessione WSX.** All'apertura del socket si genera un
  `connection_id = uuid4()`, si autentica dallo scope e si registra un
  `WsxConnectionInfo` (`wsx/handler.py:88,103`; `wsx/registry.py:36-70`). Alla
  chiusura, `unregister` (`wsx/handler.py:114`). `WsxConnectionInfo` espone
  `identity` (da `auth`) e `client` (host, port).

- **Stato per-connessione: non esiste.** Ogni messaggio WSX è dispatchato come
  una request indipendente (`wsx/handler.py:188-264`); `WsxConnectionInfo` ha
  `__slots__` fissi (`connection_id, websocket, scope, auth`) e non tiene stato
  applicativo. Niente "namespace della connessione" che sopravviva fra messaggi.

- **Registry + push.** `WsxRegistry` mantiene `_connections: {cid → info}` e offre
  `broadcast(data, exclude=)` e `send_to(identity, data)`: send server→client
  **non sollecitato** (`wsx/registry.py:72-158`). È il canale di push già pronto.

- **Applicazione = singleton.** Ogni `AsgiApplication` è istanziata **una volta**
  al boot per mount, condivisa da tutti i client (`server/server.py:485-541`;
  base con router `main` e `@route` in
  `applications/asgi_application/asgi_application.py:27-65`). Il routing è
  path-based gerarchico: `/index` → metodo `index`, segmenti extra → argomenti,
  sotto-path via `include()` (`genro-routes/core/base_router.py`).

---

## 3. Referto — cosa manca

Un solo buco. Poiché l'applicazione è un **singleton condiviso**, lo stato
per-client (le pagine vive) **non può** stare in attributi d'istanza dell'app —
come invece fa oggi la palestra (`self.demos`/`self.current` sono globali a tutti
i client; la demo è mono-utente di fatto).

Manca quindi **un registro di pagine vive, scoped per client**, in cui ogni voce
è un handler SPA con identità stabile (un `page_id`). Tutto il resto — sessione,
connessione, registry, push — genro-asgi lo fornisce già. Non c'è nient'altro da
inventare a questo livello.

---

## 4. Il modello di pagina viva

```
Server (singleton)
└─ Session (cookie, persiste a reload — genro-asgi)
   └─ registro pagine vive {page_id → SPA handler + last_seen}   ← nuovo
      e le connessioni WSX correnti sono trasporto effimero che si ri-aggancia
```

- **Sotto la sessione, non sotto la connessione.** Una pagina deve sopravvivere a
  un reload del browser e a una riconnessione del WebSocket. La connessione WSX
  muore col socket; la sessione (cookie) persiste. Quindi le pagine vivono nella
  sessione, e la connessione WSX corrente è solo il *trasporto* a cui la pagina
  è agganciata in questo momento: se il socket cade e se ne apre uno nuovo, la
  pagina è ancora lì e vi si ri-aggancia.

- **Login futuro: nessun cambiamento al modello.** Si parte in HTTP; con un login
  la sessione acquista un utente (`auth`/`avatar` sono già campi della `Session`).
  Il registro pagine resta dov'è — diventa solo "le pagine di quell'utente".

- **Una pagina = un handler SPA.** Un `HtmlBuilderHandler` (dialetto HTML di
  genro-builders) con il suo stato e il suo source. L'`InteractiveDemo` della
  palestra ne è il prototipo.

- **Più pagine per sessione.** Tab, finestre o iframe separati: ciascuno è una
  pagina viva distinta col proprio `page_id`, tenuta viva in parallelo nella
  stessa sessione.

---

## 5. Ciclo di vita della pagina

- **Nascita.** L'apertura di una pagina SPA crea l'handler, lo `create()`-a e lo
  registra con un `page_id` sotto la sessione.

- **Vita.** Fra un messaggio e l'altro la pagina resta nel registro. La
  connessione WSX corrente è solo il trasporto: una riconnessione si ri-aggancia
  alla stessa pagina.

- **Morte esplicita.** Il client, su `unload`, manda un `navigator.sendBeacon` a
  un endpoint che chiude la pagina (`close_page(page_id)`): rimozione immediata
  dal registro.

- **Morte per scadenza.** Ogni pagina porta un `last_seen`. Un *reaper*
  periodico rimuove le pagine il cui websocket è morto da più di un Δ (la pagina
  non ha più un trasporto attivo che la "tocchi" da un po'). È la rete di
  sicurezza per i client spariti senza beacon (crash, kill della tab).

> **Rinvio esplicito.** Il reaper è uno dei *timer di sistema* di questo strato.
> La forma dei timer (sync sotto lock vs async) è una decisione aperta, legata
> al modello dei data-element di genro-builders e al recupero del timer
> thread-based di genro-toolbox. **Non si decide qui.** Questo documento si
> limita a dichiarare che il reaper esiste come requisito del ciclo di vita.

---

## 6. Proposta — `WsWebSpaApplication(AsgiApplication)`

Una sottoclasse di `AsgiApplication` che aggiunge lo strato mancante. Qui se ne
fissano **responsabilità e confini**, non le firme.

Cosa aggiunge sopra `AsgiApplication`:

- **Possiede il registro delle pagine vive per-client**, keyed in modo che lo
  stato non finisca mai in attributi d'istanza condivisi (l'app resta singleton):
  il registro è scoped per sessione (sopra `session.data` o uno store dedicato
  keyed per session_id — scelta rinviata, vedi sotto).

- **Espone le rotte di ciclo-vita della pagina** come `@route` (apertura,
  chiusura via beacon, recupero di una pagina per `page_id`), oltre alle rotte
  che servono il guscio SPA e gli artefatti renderizzati.

- **Aggancia la connessione WSX corrente alla pagina** come trasporto, e usa il
  `WsxRegistry` / `send_to(identity, ...)` per spingere le patch a *quella*
  sessione/identità. È il punto in cui il push già esistente di genro-asgi
  diventa il canale delle patch DOM di VISION.md §4.

- **Resta singleton** (com'è corretto per un'app ASGI): tutto lo stato per-client
  vive nei suoi store keyed, non sull'istanza.

Il riempimento del contenuto di pagina passa per il meccanismo generico `@node`
del core genro-builders (vedi `roadmap/node-decorator.md` di genro-builders):
l'handler SPA di base monta il guscio (documento, `<head>` con la runtime,
bootstrap) e crea la radice logica con un `node_id` fisso documentato — es.
`spa_root`. L'autore della pagina si abbona con `@node("spa_root")` e costruisce
lì il contenuto. Niente decoratore `@spa` né metodo `content` convenuto: la SPA
è il primo cliente di `@node`, non un caso speciale.

Esplicitamente **fuori** da questo documento (decisioni successive): le firme dei
metodi; il formato del `page_id`; la scelta fra `session.data` e uno store
dedicato; il render parziale (Tema B di VISION); il modello di eventi (Tema A);
i widget (Tema C); e la forma dei timer (§5). Qui solo responsabilità e confini.

---

## 7. Cosa non si decide qui

- `VISION.md` resta la visione complessiva; i Temi A (eventi), B (render
  parziale), C (widget) restano aperti lì.
- La palestra `contrib/live` resta in genro-builders fino a chiusura del core
  (`VISION.md` §8.3); la migrazione in ws-web è il punto 4 di quel piano.
- Questo documento disegna solo lo *strato applicazione / sessione / pagine
  vive*: la fondazione su cui gli altri temi si appoggeranno.

---

## 8. Riferimenti

- `VISION.md` — visione di genro-ws-web (scopo, temi A/B/C, gap analysis,
  piano operativo).
- genro-builders `roadmap/architecture-contract.md` — area RX (render parziale,
  push, dispatcher generico) e livelli rinviati.
- genro-builders `roadmap/node-decorator.md` — meccanismo `@node`, di cui la SPA
  è il primo cliente (`spa_root`).
- genro-asgi `src/genro_asgi/` — sorgenti citati: `session/session.py`,
  `session/store.py`, `middleware/session.py`, `wsx/handler.py`,
  `wsx/registry.py`, `server/server.py`.
- Sessione Claude Code locale che ha generato questo documento:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-06-01).
