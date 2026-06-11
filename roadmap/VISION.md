# genro-ws-web — Vision

**Version**: 0.1.0
**Last Updated**: 2026-06-01
**Status**: 🔴 DA REVISIONARE — documento non ancora approvato

> Documento di visione iniziale. Cattura la discussione architetturale che ha
> fatto nascere il repo. Tutto è proposta finché non approvato.

---

## 1. Scopo

`genro-ws-web` è una libreria per scrivere **single-page application in puro
Python**, server-driven via WebSocket.

Lo sviluppatore descrive:
- la **struttura** della UI con il dialetto HTML di genro-builders;
- lo **stato** con una bag di dati;
- il **binding** stato↔UI con i pointer (`^`/`=`);
- la **logica** in Python, che gira sul server.

Il framework si occupa di: render iniziale, reattività (il dato cambia → la UI
si aggiorna), trasporto sul browser via WebSocket, patch del DOM. Nessun
HTML/CSS/JS scritto a mano, nessun Python nel browser.

È il modello mentale di React (UI funzione dello stato) realizzato **senza
React e senza JS applicativo**: la reattività è gestita dai WebSocket, da cui
il nome.

### Strategia in due fasi

1. **Fase 1 — solo Python, server-driven (questa)**: logica + stato + render
   sul server; il browser è un client sottile che riceve patch DOM e rimanda
   eventi. È un **prototipo valutativo**: serve a misurare *velocità ed
   efficacia* del modello server-driven puro-Python.
2. **Fase 2 — versione JS** come l'attuale GenroPy (client-side), futura.

La Fase 1 è la misura, non la destinazione. I temi tecnici qui sotto (render
parziale, eventi, widget) sono gli **strumenti** di quella misura: il render
parziale misura la velocità; eventi e widget misurano l'efficacia espressiva.

---

## 2. Nome

`genro-ws-web` — la reattività è gestita dai **WS** (WebSocket), non in JS. Il
nome dichiara il meccanismo della Fase 1. Alternative considerate: `genro-html`
(fuorviante: è il dialetto, che resta in genro-builders), `genro-pyreact`
(evocativo del paradigma ma rischia di suggerire un wrapper di React.js),
`genro-web`/`genro-spa` (generici).

---

## 3. Collocazione nei tre repo

| Repo | Ruolo | Si chiude? |
| --- | --- | --- |
| `genro-builders` | core (bag→artefatti) + dialetto **HTML base** (`contrib/html`) + reattività **livello 0** (`pointer_map`, pull, full re-render) | sì — è un core con una sua completezza |
| `genro-asgi` | web server: routing, HTTP/WS dispatch, sessione | indipendente |
| **`genro-ws-web`** | framework SPA: pagine Python, client fisso, render parziale, eventi, widget | in espansione |

**Dato di fatto** (verificato 2026-06-01): nessun downstream esterno
(genro_office, genro_print, genro_textual, genro_scriba) usa il dialetto HTML
dei builder — usano solo il core. genro-asgi non dipende dai builder. Quindi
estrarre il filone HTML-interattivo in un repo a sé è **a basso rischio**:
non rompe nessun downstream.

### Cosa genro-ws-web NON fa

- **Routing**: lo fa genro-asgi (`@route` su `RoutingClass`/`AsgiApplication`,
  router gerarchico, stessa rotta servita su HTTP e WS, sessione per
  connessione). Una "pagina" è una route che ritorna markup.
- **Dialetto HTML**: lo fa genro-builders (`contrib/html`: grammar, renderer,
  HtmlBuilderHandler). ws-web lo *usa*, non lo reimplementa.
- **Reattività livello 0** (`pointer_map`, pull, `live()`): vive nel core
  generico di genro-builders, valida per ogni dialetto. ws-web la consuma.

### Cosa genro-ws-web fa

- **Pagine in Python**: una pagina = un BuilderHandler con stato, esposto come
  route genro-asgi.
- **Client fisso** che possiede il DOM (niente iframe — vedi §6).
- **Render parziale**: il dato cambia → si ri-renderizzano solo i nodi
  dipendenti → patch DOM via WS (Tema B).
- **Eventi generici**: un elemento dichiara "a questo evento manda questo al
  server", che esegue logica Python (Tema A).
- **Widget di alto livello** per l'espressività (Tema C).

---

## 4. Architettura (proposta)

### Modello di identità dei nodi (per il render parziale)

- **1 nodo del source ↔ 1 elemento del DOM** (biiezione, primo livello).
- L'identità dell'elemento DOM è il **path strutturale del nodo nel source**
  (es. `body.panels.users`), calcolabile risalendo i parent (label
  concatenate, fino al wrapper-root). Stabile finché la struttura non cambia.
  Distinto dall'`abs_datapath` dei pointer (che è *cosa* il nodo legge, non
  *dove* sta).
- Il server, alla mutazione di un path-dati, usa `pointer_map[path]` (già
  esistente nel core, granularità per-attributo) per sapere **quali nodi**
  aggiornare; il loro struct-path dice **come si chiamano nel DOM**; il
  ri-render del singolo nodo dà **il nuovo valore**.

### Flusso reattivo (Fase 1, server-driven)

```
browser (client fisso)  --evento-->  WS  -->  genro-asgi route  -->  handler Python
handler muta data  -->  pointer_map dà i nodi dipendenti  -->  ri-render mirato
server  --patch {id, what, value}-->  WS  -->  client applica al DOM
```

Nessun reload, focus/scroll preservati, trasferimento minimo.

### Genericità preservata

Il **dispatcher push** (chi-cosa-è-cambiato, dalla `pointer_map`) è capability
**generica del core** (contratto genro-builders, RX.2): produce eventi di
patch *astratti* (struct-path + attributo + valore), senza nozione di DOM.
L'**adattatore HTML/DOM** (tradurre la patch in `textContent`/`setAttribute`,
trasporto WS) vive in ws-web. Un altro dialetto avrebbe il suo adattatore, o
nessuno (e resta full-render). Così lo scorporo non lega il core all'HTML.

---

## 5. Temi aperti (decisioni da sciogliere)

### Tema A — Modello di eventi generici (il gap principale)

Oggi esiste solo il write-back su `change` di un input. Per essere un
framework serve un modello generale: *"questo elemento, a questo evento, fa
questa logica sul server"* (click, submit, input, ...). Due modelli:

- **A1 — dichiarativo**: l'elemento porta `data-on-<evento>="azione"`; un
  motore generico nel client fisso, su ogni evento DOM, legge l'attributo e
  agisce. **Zero JS per-widget**. Coerente col "puro Python" (vicino a htmx).
- **A2 — componenti JS**: ogni widget ha il suo modulo JS. Potente ma rompe
  il "puro Python".

Orientamento: **A1**. Il color picker è il primo caso pilota — un widget che
dichiara i *suoi* eventi (`input` live mentre scegli, `change` alla conferma),
non solo il `change` generico dei campi di testo.

### Tema B — Render parziale (RX livello 1)

Oggi ogni mutazione ridisegna l'intera pagina (livello 0, scelta consapevole
del contratto: "validare il principio"). Misurato: render lineare ~0.028
ms/nodo, impercettibile fino a ~500 nodi, pesante oltre — ma il costo vero è
il **reload dell'iframe** (ri-parsing DOM, perdita focus/scroll), non il
render Python. Soluzione: render parziale path-based (§4).

Decisioni:
- **B1** — forma dell'id nel markup: `id=` vs `data-node=` (per non collidere
  con id utente).
- **B2** — cosa manda il server: il nuovo valore o il frammento renderizzato.
- **B3** — tabella `what`→property DOM lato client (`text`→textContent,
  `value`→value, `checked`→checked, `class`→className, altro→setAttribute).
- **B4** — il caso difficile: la **struttura cambia** (nodo appare/sparisce,
  lista cresce/si riordina), non solo i dati. Equivalente delle `key` di
  React. È il punto più duro del render parziale.

### Tema C — Widget di alto livello via `_meta`

Poter scrivere `div.color_picker(value="^.border")` invece di
`div.input(html_type="color", value=...)`. Meccanismo: l'`@element` ha già un
parametro **`_meta`** (dict generico di metadati, oggi usato dai compiler
XSD/Textual). Un widget porterebbe `_meta` che dice al **renderer HTML** come
espandersi (es. tag virtuale → `<input type=color>`). `_meta` è generico: ogni
renderer legge le chiavi che gli competono, gli altri ignorano. È l'area
"componenti" droppata dalla roadmap, da riprogettare qui.

---

## 6. Conseguenze necessarie

- **Niente iframe.** La palestra `live` oggi rende in un iframe ricaricato a
  ogni mutazione. Una SPA vera (client fisso che possiede il DOM + render
  parziale che patcha) non può usare l'iframe: il client deve possedere il DOM
  per patcharlo. L'iframe è un limite della palestra, non del modello.
- **Riconnessione WS, gestione latenza, gestione errori** sono requisiti di
  produzione (non della Fase 1 valutativa, ma da tenere a mente). La latenza
  del round-trip server-driven è *proprio ciò che la Fase 1 deve valutare*.

---

## 7. Gap analysis rispetto a React (cosa manca per essere usabile)

Già presente: stato (bag), UI dichiarativa (builder), binding pull
(pointer), dependency tracking (`pointer_map`), un canale client→server
(`set_value`/WSX).

Mancante, in ordine di quanto è bloccante:
1. **Eventi generici** (Tema A) — senza, è un binder di form, non un
   framework. *Il gap più grande.*
2. **Rendering condizionale e liste dinamiche** (Tema B4) — la UI cambia
   forma, non solo valori.
3. **Componenti con stato locale e parametri** — oltre `@struct_method` e i
   widget `_meta` (Tema C), serve l'incapsulamento di stato.
4. **Effetti/lifecycle** — "quando questo dato cambia, fai side-effect".
5. **Server→client push spontaneo** — aggiornamenti iniziati dal server
   (notifiche, altri utenti, job).
6. **Form come unità** — validazione, submit, errori per campo (centrale nel
   dominio gestionale GenroPy).
7. **Navigazione client-side percepita** — cambio vista senza reload, history
   browser. (Il routing lo dà genro-asgi; il "single page" lo fa il client.)
8. **Produzione**: riconnessione WS, ottimistic update/latenza, isolamento
   errori per-connessione.

Per "app giocattolo": servono #1 e #2. Per "app vera": #3, #5, #6, #8.

---

## 8. Piano operativo (concordato 2026-06-01)

1. **Creare il repo `genro-ws-web`** (sub-project Pre-Alpha: documenti e
   architettura, niente codice). ← *fatto in locale; repo GitHub atteso.*
2. **Spostare/raccogliere qui i documenti** architetturali e decisionali del
   filone reattività-SPA (questo VISION.md è il primo).
3. **Tenere provvisoriamente la demo `live` in genro-builders** (`contrib/live`)
   per chiudere le parti di builders ancora da testare. La palestra resta lo
   strumento di validazione delle API del core.
4. **A builders chiuso, migrare** `contrib/live` e tutto il filone SPA in
   genro-ws-web (inclusa la decisione sul destino di `include_datapath` /
   `data-*-pointer`: restano capability opt-in del renderer builders, o
   escono e ws-web estende il renderer — vedi §4 genericità).

Stato corrente in genro-builders già committato e attinente al filone (da
migrare al punto 4): `include_datapath`/`data-*-pointer` nel renderer HTML,
route `set_value`, `app.js`, palestra `live`, demo `colorpicker`.

---

## 9. Riferimenti

- Contratto genro-builders: `roadmap/architecture-contract.md` (area RX,
  livelli successivi rinviati).
- Sotto-contratto reattività livello 0: genro-builders
  `roadmap/reactivity/contract.md` (DR1-DR9).
- Sessione Claude Code locale che ha generato questo documento:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-06-01).
