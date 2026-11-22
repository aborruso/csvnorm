# Rapporto della fase 7: revisione critica

* **Documento:** `docs/designs/speed-up-large-files.md`, righe 1-277 (parte di design)
* **Data:** 2026-11-22, round 1
* **Revisori:** egm-design (completed), egm-structural (completed), egm-style (completed)
* **Standard:** `feature-spec-standard.md` per design e struttura; persona di stile per lo stile
* **Contesto fornito:** `src/csvnorm/encoding.py`, `validation.py`, `core.py`, `tests/test_encoding.py`, `tests/test_validation.py`, `openspec/specs/encoding-detection/spec.md`

## Indice

- Esito
- Blocker
- Major
- Nit
- Affermazioni verificate dai revisori

## Esito

Il documento non è ancora pronto: 3 Blocker, tutti di egm-design, 15 Major dopo aver unito i doppioni, e una ventina di Nit. Due Blocker ripetono il rilievo principale della fase 5 su `charset_normalizer`, e qui risultano bloccanti. Gli identificativi seguono la forma `<revisore>-<round>-<n>`.

## Blocker

- **design-1-B1. Descrizione sbagliata di cosa fa oggi `charset_normalizer`** (righe 34, 62, 95, 123, 175-180). Caos e coerenza si calcolano solo su 5 pezzi da 512 byte (`api.py:393-397`, `515-544`, `647-665`). L'intero file serve solo ai controlli di decodifica stretta (`api.py:350`, `573`), ed è lì che vanno i 106 s. Sul file da 826 MB lo spareggio fra cp1250 e cp1252 si decide quindi su circa 2,5 KB, con ogni probabilità tutti ASCII. La garanzia vera di oggi è più stretta: esclude solo le codifiche che non decodificano qualche byte. Il rischio e le mitigazioni vanno riscritti su questa base.
- **design-1-B2. Il campione mirato verrebbe ridotto di nuovo a 5×512 byte** (riga 173). `from_bytes` ha gli stessi parametri di default e analizza l'input per intero solo sotto `chunk_size*steps` = 2560 byte (`api.py:130-139`). I pezzi possono cadere sul contesto ASCII invece che sui byte non ASCII. Servono parametri `steps` e `chunk_size` espliciti, oppure un campione sotto i 2560 byte, più un test che dimostri che i pezzi esaminati coprono i byte non ASCII.
- **design-1-B3. CUJ 2 chiede un comportamento che oggi non c'è** (righe 91-95 contro riga 288). CUJ 2 vuole che csvnorm riconosca cp1252 «come fa oggi» in un file ASCII con un solo byte accentato. La riga 288 dice che un caso analogo oggi dà cp1006. Con così poco segnale, una scelta sbagliata fra codifiche a un byte converte senza errori. Va allineato CUJ 2 alla regola decisa («uguale o migliore di oggi, documentato»), oppure va definita una regola deterministica per il caso con pochi byte non ASCII, per esempio la preferenza per le codifiche occidentali sotto una certa quantità.

## Major

### Rilevamento dell'encoding

- **design-1-M1, style-1-N, structural (coerenza). «Un solo passaggio» non è uno** (righe 162-173). La scansione «si ferma al primo errore», ma il campione ha bisogno delle posizioni non ASCII «in tutto il file». Per le codifiche dense (cp1251, cp1253, Shift_JIS, GBK), elencare ogni corrispondenza vuol dire milioni di oggetti Python e una lista senza limite: questo rompe l'obiettivo di memoria. Proposta: una passata che continua oltre il primo errore e raccoglie le posizioni con un tetto fisso o a passo fisso sull'offset del file, con un budget dichiarato di tempo e memoria.
- **design-1-M2. La ricaduta sul rilevamento completo viola gli obiettivi di tempo e memoria** (riga 178). `from_path` legge tutto il file in RAM e richiede circa 106 s. Va esentata in modo esplicito negli obiettivi, va detto in quale strato vive il nuovo tentativo, e va definito cosa succede se fallisce anche la seconda conversione: oggi è il pannello «Encoding conversion failed», exit 1. Nota: la fase 5 proponeva invece di spostare la ricaduta in `encoding.py`.
- **design-1-M5. La via rapida accetta file binari** (righe 170-172). `isascii()` e UTF-8 stretto accettano NUL e byte di controllo, quindi un file binario senza byte `>= 0x80` diventerebbe `ascii`. Oggi `tests/test_encoding.py::test_binary_file` si aspetta `ValueError`. Serve un controllo sui byte di controllo, oppure il cambiamento va dichiarato. File vuoti e binari vanno nell'insieme di equivalenza.
- **design-1-M6. UTF-16, UTF-32 e codifiche a più byte** (riga 173). Le finestre allineate su 0x0A rompono l'allineamento a 2 e 4 byte, e l'unione di finestre può produrre sequenze non valide. Un BOM UTF-16 fa fallire UTF-8 al byte 0 e manda il file sul percorso del campione. Vanno riconosciuti prima i BOM UTF-16 e UTF-32, oltre al caso BOM UTF-8 seguito da UTF-8 non valido, e servono file di prova.
- **design-1-M7, style-1-M4, structural-1-M7. «Migliore» non è definito e il controllo di equivalenza non coglie il rischio** (righe 62, 64-67, 180). I file di prova sono piccoli: sotto 1 MB il campione è quasi il file intero, quindi vecchio e nuovo coincidono per costruzione. La riga 62 («stesso risultato») e la riga 67 («migliore») insieme non si possono falsificare. Servono file sintetici grandi con pochi byte non ASCII (all'inizio, a metà, in fondo, con codifiche che si somigliano come cp1250 e cp1252), oppure un budget ridotto solo per i test. «Migliore» va definito con un criterio oggettivo, per esempio una codifica attesa dichiarata per ogni file di prova. La riga 180 «Oggi è protetto» va riformulata.

### Contratto, file degli scarti e disco

- **design-1-M8. Le promesse sull'output e sul file degli scarti non valgono per i file non UTF-8** (righe 63-67, 189). Oggi la conversione in modalità testo trasforma in LF tutti i fine riga CRLF e CR prima che DuckDB veda il file. Dopo la modifica DuckDB legge i fine riga originali. Cambiano quindi `byte_position` e `csv_line` nel file degli scarti di ogni file non UTF-8 con CRLF, e su file con solo CR il riconoscimento del formato potrebbe cambiare dialetto o scarti. La parità degli scarti va definita come stessi numeri di riga e stessi tipi d'errore. Il cambio dei fine riga va fra le deviazioni dichiarate, con file di prova CR e fine riga misti.
- **design-1-M3. Disco pieno promesso in CUJ 5 ma non progettato** (righe 109-113, 190). `_prepare_working_file` (`core.py:464-471`) intercetta solo `ValueError`, `UnicodeDecodeError` e `LookupError`. Un `OSError` per disco pieno uscirebbe come traceback, non come il pannello promesso con exit 1.
- **style-1 (Major possibile), structural-1-N15, design-1-N3. Il disco resta poco chiaro** (righe 46, 61, 213). È elencato fra i problemi, ma l'obiettivo è «come oggi». La riga 213 mescola temporanei su disco e memoria e cita un «terzo passaggio» mai definito. Va scritto chiaramente cosa cambia: se il disco va fra i non obiettivi, oppure le misure proposte in fase 5 (output provvisorio accanto a quello finale, `os.replace`). Va anche notato che con `/tmp` su tmpfs i temporanei occupano RAM.
- **structural-1-M8. Lo schema «Dopo» non coincide con il testo** (righe 140-154 contro 213 e 61). Lo schema va da `utf8.csv` a `output.csv` senza `normalized.csv`, mentre il testo dice che `normalized.csv` resta, come in `core.py:778-816`.

### Coerenza interna

- **style-1-M1, structural-1-M2, structural-1-M3, structural-1-M6, design-1-M9. Stato del `COPY` unico contraddittorio** (righe 81, 272, 282). La riga 81 dice «Nessuna aperta», la riga 272 dice «fra le domande aperte», la riga 282 la dà per decisa come fase condizionale. Il rimando della riga 81 porta fuori dalla parte di design. La voce della riga 272 non è un'alternativa scartata: va fra le decisioni o fra i miglioramenti futuri. Le decisioni vanno almeno riassunte in «Domande aperte».
- **style-1-M2, structural-1-N13, design-1-N1. Cifre dei tempi incoerenti** (righe 24, 44). I passaggi Python della tabella sommano circa 170-177 s, non «circa 160» e non «due terzi» di 220. Serve una cifra sola, ricavata dalla tabella.
- **style-1-M3, structural-1-M7. «Due correzioni» seguite da tre voci** (righe 64-67). La terza voce, il rilevamento migliore, non è una correzione decisa. Va scritto «tranne i casi seguenti», oppure la voce va spostata sotto l'obiettivo dell'encoding.
- **style-1-M5. Contraddizione su gzip** (righe 76 e 219). La riga 76 dice che gzip non passa da rilevamento e conversione, la riga 219 lo mette fra gli input che «passano dalle stesse funzioni». La riga 219 deve elencare solo gli input che passano davvero da `detect_encoding` e `convert_to_utf8`.

### Conformità allo standard

- **structural-1-M1, design-1-M9. Manca una sezione «Rischi e mitigazioni».** Rischi senza posto: dipendenza da DuckDB 2.0.0 per `COLUMNS ... AS '\1\2'` e `NEW_LINE`, con `duckdb>=2.0.0` senza limite superiore; dipendenza dal comportamento di `charset-normalizer>=3.0.0`; escape dell'alternanza di parole chiave inserita nell'SQL; caso in cui `from_bytes` sul campione non restituisce nulla (oggi `ValueError`, `encoding.py:63-65`); disco; sicurezza, anche solo per dire «nessuna implicazione». Proposta: una sezione H2 fra «Piano tecnico» e «Alternative considerate».
- **structural-1-M4, structural-1-M5, design-1-M9, style-1-N9. Scarti attribuiti all'autore senza link** (righe 230, 236, 242, 248, 254, 260, 266). Lo standard non vuole scarti attribuiti a una persona senza un link a issue, discussione o PR. Ogni «Motivo dello scarto» deve essere un compromesso tecnico. La riga 266 dà un motivo di processo («mai discussa con l'autore») e contraddice la riga 276. La 265 dà per certo che le altre codifiche richiedano un'estensione scaricata dalla rete, la 276 dice che va ancora verificato se DuckDB 2.0.0 legge latin-1 senza estensioni.
- **design-1-M4. Spec delta non nominato nella parte di design** (righe 158-182 contro `openspec/specs/encoding-detection/spec.md`). La spec dice che il rilevatore principale è `charset_normalizer`. Il design fa di UTF-8 stretto il rilevatore principale. Il delta MODIFIED è citato solo nel piano dettagliato.

## Nit

- Cifre vaghe senza misura: «sui file piccoli il costo non si vede» (riga 24), «alcuni GB» (riga 45), «ordine di qualche MB» in un obiettivo (riga 60, serve un tetto, per esempio 8 MB), «risposta rapida» (riga 240), «semplice» (riga 252), «API moderna» (riga 228). (style)
- «Una esecuzione per fase» ma con l'intervallo «10-14 s» (righe 30, 39); meglio «un'esecuzione». (style)
- «rende veloce il percorso normale» va legato all'obiettivo misurabile (riga 26). (style)
- La frase sul guadagno per stdin, stdout e mojibake (riga 75) è un'attenuazione senza decisione. (style)
- «cp1252 fallisce solo su cinque» senza sostantivo: «cinque valori di byte (0x81, 0x8D, 0x8F, 0x90, 0x9D)» (riga 253). (style)
- Paragrafo lungo dei miglioramenti futuri che ripete le righe 262-266; «undici valori non ASCII» ambiguo (valori distinti o occorrenze); «buttato» colloquiale (righe 271, 276). (style)
- «Overview» e «Proposed» in inglese; «CUJ» mai sciolto; `...` nella regex va detto che è un elenco abbreviato; l'esempio `_select` che diventa `_select_1` contraddice «tutte le altre escono invariate» e non dice che `_1` è il suffisso di DuckDB per i duplicati. (style, structural)
- Nel blocco di metadati gli elenchi usano `*`, mentre il resto del documento usa `-` (righe 3-5). (structural)
- «La soluzione proposta in breve» dentro «Il problema» ripete l'Overview (righe 51-55). (structural)
- Lo schema «Prima» ha i tempi per fase, lo schema «Dopo» no (righe 121-154). (structural)
- La riga 207 attribuisce a `core.py` l'impostazione di `crlf`, ma la chiamata passa da `_normalize_and_refresh_errors` (`core.py:787`), la cui firma cambia anche lei. (structural)
- Manca un budget di tempo per fase sotto l'obiettivo dei 60 s (riga 59). (design)
- L'insieme «dichiarato» dei file di prova non è dichiarato nella parte di design (riga 64). (design)
- Versioni: `duckdb>=2.0.0` e `charset-normalizer>=3.0.0` senza limite superiore; va dichiarata come limite accettato la rinomina di una colonna che l'utente ha chiamato davvero `_select`, come oggi. (design)
- Indice senza link: rilevato da structural come Nit, ma corrisponde a una regola dell'autore, quindi è da contestare.

## Affermazioni verificate dai revisori

Corrispondono al codice:

- i tre punti che costruiscono il `COPY` (`validation.py:356`, `406`, `428`);
- la correzione dell'header solo con la virgola (`validation.py:478`);
- `convert_to_utf8` in modalità testo senza `newline=""` (`encoding.py:125-129`);
- la condizione `input_has_crlf and not use_stdout` (`core.py:812`);
- lo stdin letto per intero (`core.py:662`);
- `f.read()` su stdout (`core.py:360`);
- le verifiche DuckDB 2.0.0 datate 2026-11-22.

---

# Round 2 (2026-11-22, righe 1-311 dopo le correzioni)

Revisori: egm-design (completed), egm-structural (completed), egm-style (completed). Nessun Blocker. Major: design 6, structural 2, style 6; dopo l'unione dei doppioni restano 11 rilievi Major. Il round non è pulito.

## Già chiusi, non riaperti

- **design-2-M6, structural-2-M1, style-2-N14 (in parte).** Gli scarti attribuiti all'autore senza link sono gli stessi dell'Issue 16 del round 1, contestata (il template prevede «Rejected by author: technical rationale»). Il rilievo resta chiuso e non si riapre.

## Major nuovi o riaperti

- **style-2-M1, design-2-N1.** La riga 27 promette «sotto i 60 s» come certo, la riga 178 stima 54-62 s, e CUJ 1 chiede meno di 60 s mentre la soglia di rilascio è 3 volte la base.
- **style-2-M2.** «È la causa dei 106 s» (riga 45): il profilo mostra il 61% sui 100 MB, quindi è la causa principale, non tutta.
- **style-2-M3.** Lo spareggio citato alla riga 47 non corrisponde al codice. Verificato il 2026-11-22 sui primi 100 MB:
  - il `best()` di `charset_normalizer` da solo sceglierebbe cp1250 (coerenza 0,4918);
  - fra i candidati con caos 0, dieci hanno la coerenza massima a pari merito, 0,4988: cp1252, cp1254, cp1258, latin_1, iso8859_3, iso8859_9, iso8859_14, iso8859_15, iso8859_16, e la variante occidentale;
  - lo spareggio di csvnorm sceglie cp1252 su questo pari merito esatto.
- **style-2-M4.** La riga 49 usa giudizi retorici («vera», «di quanto sembri», «debole»).
- **style-2-M5.** «Il picco è di più volte la dimensione del file» (riga 54) non è misurato.
- **style-2-M6, design-2-M2, design-2-N3.** Il campione non ha limiti:
  - «riga» non è definita, e con un file a solo CR o con una cella quotata enorme una «riga» può essere grande quanto il file;
  - il tetto non ha un numero, e non c'è una regola di precedenza fra «almeno una riga per valore di byte» e il tetto;
  - il «passo fisso» richiede di sapere quante righe ci sono, cioè forse una terza passata;
  - i 3-6 s non sono misurati.
- **design-2-M1.** La promessa sugli scarti (riga 72) contraddice il rischio dei fine riga (riga 253). Con un altro dialetto cambiano gli scarti, non solo le posizioni. Per `\r\r\n` nei file non UTF-8, oggi la modalità testo produce `\n\n`, cioè una riga vuota in più, e il risultato atteso non è scritto.
- **design-2-M3.** Chi chiama da solo `detect_encoding`, che è API pubblica, perde la rete di sicurezza: il filtro sui byte vale solo per le codifiche a un byte, e la conversione stretta sta nella nuova funzione che rileva e converte.
- **design-2-M4, design-2-N2.** Non è detto dove vanno i file con un byte NUL. Gli UTF-16 senza BOM contengono NUL e romperebbero il campione per righe. Anche i percorsi della riga 188 caricano l'intero file e vanno esentati dal limite di memoria.
- **design-2-M5, design-2-N4.** Il disco pieno non copre tutto:
  - `shutil.move` (`core.py:816`) fra filesystem diversi è una copia seguita da una cancellazione, senza gestione d'errore; se fallisce, può lasciare un `output.csv` parziale o distruggere quello esistente con `--force`;
  - non è coperta nemmeno l'esportazione degli scarti (`validation.py:259`);
  - lo spazio si controlla solo nella directory temporanea;
  - riconoscere l'errore dal testo inglese «No space left on device» è fragile;
  - i temporanei sono più grandi dell'input: con cp1252 i caratteri accentati passano da 1 a 2 byte, e virgolette e CRLF fanno crescere l'output.
- **structural-2-M2.** «Nessuna domanda aperta» (riga 91) contraddice le due verifiche aperte della riga 254 (tmpfs e filesystem diversi).

## Nit

- La soluzione in breve sta dentro «Il problema». Le decisioni sono elencate due volte. Due criteri rimandano al piano dettagliato. Lo schema «Prima» non mostra i conteggi. In CUJ 5 il «Quando» non è un'azione dell'utente. Le etichette «Mitigazione» non sono uniformi. Non obiettivi e alternative si sovrappongono. (structural)
- «quasi quattro quinti»; il punto della riga 62 è troppo denso; «ripetibile»; «pannello chiaro»; «Questi file sono rari»; «spesso tutti ASCII»; i parametri non nominati; «senza costo aggiuntivo»; i 24 s presi da oggi e non dichiarati come tali; termini diversi per la stessa ricaduta; «(correzione decisa)» opaco; «resta leggibile»; «ne guadagnano il tempo»; il limite superiore di versione non deciso; verifica da spostare nella fase uno; ripetizioni; inciso su rfc4180-bis; «quasi sempre». (style)
- Manca l'alternativa «regolare `charset_normalizer` sull'intero file». I test cancellati vanno elencati con dove si spostano. (design; il secondo punto riguarda il piano dettagliato, fase 9)
- Indice senza link (structural): stessa regola dell'autore del round 1, già confermata.
