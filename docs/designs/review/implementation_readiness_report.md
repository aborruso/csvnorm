# Rapporto della fase 9: pronto per l'implementazione?

* **Documento:** `docs/designs/speed-up-large-files.md`, righe 322-546 (piano di implementazione dettagliato)
* **Data:** 2026-11-22, round 1
* **Revisori:** egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed)
* **Standard:** `implementation-readiness-standard.md` per i primi due; la persona di stile per il terzo
* **Contesto fornito:** `src/csvnorm/encoding.py`, `validation.py`, `core.py`, `tests/test_encoding.py`, `tests/test_validation.py`, `openspec/specs/encoding-detection/spec.md`. codebase-details ha letto anche `__init__.py`, `cli.py`, `pyproject.toml`, `tests/test_integration.py`, `tests/test_core_helpers.py` e i sorgenti installati di `charset_normalizer`.

## Indice

- Esito
- Blocker
- Major
- Nit
- Verificato e corretto
- Legame con la fase 8

## Esito

**Non pronto.** Dopo l'unione dei doppioni restano 5 Blocker, 17 Major e una quindicina di Nit. Quasi tutto viene da un solo fatto: il piano dettagliato non è stato riallineato alla parte di design dopo le fasi 7 e 8. Chi implementa dovrebbe scegliere fra due testi, e lo standard non lo ammette, perché vuole zero decisioni lasciate a chi implementa.

## Blocker

- **B1. Il campione della fase quattro contraddice il design** (righe 471, 474, 475; tutti e tre i revisori).
  - Il piano descrive ancora la prima versione: 64 KB iniziali, finestre da 4 KiB allineate alle righe, budget da 1 MiB, «una ogni k», costanti da alzare finché il test passa.
  - Il design (righe 193-197) dice tutt'altro: al massimo 128 finestre da 512 byte, prima occorrenza di ogni valore di byte, 64 punti fissi, nessun conteggio di righe, `from_bytes` con `chunk_size=512` e `steps` espliciti.
  - Mancano la funzione che raccoglie i valori di byte e la regola con cui si scarta un candidato. Anche il testo del log è diverso fra le righe 475 e 206.
- **B2. Rami del rilevamento senza voce nel piano** (righe 469-475; implementation-readiness, codebase-details, style).
  - Non c'è nessuna voce per:
    - i BOM UTF-16 e UTF-32, e il BOM UTF-8 seguito da UTF-8 non valido;
    - il byte NUL, senza il quale `binary_file.bin` non darebbe più `ValueError` (`tests/test_encoding.py:135-138`);
    - la verifica delle codifiche a più byte;
    - la regola che distingue una codifica a più byte da una a un byte.
  - `ScanResult` è citato ma non definito.
  - Nessuno di questi rami ha un test.
- **B3. La ricaduta sta nel modulo sbagliato, e così non si può implementare** (righe 473, 477-480, 488; tutti e tre i revisori).
  - Il design la mette in una funzione di `encoding.py` che rileva e converte. Il piano la mette in `core._handle_local_encoding`.
  - La condizione «dopo un rilevamento a campione» non si può verificare: `detect_encoding` restituisce solo una stringa.
  - `detect_encoding_full` è detta privata ma non ha il trattino basso, e viene importata da `core.py` e da un test.
  - Cinque test di `tests/test_core_helpers.py` (righe 71-174) sostituiscono `csvnorm.core._handle_local_encoding`, e il piano non ne tiene conto.
- **B4. Disco e temporanei senza voci nel piano** (righe 238-241 del design, obiettivo «Disco», CUJ 5; implementation-readiness, codebase-details, style).
  - Nessuna fase prevede:
    - l'output provvisorio `.<nome>.csvnorm-partial` e `os.replace` al posto di `shutil.move` (`core.py:816`), con il nuovo percorso restituito da `_setup_output_paths` (`core.py:83-116`);
    - la pulizia del provvisorio in caso di errore e di `--strict` (`core.py:805-810`);
    - l'avviso preventivo sullo spazio, con API e testo;
    - il riconoscimento dello spazio esaurito per DuckDB e per l'esportazione degli scarti (`core.py:792-803`, `validation.py:259`, `416`);
    - il testo del pannello, il delta OpenSpec, i test di CUJ 5.
  - Non sono nel perimetro dei file i test toccati: `tests/test_integration.py::TestOutputWrittenAtTheEnd` (righe 394-449) e `::TestCrlfPreservation` (righe 347-391).
- **B5. Versione in `src/csvnorm/__init__.py`** (riga 535; codebase-details). Il file non contiene una versione: la versione sta solo in `pyproject.toml:7` e si legge con `importlib.metadata` (`cli.py:11`, `39`). La riga 535 va corretta togliendo `__init__.py`.

## Major

- **M1. `utf-8-sig` per i file con BOM contraddice il comportamento di oggi** (riga 469, test alla riga 487; codebase-details). Verificato il 2026-11-22: oggi `detect_encoding("test/utf8_sig_bom.csv")` restituisce `utf-8`. Lo stesso errore è anche nella parte di design (riga 193). Va mantenuto `utf-8`, oppure dichiarato come differenza con il suo motivo.
- **M2. I file di riferimento sono solo una cartella** (righe 370-374). Mancano i nomi dei file, la convenzione per le coppie input e output atteso, gli argomenti della CLI per ogni caso (per esempio un file di manifesto), e i casi non UTF-8 con solo CR, fine riga misti e `\r\r\n` che il design promette per la fase uno. I casi «che la fase quattro migliora» si scoprono solo nella fase quattro, ma i file si creano nella fase uno, e nessuna fase toglie quei `xfail`, mentre il piano di verifica non ne ammette di residui.
- **M3. Il confronto byte per byte del file degli scarti** (riga 379) contraddice la riga 72. `byte_position` e `line_byte_position` cambieranno con la fase tre per i file non UTF-8. Va detto quali colonne si confrontano.
- **M4. Il test di equivalenza non è definito** (righe 382-386, 473). Va scelto se il riferimento è la «copia congelata» o `detect_encoding_full`. Va detto dove sta la codifica attesa per ogni file e quali valori ha, e come si trattano `binary_file.bin` e `README.md` dentro `test/`. «Migliore» va sostituito con il criterio della riga 71.
- **M5. Il formato del log dei tempi per fase non è definito** (righe 391, 400-403): livello, testo, nomi delle fasi, espressione regolare usata da `bench_large.py`. Il log passa da `RichHandler` su stderr, che può mandare a capo le righe.
- **M6. `scripts/make_large_csv.py` senza interfaccia** (righe 394-398, 485): mancano argomenti, contenuto e codifica predefinita. Non è detto se i test lo importano, ma `scripts/` non è un pacchetto, oppure se generano i dati da soli.
- **M7. Spazio esaurito nella conversione incompleto** (riga 448). Va aggiunto `OSError` a `_prepare_working_file` (`core.py:464-471`), con il testo del pannello e un `OSError` diverso da `ENOSPC` gestito a parte, più un test.
- **M8. Ricostruzione di `UnicodeDecodeError`** (righe 442, 448). La formula della posizione è sbagliata per le codifiche a più byte: va tolta la parte ancora nel buffer del decoder. Va detto quale `object` si passa, perché decide cosa mostra il pannello a `core.py:470`. Il controllo `codecs.lookup` (`encoding.py:118-122`) deve restare prima di aprire l'output, perché `test_unsupported_encoding` si aspetta `LookupError`.
- **M9. Lo spareggio insieme al filtro non è definito** (righe 471-472). `_pick_encoding` usa `result.best()` e `best.chaos` (`encoding.py:61-74`): se il filtro toglie dei candidati, `best()` può essere una codifica esclusa.
- **M10. Decisioni lasciate a chi implementa:**
  - riga 419: cosa fare se l'espressione `COLUMNS` dà un header diverso da oggi;
  - riga 474: come alzare le costanti;
  - riga 341: chi decide se una voce di `preserve-crlf-line-endings` non è verificabile;
  - riga 503: la soglia di rilascio va dichiarata raggiungibile senza la fase cinque.
- **M11. Limite superiore di DuckDB promesso dal design (riga 253) ma assente dal piano** (righe 405-407). Serve uno specificatore esatto, per esempio `duckdb>=2.0.0,<3`.
- **M12. Domanda aperta su tmpfs** (righe 91, 258): la fase uno non ha né il passo né la regola per il caso tmpfs.
- **M13. Test della fase quattro incompleti** (righe 482-489). Mancano:
  - i test per NUL, BOM UTF-16 e UTF-32;
  - il filtro che esclude una codifica, per esempio cp1252 con 0x81 presente;
  - la verifica delle codifiche a più byte;
  - il messaggio di `--verbose`;
  - CUJ 2.

  Il test della ricaduta non dice quale simbolo sostituire, quale codifica restituire né quale codifica controllare alla fine.
- **M14. Memoria nel test** (riga 457). Non è spiegato il rapporto fra il limite di 32 MB e gli 8 MB per blocco dell'obiettivo, e non è detto se il test è `slow` né come si genera il file.
- **M15. Firma di `_normalize_and_refresh_errors`** (righe 423, 428): mancano nome, tipo e posizione del nuovo parametro, perché la chiamata è posizionale a `core.py:787-791`. Manca anche la rimozione dell'import a `tests/test_validation.py:14`.
- **M16. «Output identico a oggi su un file senza CR dentro le celle»** (riga 456, style): non è vero per i file non UTF-8 con righe CRLF, perché oggi la modalità testo le trasforma. Va ristretto a «un file con soli LF», oppure va detto quale file si confronta.
- **M17. «uno migliore» e «stesso risultato di oggi o migliore»** (righe 332, 386, style): vanno sostituiti con il criterio della riga 71.

## Nit

- Testo e lingua del pannello per lo spazio esaurito; oggi i pannelli sono in inglese (implementation-readiness).
- Stringhe SQL in Python: `'\1\2'` e `NEW_LINE '\r\n'` richiedono stringhe raw o barre rovesciate raddoppiate (implementation-readiness).
- Numero della nuova versione non indicato, per esempio 1.4.0 (implementation-readiness).
- Il commento a `validation.py:34` cita `_fix_duckdb_keyword_prefix`, che sparirà (implementation-readiness, codebase-details).
- `addopts = "-m 'not slow'"`: un `-m 'not network'` da riga di comando lo sostituisce (`tasks/todo.md:69`); non è detto quali test diventano `slow` (codebase-details).
- Comando esatto di `openspec archive` e obiettivo di `validate --strict` (codebase-details).
- Il passaggio di `crlf` attraverso `_normalize_and_refresh_errors` non ha un test diretto (codebase-details).
- In `tasks/todo.md:12` la voce «misure di memoria e prestazioni» sta dentro un elenco più lungo e non si chiude da sola (codebase-details).
- `PRD.md` NFR-2 (riga 55, «Memory footprint SHOULD not exceed 2x input file size») non è fra gli aggiornamenti (codebase-details).
- `LOG.md` va scritto nelle fasi da uno a quattro, ma compare nei file solo nella fase sei (codebase-details).
- Numero di test in `CLAUDE.md` senza un valore atteso (codebase-details).
- Il guadagno di 54 s è una stima, non una misura; «base stimata a 220 s» contraddice la tabella, che la dà come misurata; unità miste (MB e MiB); `detect_encoding_full` senza trattino basso; l'inciso su mypy (style).
- I commit `107e8e2` e `0c7b8d8` sono stati segnalati come non verificati da codebase-details, che non poteva usare git. Sono verificati nel `git log` della sessione del 2026-11-22.

## Verificato e corretto

- I tre punti del `COPY` in `normalize_csv` (`validation.py:355`, `405`, `427`).
- L'espressione regolare di oggi `(^|,)_([A-Za-z0-9]+)\b`, che lascia invariato `_select_1`.
- Il pannello della conversione a `core.py:468-471` e i test a `tests/test_encoding.py:84-138`.
- `README.md:187` e `PRD.md:42`.
- Le 9 voci di `preserve-crlf-line-endings/tasks.md`.
- In `pyproject.toml`: nessun `addopts`, e il marker `network` presente.
- `mypy` e `pytest-cov` fra le dipendenze di sviluppo.
- Il delta di `add-input-encoding-option` è solo ADDED e non collide con il MODIFIED previsto.

## Legame con la fase 8

I Major della fase 8 sulla parte di design (filtro doppio, finestre che spezzano i caratteri a più byte, tre livelli di ricaduta, dettaglio eccessivo nel piano tecnico) sono ancora aperti, e toccano proprio i Blocker B1, B2 e B3 e i Major M9 e M13 di questa fase. Conviene decidere la semplificazione del rilevamento prima di riscrivere la fase quattro del piano, altrimenti il piano andrebbe riscritto due volte.

---

# Round 2 (2026-11-22, piano riscritto, righe 319-637)

Revisori: egm-implementation-readiness (completed), egm-codebase-details (completed), egm-style (completed). Dopo l'unione dei doppioni: 4 Blocker, 15 Major, una decina di Nit. È l'ultimo giro ammesso per la fase 9.

## Verifiche fatte il 2026-11-22

- `core.py:464-471`: `except ValueError` viene prima di `except (UnicodeDecodeError, LookupError)`. `UnicodeDecodeError` è una sottoclasse di `ValueError`, quindi oggi un errore di conversione compare senza il titolo «Encoding conversion failed».
- `test/binary_file.bin`: 20 byte, comincia con `0x89` (UTF-8 non valido al byte 0), primo NUL al byte 8. Con il piano attuale finirebbe sul percorso del campione invece che sul rilevamento completo.
- File vuoto: oggi `detect_encoding` dà `utf-8`.
- Nomi normalizzati: `shift_jis` diventa `shift-jis`, `latin_1` diventa `latin-1`, `iso8859_15` diventa `iso8859-15`.
- `charset_normalizer/api.py:130-139`: con `steps=1, chunk_size=len(sample)` il campione viene esaminato come un solo pezzo.
- `_setup_output_paths` restituisce oggi una tupla di 3 percorsi, usata solo a `core.py:684`.

## Blocker

- **R2-B1 (implementation-readiness).** Il campione può risultare UTF-8 valido anche se la prima passata ha dimostrato il contrario: un byte come 0x92 compare per la prima volta dentro `’` (E2 80 99), e più avanti da solo in una riga cp1252. In quel caso `detect_encoding` dà `utf-8`, la conversione non parte, la ricaduta non scatta mai e DuckDB riceve UTF-8 non valido. È una regressione: oggi `from_path` esclude `utf_8`.
- **R2-B2 (implementation-readiness, codebase-details).** Il test della ricaduta non può funzionare: con `ascii` non c'è conversione, quindi non c'è errore, quindi non c'è ricaduta.
- **R2-B3 (codebase-details, implementation-readiness).** Ordine delle `except` in `_prepare_working_file`, come verificato qui sopra. Il piano non dice dove va `except OSError`, e lo stesso problema c'è in `detect_and_convert`.
- **R2-B4 (codebase-details, implementation-readiness).** `_warn_if_low_disk_space` ha bisogno di sapere se servirà la conversione prima che la codifica sia nota. Inoltre non è definito il momento della chiamata rispetto a scaricamento ed estrazione, non è detto cosa succede in modalità stdout, e il nome del parametro copre la funzione `needs_conversion` importata.

## Major

- **R2-M1.** Seconda passata senza un metodo veloce per trovare i valori di byte: un ciclo Python byte per byte riporterebbe i 40 s di oggi.
- **R2-M2.** Il NUL si controlla solo nella prima passata, che si ferma al primo errore UTF-8. `binary_file.bin` è proprio questo caso.
- **R2-M3.** Regole delle finestre incomplete:
  - il valore va in `high_bytes` prima o dopo il taglio;
  - cosa succede ai valori che non ottengono mai una finestra, che rompe la proprietà dichiarata;
  - se inizio e fine file valgono come punti di taglio;
  - il lato destro di una finestra a cavallo di due blocchi;
  - le finestre sovrapposte;
  - il campione vuoto;
  - `MAX_CUT_SEARCH` per lato o in totale, da cui dipende se il limite è 73 KiB o 80 KiB.
- **R2-M4.** A `_ScanResult` mancano il motivo e il numero di finestre che servono al log. Non sono indicati né il livello del log né la funzione che lo scrive.
- **R2-M5.** File vuoto: il piano darebbe `ascii`, oggi dà `utf-8`.
- **R2-M6.** Valori attesi: `shift-jis`, oppure `cp932`, non `shift_jis`. «Codifica occidentale» va scritto come elenco: `cp1252`, `latin-1`, `iso8859-15`.
- **R2-M7.** I messaggi di avanzamento di oggi («Detected encoding: X», «Converting from X...») non si possono mostrare con una sola chiamata a `detect_and_convert`. Mancano la regola per `temp_files` e la rimozione degli import inutilizzati a `core.py:18`.
- **R2-M8.** Nuova forma del risultato di `_setup_output_paths` non specificata, compreso il caso stdout.
- **R2-M9.** Test di memoria: con caratteri sopra U+00FF la stringa decodificata raddoppia e il picco può superare i 16 MiB. Il contenuto del file non è fissato, e l'obiettivo «8 MB per blocco» non corrisponde al test.
- **R2-M10.** File di riferimento: mancano i nomi dei file, i byte dei nuovi input, il comando esatto di `subprocess.run`, la directory da cui si risolvono gli input e il caso `empty_file`, che non produce output.
- **R2-M11.** `-d '\t'` in TOML: in una stringa letterale sono due caratteri, e `validate_delimiter` (`utils.py:78`) li rifiuta.
- **R2-M12.** Manca un delta MODIFIED su `output-location`, «Temp and reject file locations», per l'output provvisorio accanto a quello finale.
- **R2-M13.** Test per lo spazio esaurito solo su `normalize_csv`. Mancano conversione, esportazione degli scarti e un test diretto di `_is_disk_full`.
- **R2-M14.** Posizione dell'errore: non è detto quando si legge lo stato del decoder né come si tratta la chiamata finale con `final=True`. Il caso a più byte non è testato, e il messaggio mostrerebbe due posizioni diverse.
- **R2-M15.** Test dei parametri di `from_bytes` non definito. `bench_large.py` non viene aggiornato nelle fasi due e quattro. Il criterio di copertura non si può misurare. `PRD.md` NFR-2 omette alcune esclusioni.

## Nit

- GB18030 ha cifre (0x30-0x39) come secondo e quarto byte delle sequenze a 4 byte: tagliare dopo una cifra potrebbe spezzare un carattere.
- `validation.py:416` sta nel ramo di riserva di `normalize_csv`, quindi lo copre il gestore della normalizzazione.
- Intervalli di riga: i test di `_handle_local_encoding` vanno da 71 a circa 190; i test di rilevamento esistenti vanno da 59 a 138.
- `uv.lock` non è versionato e non è nell'elenco dei file.
- Formati di N e M nell'avviso preventivo; il test di CUJ 5 non controlla l'avviso.
- «uno per ciascuno dei casi coperti prima» non è esatto; c'è una contraddizione di certezza fra le righe 546 e 549; unità; «circa 73 s» va ricavato come 220 / 3; `LOG.md` nelle fasi zero e sei; formulazioni imprecise alle righe 388, 481, 512 e 581.
