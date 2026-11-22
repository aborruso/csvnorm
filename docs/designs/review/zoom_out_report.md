# Rapporto della fase 5: visione d'insieme

* **Documento:** `docs/designs/speed-up-large-files.md` (righe 1-502)
* **Data:** 2026-11-22
* **Revisori:** egm-zoom-out (semplicità e perimetro), egm-inventive-catalyst (compromessi evitabili)
* **Contesto fornito:** `src/csvnorm/encoding.py`, `validation.py`, `core.py`, `tests/test_encoding.py`, `tests/test_validation.py`, `openspec/specs/encoding-detection/spec.md`

## Indice

- Esito
- Rilievo principale: come lavora davvero charset_normalizer
- Rilievi Major
- Rilievi minori (Nit)
- Cosa i revisori considerano solido

## Esito

Nessun Blocker. I Major sono cinque, di cui due segnalati da entrambi i revisori, e i Nit sette. Il rilievo più pesante riguarda la premessa del rilevamento dell'encoding: il documento descrive in modo sbagliato cosa fa oggi `charset_normalizer`.

## Rilievo principale: come lavora davvero charset_normalizer

**Major, egm-zoom-out. Verificato il 2026-11-22 sul codice installato.**

Il documento sostiene che oggi lo spareggio fra codifiche sia protetto perché lavora «sull'intero file» (righe 95 e 180). Non è così:

- `from_path` e `from_bytes` hanno di default `steps=5, chunk_size=512` (`charset_normalizer/api.py:59-60`). Caos e coerenza si calcolano su 5 pezzi di circa 512 caratteri a distanze regolari, cioè circa 2,5 KB in tutto, qualunque sia la dimensione del file.
- Per i file da almeno 10 MB (`TOO_BIG_SEQUENCE = int(10e6)`, `constant.py:24`) il resto del lavoro è una decodifica stretta del file intero, ripetuta per ogni codifica candidata (`api.py:573`, `sequences[int(50e3):].decode(..., errors="strict")`). È questa, con ogni probabilità, la causa dei 106 s, e non un'«analisi» del contenuto. Va confermato con un profilo.
- Il caso «200.000 righe ASCII più un byte latin-1 riconosciuto come cp1006» lo conferma: i pezzi esaminati non contengono quel byte.

Conseguenze per il design:

- Il campione da 1 MB passato a `from_bytes` verrebbe ricampionato a sua volta: 5 pezzi da 512 caratteri. I 64 KB iniziali sono quasi tutti ASCII, e i byte non ASCII delle finestre potrebbero non essere esaminati affatto. Finestre, budget, diradamento «una ogni k» e allineamento alle righe servirebbero a poco.
- Il test di equivalenza non lo vedrebbe, perché i file di `test/` stanno sotto i 10 MB e seguono un altro percorso nella libreria.
- La protezione vera sui file grandi oggi viene dalla decodifica stretta dell'intero file, e il design la sostituisce già con la conversione stretta a blocchi più la ricaduta. Il confronto di riga 180 va riscritto su questa base.

**Direzione proposta:** quando la decodifica UTF-8 fallisce, dare a `charset_normalizer` un campione compatto fatto solo delle righe che contengono byte non ASCII, fino a un tetto. Il campione va esaminato per intero: o è abbastanza piccolo da stare in un solo pezzo (`api.py:130-139` riduce `steps` a 1 quando la lunghezza è al massimo `steps*chunk_size`), oppure si passano `steps` e `chunk_size` adeguati. La conversione stretta a blocchi resta il controllo sull'intero file. Spariscono finestre, diradamento e allineamento.

Collegato, **Major, egm-inventive-catalyst:** il ramo di diradamento «una ogni k» non è toccato da nessun test previsto (file di prova piccoli, casi con uno o due byte non ASCII, file da 826 MB con undici soli valori non ASCII). Il diradamento uniforme è anche la scelta che più facilmente perde un byte raro e decisivo, per esempio un solo byte 0x80-0x9F fra migliaia di vocali accentate. Proposte: test con budget ridotti apposta per forzare quel ramo, e un caso sintetico denso di byte non ASCII con byte rari decisivi, confrontato con il rilevamento completo. Se si adotta la direzione qui sopra, il ramo sparisce e restano utili solo i casi sintetici.

## Rilievi Major

### La fase cinque è probabile, non eventuale

**Entrambi i revisori.** Con i numeri del documento, dopo le fasi due, tre e quattro restano: normalizzazione 24 s, validazione 19 s, conteggi 3 s, conversione a blocchi (oggi 10-14 s) e una o due passate Python nuove sul file. Fanno circa 55-65 s, a ridosso dei 60 s (stima dei revisori). La fase cinque, il `COPY` unico, cambia ordine dei messaggi, exit code e `--strict`, ed è proprio quella senza piano.

- egm-inventive-catalyst nota che l'architettura attuale assorbe già gran parte del costo citato contro il `COPY` unico. La normalizzazione scrive già su un file di appoggio spostato solo alla fine (`core.py:773-816`), e c'è già un'uscita `--strict` dopo la normalizzazione (`core.py:805-810`). Due letture separate hanno anche un costo di accoppiamento: `validate_csv` e `normalize_csv` hanno scale di riserva diverse, e il disaccordo oggi si ricuce dopo, in `_normalize_and_refresh_errors` (`core.py:337-345`).
- egm-zoom-out nota che le due soglie (60 s per la fase cinque, 3 volte per il rilascio) governano due decisioni diverse e lasciano spazio a uno slittamento del perimetro. Propone di decidere adesso fra fase cinque e lettura diretta `latin-1` di DuckDB, invece che a fine lavoro.

**Proposta:** decidere ora il contratto della CLI per il `COPY` unico (ordine dei messaggi, momento dell'uscita con `--strict`, `--check` che resta solo validazione), così la fase cinque diventa un'opzione pianificata e non una riscrittura non prevista.

### Il disco pieno visto davvero non è gestito

**egm-inventive-catalyst.** Il guasto registrato nel problema è la normalizzazione fallita per spazio esaurito. Il design gestisce lo spazio esaurito solo durante la conversione UTF-8 (CUJ 5).

- Un `COPY` di DuckDB senza spazio finisce ancora nel pannello generico «Normalization failed» (`core.py:792-803`).
- Il controllo dello spazio libero sta solo in `scripts/bench_large.py`, non in csvnorm.
- `normalized.csv` si scrive dentro `tempfile.mkdtemp` (`core.py:681`, `778-780`) e arriva all'output con `shutil.move` (`core.py:816`). Se la directory temporanea e quella di output stanno su filesystem diversi, lo spostamento è una copia completa: un'altra scrittura grande e, per un momento, un terzo file grande quanto l'input. Questo punto è condizionale, perché il revisore non può vedere i filesystem della macchina.

**Proposte:**

- controllare lo spazio libero in csvnorm prima di partire, con un avviso invece che un blocco;
- scrivere l'output provvisorio accanto a quello finale, per esempio `.output.csv.partial`, e chiudere con `os.replace`, che è atomico e non copia;
- cancellare `utf8.csv` appena finita la normalizzazione;
- mostrare lo stesso pannello di spazio esaurito anche per gli errori di DuckDB e per gli `OSError` della normalizzazione.

### La ricaduta sul rilevamento completo sta nel modulo sbagliato

**egm-zoom-out.** La regola «se la conversione fallisce dopo un rilevamento a campione, rileva sull'intero file e riconverti» sta in `core.py`. Per applicarla, `core.py` deve sapere come ha lavorato il rilevamento e intercettare `UnicodeDecodeError`. È una questione di encoding e va in `encoding.py`: una funzione che rileva e converte, chiamata una volta da `core.py`. Così `detect_encoding_full` non esce dal modulo.

Inoltre la ricaduta usa `from_path`, che carica in RAM tutto il file, proprio sul percorso dei file grandi e difficili. L'obiettivo «Memoria» deve dichiarare questa eccezione.

### Troppa impalcatura nella fase uno

**egm-zoom-out.** La fase uno aggiunge sette pezzi prima di qualsiasi lavoro sulla velocità. La cartella `scripts/` oggi non esiste.

- `scripts/make_large_csv.py` si può togliere: i casi limite si generano con un fixture pytest in `tmp_path`.
- Il marker `slow` con `addopts` non sembra necessario: l'unico test grande previsto è quello da 50 MB con `tracemalloc`, che si genera in pochi secondi.
- `tests/test_golden.py` può stare dentro i test esistenti. `tests/test_cli.py` lancia già csvnorm con `subprocess` e ha casi di CR conservati (intorno alle righe 427, 470, 573, 760), e `tests/test_integration.py:354-385` copre già il CRLF. Si riusano gli input di `test/` e la nuova cartella contiene solo gli output attesi.
- `tests/test_encoding_equivalence.py` ha una base di confronto ambigua: la riga 341 parla di «copia congelata», la riga 429 di `detect_encoding_full`. Il modo più semplice è scrivere nel test, per ogni file di prova, la codifica che dà oggi, come valore letterale.
- I tempi per fase in `core.py` mettono strumentazione permanente nel percorso principale per un'ottimizzazione una tantum. Meglio misurare nello script di benchmark, attorno alle chiamate di libreria. Se restano, che siano un solo piccolo helper.

## Rilievi minori (Nit)

- **Conversione con la libreria standard** (egm-zoom-out). Due `open(..., newline="")` in modalità testo e `shutil.copyfileobj(src, dst, CHUNK)` danno una conversione a blocchi a memoria costante, conservano CR, LF e CRLF e gestiscono i caratteri multibyte spezzati. Si perde solo la posizione assoluta nel `UnicodeDecodeError`. Cancellare il parziale è ridondante dal lato CLI, perché `temp_dir` viene rimossa nel `finally` (`core.py:829`).
- **Fase zero slegata** (egm-zoom-out). L'archiviazione di `preserve-crlf-line-endings` aggiorna `output-location`, mentre i delta di questo lavoro toccano `encoding-detection` e `processing-pipeline`. Il documento non mostra la dipendenza: si fa a parte, oppure si cita il requisito di `output-location` che questo lavoro tocca.
- **Incoerenze interne** (entrambi):
  - la riga 81 dice che non ci sono domande aperte, la riga 272 rimanda il `COPY` unico «fra le domande aperte»;
  - la riga 162 parla di «un solo passaggio», la riga 427 di «una seconda passata»;
  - l'obiettivo «Memoria» non cita la ricaduta su `from_path`.

  L'algoritmo va descritto una volta sola, nel piano tecnico.
- **Dettaglio di codice nel piano tecnico** (egm-zoom-out). `getincrementaldecoder`, `isascii()`, 4 MB, 64 KB, 1 MB stanno meglio nel piano di implementazione. Il piano tecnico dovrebbe dire la strategia e la proprietà che garantisce.
- **Espressione `COLUMNS` con circa 90 parole chiave** (egm-zoom-out). Funziona ed è verificata. In alternativa si leggono i nomi con `DESCRIBE` e si costruisce in Python una lista esplicita `SELECT "_select" AS "select", ...`, più leggibile, al costo di una query sui metadati. Il revisore non chiede di cambiarla.
- **Segnale d'errore sprecato** (egm-inventive-catalyst). Quando la conversione fallisce, `UnicodeDecodeError` indica la posizione esatta dei byte che smentiscono la scelta. Si potrebbe fare un solo tentativo con un campione allargato attorno a quella posizione, prima del rilevamento completo.
- **Rilettura per i conteggi** (egm-inventive-catalyst). Il numero di righe potrebbe venire dal risultato del `COPY`, ma non è verificato con DuckDB 2.0.0, e con a capo dentro le celle il conteggio potrebbe differire da `get_row_count`.
- **Scansione e campione in due passate** (egm-inventive-catalyst). La scansione UTF-8 potrebbe raccogliere da sola le posizioni non ASCII invece di fermarsi al primo errore, risparmiando una lettura sui file non UTF-8.

## Cosa i revisori considerano solido

- Header e CRLF scritti da DuckDB durante il `COPY`: tolgono due riscritture complete (54 s misurati), eliminano codice invece di aggiungerlo e correggono il difetto del delimitatore alla radice.
- Collo di bottiglia misurato, quindi nessuna ottimizzazione prematura. Scarti motivati di Polars, della modalità separata e della validazione a campione.
- Pulizia della spec: il fallback `file -b --mime-encoding` non esiste nel codice.
- Non obiettivi su stdin, stdout e `--fix-mojibake` espliciti e motivati.
