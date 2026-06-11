# genro-ws-web — Scalabilità: mono-processo, multi-processo, Kubernetes

**Version**: 0.1.0
**Last Updated**: 2026-06-01
**Status**: 🔴 DA REVISIONARE — analisi non ancora approvata

> Analisi del modello d'esecuzione (sync-in-thread sotto genro-asgi), dei suoi
> limiti di scala, e di cosa serve per passare da mono a multi-processo /
> Kubernetes. Numeri *misurati* contro numeri *stimati* sono marcati come tali.
> Compagno di `spa-application.md`. Tutto è proposta finché non approvato.

---

## 1. Il modello d'esecuzione (verificato)

Sotto genro-asgi, HTTP e WSX invocano gli handler **identicamente**:

```python
result = await smartasync(node)(**dict(request.query))
```

(`server/dispatcher.py:137`, `wsx/handler.py:215`). `smartasync` dispatcha su
`(async_context, is_coro)`: un handler **sync** dentro un loop attivo cade nel
caso `(True, False)` → **`asyncio.to_thread`** (`smartasync.py:177`).

**Conseguenza verificata empiricamente**: l'handler sync (create+render,
mutazioni `live`) gira in un **thread executor**, dove `is_async_context()`
ritorna **False** e il loop non è visibile in quel thread (`get_running_loop`
è thread-specific). Quindi:

- il ciclo `live` (mutazione → derivazioni → render) è **sempre sync, in un
  thread, sotto `RLock`** — sia al primo render (HTTP `create`) sia ad ogni
  evento successivo (WSX). **Un solo mondo d'esecuzione** per tutto il ciclo di
  vita della pagina, su entrambi i transport;
- l'**async ricompare solo al confine d'uscita** verso il browser
  (`await ws.send_text(...)`), fatto dal dispatcher *dopo* che il thread ha
  restituito il risultato. Il thread sync non tocca mai il websocket.

**Cautela nota**: `is_async_context()` controlla prima un ContextVar
(`_async_mode`) e `to_thread` propaga il contesto. Oggi nessuno chiama
`set_async()`/`set_sync()` (verificato in asgi e toolbox), quindi il thread è
genuinamente sync. Se un domani qualcuno chiamasse `set_async()`, il thread
executor erediterebbe "async" pur senza loop → fragilità da tenere a mente.

---

## 2. Il GIL — il vincolo che governa la scala

- **Un GIL per processo.** Dentro un processo CPython, un solo thread alla volta
  esegue bytecode Python. I thread di un processo **non** parallelizzano il
  *calcolo* Python.
- **L'I/O rilascia il GIL.** Durante una query DB / `recv` / lettura disco il
  thread rilascia il GIL → gli altri thread lavorano. Quindi l'I/O-bound
  **scala** sui thread; il CPU-bound **no**.
- **Per parallelizzare il calcolo Python servono più processi** (un GIL
  ciascuno). È la ragione del multi-worker (gunicorn/uvicorn) e del multi-pod.

Per il nostro modello: il render è **CPU-Python** → il throughput di cicli/s di
un mono-processo è governato dal GIL ≈ quanto rende **un core**. L'I/O (DB) di un
`data_controller` rilascia il GIL → quello scala sui thread, ma è limitato dal
**connection pool**, non dal GIL.

---

## 3. Numeri misurati

Misurato in-process su una pagina realistica (**62 nodi**, ~20 righe con pointer):

| Metrica | Valore misurato |
| --- | --- |
| Ciclo `live` completo (mutazione + full re-render DR3) | **0,54 ms/ciclo** |
| Render puro | 0,535 ms |
| Throughput single-thread (su CPU di sviluppo) | **~1850 cicli/s** |

Il render è quasi tutto il costo del ciclo. È CPU-Python puro, **sorprendentemente
economico**: ~20-50× più veloce di una tipica query DB.

*Stima* (non misurata) per un core di un server cloud entry, più lento della CPU
di test: **~1000-1800 cicli/s per core**.

---

## 4. Stima di capacità per il target reale

**Target dichiarato**: 7000 utenti totali, picco **400-500 contemporanei**,
**picco ~20 chiamate/secondo** totali.

Contro i numeri misurati:

| Risorsa | A 20 cps di picco | Margine |
| --- | --- | --- |
| CPU render (GIL, 1 core) | 20 × 0,54 ms = ~11 ms/s di lavoro | **~1% di un core** |
| RAM pagine vive (~500 attive) | *stima* ~50-200 KB/pagina → ~100-300 MB | rumore su server grosso |
| WebSocket aperte (~500) | banale per un event loop | nessun problema |
| DB (~20 query/s) | trascurabile per Postgres | pool da 10 abbonda |

**Conclusione**: a 20 chiamate/s di picco il sistema usa **~1% di un core**. Il
collo di bottiglia **non è in nessuna parte dell'infrastruttura** — né CPU, né
RAM, né DB, né GIL. **Un mono-processo mono-worker è la risposta definitiva, non
provvisoria.**

Anche scenari molto più carichi (ipotetici) reggono mono-processo: 500
contemporanei che interagiscono ogni 3-4 s = ~130-170 cicli/s = ~10-15% di un
core. Il GIL inizia a mordere solo oltre ~1000 cicli/s *sostenuti* di puro
render — ben oltre il target.

> Nota di onestà: i costi-RAM per pagina e i cicli/s del vCPU cloud sono
> *stime/estrapolazioni*, non misure. Sono ordini di grandezza per ragionare,
> non SLA. Il numero misurato solido è 0,54 ms/ciclo.

---

## 5. Quando (non) serve il multi-processo

Il multi-processo serve per **due** motivi, nessuno dei quali è imposto dal
target attuale:

1. **CPU-bound**: se il render diventasse il costo dominante (pagine da migliaia
   di nodi, render sostenuto > ~1000 cicli/s). Non è il caso a 20 cps.
2. **Resilienza**: isolare i crash, fare rolling deploy senza fermo. Questo è un
   tema di *disponibilità*, non di *capacità*.

A 20 cps di picco: **niente multi-processo, niente sticky, niente pgbouncer,
niente bus pub/sub.** Mono-processo + `MemorySessionStore` + registro pagine in
un dict del processo basta e avanza.

---

## 6. Se/quando si va multi-processo: i limiti strutturali

Il modello "pagine vive server-side" è **stateful in RAM**. Multi-processo
(uvicorn `--workers N` o N pod k8s) significa **N processi separati: N GIL, N RAM,
N event loop, N registri**. Conseguenze:

- **Le pagine vive si frammentano.** 1400 pagine con 4 processi = ~350 per
  processo, in **4 registri separati che non si vedono** (memoria non condivisa).
  Una pagina è raggiungibile **solo** dal processo che la possiede.
- **Sticky obbligatorio.** HTTP e WSX dello stesso browser devono finire sullo
  **stesso** processo (quello che ha le sue pagine). Lo smistamento
  connessione→worker è del **kernel** (criterio di trasporto, cieco
  all'applicazione) — né uvicorn né il kernel sanno fare affinità per sessione.
  Serve un proxy **L7** davanti che legge il cookie.
- **Sticky sulla SESSIONE, non sul page_id.** Il cookie identifica il *browser*,
  non la singola pagina; tutte le pagine di un browser le vuoi sullo stesso
  processo comunque; e al primo routing il `page_id` non esiste ancora. L'unità
  di affinità è quindi il **cookie di sessione**.
- **Sessioni condivisibili, pagine no.** `SessionStore` è già un `Protocol` in
  genro-asgi → un `RedisSessionStore` rende le **sessioni** durabili/condivise.
  Le **pagine vive** (handler con stato vivo) restano per-processo → sticky resta
  necessario anche con sessioni su Redis.
- **Push cross-processo assente.** `WsxRegistry.send_to(identity)` raggiunge solo
  le connessioni del processo locale. Push a un utente su un altro processo, o
  broadcast → serve un **bus pub/sub** tra i registri. Non esiste oggi.
- **Crash di un processo = sue pagine perse.** Sono in RAM, non serializzate. Il
  client deve sapersi riconnettere e **ricostruire** la pagina (vedi §8).

---

## 7. Kubernetes — problemi specifici

Tutto §6, più i tratti effimeri di k8s:

- **Pod effimeri.** Rolling deploy, autoscaling, OOM, node drain, eviction
  uccidono pod di routine → le pagine vive di quel pod spariscono. Il client deve
  ricostruire. `terminationGracePeriodSeconds` + gestione `SIGTERM` per drenare
  dolcemente attenua, non elimina.
- **Connection pool × pod vs `max_connections` Postgres.** Ogni pod ha il suo
  pool psycopg3; l'autoscaling moltiplica i pod → `pod × pool` può superare il
  `max_connections` del DB → connessioni rifiutate. **pgbouncer** davanti è
  praticamente obbligatorio con autoscaling.
- **I default thread/pool mentono in container.** Il pool di `to_thread` è
  `min(32, cpu+4)` calcolato sul `cpu_count` del **nodo**, non sul limite del
  pod. Un pod con `cpu: 1` su un nodo da 64 core crede di avere 64 core → 32
  thread per 1 CPU → thrashing. **Dimensionare esplicitamente** thread pool e
  connection pool.
- **Probe leggere.** liveness/readiness su un endpoint HTTP che **non** tocca il
  DB (un DB lento killerebbe pod sani a cascata).
- **Pattern pulito: 1 worker per pod, scala con i pod.** Lascia a k8s il
  multi-processo (un GIL per pod); ogni pod resta semplice. Evita il doppio
  livello `--workers N × M pod`.

---

## 8. Durabilità: cosa sopravvive a un riavvio/crash del processo

Distinzione cruciale fra **login** e **pagina viva**:

| | Dove può vivere | Sopravvive al crash del processo? |
| --- | --- | --- |
| Sessione / login | Redis (se `RedisSessionStore`) | **sì** → niente re-login |
| Pagina viva (stato) | RAM del processo | **no** → va ricostruita |

Con sessione in-RAM (default attuale): crash → **rifare login**. Con sessione su
Redis: l'utente resta autenticato, ma deve **ricostruire la pagina**.

### Cosa è ricostruibile e cosa no

- **`data` (data bag)**: dati puri, **serializzabili** (`data.to_xml()` →
  `from_xml`, verificato). Salvabile su Redis.
- **`source` struttura**: serializzabile (`source.to_xml()` verificato:
  preserva tag/attributi/pointer). **Ma** la struttura *statica* (prodotta da
  `main()`) è **rigenerabile** eseguendo `create()` — non va salvata. La
  struttura **aggiunta a runtime dal client** (pannelli/nodi inseriti via `live`)
  **non** è rigenerabile da `create()` (non è prodotta dal codice) → quella sì va
  salvata, se la si vuole preservare.
- **Le `func` dei data-element**: una **lambda inline NON è serializzabile**
  (verificato: `pickle` la rifiuta, l'XML non può salvarne il corpo). Un
  riferimento per **nome di metodo** sì (il corpo viene dal codice del processo
  che ricarica). → vedi decisione in `genro-builders/roadmap/data-elements.md`:
  `func` canonica = **nome di metodo dell'handler**; la lambda resta ammessa ma
  **rende la pagina non-serializzabile** (non sopravvive a crash, non adatta a
  multi-processo/durabilità).
- **pickle dell'handler/source "as is"**: **non funziona** — c'è un `RLock`
  (`_live_lock`) che pickle rifiuta; servirebbe `__getstate__` custom. La via
  pulita è XML + func-per-nome, non pickle (più robusto ai rolling update e
  niente superficie d'attacco da deserializzazione).

**Modello di ricostruzione dopo crash** (quando lo si vorrà):
`create()` rigenera struttura statica + func + grafo; la `data` si recupera da
Redis; la struttura dinamica (se preservata) si ricarica da `source.to_xml()`
salvato. Il *riaggancio runtime* della source ricaricata (pointer_map, backref,
handler) è un punto d'implementazione **non ancora verificato**.

> A 20 cps / poche centinaia di sessioni, la durabilità è una **comodità**, non
> una necessità: un riavvio raro che fa ricaricare poche pagine è accettabile.
> Le decisioni di design (func-per-nome, serializzabilità) restano valide come
> *qualità architetturale*, non come requisito di scala.

---

## 9. Ricette operative (per quando servisse)

> Da usare **solo** se si va multi-processo per resilienza/CPU — non imposto dal
> target attuale. Esempi indicativi, da validare nel deployment reale.

### Sticky di sessione con Traefik

Affinità via cookie generato da Traefik sul Service (lega browser→pod, copre
HTTP e WSX se passano dallo stesso router):

```yaml
# IngressRoute / Service Traefik
spec:
  services:
    - name: ws-web
      port: 8000
      sticky:
        cookie:
          name: ws_web_affinity
          secure: true
          httpOnly: true
          sameSite: lax
```

### pgbouncer davanti a Postgres

I pod si connettono a pgbouncer (transaction pooling), che multiplexa su poche
connessioni reali al DB → `pod × pool_pod` non satura `max_connections`. Pool
per-pod **piccolo** (es. 5-10), dimensionato sapendo il `maxReplicas` dell'HPA.

### Sessioni su Redis

`SessionStore` è un `Protocol` in genro-asgi (`session/store.py`). Implementare
`RedisSessionStore` con `get/create/dump/restore` e iniettarlo al posto di
`MemorySessionStore` (`server.py:121`). Rende le sessioni durabili/condivise tra
pod; **non** sposta le pagine vive (restano per-processo).

### uvicorn workers vs k8s pods

- `uvicorn --workers N` = pre-fork di N processi sulla stessa socket; smistamento
  del **kernel** (non applicativo) → **non** garantisce HTTP+WS sullo stesso
  worker senza un L7 davanti.
- **k8s consigliato**: `--workers 1` per pod + scalare i pod; Ingress con
  cookie-affinity fa lo sticky che il kernel non sa fare.

### Dimensionare il thread pool in container

Non fidarsi del default `min(32, cpu+4)` (legge il `cpu_count` del nodo). Fissare
esplicitamente l'executor di default all'avvio e il connection pool DB, coerenti
fra loro (inutile avere 100 thread con 15 connessioni DB).

---

## 10. Riferimenti

- `VISION.md` — visione di genro-ws-web; §7.8 cita la produzione (riconnessione,
  isolamento per-connessione).
- `spa-application.md` — strato sessione / connessione / pagine vive; il registro
  pagine per-sessione di cui qui si discute la frammentazione.
- genro-builders `roadmap/data-elements.md` — decisione `func` per-nome vs
  lambda e relativa serializzabilità.
- genro-asgi `src/genro_asgi/` — `server/dispatcher.py`, `wsx/handler.py`,
  `session/store.py`, `server/server.py`; genro-toolbox `smartasync.py`.
- Sessione Claude Code locale che ha generato questo documento:
  `-Users-gporcari-Sviluppo-genro-ng-meta-genro-modules-sub-projects-genro-builders`
  (2026-06-01).
