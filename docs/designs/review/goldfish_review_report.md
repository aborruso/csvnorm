# Goldfish Annotated Review Report

**Status: resolved** (2026-11-22, auto accept: applicate le correzioni PROPOSE FIX, comprese le quattro da decidere con la proposta indicata; Issue 16 contestata in parte; Issue 17 da confermare; Nit DECLINE non applicati)

**Target:** `docs/designs/speed-up-large-files.md` (righe 1-277, parte di design)
**Fase:** 7, revisione critica, round 1. Fonte dei rilievi: `critic_report.md`.

## Indice

- Verifica fatta prima delle proposte
- Rilievi che chiedono una tua decisione
- Correzioni proposte
- Contestati e da confermare
- Nit non corretti

## Verifica fatta prima delle proposte

Il 2026-11-22 ho profilato `charset_normalizer.from_path` sui primi 100 MB del file da 826 MB:

- tempo totale 8,7 s, di cui 5,3 s in `_codecs.charmap_decode`, la decodifica stretta per ogni codifica candidata;
- i primi sei candidati (cp1250, cp1252, cp1254, cp1257, cp1258, cp850) hanno tutti caos 0,0 e coerenza fra 0,492 e 0,499;
- cp1252 vince solo per lo spareggio di csvnorm, che preferisce le codifiche occidentali (`encoding.py:67-74`).

Il rilievo design-1-B1 è quindi confermato: oggi la scelta fra codifiche a un byte si basa su un segnale debolissimo, e la parte costosa è la decodifica dell'intero file per ogni candidato.

## Rilievi che chiedono una tua decisione

Le correzioni di questi punti cambiano l'architettura, quindi la proposta va approvata da te.

### [Issue 1] [`egm-design`] - Severity: Blocker (design-1-B1, design-1-B2, design-1-M1, design-1-M7; stesso rilievo di zoom-out in fase 5)

* **Affected Scope:** righe 34, 62, 95, 123, 158-182 (Il problema, Obiettivi, CUJ 2, Rilevamento dell'encoding).
* **Discrepancy Description:** il documento dice che oggi la codifica si sceglie analizzando l'intero file. In realtà oggi si decodifica l'intero file per ogni candidato, ed è lì che vanno i 106 s, mentre il punteggio si calcola su 5 pezzi da 512 byte. Il campione mirato da 1 MB verrebbe tagliato di nuovo a 5×512 byte. «Un solo passaggio» non è uno. Elencare tutte le posizioni non ASCII non ha limite di memoria nelle codifiche dense.
* **Rationale:** l'analisi dei rischi parte da una protezione che oggi non esiste, e il campione non farebbe quello che il testo promette.
* ***AI Suggestion:*** PROPOSE FIX, da decidere.
* ***Justification:*** confermato dal profilo qui sopra e dal codice (`charset_normalizer/api.py:59-60`, `130-139`, `573`).
* ***Proposed Edit:*** riscrivere il rilevamento così:
  * **Passata 1, UTF-8.** Decodifica UTF-8 stretta a blocchi, che si ferma al primo errore. Esito invariato: `utf-8-sig`, `ascii`, `utf-8`.
  * **Passata 2, solo per i file non UTF-8**, sempre a blocchi. Raccoglie due cose:
    * **l'insieme dei valori di byte `>= 0x80` presenti in tutto il file**, al massimo 128 valori, calcolato con `bytes.translate`;
    * **un campione di righe che contengono byte non ASCII**, scelte in modo deterministico a passo fisso sull'offset del file, con almeno una riga per ogni valore di byte presente e un tetto fisso (per esempio 64 KB).
  * **Filtro di decodificabilità senza decodificare tutto.** Per le codifiche a un byte la decodificabilità dipende solo dai valori di byte presenti, quindi l'insieme raccolto basta per escludere i candidati che oggi la decodifica completa escluderebbe. Riproduce la garanzia vera di oggi senza decodificare l'intero file per ogni candidato.
  * **Punteggio sul campione intero.** Il campione va a `from_bytes` con `chunk_size=512` e `steps` uguale al numero di pezzi del campione, così ogni byte del campione viene esaminato. I candidati esclusi dal filtro si scartano, poi si applica lo spareggio di oggi.
  * **Memoria limitata:** l'insieme dei byte più il campione, indipendenti dalla dimensione del file.
  * Il piano tecnico descrive la strategia e la proprietà garantita; numeri come 64 KB, 4 MB e `steps` passano nel piano dettagliato.

### [Issue 2] [`egm-design`] - Severity: Major (design-1-M2; in conflitto con zoom-out fase 5)

* **Affected Scope:** righe 60, 178 (Obiettivi «Memoria», seconda mitigazione).
* **Discrepancy Description:** la ricaduta su `from_path` legge tutto il file in RAM e costa circa 106 s, senza esenzione negli obiettivi. Non è detto in quale strato vive il nuovo tentativo, né cosa succede al secondo fallimento.
* **Rationale:** viola gli obiettivi di tempo e memoria proprio sul percorso dei file grandi.
* ***AI Suggestion:*** PROPOSE FIX, da decidere dove vive il nuovo tentativo.
* ***Justification:*** i due revisori propongono strati diversi: egm-design dice `core.py`, egm-zoom-out (fase 5) dice `encoding.py`. Con l'Issue 1 la ricaduta scatta solo se la conversione stretta fallisce dopo il filtro di decodificabilità. Per le codifiche a un byte non può succedere, quindi resta per quelle a più byte.
* ***Proposed Edit:***
  * negli obiettivi: «La ricaduta sul rilevamento completo, rara, è esente dai limiti di tempo e memoria»;
  * nel piano tecnico: nuovo tentativo in un solo punto, una funzione di `encoding.py` che rileva e converte, chiamata da `core.py` (proposta di zoom-out, che tiene `core.py` sottile);
  * al secondo fallimento resta il pannello «Encoding conversion failed», exit 1, come oggi.

### [Issue 3] [`egm-design`] - Severity: Major (design-1-M8)

* **Affected Scope:** righe 63-67, 189 (Obiettivi «Output» e «Validazione completa», Conversione in UTF-8).
* **Discrepancy Description:** oggi la conversione in modalità testo trasforma in LF tutti i fine riga dei file non UTF-8. Dopo la correzione DuckDB vede i fine riga originali, quindi `byte_position` e `csv_line` del file degli scarti cambiano per ogni file non UTF-8 con CRLF.
* **Rationale:** «il file degli scarti contiene le stesse righe di oggi» e l'identità byte per byte non possono valere.
* ***AI Suggestion:*** PROPOSE FIX, da decidere come definire la parità.
* ***Justification:*** è un effetto diretto della correzione che hai deciso (`newline=""`), non previsto nel documento.
* ***Proposed Edit:***
  * la parità del file degli scarti diventa «stessi numeri di riga, stesse colonne e stessi tipi di errore»; le posizioni in byte possono cambiare per i file non UTF-8;
  * il cambio dei fine riga che DuckDB vede entra fra le deviazioni dichiarate;
  * nell'insieme di riferimento entrano file non UTF-8 con solo CR e con fine riga misti.

### [Issue 4] [`egm-design`, `egm-structural`, `egm-style`] - Severity: Major (design-1-M3, structural-1-M8, style-1 disco, design-1-N3)

* **Affected Scope:** righe 46, 61, 109-113, 140-154, 190, 211-214 (Disco, CUJ 5, schema «Dopo», Spazio su disco).
* **Discrepancy Description:**
  * CUJ 5 promette un pannello per il disco pieno, ma `core.py:464-471` non intercetta `OSError`;
  * il disco pieno visto davvero il 2026-11-22 è avvenuto durante la normalizzazione di DuckDB, non durante la conversione;
  * lo schema «Dopo» non mostra `normalized.csv`;
  * la riga 213 confonde il disco con la memoria e cita un «terzo passaggio» mai definito.
* **Rationale:** un problema dichiarato resta senza risposta, e il testo si contraddice.
* ***AI Suggestion:*** PROPOSE FIX, da decidere quanto spingersi.
* ***Justification:*** verificato sul codice (`core.py:464-471`, `792-803`). Il caso delle directory su filesystem diversi, segnalato in fase 5, resta da verificare sulla macchina.
* ***Proposed Edit:*** versione minima, senza cambiare dove stanno i temporanei:
  * spazio esaurito durante la conversione e la normalizzazione: in entrambi i casi un `OSError` con `ENOSPC`, oppure l'errore di DuckDB con «No space left on device», danno lo stesso pannello con exit 1;
  * avviso, non blocco, se prima di partire lo spazio libero è meno del doppio dell'input;
  * `normalized.csv` aggiunto allo schema «Dopo»;
  * la riga 213 riscritta così: «Oggi e dopo: al picco l'input più due temporanei su disco. Cambia la memoria, non il disco»;
  * gli spostamenti fra filesystem diversi vanno fra i rischi.

  In alternativa c'è la versione ampia della fase 5: output provvisorio accanto a quello finale e `os.replace`.

## Correzioni proposte

### [Issue 5] [`egm-design`] - Severity: Blocker (design-1-B3)

* **Affected Scope:** righe 91-95 (CUJ 2).
* **Discrepancy Description:** CUJ 2 chiede di riconoscere cp1252 «come fa oggi» con un solo byte accentato, ma oggi un caso analogo dà cp1006.
* **Rationale:** un criterio d'accettazione che neanche oggi è rispettato.
* ***AI Suggestion:*** PROPOSE FIX
* ***Justification:*** riga 288 del documento e profilo di oggi.
* ***Proposed Edit:*** il «Allora» di CUJ 2 diventa: «csvnorm sceglie una codifica occidentale a un byte che decodifica quel byte, converte la riga senza mandarla fra gli scarti, e il risultato coincide con la codifica attesa dichiarata per quel file di prova».

### [Issue 6] [`egm-design`] - Severity: Major (design-1-M5)

* **Affected Scope:** righe 170-172.
* **Discrepancy Description:** la via rapida accetta come `ascii` un file binario senza byte alti, mentre `test_binary_file` si aspetta `ValueError`.
* ***AI Suggestion:*** PROPOSE FIX
* ***Justification:*** `tests/test_encoding.py:135-138`.
* ***Proposed Edit:*** un byte NUL in un blocco fa uscire dalla via rapida verso il rilevamento con `charset_normalizer`, che oggi rifiuta i file binari. Il file vuoto resta `ascii`, come consente il test di oggi.

### [Issue 7] [`egm-design`] - Severity: Major (design-1-M6)

* **Affected Scope:** riga 173.
* **Discrepancy Description:** UTF-16 e UTF-32 rompono le finestre allineate alle righe e, con un BOM, finiscono sul percorso del campione.
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** un BOM UTF-16 o UTF-32, oppure un BOM UTF-8 seguito da UTF-8 non valido, porta direttamente al rilevamento di oggi sull'intero file. Questi file sono rari e restano sul percorso lento di oggi. Servono file di prova per ciascun caso.

### [Issue 8] [`egm-design`, `egm-style`, `egm-structural`] - Severity: Major (design-1-M7, style-1-M4, structural-1-M7)

* **Affected Scope:** righe 62, 64-67, 180.
* **Discrepancy Description:** «migliore» non è definito, la riga 62 contraddice la 67, e il controllo di equivalenza sui file piccoli non coglie il rischio.
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * ogni file di prova dichiara a mano la codifica attesa;
  * «migliore» significa che la scelta nuova coincide con quella attesa dove la scelta di oggi non coincideva;
  * la riga 62 diventa «uguale a oggi o coincidente con la codifica attesa, su tutti i file di prova»;
  * si aggiungono file sintetici grandi con pochi byte non ASCII (all'inizio, a metà, in fondo; cp1250 contro cp1252), più un test con il tetto del campione ridotto;
  * la riga 180 si riscrive sulla base del profilo di oggi.

### [Issue 9] [`egm-style`, `egm-structural`, `egm-design`] - Severity: Major (stato del `COPY` unico)

* **Affected Scope:** righe 79-81, 268-272.
* **Discrepancy Description:** la riga 81 dice che non ci sono domande aperte, la riga 272 dice il contrario, e le decisioni stanno fuori dalla parte di design.
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * la sezione «Domande aperte» diventa «Decisioni e domande aperte» e riassume in una riga ciascuna le decisioni del 2026-11-22 (le sette della riga 280 e seguenti);
  * la voce sul `COPY` unico esce da «Alternative considerate» e diventa una riga delle decisioni: «fase condizionale, si fa se la mediana resta sopra i 60 s».

### [Issue 10] [`egm-style`, `egm-structural`, `egm-design`] - Severity: Major (cifre dei tempi)

* **Affected Scope:** righe 24, 44; schema «Dopo».
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * righe 24 e 44: «circa 170 s su 220, quasi quattro quinti, vanno in passaggi Python» (106 + 40 + 14 + 12 come valore medio di 10-14);
  * schema «Dopo»: tempi attesi per fase marcati come stime, con il totale atteso. Questo risponde anche al Nit sul budget di tempo (design-1-N2).

### [Issue 11] [`egm-style`, `egm-structural`] - Severity: Major (due correzioni, tre voci)

* **Affected Scope:** riga 64.
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** «tranne le due correzioni decise, ciascuna con un test proprio:» diventa «tranne i casi seguenti, ciascuno con un test proprio:».

### [Issue 12] [`egm-style`] - Severity: Major (gzip)

* **Affected Scope:** riga 219.
* ***AI Suggestion:*** PROPOSE FIX
* ***Justification:*** `core.py:447-455`: gzip salta rilevamento e conversione.
* ***Proposed Edit:*** «Gzip, zip, URL remoti, stdin: passano dalle stesse funzioni» diventa «Zip, URL remoti e stdin passano da rilevamento e conversione dopo il salvataggio su file e ne guadagnano il tempo; gzip non ci passa, come oggi».

### [Issue 13] [`egm-structural`, `egm-design`] - Severity: Major (manca «Rischi e mitigazioni»)

* **Affected Scope:** fra «Piano tecnico» e «Alternative considerate».
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** nuova sezione H2 «Rischi e mitigazioni», aggiunta all'indice, con:
  * dipendenza da DuckDB 2.0.0 per `COLUMNS ... AS` e `NEW_LINE`, con `duckdb>=2.0.0` senza limite superiore (mitigazione: test di riferimento in CI e limite superiore alla prossima versione maggiore);
  * dipendenza dal comportamento di `charset-normalizer>=3.0.0` (mitigazione: test di equivalenza con versione fissata nei test);
  * escape: le parole chiave vengono da `_DUCKDB_KEYWORD_SET`, sono costanti del codice e passano per `re.escape`, quindi nessun dato dell'utente entra nell'SQL;
  * `from_bytes` sul campione senza risultato: `ValueError` come oggi;
  * disco, come nell'Issue 4;
  * sicurezza: nessuna implicazione nuova, perché i dati in ingresso non entrano nell'SQL.

### [Issue 14] [`egm-design`] - Severity: Major (spec delta)

* **Affected Scope:** fine del paragrafo «Rilevamento dell'encoding».
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** aggiungere: «Cambia il contratto della spec `openspec/specs/encoding-detection/spec.md`, che oggi indica `charset_normalizer` come rilevatore principale e un fallback `file -b` che nel codice non esiste: serve un delta MODIFIED, descritto nel piano dettagliato».

### [Issue 15] [`egm-structural`, `egm-style`] - Severity: Major (contraddizione su latin-1 in DuckDB)

* **Affected Scope:** righe 265, 276.
* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** la riga 265 dice «Per le altre codifiche servirebbe, da verificare, un'estensione DuckDB scaricata dalla rete». Il motivo di processo della riga 266 («mai discussa con l'autore») diventa tecnico: «un secondo percorso valido solo per alcune codifiche, con costo in tempo non misurato».

## Contestati e da confermare

### [Issue 16] [`egm-structural`, `egm-design`] - Severity: Major (scarti attribuiti all'autore senza link)

* **Affected Scope:** righe 230, 236, 242, 248, 254, 260.
* ***AI Suggestion:*** CONTEST in parte, PROPOSE FIX per le righe 236 e 260.
* ***Justification:*** lo standard vieta di attribuire uno scarto a un maintainer senza link. Il template del documento di design prevede invece esplicitamente «Rejected by author: [technical rationale]». Qui l'autore è chi ha scritto il documento, e le righe 230, 242, 248 e 254 hanno già un motivo tecnico.
* ***Proposed Edit:***
  * riga 236: «scartata dall'autore: due percorsi da mantenere e testare, e i passaggi lenti lo sono per tutti i file»;
  * riga 260: «scartata dall'autore: DuckDB fa le due cose durante il `COPY`, senza una lettura e una scrittura in più».

### [Issue 17] [`egm-structural`] - Severity: Nit (indice senza link)

* **Affected Scope:** righe 11-20.
* ***AI Suggestion:*** ESCALATE
* ***Justification:*** è una regola dell'autore per i documenti da condividere (indice in testa, senza ancore né link `#id`), scritta nelle istruzioni dell'autore, che il revisore non poteva leggere. Va confermata, non cambiata.

## Nit non corretti (DECLINE), tranne quelli marcati

- Cifre vaghe senza misura (righe 24, 45, 228, 240, 252): **PROPOSE FIX** per la riga 60 («al massimo 8 MB per blocco»), DECLINE per le altre.
- «Una esecuzione» diventa «un'esecuzione», e si aggiunge da dove viene l'intervallo 10-14 s (due misure, 2026-11-22): **PROPOSE FIX**.
- «cinque valori di byte (0x81, 0x8D, 0x8F, 0x90, 0x9D)» alla riga 253: **PROPOSE FIX**.
- «CUJ» sciolto alla prima occorrenza come «Critical User Journey»; `...` nella regex dichiarato come elenco abbreviato; spiegare che `_1` in `_select_1` è il suffisso di DuckDB per i nomi duplicati, uguale a oggi: **PROPOSE FIX**.
- La riga 207 cita anche `_normalize_and_refresh_errors`: **PROPOSE FIX**.
- «Overview» e «Proposed» in inglese, i metadati con `*`, la soluzione in breve dentro «Il problema», il paragrafo lungo dei miglioramenti futuri, «buttato»: DECLINE, non cambiano il contenuto.
- Rinomina di una colonna che l'utente ha chiamato davvero `_select`: va fra i rischi come limite accettato, uguale a oggi (Issue 13).

---

# Round 2

**Target:** `docs/designs/speed-up-large-files.md` (righe 1-311). Fonte: `critic_report.md`, sezione «Round 2». Questo è l'ultimo giro ammesso per la fase 7: i rilievi che restano dopo questa risoluzione si registrano come compromessi accettati.

## Rilievi che chiedono una tua decisione

### [R2-1] [`egm-design`] - Severity: Major (design-2-M5, design-2-N4)

* **Affected Scope:** righe 70, 131, 232-237, 254 (Disco, CUJ 5, Spazio su disco, Rischi).
* **Discrepancy Description:** `shutil.move` fra filesystem diversi copia e poi cancella, senza gestione d'errore. Se fallisce a metà, lascia un `output.csv` parziale oppure, con `--force`, distrugge l'output che c'era. Non sono coperti nemmeno l'esportazione degli scarti, il controllo dello spazio nella directory di output e il riconoscimento dell'errore indipendente dalla lingua del sistema.
* ***AI Suggestion:*** PROPOSE FIX, da decidere. Adotta la versione ampia della fase 5.
* ***Justification:*** il comportamento di `shutil.move` fra filesystem diversi è documentato nella libreria standard (copia e poi `unlink`). Il commento a `core.py:773-775` promette «never leaves a partial or overwritten output», ma oggi è vero solo se le due directory stanno sullo stesso filesystem. Il messaggio di DuckDB visto il 2026-11-22 contiene `"errno":"28"`, utilizzabile al posto del testo inglese.
* ***Proposed Edit:***
  * `normalized.csv` si scrive nella directory di output con un nome nascosto riconoscibile (`.<nome>.csvnorm-partial`) e alla fine si fa `os.replace`, che è atomico e non copia. Il caso di filesystem diversi sparisce;
  * spazio esaurito riconosciuto da `errno == ENOSPC` per `OSError`, e da `"errno":"28"` o «No space left» nel messaggio di DuckDB. Su Windows va verificato quale codice riporta DuckDB;
  * stesso pannello anche per l'esportazione degli scarti;
  * avviso preventivo su entrambe le directory: nella temporanea, il doppio dell'input per `utf8.csv` (caso peggiore, cp1252 con tutti caratteri accentati); in quella di output, il doppio dell'input;
  * un `.csvnorm-partial` rimasto da un'interruzione forzata viene sovrascritto alla prossima esecuzione sullo stesso output.

### [R2-2] [`egm-design`, `egm-style`] - Severity: Major (design-2-M2, style-2-M6, design-2-N3)

* **Affected Scope:** righe 69, 162, 190-195.
* **Discrepancy Description:** il campione non ha limiti, la «riga» non è definita, e il passo fisso richiede di contare le righe.
* ***AI Suggestion:*** PROPOSE FIX, da decidere i numeri.
* ***Proposed Edit:*** il campione è fatto di **finestre di 512 byte**, al massimo 128, quindi **al massimo 64 KB**. Ogni finestra è centrata su un byte `>= 0x80`. Si scelgono in una sola passata, senza contare le righe:
  * la prima occorrenza di ogni valore di byte presente, che dà al massimo 128 finestre ed è la regola che vince;
  * se restano posti, la prima sequenza non ASCII dopo ciascuno di 64 punti fissi del file (posizione = k × dimensione / 64), fino al massimo di 128 finestre.

  Niente righe, quindi niente problemi con i file a solo CR o con le celle enormi. `from_bytes` riceve `steps` uguale al numero di finestre e `chunk_size=512`, così ogni finestra viene esaminata. Nel piano tecnico i 3-6 s restano dichiarati come stima, da misurare nella fase quattro.

## Correzioni proposte

### [R2-3] [`egm-style`, `egm-design`] - Severity: Major (style-2-M1, design-2-N1)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * riga 27: «Questo design ha l'obiettivo di portare quel file sotto i 60 s, con soglia di rilascio a 3 volte più veloce della base misurata»;
  * CUJ 1: «finisce in meno di 60 s (obiettivo) e comunque almeno 3 volte più veloce della base misurata (soglia di rilascio)».

### [R2-4] [`egm-style`] - Severity: Major (style-2-M2, style-2-M3, style-2-M4)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** il paragrafo su come lavora oggi `charset_normalizer` si riscrive così:
  * «la causa principale: sui 100 MB il 61% del tempo»;
  * lo spareggio con i numeri verificati: `best()` darebbe cp1250 (0,4918); dieci candidati sono a pari merito a 0,4988; csvnorm sceglie cp1252 per la preferenza occidentale sul pari merito esatto;
  * la riga 49 diventa «Oggi la garanzia è questa: esclude le codifiche che non decodificano qualche byte del file; fra le restanti sceglie su circa 2,5 KB, e su questo file su un pari merito esatto fra dieci codifiche».

### [R2-5] [`egm-style`] - Severity: Major (style-2-M5)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** «il picco stimato, non misurato, è di circa tre volte la dimensione del file (byte letti, stringa decodificata, byte riscritti)».

### [R2-6] [`egm-design`] - Severity: Major (design-2-M1)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * nell'obiettivo «Validazione completa», un'eccezione: per i file non UTF-8 con righe a solo CR, con fine riga misti o con `\r\r\n` gli scarti possono cambiare, perché oggi la modalità testo li trasforma prima (`\r\r\n` diventa `\n\n`, con una riga vuota in più);
  * i risultati attesi si misurano e si fissano nella fase uno, uno per caso;
  * lo stesso punto va in «Rischi e mitigazioni».

### [R2-7] [`egm-design`] - Severity: Major (design-2-M3)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** se il candidato scelto è una codifica a più byte, `detect_encoding` lo verifica con una decodifica stretta in streaming sull'intero file e, se fallisce, ricade sul rilevamento di oggi. Così la garanzia della riga 71 vale anche per chi chiama `detect_encoding` da solo. Il costo c'è solo per le codifiche a più byte; per quelle a un byte basta il filtro.

### [R2-8] [`egm-design`] - Severity: Major (design-2-M4, design-2-N2)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:***
  * un byte NUL nella prima passata porta al rilevamento di oggi sull'intero file. Lì i file binari continuano a dare `ValueError`, e gli UTF-16 e UTF-32 senza BOM vengono trattati come oggi;
  * l'esenzione dai limiti di tempo e memoria nell'obiettivo «Memoria» elenca tutti i casi che vanno sul percorso di oggi: BOM UTF-16 e UTF-32, BOM UTF-8 seguito da UTF-8 non valido, byte NUL, conversione fallita.

### [R2-9] [`egm-structural`] - Severity: Major (structural-2-M2)

* ***AI Suggestion:*** PROPOSE FIX
* ***Proposed Edit:*** con R2-1 lo spostamento fra filesystem diversi sparisce. Resta il caso di `/tmp` su tmpfs, che diventa una domanda aperta in «Decisioni e domande aperte», da verificare nella fase uno sulla macchina di misura.

## Nit corretti

- La soluzione in breve passa in fondo all'Overview.
- Lo schema «Prima» aggiunge i conteggi (3 s).
- CUJ 5 riscritto: il «Dato» descrive il disco quasi pieno e il «Quando» è il comando dell'utente.
- Etichette «Mitigazione:» uniformi.
- I 24 s dichiarati come valore di oggi, assunto invariato.
- Un solo termine, «ricaduta», per il ritorno al rilevamento completo.
- «Questi file sono rari» tolto.
- «spesso tutti ASCII» diventa «su questo file tutti ASCII».
- `steps` e `chunk_size` nominati.
- «senza costo aggiuntivo» diventa «senza una lettura e una scrittura in più».
- «resta leggibile» diventa «riporta la posizione nel file».
- Nuova alternativa «regolare `charset_normalizer` sull'intero file», scartata: anche restringendo i candidati resta una decodifica completa per ciascuno, e il punteggio resta su 2,5 KB.

## Nit non corretti (DECLINE)

- Le decisioni elencate due volte: il riassunto serve a chi legge solo la parte di design.
- I due rimandi al piano dettagliato: sono i dettagli di implementazione, e la parte di design dice cosa si garantisce.
- «Overview» e «Proposed» in inglese, «quasi quattro quinti», ripetizioni fra non obiettivi e alternative, inciso su rfc4180-bis, «quasi sempre».
- Il limite superiore della versione di DuckDB resta una proposta.
- L'elenco dei test cancellati e dove si spostano riguarda il piano dettagliato: va alla fase 9.
- Indice senza link: regola dell'autore, già confermata nel round 1.

**Round 2 status: resolved** (2026-11-22, auto accept: applicate R2-1..R2-9 e i Nit marcati come corretti; giro massimo della fase 7 raggiunto, i DECLINE restano compromessi accettati)

---

# Fase 9 (e residui della fase 8)

**Target:** `docs/designs/speed-up-large-files.md`, piano dettagliato (righe 322-546) e, per i rilievi della fase 8, la sezione «Rilevamento dell'encoding» del piano tecnico.
**Fonti:** `implementation_readiness_report.md`, `intermediate_zoom_out_report.md`.
**Versione proposta completa:** `speed-up-large-files.proposed.md`, nella cartella del progetto. Con «auto accept» sostituisce il documento.

## Proposte sulla parte di design (residui della fase 8)

- **[F8-1] Filtro sui byte doppio — PROPOSE FIX.** Il filtro come passo separato si toglie. La proprietà diventa: il campione contiene ogni valore di byte alto del file, e `from_bytes` lo decodifica in modo stretto per ogni candidato. Verificato il 2026-11-22 in `api.py:349-391`.
- **[F8-2] Finestre che spezzano i caratteri a più byte — PROPOSE FIX, con una correzione al revisore.** Il revisore proponeva di tagliare le finestre su un byte ASCII, ma in Shift_JIS, GBK e Big5 la seconda metà di un carattere può valere da 0x40 a 0x7E, quindi può essere un byte ASCII. Si taglia invece subito dopo un byte inferiore a 0x40 (a capo, virgola, spazio, cifra), che in quelle codifiche, in EUC e in UTF-8 non è mai la seconda metà di un carattere.
- **[F8-3] Tre livelli di ricaduta — PROPOSE FIX.** La verifica delle codifiche a più byte dentro `detect_encoding` si toglie. Resta una sola ricaduta, in `detect_and_convert`. L'obiettivo «Correttezza» si riscrive di conseguenza: la garanzia completa vale sul percorso della CLI, mentre `detect_encoding` da sola la dà per le codifiche a un byte.
- **[F8-4] Dettagli di implementazione nel piano tecnico — PROPOSE FIX.** Costanti, nomi dei file provvisori e codici d'errore passano nel piano dettagliato. La regola dei «64 punti fissi» si toglie.
- **[F9-M1] `utf-8-sig` — PROPOSE FIX.** Oggi un file con BOM dà `utf-8` (verificato su `test/utf8_sig_bom.csv`), e così resta.
- **Nit della fase 8 — PROPOSE FIX:** pulizia del provvisorio tramite `temp_files`; avviso che somma i bisogni sullo stesso filesystem; voci di riempimento tolte dai rischi e spostate in «Cosa non cambia»; tempi per fase misurati dallo script di benchmark e non più con `--verbose`.

## Proposte sul piano dettagliato

Il piano viene riscritto per intero. Corrispondenza con i rilievi:

- **B1, B2, M9, M13:** la fase quattro descrive `_ScanResult`, `_scan` con tutti i rami (BOM UTF-16 e UTF-32, NUL, BOM UTF-8, ASCII, UTF-8, campione), le costanti fisse, `_pick_encoding`, `_detect_encoding_full` privata, `from_bytes(sample, steps=1, chunk_size=len(sample))` e un test per ogni ramo. Il comportamento di `steps=1` è un punto di arresto: se la libreria non lo rispetta, decide l'autore.
- **B3:** `detect_and_convert` in `encoding.py`. `_handle_local_encoding` mantiene nome e firma, così i 5 test di `test_core_helpers.py` restano validi.
- **B4, M7:** la fase tre diventa «Conversione UTF-8 a blocchi e spazio su disco». Contiene `_is_disk_full`, `_warn_if_low_disk_space`, il testo del pannello, `except OSError` in `_prepare_working_file`, l'output provvisorio con `os.replace` registrato in `temp_files`, i test di integrazione toccati e un test per CUJ 5.
- **B5:** la versione sta solo in `pyproject.toml`, `1.4.0`.
- **M2, M3:** il manifesto `tests/fixtures/golden/cases.toml` elenca casi con nome, argomenti, exit code e `xfail_until`, e aggiunge i casi `\r\r\n`, solo CR e fine riga misti. Il file degli scarti si confronta sulle colonne `line`, `column_idx`, `column_name` ed `error_type`.
- **M4, M17:** il test di equivalenza usa un dizionario letterale `EXPECTED` con la codifica attesa per ogni file. Niente copia congelata del rilevatore, e il criterio «migliore» sparisce.
- **M5, M6:** niente log dei tempi da interpretare. I tempi per fase li misura `bench_large.py` attorno alle chiamate di libreria. `make_large_csv.py` si toglie e al suo posto c'è la fixture `make_csv` in `tests/conftest.py`. Spariscono anche il marker `slow` e `addopts`.
- **M8:** formula della posizione `offset_blocco - len(decoder.getstate()[0]) + e.start`, eccezione ricostruita con la posizione nel messaggio, `codecs.lookup` sempre per primo.
- **M10:** una regola per ogni punto. Se `COLUMNS` dà un header diverso da oggi si passa a `DESCRIBE` più una lista esplicita. Le costanti sono fisse. Le voci non verificabili di `preserve-crlf` le decide l'autore. La soglia di rilascio si dichiara raggiungibile senza la fase cinque.
- **M11:** `duckdb>=2.0.0,<3`.
- **M12:** il controllo tmpfs sta in `bench_large.py`, con l'azione da fare (`TMPDIR` su un disco).
- **M14:** limite di `tracemalloc` di 16 MiB, legato a `CHUNK_SIZE`.
- **M15:** `crlf` passato solo per nome in fondo alla firma, rimozione dell'import, un test in `test_core_helpers.py`.
- **M16:** «su un file con soli LF».
- **Nit applicati:** stringhe raw per l'SQL, pannelli in inglese, commento a `validation.py:34`, comandi `openspec` esatti, `PRD.md` NFR-2, `LOG.md` in ogni fase, numero di test calcolato con `--collect-only`, voce di `tasks/todo.md` riscritta, unità in KiB e MiB, 54 s indicati come stima.
- **Contestato:** i commit `107e8e2` e `0c7b8d8`, segnalati come non verificati, sono verificati nel `git log` del 2026-11-22.

## Punti da guardare

- La fase tre ora contiene anche il lavoro sul disco. Le fasi restano sette (da zero a sei), con la stessa numerazione.
- Il taglio sotto 0x40 viene da una conoscenza delle codifiche, non da una misura: lo verifica il test Shift_JIS della fase quattro.
- Se `steps=1, chunk_size=len(sample)` non fa valutare l'intero campione, la fase quattro si ferma.

**Fase 9 status: resolved** (2026-11-22, auto accept: versione proposta applicata a docs/designs/speed-up-large-files.md)

---

# Fase 9, round 2

**Fonte:** `implementation_readiness_report.md`, sezione «Round 2». **Versione proposta:** `speed-up-large-files.proposed.md`. È l'ultimo giro: i Nit non applicati restano compromessi accettati.

## PROPOSE FIX (tutti)

- **R2-B1, il campione risulta UTF-8 valido.** Sul percorso del campione `from_bytes` riceve `cp_exclusion=["utf_8", "ascii"]`, un parametro che esiste nella libreria, e il campione include sempre una finestra attorno al primo errore UTF-8. Test con il caso del revisore: `’` all'inizio, `0x92` da solo più avanti.
- **R2-B2, test della ricaduta.** La funzione sostituita restituisce `shift-jis` su un file cp1252 con `0xFD`, che in `shift_jis` non è definito. Il test controlla una sola chiamata a `_detect_encoding_full`.
- **R2-B3, ordine delle `except`.** In `_prepare_working_file` l'ordine diventa `(UnicodeDecodeError, LookupError)`, poi `OSError`, poi `ValueError`. In `detect_and_convert` `UnicodeDecodeError` si intercetta prima di `ValueError`. Il design dice che il titolo «Encoding conversion failed» è una piccola correzione rispetto a oggi.
- **R2-B4, avviso preventivo.** Si chiama dopo scaricamento ed estrazione e prima dello `Progress`. `may_convert` è vero se nei primi 64 KiB c'è un byte alto. In modalità stdout si conta solo la directory temporanea. Per i gzip non si chiama. Il parametro è stato rinominato.
- **R2-M1, scansione veloce.** `set(chunk.translate(None, ASCII_BYTES))` e `chunk.find` per ogni valore nuovo, tutto in C.
- **R2-M2, NUL.** Il controllo del NUL c'è anche nella seconda passata. Test con `test/binary_file.bin`.
- **R2-M3, regole delle finestre complete:**
  - un valore entra fra quelli coperti solo con una finestra accettata;
  - inizio e fine file valgono come punti di taglio;
  - le finestre a cavallo di due blocchi restano in sospeso;
  - le finestre sovrapposte si uniscono;
  - un valore senza finestra a fine file manda il file a `full`;
  - `MAX_CUT_SEARCH` vale per lato, quindi il limite è circa 81 KiB;
  - le cifre sono escluse dai punti di taglio per GB18030 (Nit).
- **R2-M4, campi di `_ScanResult`.** Ora ci sono `reason`, `windows` e `high_values`; i motivi sono elencati, e il log va al livello `DEBUG` del logger `csvnorm`, scritto da `detect_encoding`.
- **R2-M5, file vuoto.** Dà `utf-8`, come oggi.
- **R2-M6, valori attesi normalizzati.** `shift-jis` oppure `cp932`; per le codifiche occidentali l'elenco `cp1252`, `latin-1`, `iso8859-15`.
- **R2-M7, messaggi di avanzamento.** `detect_and_convert` riceve una funzione `on_detected` che li aggiorna. È scritta la regola per `temp_files`, e si tolgono gli import inutilizzati.
- **R2-M8, `_setup_output_paths`.** Restituisce quattro valori, l'ultimo `None` in modalità stdout.
- **R2-M9, memoria.** L'obiettivo diventa 24 MiB indipendenti dalla dimensione del file, il contenuto del test è fissato (`0xE9`), ed è scritto il conto del picco.
- **R2-M10, file di riferimento.** Sono elencati i nomi dei file, i byte dei nuovi input, il comando esatto di `subprocess.run` e il caso `output = false`.
- **R2-M11, tab.** Si scrive come stringa TOML normale, `"\t"`.
- **R2-M12, spec.** Nuovo delta MODIFIED su `output-location`.
- **R2-M13, test dello spazio esaurito.** Coprono conversione, esportazione degli scarti, l'avviso e `_is_disk_full`.
- **R2-M14, posizione dell'errore.** Lo stato del decoder si legge prima di ogni chiamata a `decode`, la chiamata finale è separata, la posizione va in `e.file_offset`, e c'è un test `shift_jis` a cavallo di due blocchi.
- **R2-M15, altri punti:**
  - test dei parametri di `from_bytes` definito (`0x81` dopo il byte 3.000);
  - `bench_large.py` aggiornato nelle fasi due e quattro;
  - copertura minima del 90% su `csvnorm.encoding`;
  - `PRD.md` NFR-2 con tutte le esclusioni.
- **Nit applicati:**
  - riferimento a `validation.py:416` attribuito al gestore della normalizzazione;
  - intervalli di riga corretti;
  - `uv.lock` dichiarato fuori dal perimetro;
  - formato dei numeri nell'avviso;
  - 220 s / 3;
  - `LOG.md` solo dalla fase uno alla quattro;
  - unità, con l'eccezione dei 10 MB della libreria;
  - formulazioni delle righe 388, 512 e 581.

## DECLINE

- La contraddizione di certezza fra le righe 546 e 549. Ora il testo dice «secondo `api.py:130-139`», e il test resta come conferma di un fatto letto nel codice.

**Fase 9 round 2 status: resolved** (2026-11-22, auto accept; revisione chiusa)
