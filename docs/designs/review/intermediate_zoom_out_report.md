# Rapporto della fase 8: visione d'insieme intermedia

* **Documento:** `docs/designs/speed-up-large-files.md` (righe 1-546)
* **Data:** 2026-11-22
* **Revisore:** egm-zoom-out, con il rapporto della fase 5 (`zoom_out_report.md`) e i sorgenti come contesto

## Indice

- Esito
- Cosa è stato risolto rispetto alla fase 5
- Rilievi Major
- Rilievi minori (Nit)
- Aggiunte giudicate proporzionate
- Semplificazione proposta

## Esito

Nessun Blocker, 4 Major e 6 Nit. La parte nuova che si è complicata più del necessario è il rilevamento dell'encoding: ha due meccanismi per una sola garanzia e tre livelli di ricaduta. Due affermazioni del revisore sono state verificate sul codice installato il 2026-11-22, vedi Major 1.

## Cosa è stato risolto rispetto alla fase 5

- **Risolti:**
  - la premessa su `charset_normalizer`, ora basata su un profilo;
  - l'output provvisorio accanto a quello finale con `os.replace`;
  - il pannello per lo spazio esaurito anche per DuckDB e per l'esportazione degli scarti;
  - la ricaduta spostata in `encoding.py`;
  - le eccezioni all'obiettivo di memoria;
  - l'incoerenza sulle domande aperte.
- **Non risolti:**
  - il contratto della CLI per la fase cinque, il `COPY` unico. Con la stima di 54-62 s quella fase diventa una scommessa alla pari, ma il contratto resta rimandato;
  - i tempi per fase permanenti in `--verbose`.
- **Peggiorato:** il livello di dettaglio del piano tecnico (Major 4).
- **Piano dettagliato non aggiornato:** contraddice il nuovo design alle righe 362, 385, 471-474 e 479, e l'impalcatura della fase uno è rimasta com'era. Rimandato alla fase 9.

## Rilievi Major

### Major 1: il filtro sui valori di byte duplica una garanzia che il campione dà già

- **Ambito:** Piano tecnico, «Rilevamento dell'encoding» (righe 193-197); Overview (riga 31); schema (riga 164).
- **Motivazione:**
  - La regola che vince prende la prima occorrenza di ogni valore di byte `>= 0x80`, quindi il campione da 64 KB contiene già ogni valore di byte alto presente nel file.
  - Sotto i 10 MB, `from_bytes` decodifica in modo stretto l'intero campione per ogni candidato e scarta quelli che falliscono: verificato il 2026-11-22 in `charset_normalizer/api.py:349-391`, dove si riempie `tested_but_hard_failure`.
  - Il campione esclude quindi già le stesse codifiche a un byte che oggi esclude la decodifica completa. Il filtro come passo separato è un secondo meccanismo per la stessa garanzia.
  - L'insieme dei valori di byte serve ancora, ma solo per scegliere le finestre.
- **Proposta:** togliere il filtro come passo della pipeline e dichiarare la proprietà: ogni valore di byte del file compare nel campione, e la decodifica stretta del campione esclude le stesse codifiche che esclude oggi la decodifica completa.

### Major 2: le finestre a byte fisso rompono le codifiche a più byte, e la verifica nuova protegge il lato sbagliato

- **Ambito:** righe 191, 195, 198.
- **Motivazione:**
  - Una finestra di 512 byte centrata su un byte alto spesso inizia o finisce a metà di un carattere Shift_JIS, GBK, Big5, EUC o CP949, e unire le finestre peggiora le cose.
  - Con la decodifica stretta del campione la codifica a più byte giusta può essere scartata come errore, e può vincere una codifica a un byte che decodifica tutto, come latin_1. Il risultato è testo alterato con exit 0, proprio il difetto per cui è stata scartata l'alternativa della riga 291.
  - La verifica della riga 198 scatta solo quando si sceglie una codifica a più byte: copre il caso che il campionamento rende improbabile e non quello che crea.
  - Né i test né il piano hanno un caso di rilevamento a più byte. `tests/test_encoding.py` copre latin-1, cp1251 e macroman.
- **Proposta:** tagliare le finestre su un byte ASCII. Nelle codifiche a più byte compatibili con ASCII un byte ASCII non è mai la parte finale di un carattere, quindi l'allineamento resta valido senza una verifica separata. Tagliare sul byte ASCII più vicino, e non sull'a capo, risolve anche i file a solo CR e le celle enormi. La riga 198 si può togliere: la conversione stretta a blocchi è già una decodifica completa, e la ricaduta della riga 200 intercetta i fallimenti.

### Major 3: tre livelli di ricaduta dove ne basta uno

- **Ambito:** righe 191-192 (BOM e NUL verso il percorso di oggi), 198 (verifica delle codifiche a più byte con la sua ricaduta), 200 (ricaduta in rileva-e-converti).
- **Motivazione:**
  - La riga 200 dice «la ricaduta vive in un solo punto», ma la riga 198 aggiunge dentro `detect_encoding` una seconda passata completa con la sua ricaduta. I file a più byte verrebbero decodificati per intero due volte prima della conversione.
  - L'unica ragione data è chi chiama `detect_encoding` da solo come API pubblica. Il documento non mostra nessun chiamante esterno che abbia bisogno di questa garanzia: è un requisito ipotetico.
  - Con i Major 1 e 2 applicati basta la ricaduta della riga 200. Lo stesso piano, per arrivarci in un test, deve sostituire `charset_normalizer` con `monkeypatch` (riga 488): segno di quanto scatti di rado.
  - Gli instradamenti per BOM e NUL (righe 191-192) sono giustificati e restano.

### Major 4: la parte di design è scesa nei dettagli di implementazione

- **Ambito:** righe 194-197 (128 valori, 128 finestre, 512 byte, «k × dimensione / 64», `chunk_size=512`, `steps`), 238 (`.<nome>.csvnorm-partial`), 240 (`"errno":"28"`), 216.
- **Motivazione:**
  - Il piano tecnico dovrebbe dire la strategia e la proprietà garantita; le costanti stanno nel piano dettagliato.
  - La regola secondaria dei «64 punti fissi» non ha test, prove né una proprietà dichiarata: è un residuo del diradamento uniforme che la fase 5 chiedeva di togliere.
  - `steps` uguale al numero di finestre con `chunk_size=512` fa coincidere i pezzi della libreria con le finestre solo se ogni finestra è lunga esattamente 512 byte. Le finestre a inizio e fine file, e quelle sovrapposte, rompono la corrispondenza.
- **Proposta:** togliere la regola dei 64 punti, se nessun caso di test la giustifica, e spostare le costanti nel piano dettagliato.

## Rilievi minori (Nit)

- **Rischi in contraddizione con il nuovo campione** (riga 255): parla di «righe non ASCII», mentre la riga 195 descrive finestre di byte. L'algoritmo va descritto una volta sola.
- **Tre modi di riconoscere lo spazio esaurito** (riga 240), di cui uno legge il testo del messaggio. Bastano `OSError.errno` e un solo controllo sul messaggio di DuckDB, possibilmente fatto solo dopo che il `COPY` è fallito e il controllo dello spazio conferma il disco pieno.
- **Pulizia dell'output provvisorio non specificata** (righe 70, 238-239). `_cleanup_temp_artifacts` (`core.py:387-418`) cancella solo i percorsi in `temp_files`, e il provvisorio sta fuori da `temp_dir`. Con un errore di DuckDB o con l'uscita di `--strict` (`core.py:805-810`) resterebbe un file nascosto accanto all'output. Basta una frase: il provvisorio si registra in `temp_files`.
- **Soglie del controllo preventivo** (riga 241): con la directory temporanea e quella di output sullo stesso filesystem, il caso comune, i due bisogni si sommano. O si accetta l'approssimazione in modo esplicito, o si controlla una volta per filesystem.
- **Voci di riempimento fra i rischi** (righe 256, 259, 260): registrano che non cambia nulla. Possono stare in una riga di «Cosa non cambia».
- **Tempi per fase permanenti** (riga 68, piano righe 400-403): già segnalato nella fase 5.

## Aggiunte giudicate proporzionate

- Output provvisorio accanto a quello finale con `os.replace`: sostituisce un `shutil.move` che fra filesystem diversi copia senza dirlo (`core.py:816`) e rende vera la promessa del commento a `core.py:773-775`.
- Instradamento di BOM UTF-16, UTF-32 e NUL verso il percorso di oggi.
- L'analisi corretta di `charset_normalizer` (righe 49-55, 300-304).
- Un solo pannello per lo spazio esaurito in conversione, DuckDB ed esportazione degli scarti. È eccessivo solo il modo di riconoscere l'errore.

## Semplificazione proposta

Una sola regola di campionamento: una finestra per ogni valore di byte alto distinto, tagliata su byte ASCII ed esaminata per intero dalla libreria. Si tolgono il filtro separato, la regola dei 64 punti e la verifica delle codifiche a più byte, e resta una sola ricaduta, al momento della conversione. Spariscono due passi e una passata completa sul file, e si chiude il buco delle codifiche a più byte che i passi aggiunti avevano lasciato aperto.
