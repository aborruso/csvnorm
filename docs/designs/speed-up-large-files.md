# csvnorm veloce sui file grandi

* **Autore:** aborruso
* **Stato:** Implemented (branch `perf/large-files`, 2026-11-22)
* **Data:** 2026-11-22

---

## Indice

- Overview
- Esito dell'implementazione
- Il problema
- Obiettivi
- Non obiettivi
- Decisioni e domande aperte
- Percorsi utente (CUJ, Critical User Journey)
- Piano tecnico
- Rischi e mitigazioni
- Alternative considerate
- Miglioramenti futuri
- Piano di implementazione dettagliato

## Overview

csvnorm valida e normalizza CSV con un percorso fatto di passaggi Python e di due letture DuckDB. Sui file da centinaia di MB i passaggi Python dominano: un CSV cp1252 da 826 MB richiede circa 220 s, e circa 170 s, quasi quattro quinti, vanno in lavoro Python che legge o riscrive il file intero più volte.

Questo design ha l'obiettivo di portare quel file sotto i 60 s, con soglia di rilascio a 3 volte più veloce della base misurata, senza aggiungere una modalità per i file grandi. Il principio è togliere passaggi dove DuckDB può fare lo stesso lavoro mentre scrive l'output, e far lavorare a blocchi quelli che restano in Python. La validazione resta completa: ogni riga viene controllata. Il lavoro corregge anche due difetti esistenti che toccano le stesse funzioni.

La soluzione proposta in breve:

- rilevamento dell'encoding: fino a 50 MiB sull'intero file, come oggi; sopra, una decodifica UTF-8 stretta e, se fallisce, `charset_normalizer` su un campione che contiene ogni valore di byte non ASCII del file, esaminato per intero;
- CRLF scritto da DuckDB con `NEW_LINE '\r\n'`, header corretto da DuckDB con alias nella `SELECT`;
- conversione UTF-8 a blocchi, conservando CR e CRLF.

## Esito dell'implementazione

Misure del 2026-11-22 con `scripts/bench_large.py` sul file da 826 MB, mediana di tre esecuzioni dopo un riscaldamento:

| Fase completata | Mediana | Rilevamento | Note |
| --- | --- | --- | --- |
| Base (1.3.0) | 162,8 s | 87,7 s | |
| Header e CRLF in DuckDB | 131,0 s | 91,5 s | |
| Conversione a blocchi, disco | 140,1 s | 94,6 s | conversione 3,0 s (era 7,1); differenza dovuta alla variabilità del rilevamento |
| Rilevamento a campione | 47,8 s | 2,8 s | 3,4 volte più veloce della base |

La soglia di rilascio, 3 volte la base cioè 54 s, e l'obiettivo dei 60 s sono raggiunti; la fase cinque non è servita. Il picco di memoria del processo resta 2,8 GB, ma è di DuckDB: misurate in processi separati, conversione 94 MiB, validazione 876 MiB, normalizzazione 2.894 MiB.

Differenze dal piano, decise durante l'implementazione:

- **Rilevamento ibrido per dimensione.** Una revisione su file sintetici ha mostrato che il campione peggiora il rilevamento per alcune lingue rispetto al file intero (turco cp1254 da 8/8 a 0/8, polacco cp1250 da 6/8 a 0/8, peggioramenti anche per lituano e ungherese). Deciso con l'autore: fino a 50 MiB (`FULL_DETECTION_MAX_BYTES`) resta il rilevamento sull'intero file, con gli stessi risultati della 1.3.0 e un costo di qualche secondo al massimo; il campione vale solo sopra. Sopra la soglia il rischio resta, accettato, e la via d'uscita è `--encoding`.
- **Preferenza occidentale sul campione.** Sul file da 826 MB il campione dava cp1258 (limite noto di `charset_normalizer` sull'italiano). Fra i candidati con caos minimo vince una codifica occidentale (cp1252, latin-1, iso8859-15); in più, una codifica occidentale che decodifica il campione allo stesso testo è preferita.
- **Finestre.** Si leggono con un `seek` per finestra invece di tenere finestre in sospeso fra blocchi; se nella fascia esterna non c'è un punto di taglio, la finestra si stringe verso il byte. Al massimo 8 occorrenze tentate per valore, ciascuna oltre la finestra fallita, poi rilevamento completo.
- **Tetto dei tentativi.** Le 8 occorrenze si contano per blocco da 4 MiB, non per l'intero file; un valore che a fine file non ha nessuna finestra manda comunque al rilevamento completo. La costante `MAX_WINDOWS` del piano non esiste: c'è `MAX_ATTEMPTS = 8`. La finestra del primo errore UTF-8 si aggiunge solo se ha un punto di taglio; il byte dell'errore resta coperto dalla finestra del suo valore.
- **Nomi e messaggi.** `_pick_encoding(result, file_path)`; log `Encoding route: sample (N windows, M byte values, B bytes)`, `Encoding route: full (file below the sampling threshold)`, `Encoding route: full (no candidate for the sample)`, `Encoding route: full (7-bit escape sequences)`; pannello «No space left on device. Free some space on the output disk or on the temp disk (or set TMPDIR to another disk), then retry.»; un `OSError` diverso da `ENOSPC` in conversione dà «File error during encoding conversion»; l'avviso preventivo riceve la directory temporanea come directory di output in modalità stdout e nessuna directory di output con `--check`, e ignora gli errori del controllo; l'errore di decodifica nomina la codifica sorgente invece di `charmap`.
- **Casi di riferimento.** `empty_file` con la 1.3.0 produce un output (`column0`) ed esce con 0: registrato così. `windows1252_quotes.csv` ha come codifica attesa cp1252 ma oggi dà cp437 (limite 7.1b): `xfail` non stretto.
- **Script di misura.** Picco di memoria con `resource.getrusage`, perché `/usr/bin/time` manca; la colonna «Rilevamento» viene da una chiamata separata a `detect_encoding` prima di `detect_and_convert`.
- **Altri instradamenti al rilevamento completo.** Campione senza candidati (per esempio testo misto UTF-8 e cp1252) e file ASCII con sequenze ISO-2022 o HZ (`ESC`, `~{`).
- **Ricaduta.** Se il rilevamento completo restituisce la stessa codifica già fallita, l'errore si propaga senza una seconda conversione.

## Il problema

Misure del 2026-11-22 su `tmp/comuni_giornaliero_30settembre26.csv` (826 MB, 5,4 milioni di righe, 57 colonne, cp1252, righe CRLF), WSL2, un'esecuzione per fase. Per la conversione in UTF-8 ci sono due misure, da qui l'intervallo.

| Fase | Tempo | Dove |
| --- | --- | --- |
| Rilevamento encoding, `charset_normalizer.from_path` | 106 s | `src/csvnorm/encoding.py` `detect_encoding` |
| Conversione delle righe in CRLF, ciclo byte per byte | 40 s | `src/csvnorm/validation.py` `convert_row_endings_to_crlf` |
| Normalizzazione, `COPY` DuckDB | 24 s | `src/csvnorm/validation.py` `normalize_csv` |
| Validazione, `read_csv` DuckDB con `store_rejects` | 19 s | `src/csvnorm/validation.py` `validate_csv` |
| Riscrittura dell'intero output per correggere l'header | 14 s | `src/csvnorm/validation.py` `_fix_duckdb_keyword_prefix` |
| Conversione in UTF-8, file letto tutto in memoria | 10-14 s | `src/csvnorm/encoding.py` `convert_to_utf8` |
| Conteggio righe e colonne | 3 s | `src/csvnorm/utils.py` |

Come lavora oggi `charset_normalizer`, verificato sul codice installato e con un profilo sui primi 100 MB del file (2026-11-22):

- per ogni codifica candidata decodifica in modo stretto tutto il file (`charset_normalizer/api.py:573`, per i file da almeno 10 MB): sui 100 MB, 5,3 s su 8,7, il 61%, vanno in questa decodifica. È la causa principale dei 106 s;
- il punteggio che distingue le codifiche (caos e coerenza, le due misure della libreria) si calcola solo su 5 pezzi da 512 byte (`api.py:59-60`), cioè circa 2,5 KB, qualunque sia la dimensione del file;
- sui 100 MB il `best()` di `charset_normalizer` da solo sceglierebbe cp1250 (coerenza 0,4918). Fra i candidati con caos 0, dieci hanno la coerenza massima a pari merito, 0,4988: cp1252, cp1254, cp1258, latin_1 e sei varianti iso8859. Lo spareggio di csvnorm (`encoding.py:67-74`) tiene la coerenza più alta fra i meno caotici e, sul pari merito esatto, preferisce le codifiche occidentali: per questo esce cp1252.

Oggi la garanzia è questa: esclude le codifiche che non decodificano qualche byte del file; fra le restanti sceglie su circa 2,5 KB, e su questo file su un pari merito esatto fra dieci codifiche.

Quattro problemi ne derivano:

- **Tempo.** Circa 170 s su 220 vanno in passaggi Python che rileggono o riscrivono tutto il file. DuckDB pesa circa 45 s.
- **Memoria.** Conversione UTF-8, correzione dell'header e passaggio CRLF caricano l'intero file in RAM: il picco stimato, non misurato, è di circa tre volte la dimensione del file (byte letti, stringa decodificata, byte riscritti).
- **Disco.** Il percorso usa due temporanei grandi quanto l'input. Durante le prove il disco, con 2 GB liberi, si è riempito, e la normalizzazione di DuckDB è fallita con «No space left on device» dentro il pannello generico «Normalization failed».
- **Due difetti esistenti, nelle stesse funzioni.**
  - `convert_to_utf8` apre i file in modalità testo senza `newline=""`. Per i file non UTF-8 tutti i fine riga, anche i CR dentro le celle, diventano LF prima che DuckDB li veda, e su Windows l'output cambia rispetto a Linux.
  - La correzione dei prefissi delle parole chiave nell'header riconosce solo la virgola come separatore. Con `-d ';'` non fa nulla.

## Obiettivi

- **Tempo:** sul file da 826 MB, mediana di tre esecuzioni dopo un riscaldamento, sotto i 60 s, contro circa 220 s di oggi; soglia di rilascio 3 volte più veloce della base misurata. Protocollo di misura e tempi per fase nello script di benchmark della fase uno del piano dettagliato.
- **Memoria:** la memoria dei passaggi Python del percorso su file locale resta sotto i 24 MiB qualunque sia la dimensione del file, escluso DuckDB. Fanno eccezione i casi che vanno sul rilevamento di oggi, descritti nel piano tecnico: file fino a 50 MiB, BOM UTF-16 o UTF-32, BOM UTF-8 seguito da UTF-8 non valido, byte NUL, sequenze ISO-2022 o HZ, valori di byte senza punto di taglio, campione senza candidati, conversione fallita. Lì restano tempo e memoria di oggi.
- **Disco:** il picco resta quello di oggi: l'input, `utf8.csv` per i file non UTF-8 (fino al doppio dell'input con cp1252) e l'output provvisorio. Cambiano due cose: l'output provvisorio sta accanto a quello finale e diventa definitivo con una rinomina atomica, quindi un errore non lascia mai un output parziale né distrugge quello esistente; e lo spazio esaurito ha un avviso prima di partire, il pannello «spazio su disco esaurito» ed exit 1 quando succede, temporanei cancellati.
- **Correttezza dell'encoding:** su ogni file di prova il nuovo rilevamento dà lo stesso risultato di oggi, oppure coincide con la codifica attesa dichiarata a mano per quel file dove oggi non coincide. Sul percorso della CLI nessuna codifica che non sa decodificare il file viene mai usata: la conversione stretta lo verifica e, se fallisce, scatta la ricaduta. `detect_encoding` usata da sola dà la stessa garanzia per le codifiche a un byte.
- **Validazione completa:** ogni riga resta controllata. Il file degli scarti ha gli stessi numeri di riga, le stesse colonne e gli stessi tipi d'errore di oggi. Le posizioni in byte possono cambiare nei file non UTF-8, perché DuckDB vede i fine riga originali. Per i file non UTF-8 con righe a solo CR, con fine riga misti o con `\r\r\n` possono cambiare anche gli scarti: oggi la modalità testo trasforma questi fine riga prima di DuckDB (`\r\r\n` diventa `\n\n`, con una riga vuota in più). I risultati attesi si misurano e si fissano nella fase uno, uno per caso.
- **Output:** identico byte per byte alla release 1.3.0 su Linux sull'insieme di file di riferimento elencato nella fase uno del piano dettagliato, tranne i casi seguenti, ciascuno con un test proprio:
  - i fine riga dei file non UTF-8, compresi CR e CRLF dentro le celle, restano come nell'input (correzione decisa dall'autore);
  - la correzione dei prefissi delle parole chiave nell'header funziona con ogni delimitatore (correzione decisa dall'autore);
  - nei file in cui il nuovo rilevamento coincide con la codifica attesa e quello di oggi no, l'output segue la codifica nuova. Ogni caso è elencato con il motivo in `tests/test_encoding_equivalence.py`.
- **Contratto invariato:** exit code 0/1/2, input mai sovrascritto, API pubblica `detect_encoding` con la stessa firma.

## Non obiettivi

- **Cambiare libreria**, per esempio Polars: DuckDB pesa circa 45 s su 220, il costo sta altrove.
- **Una modalità per i file grandi**: sarebbero due percorsi da mantenere e testare.
- **Validazione a campione**: requisito dell'autore, nessuna riga malformata deve sfuggire.
- **Memoria limitata per stdin, output su stdout e `--fix-mojibake`**: oggi leggono l'intero file e continuano a farlo.
- **Ridurre il picco di disco**: resta quello di oggi; la copia unica è fra i miglioramenti futuri.
- **Velocizzare l'input gzip**: non passa da rilevamento e conversione.
- **Aggiungere `--encoding`**: è la proposta separata `openspec/changes/add-input-encoding-option`.

## Decisioni e domande aperte

Una domanda aperta: se sulla macchina di misura `/tmp` sta su tmpfs, i temporanei occupano RAM. Si verifica nella fase uno, prima della misura di partenza.

Decisioni del 2026-11-22, dettagliate all'inizio del piano di implementazione:

- validazione e normalizzazione in un solo `COPY`: fase condizionale, si fa se dopo le altre fasi la mediana resta sopra i 60 s;
- questo lavoro va prima di `add-input-encoding-option`;
- si rilascia se il miglioramento è di almeno 3 volte rispetto alla base misurata;
- nessun interruttore per forzare il rilevamento completo: la via d'uscita sarà `--encoding`;
- `preserve-crlf-line-endings` si archivia prima di cominciare;
- il caso `\r\r\n` diventa un file di riferimento;
- temporanei su disco come oggi, con l'output provvisorio accanto a quello finale e rinomina atomica.

## Percorsi utente (CUJ, Critical User Journey)

### CUJ 1: file grande non UTF-8 con output su file

- **Dato** un CSV cp1252 locale da circa 800 MB con righe CRLF e 6 GB di disco libero.
- **Quando** l'utente lancia `csvnorm input.csv -o output.csv`.
- **Allora** csvnorm finisce in meno di 60 s (obiettivo) e comunque almeno 3 volte più veloce della base misurata (soglia di rilascio), l'output è UTF-8 con righe CRLF e header in snake_case, la tabella finale riporta encoding cp1252 e il conteggio di righe e colonne, l'exit code è 0, e a fine lavoro non restano temporanei.

### CUJ 2: byte non ASCII solo in fondo al file

- **Dato** un CSV di 500 MB in ASCII puro tranne una riga, vicino alla fine, con un carattere cp1252 accentato.
- **Quando** l'utente lancia `csvnorm input.csv -o output.csv`.
- **Allora** csvnorm sceglie una codifica occidentale a un byte che decodifica quel byte, converte la riga senza mandarla fra gli scarti, e il risultato coincide con la codifica attesa dichiarata per quel file di prova.

### CUJ 3: CR dentro una cella di un file non UTF-8

- **Dato** un CSV latin-1 con un campo quotato che contiene `\r\n`.
- **Quando** l'utente lo normalizza su Linux e poi su Windows.
- **Allora** il campo arriva nell'output con `\r\n` intatto, e i due output sono identici byte per byte.

### CUJ 4: header con parole chiave e delimitatore punto e virgola

- **Dato** un CSV con colonne `select` e `_id`.
- **Quando** l'utente lancia `csvnorm input.csv -d ';' -o output.csv`.
- **Allora** l'header dell'output è `select;_id`, senza il prefisso `_` aggiunto da DuckDB alla parola chiave, e `_id` resta invariato.

### CUJ 5: disco pieno durante conversione o normalizzazione

- **Dato** un CSV non UTF-8 e un disco con meno spazio libero di quello che servirà, e un `output.csv` già esistente.
- **Quando** l'utente lancia `csvnorm input.csv -o output.csv --force` e lo spazio finisce durante la conversione, il `COPY` di DuckDB o l'esportazione degli scarti.
- **Allora** csvnorm ha già avvisato prima di partire, mostra il pannello «spazio su disco esaurito», esce con 1, cancella i temporanei, e l'input e il vecchio `output.csv` restano intatti.

## Piano tecnico

### Flusso, prima e dopo

Oggi, per un file locale non UTF-8 con righe CRLF e output su file (`-o`, non stdout):

```text
input.csv
  │  detect_encoding: charset_normalizer, decodifica
  │  dell'intero file per ogni candidato ................. 106 s
  ▼
  │  convert_to_utf8: tutto in memoria, modalità testo ... 10-14 s
  ▼
utf8.csv (temporaneo)
  │  validate_csv: DuckDB read_csv con store_rejects ..... 19 s
  │  normalize_csv: DuckDB COPY .......................... 24 s
  ▼
normalized.csv (temporaneo)
  │  _fix_duckdb_keyword_prefix: rilegge e riscrive ...... 14 s
  │  convert_row_endings_to_crlf: byte per byte .......... 40 s
  ▼
output.csv
  │  conteggio righe e colonne ........................... 3 s
```

Dopo, con tempi stimati, non misurati:

```text
input.csv
  │  detect_encoding: UTF-8 stretto, poi campione
  │  sui byte non ASCII .................................. stima 3-6 s
  ▼
  │  convert_to_utf8: a blocchi, fine riga conservati .... stima 5-10 s
  ▼
utf8.csv (temporaneo)
  │  validate_csv: invariato ............................. 19 s
  │  normalize_csv: un solo COPY che scrive
  │    - l'header già corretto (alias nella SELECT)
  │    - le righe CRLF se l'input era CRLF (NEW_LINE) .... 24 s (valore di oggi, assunto invariato)
  ▼
.output.csv.csvnorm-partial (accanto all'output, rinominato alla fine)
  │  conteggio righe e colonne ........................... 3 s
  ▼
output.csv
```

Totale stimato: 54-62 s. L'obiettivo dei 60 s è quindi al limite, ed è per questo che esistono la soglia di rilascio a 3 volte e la fase condizionale del `COPY` unico.

Spariscono due passaggi Python che leggono e riscrivono tutto il file. Gli altri due lavorano a blocchi di dimensione fissa. Le due letture DuckDB restano come sono.

### Rilevamento dell'encoding

`detect_encoding(file_path)` conserva firma e valori restituiti di oggi: `"utf-8"` (anche con il BOM, come oggi), `"ascii"` o il nome normalizzato di un'altra codifica.

Fino a 50 MiB (`FULL_DETECTION_MAX_BYTES`) il rilevamento resta quello di oggi, sull'intero file. Sopra la soglia la strategia ha tre passi (le scelte fatte durante l'implementazione sono in «Esito dell'implementazione»):

- **Casi che restano sul percorso di oggi.** Un BOM UTF-16 o UTF-32, un BOM UTF-8 seguito da UTF-8 non valido, un byte NUL in qualsiasi punto del file, oppure un valore di byte alto per cui non si trova una finestra valida, portano al rilevamento di oggi sull'intero file. Il campione romperebbe l'allineamento a 2 o 4 byte di UTF-16 e UTF-32, che contengono NUL anche senza BOM, e un file binario deve continuare a dare `ValueError` come oggi.
- **UTF-8 stretto.** Una passata a blocchi con un decoder UTF-8 stretto, che si ferma al primo errore. Se il file è tutto ASCII il risultato è `ascii`, se è UTF-8 valido è `utf-8`; un file vuoto dà `utf-8`, come oggi.
- **Campione, solo per i file non UTF-8.** Una seconda passata a blocchi costruisce un campione con una finestra attorno al punto del primo errore UTF-8 e una attorno alla prima occorrenza utilizzabile di ogni valore di byte `>= 0x80` presente nel file. I valori sono al massimo 128, quindi il campione resta piccolo, nell'ordine delle decine di KiB. Ogni finestra comincia e finisce subito dopo un byte inferiore a 0x40 che non sia una cifra (a capo, virgola, spazio, punto e virgola), oppure all'inizio o alla fine del file. Nelle codifiche a più byte diffuse (Shift_JIS, GBK, GB18030, Big5, EUC, UTF-8) un byte così non è mai una parte successiva di un carattere: le finestre non spezzano i caratteri, e il taglio non dipende dalle righe. Le cifre sono escluse perché in GB18030 compaiono dentro le sequenze a 4 byte. Il campione va a `charset_normalizer.from_bytes` con parametri che lo fanno esaminare come un solo pezzo e con UTF-8 e ASCII esclusi dai candidati, perché la prima passata ha già dimostrato che il file non è né l'uno né l'altro; poi si applica lo spareggio di oggi.

La proprietà che ne risulta: il campione contiene ogni valore di byte alto del file, e `from_bytes` lo decodifica in modo stretto per ogni candidato, scartando quelli che falliscono (`charset_normalizer/api.py:349-391`). Una codifica a un byte che non sa decodificare qualche byte del file viene quindi esclusa, come oggi, senza decodificare l'intero file per ogni candidato.

La ricaduta vive in un solo punto: una funzione di `encoding.py` che rileva e converte, chiamata una volta da `core.py`. Se la conversione stretta fallisce, cosa possibile solo per le codifiche a più byte, la funzione rileva come oggi, con `from_path` sull'intero file, e riconverte una sola volta. La ricaduta è esente dai limiti di tempo e memoria. Se fallisce anche la seconda conversione compare il pannello «Encoding conversion failed», exit 1. Oggi, per l'ordine delle `except` a `core.py:464-471`, lo stesso errore compare senza titolo: il titolo è una piccola correzione.

Il rischio che resta è una codifica a un byte sbagliata che decodifica comunque tutti i byte presenti, per esempio cp1250 al posto di cp1252. Oggi la scelta fra queste codifiche si fa su circa 2,5 KB, su questo file tutti ASCII. Con il campione esaminato per intero, il punteggio lavora sui byte che distinguono le codifiche. Va dimostrato con file di prova che dichiarano la codifica attesa, compresi file sintetici grandi con pochi byte non ASCII.

Cambia il contratto della spec `openspec/specs/encoding-detection/spec.md`, che oggi indica `charset_normalizer` come rilevatore principale e un fallback `file -b` che nel codice non esiste: serve un delta MODIFIED, descritto nel piano dettagliato.

Con `--verbose` il log dice quale strada è stata presa: ASCII, UTF-8, campione, rilevamento completo, oppure ricaduta e perché. Le costanti (dimensioni dei blocchi e delle finestre) stanno nel piano dettagliato.

### Conversione in UTF-8

`convert_to_utf8(input_path, output_path, source_encoding)` conserva la firma. Cambia l'interno:

- lettura in binario a blocchi, decodifica con un decoder incrementale stretto della codifica sorgente, scrittura in UTF-8 in binario;
- niente modalità testo, quindi CR, LF e CRLF passano intatti, anche dentro le celle, e l'output è lo stesso su Linux e Windows (correzione decisa);
- in caso di errore (decodifica, disco pieno) il file parziale viene cancellato prima di propagare l'eccezione.

La posizione riportata da un `UnicodeDecodeError` diventa relativa al blocco: la funzione la riporta alla posizione nel file prima di propagarla, così il pannello d'errore riporta la posizione nel file.

### Header e CRLF scritti da DuckDB

`normalize_csv` costruisce oggi il `COPY` in tre punti: il percorso normale, il ritorno alle configurazioni di riserva (`FALLBACK_CONFIGS`, coppie di delimitatore e righe da saltare provate quando DuckDB non riconosce il formato) e l'ultimo tentativo con `strict_mode=false`. I tre punti passano a usare due elementi comuni.

- **Elenco delle colonne.** Con `normalize_names=True`, al posto di `SELECT *` si usa una sola espressione (le parole chiave sono abbreviate con `...`):

  ```sql
  SELECT COLUMNS('^(?:_(select|from|...)|(.*))$') AS '\1\2' FROM read_csv(...)
  ```

  L'alternanza contiene le parole di `_DUCKDB_KEYWORD_SET`. Una colonna che DuckDB ha rinominato in `_select` esce come `select`. Tutte le altre, compresa una `_id` scritta dall'utente, escono invariate. L'ordine delle colonne resta quello del file. Verificato il 2026-11-22 con DuckDB 2.0.0: un header `select,_id,From,a b,_select` con `-d ';'` dà `select;_id;from;a_b;_select_1`. Il `_1` è il suffisso che DuckDB aggiunge ai nomi duplicati, perché `_select` collide con la colonna `select` già rinominata, e lo aggiunge anche oggi. La regola vale per ogni delimitatore, perché lavora sui nomi delle colonne e non sul testo dell'header (correzione decisa). Con `--keep-names` resta `SELECT *`.
- **Opzioni del COPY.** Si aggiunge `NEW_LINE '\r\n'` quando l'input aveva righe CRLF e l'output va su file. Verificato il 2026-11-22: gli a capo dentro le celle quotate restano invariati (`"a\nb"` resta così, `"d\r\ne"` resta così).

`normalize_csv` riceve un nuovo parametro facoltativo, `crlf: bool = False`. Le chiamate esistenti all'API pubblica continuano a funzionare. `core.py` lo valorizza con `input_has_crlf and not use_stdout`, la stessa condizione di oggi, e lo passa attraverso `_normalize_and_refresh_errors`, la cui firma cambia anche lei. `input_has_crlf` è vero quando il primo fine riga fuori dalle virgolette, nei primi 8 KB del file, è CRLF (`utils.has_crlf_line_endings`).

`_fix_duckdb_keyword_prefix` e `convert_row_endings_to_crlf` non vengono più chiamate e si tolgono, insieme ai loro test. I test di comportamento equivalenti si spostano sull'output di `normalize_csv` e della CLI.

### Spazio su disco e temporanei

- Oggi e dopo, al picco, su disco ci sono l'input, `utf8.csv` per i file non UTF-8 (fino al doppio dell'input con cp1252, perché i caratteri accentati passano da 1 a 2 byte) e l'output provvisorio. Le due riscritture Python di oggi pesano in memoria, non su disco: toglierle riduce la memoria, non il disco.
- **Output provvisorio accanto a quello finale.** Oggi `normalized.csv` sta nella directory temporanea e arriva all'output con `shutil.move` (`core.py:816`). Se le due directory stanno su filesystem diversi, `shutil.move` copia e poi cancella: un errore a metà lascia un output parziale oppure, con `--force`, distrugge quello esistente, contro quanto promette il commento a `core.py:773-775`. Dopo, l'output provvisorio si scrive nella directory di output con un nome nascosto riconoscibile e diventa definitivo con una rinomina atomica, senza copia. Il provvisorio è registrato fra i temporanei, quindi viene cancellato su errore e sull'uscita di `--strict`; uno rimasto da un'interruzione forzata viene sovrascritto alla prossima esecuzione sullo stesso output.
- `utf8.csv` resta nella directory temporanea e la pulizia resta in `_cleanup_temp_artifacts`. La conversione cancella da sola il proprio parziale in caso di errore.
- **Spazio esaurito.** Durante la conversione, il `COPY` di DuckDB o l'esportazione degli scarti, dà lo stesso pannello «spazio su disco esaurito» con exit 1. Si riconosce dal codice d'errore di sistema per Python e dal codice riportato nel messaggio di DuckDB, presente nell'errore visto il 2026-11-22; su Windows il codice che riporta DuckDB va verificato. Oggi `_prepare_working_file` (`core.py:464-471`) non intercetta `OSError` e la normalizzazione mostra un pannello generico (`core.py:792-803`).
- **Avviso preventivo**, senza fermarsi, se lo spazio libero non basta per `utf8.csv` nella directory temporanea e per l'output provvisorio in quella di output; se le due stanno sullo stesso filesystem, i due bisogni si sommano.

### Cosa non cambia

- Validazione con DuckDB: stessa query.
- Zip, URL remoti e stdin passano da rilevamento e conversione dopo il salvataggio su file, e ne guadagnano il tempo; lo stdin resta letto tutto in memoria (`core.py:662`). Gzip non ci passa, come oggi.
- Output su stdout: nessun CRLF, come oggi. La lettura del temporaneo con `f.read()` a `core.py:359-360` resta.
- `--fix-mojibake`: ftfy lavora sull'intero testo, come oggi.
- Exit code e messaggi, tranne il log di `--verbose` sulla strada del rilevamento, il nuovo pannello per lo spazio esaurito e l'avviso preventivo.
- Se il campione non dà candidati si passa al rilevamento completo, che come oggi solleva `ValueError` se non trova nulla. Una colonna che l'utente ha chiamato davvero `_select` viene rinominata come oggi.

## Rischi e mitigazioni

- **Dipendenza da DuckDB 2.0.0.** `COLUMNS(...) AS '\1\2'` e `NEW_LINE` sono verificati su DuckDB 2.0.0, ma `pyproject.toml` chiede `duckdb>=2.0.0` senza limite superiore. Mitigazione: i test di riferimento coprono entrambi i comportamenti e falliscono se una versione nuova li cambia; limite superiore alla prossima versione maggiore.
- **Dipendenza dal comportamento di `charset-normalizer`.** Parametri come `steps` e `chunk_size` e il punteggio possono cambiare fra versioni (`>=3.0.0`). Mitigazione: test di equivalenza con la codifica attesa per ogni file di prova.
- **Campione non rappresentativo.** Una codifica a un byte sbagliata che decodifica tutti i byte presenti può essere scelta; la revisione del codice lo ha misurato per turco, polacco, lituano e ungherese. Mitigazione: campione solo sopra 50 MiB, una finestra per ogni valore di byte alto esaminata per intero, file di prova sintetici; via d'uscita per l'utente con `--encoding`.
- **Codifiche a più byte.** Una finestra che spezza un carattere farebbe scartare la codifica giusta. Mitigazione: tagli solo dopo un byte inferiore a 0x40 che non sia una cifra, test con un file Shift_JIS, e la ricaduta in conversione.
- **Regressioni sui fine riga.** DuckDB vede ora i fine riga originali dei file non UTF-8: un file con solo CR, con fine riga misti o con `\r\r\n` potrebbe essere letto con un altro dialetto e dare scarti diversi. Mitigazione: eccezione dichiarata nell'obiettivo «Validazione completa» e risultati attesi misurati e fissati nella fase uno.
- **Disco.** Il picco resta quello di oggi. Con `/tmp` su tmpfs `utf8.csv` occupa RAM. Mitigazione: verifica nella fase uno (domanda aperta), avviso preventivo e pannello «spazio su disco esaurito». Il caso delle directory su filesystem diversi sparisce con la rinomina atomica.
- **Sicurezza.** Mitigazione: non serve, nessuna implicazione nuova: le parole chiave nell'espressione SQL sono costanti del codice, passate per `re.escape`, e nessun dato dell'input entra nell'SQL.

## Alternative considerate

### Cambiare libreria, per esempio Polars

- **Pro:** lettura parallela e a blocchi.
- **Contro:** DuckDB pesa circa 45 s su 220. Il costo sta nei passaggi Python attorno, che Polars non tocca. Bisognerebbe riscrivere validazione e file degli scarti, che si basano su `store_rejects` di DuckDB.
- **Motivo dello scarto:** scartata dall'autore, perché le misure mostrano che il collo di bottiglia non è la lettura del CSV.

### Modalità separata per i file grandi

- **Pro:** nessun rischio per il percorso dei file piccoli.
- **Contro:** due percorsi da mantenere e testare, e un'opzione che l'utente deve conoscere.
- **Motivo dello scarto:** scartata dall'autore: due percorsi da mantenere e testare, e i passaggi lenti lo sono per tutti i file, quindi correggerli nel percorso unico basta.

### Validazione a campione

- **Pro:** tempo di validazione fisso, indipendente dalla dimensione del file.
- **Contro:** le righe malformate nelle zone non lette sfuggono. La validazione costa 19 s e non è il collo di bottiglia.
- **Motivo dello scarto:** scartata dall'autore: nessuna riga malformata deve sfuggire.

### Rinunciare al CRLF in output

- **Pro:** toglie un passaggio.
- **Contro:** perde la fedeltà all'input. L'RFC 4180 indica CRLF, anche se è di tipo Informational e la bozza rfc4180-bis ammette CR, LF e CRLF.
- **Motivo dello scarto:** scartata dall'autore. Il CRLF si tiene e lo scrive DuckDB con `NEW_LINE`, senza una lettura e una scrittura in più.

### Rilevamento su blocchi casuali, con ritorno all'intero file solo se la conversione fallisce

- **Pro:** nessuna scansione dell'intero file, costo fisso.
- **Contro:** il ritorno non scatta nei casi pericolosi. `latin_1` decodifica qualsiasi byte e cp1252 fallisce solo su cinque valori di byte (0x81, 0x8D, 0x8F, 0x90, 0x9D). Una scelta sbagliata fra codifiche a un byte converte senza errori e produce testo alterato con exit 0. Se i blocchi sono tutti ASCII, il verdetto è `ascii`, la conversione non parte e i byte accentati successivi finiscono fra gli scarti.
- **Motivo dello scarto:** scartata dall'autore, perché un errore passerebbe in silenzio. Al suo posto: UTF-8 stretto e campione con ogni valore di byte non ASCII del file.

### CRLF e header riscritti in Python a blocchi

- **Pro:** non dipende da opzioni di DuckDB e conserva esattamente la logica di oggi.
- **Contro:** resta una lettura e una scrittura in più dell'intero output. Va scritto e testato il codice che tiene traccia, da un blocco all'altro, di quando si è dentro un campo fra virgolette.
- **Motivo dello scarto:** scartata dall'autore: DuckDB 2.0.0 fa entrambe le cose durante il `COPY`, `NEW_LINE '\r\n'` e la rinomina con `COLUMNS(...) AS`, senza una lettura e una scrittura in più. Entrambe verificate il 2026-11-22.

### Regolare `charset_normalizer` sull'intero file

- **Pro:** nessun campionatore da scrivere; si restringono i candidati o si cambiano `steps` e `chunk_size`.
- **Contro:** anche con meno candidati resta una decodifica completa del file per ciascuno, che è la causa principale dei 106 s; e con più `steps` il punteggio cresce con la dimensione del file.
- **Motivo dello scarto:** non adottata: non toglie il costo della decodifica completa per candidato, che il campione con ogni valore di byte sostituisce con una sola passata.

### DuckDB che legge direttamente l'originale con `encoding='latin-1'`

- **Pro:** elimina la conversione e il temporaneo UTF-8, quando nel file non ci sono byte 0x80-0x9F e cp1252 coincide con latin-1.
- **Contro:** è un secondo percorso valido solo per alcune codifiche. Per le altre servirebbe, da verificare, un'estensione DuckDB scaricata dalla rete.
- **Motivo dello scarto:** non adottata in questo design: un secondo percorso valido solo per alcune codifiche, con costo in tempo non misurato. È fra i miglioramenti futuri.

## Miglioramenti futuri

- **Una sola copia temporanea per i file compatibili con latin-1.**
  - Condizione: nel file non ci sono byte 0x80-0x9F, quindi cp1252 e latin-1 coincidono e DuckDB potrebbe leggere l'originale con `encoding='latin-1'`, senza `utf8.csv`.
  - Guadagno atteso: una copia del file e la conversione.
  - Caso reale: il file da 826 MB del 2026-11-22 rientra, con zero byte 0x80-0x9F e undici valori di byte non ASCII distinti, tutti vocali accentate.
  - Da verificare prima: che DuckDB 2.0.0 legga `latin-1` senza estensioni esterne, e quanto costi la decodifica in lettura, fatta due volte (validazione e normalizzazione).
  - Esclusioni: `--fix-mojibake` e le altre codifiche.
  - Priorità: da valutare con la base e i tempi per fase misurati da questo lavoro; in cima se i file grandi abituali sono quasi sempre di questo tipo.

## Piano di implementazione dettagliato

Questo piano descrive il lavoro come era stato pianificato prima dell'implementazione. Dove differisce dal codice, vale la sezione «Esito dell'implementazione».

### Decisioni prese per questo piano (2026-11-22)

- **Validazione e normalizzazione in un solo `COPY`:** fase condizionale (fase cinque). Si fa solo se, finita la fase quattro, la mediana sul file da 826 MB resta sopra i 60 s. La soglia di rilascio, 3 volte più veloce della base, è raggiungibile senza questa fase secondo la stima del piano tecnico (54-62 s contro circa 73 s, cioè 220 s / 3; con la base misurata, 162,8 s, la soglia è diventata 54 s).
- **Ordine:** questo lavoro va prima di `add-input-encoding-option`, la cui proposta andrà aggiornata dopo.
- **Soglia:** si rilascia se il miglioramento è di almeno 3 volte rispetto alla base misurata nella fase uno. I 60 s restano l'obiettivo dichiarato.
- **Interruttore per il rilevamento completo:** nessuno. La via d'uscita sarà `--encoding`.
- **`preserve-crlf-line-endings`:** si archivia prima, come fase zero.
- **Caso `\r\r\n`:** con la 1.3.0, su un file ASCII, `a,b\r\r\n1,2\r\r\n` dà `a,b\r\n1,2\r\n` (misurato il 2026-11-22). Diventa un file di riferimento, insieme alla variante non UTF-8, il cui risultato si misura nella fase uno.
- **Rilevamento rispetto a oggi:** su ogni file di prova il nuovo rilevamento dà lo stesso risultato di oggi, oppure coincide con la codifica attesa dichiarata a mano per quel file. Il caso «200.000 righe ASCII più un byte latin-1», che oggi dà cp1006 secondo la proposta `--encoding`, ha come codifica attesa una codifica occidentale a un byte.
- **Temporanei:** l'output provvisorio sta accanto a quello finale e diventa definitivo con `os.replace`.
- **Unità:** tutte le dimensioni in KiB e MiB, tranne la soglia di 10 MB di `charset_normalizer`, che nella libreria è decimale.
- **Messaggi nuovi:** in inglese, come i pannelli di oggi.

Ogni fase è uno o più commit con i suoi test e una voce in `LOG.md`; dalla fase uno alla quattro la voce riporta la mediana misurata. Alla fine di ogni fase passa la suite intera (`uv run pytest tests/ -v`). Si torna indietro con un revert, perché non c'è stato persistente. Se una verifica fallisce e il piano non dice cosa fare, ci si ferma e decide l'autore. `uv.lock` non è versionato e non si tocca.

### Fase zero: archiviare `preserve-crlf-line-endings`

#### `openspec/changes/preserve-crlf-line-endings/tasks.md` (Modify, poi archiviato)

- **Modifiche:** si verificano una per una le 9 voci sul codice e sui test (commit `107e8e2` e `0c7b8d8`) e si spuntano. Se una voce non è verificabile, decide l'autore fra tre strade: completarla, toglierla dalla change o rimandare l'archiviazione.
- **Comandi:** `openspec archive preserve-crlf-line-endings --yes`, poi `openspec validate --strict --specs`.

#### `openspec/specs/output-location/spec.md` (Modify, tramite `openspec archive`)

- **Modifiche:** riceve i requisiti CRLF della change archiviata.
- **Verifica:** `openspec validate --strict --specs` senza errori.

### Fase uno: file di riferimento e misura

#### `openspec/changes/speed-up-large-files/proposal.md`, `tasks.md`, `design.md` (Create)

- **Modifiche:** `proposal.md` riassume perché e cosa cambia; `design.md` rimanda a `docs/designs/speed-up-large-files.md`; `tasks.md` riprende le fasi di questo piano.

#### `openspec/changes/speed-up-large-files/specs/encoding-detection/spec.md` (Create)

- **Modifiche:**
  - MODIFIED «Primary encoding detection uses charset_normalizer»: sparisce il fallback `file -b --mime-encoding`, che nel codice non esiste. Entrano i passi del piano tecnico: instradamento di BOM UTF-16, UTF-32 e NUL al rilevamento completo; UTF-8 stretto; campione di finestre non ASCII; ricaduta al rilevamento completo se la conversione fallisce.
  - ADDED «UTF-8 conversion preserves line breaks»: CR, LF e CRLF passano intatti, anche dentro le celle.

#### `openspec/changes/speed-up-large-files/specs/processing-pipeline/spec.md` (Create)

- **Modifiche:** ADDED «Keyword prefix removal works with any output delimiter», con lo scenario `select,_id` e `-d ';'` che dà `select;_id`.

#### `openspec/changes/speed-up-large-files/specs/error-handling/spec.md` (Create)

- **Modifiche:** ADDED «Disk full is reported and never leaves a partial output», con lo scenario di CUJ 5.

#### `openspec/changes/speed-up-large-files/specs/output-location/spec.md` (Create)

- **Modifiche:** MODIFIED «Temp and reject file locations»: in modalità file l'output provvisorio sta nella directory di output come `.<nome>.csvnorm-partial` e diventa definitivo con una rinomina atomica; `utf8.csv` resta nella directory temporanea.

#### `tests/fixtures/golden/cases.toml` (Create)

- **Ambito:** manifesto dei casi di riferimento. Ogni caso è una tabella `[[case]]` con questi campi:
  - `name`;
  - `input`: percorso relativo alla radice del repository;
  - `args`: lista degli argomenti della CLI oltre a input e `-o`, scritti come stringhe TOML normali (il tab come `"\t"`, cioè un vero carattere di tabulazione);
  - `exit_code`;
  - `output`: `true` se il caso produce un output da confrontare;
  - `rejects`: `true` se il caso produce un file degli scarti da confrontare;
  - `xfail_until`: facoltativo, numero della fase che lo corregge.
- **Casi con input già in `test/`:** `utf8_basic`, `latin1_semicolon`, `windows1252_quotes`, `utf8_sig_bom`, `pipe_mixed_headers`, `malformed_rows` (con scarti, exit 1), `crlf_with_embedded_lf`, `empty_file` (nessun output; exit code e messaggio come registrati con la 1.3.0).
- **Casi con input nuovi in `tests/fixtures/golden/inputs/`,** un file `<name>.csv` per caso:
  - `header_only.csv`: `a,b,c\n`;
  - `keywords_comma.csv`: `select,_id,From,a b,_select\n1,2,3,4,5\n`;
  - `keywords_semicolon`: stesso input di `keywords_comma`, `args = ["-d", ";"]`, `xfail_until = 2`;
  - `delim_pipe`: input `utf8_basic`, `args = ["-d", "|"]`;
  - `delim_tab`: input `utf8_basic`, `args = ["-d", "\t"]`;
  - `cp1252_cr_in_cell.csv`: in cp1252, `id,nota\r\n1,"caff\xe8\rlatte"\r\n`, `xfail_until = 3`;
  - `latin1_crlf_in_cell.csv`: in latin-1, `id,nota\r\n1,"citt\xe0\r\nnuova"\r\n`, `xfail_until = 3`;
  - `ascii_rrn.csv`: `a,b\r\r\n1,2\r\r\n`;
  - `cp1252_rrn.csv`: `a,b\r\r\n1,caff\xe8\r\r\n`;
  - `cp1252_cr_only.csv`: `a,b\r1,caff\xe8\r2,t\xe8\r`;
  - `cp1252_mixed_endings.csv`: `a,b\r\n1,caff\xe8\n2,t\xe8\r\n`.

#### `tests/fixtures/golden/expected/` (Create)

- **File:** per ogni caso con `output = true`, `<name>.csv`; con `rejects = true`, anche `<name>_reject_errors.csv`.
- **Come si producono:** con csvnorm 1.3.0 su Linux, lanciato come sottoprocesso con lo stesso comando del test. Fanno eccezione i casi con `xfail_until`, scritti a mano con il comportamento atteso dopo la fase indicata. Per `cp1252_rrn`, `cp1252_cr_only` e `cp1252_mixed_endings` l'output della 1.3.0 si registra così com'è, e la fase tre lo aggiorna se cambia, con il motivo in `LOG.md`.
- **File degli scarti:** si confrontano solo le colonne `line`, `column_idx`, `column_name` ed `error_type`. `byte_position`, `line_byte_position` e `csv_line` possono cambiare quando cambiano i fine riga visti da DuckDB.

#### `tests/test_golden.py` (Create)

- **Modifiche:**
  - legge `cases.toml` con `tomllib`;
  - per ogni caso esegue `subprocess.run([sys.executable, "-m", "csvnorm", str(REPO / case["input"]), "-o", str(tmp_path / f"{name}.csv"), *case["args"]], cwd=tmp_path, capture_output=True)`, con `REPO = Path(__file__).resolve().parents[1]`. Il file degli scarti si chiama quindi `<name>_reject_errors.csv` (`core.py:102`);
  - controlla l'exit code e, dove previsto, confronta byte per byte l'output e le quattro colonne degli scarti; con `output = false` controlla che l'output non esista;
  - un caso con `xfail_until` è marcato `pytest.mark.xfail(strict=True)`; la fase indicata toglie il campo dal manifesto.
- **Verifica:** sul codice attuale passano tutti, tranne gli `xfail` attesi.

#### `tests/test_encoding_equivalence.py` (Create)

- **Modifiche:** un dizionario letterale `EXPECTED` associa ogni file di `test/` con estensione `.csv` e ogni input di `tests/fixtures/golden/inputs/` alla sua codifica attesa, dichiarata a mano. Il valore iniziale è quello che `detect_encoding` dà oggi, già normalizzato (per esempio `latin-1`, `iso8859-15`), controllato a mano decodificando il file e leggendo i caratteri accentati. `empty_file.csv` vale `utf-8`. `binary_file.bin` sta in un test a parte che si aspetta `ValueError`, e `README.md` resta fuori. Per ogni voce il test controlla che `detect_encoding` restituisca il valore atteso.
- **Perché:** è la prova dell'obiettivo «Correttezza dell'encoding». Non c'è una copia congelata del rilevatore: il riferimento sono i valori letterali.

#### `tests/conftest.py` (Modify)

- **Modifiche:** nuova fixture `make_csv(tmp_path)` che restituisce una funzione `make(rows: int, insert: dict[int, bytes] | None = None, crlf: bool = False, body: bytes | None = None) -> Path`.
  - Senza `body` scrive un header `a,b,c,d,e` e `rows` righe ASCII `i,i,i,i,i` (il numero di riga ripetuto).
  - `insert` sostituisce il valore della colonna `e` nelle righe indicate con i byte dati, già codificati.
  - Con `body` scrive direttamente quei byte, per i file a più byte: per esempio `"名前,住所\n".encode("shift_jis")` ripetuto.
  - Serve ai casi sintetici delle fasi tre e quattro, senza script esterni.

#### `scripts/bench_large.py` (Create)

- **Interfaccia:** `uv run python scripts/bench_large.py <file.csv> [--runs 3]`.
- **Modifiche:**
  - prima di partire controlla con `shutil.disk_usage` che lo spazio libero sia almeno 3 volte la dimensione del file, e controlla con `findmnt -n -o FSTYPE -T <tmpdir>` se la directory temporanea è tmpfs: in quel caso si ferma e chiede di impostare `TMPDIR` su un disco;
  - esegue un riscaldamento e poi `--runs` esecuzioni di `uv run csvnorm <file> -o <tmp>/out.csv --force`, e stampa la mediana del tempo totale;
  - in un'esecuzione separata chiama le funzioni di libreria una per una con `time.perf_counter` e stampa i tempi per fase, come lo script di misura del 2026-11-22. Nella fase uno le chiamate sono `detect_encoding`, `convert_to_utf8`, `validate_csv`, `normalize_csv(..., normalize_names=True)`, `get_row_count` e `get_column_count`;
  - riporta il picco di RSS con `/usr/bin/time -v` se c'è;
  - alla fine cancella i propri output.
- **Perché:** una sola esecuzione su WSL2 non basta come base di confronto. I tempi per fase si misurano qui, senza strumentazione permanente nel codice.

#### `pyproject.toml` (Modify)

- **Modifiche:** `duckdb>=2.0.0,<3`.

**Misura di partenza:** `scripts/bench_large.py tmp/comuni_giornaliero_30settembre26.csv` sul codice attuale, dopo il controllo tmpfs. La mediana ottenuta diventa la base di confronto e si registra in `LOG.md`.

### Fase due: header e CRLF scritti da DuckDB

#### `src/csvnorm/validation.py` (Modify)

- **`normalize_csv`:** nuovo parametro `crlf: bool = False`, in fondo alla firma. Due funzioni private nuove, usate dai tre punti che oggi costruiscono il `COPY` (`validation.py:355`, `405`, `427`):
  - `_select_list(normalize_names: bool) -> str`: restituisce `"*"` oppure `COLUMNS('^(?:_(k1|k2|...)|(.*))$') AS '\1\2'`, con le parole di `_DUCKDB_KEYWORD_SET` ordinate e passate per `re.escape`. Nel sorgente Python è una stringa raw, `r"..."`, così DuckDB riceve `\1\2`;
  - `_copy_options(delimiter: str, crlf: bool) -> str`: le opzioni di oggi più `NEW_LINE '\r\n'` quando `crlf` è vero. Anche qui con una stringa raw, così DuckDB riceve la sequenza `\r\n` verificata.
- **Da togliere:** `_fix_duckdb_keyword_prefix` e la sua chiamata (`validation.py:444`), `convert_row_endings_to_crlf`. Il commento a `validation.py:34` diventa «DuckDB keywords whose `_` prefix is removed in the COPY select list».
- **Verifica prima di proseguire:** su tutti i casi di riferimento con la virgola l'header è identico a oggi, e i percorsi di riserva usano la stessa espressione. Se un caso differisce, al posto di `COLUMNS` si legge l'elenco delle colonne con `DESCRIBE` sulla stessa `read_csv` e si costruisce in Python una lista esplicita `SELECT "_select" AS "select", ...`.

#### `src/csvnorm/core.py` (Modify)

- **Modifiche:**
  - `_normalize_and_refresh_errors` riceve un nuovo parametro `crlf: bool`, solo per nome, in fondo alla firma, e lo passa a `normalize_csv`;
  - la chiamata a `core.py:787-791` passa `crlf=input_has_crlf and not use_stdout`;
  - si tolgono la chiamata a `convert_row_endings_to_crlf` (`core.py:812-813`) e il relativo import.

#### `tests/test_validation.py` (Modify)

- **Modifiche:**
  - togliere l'import di `_fix_duckdb_keyword_prefix` (riga 14), `TestFixDuckdbKeywordPrefix` (righe 154-196) e i test di `convert_row_endings_to_crlf` (righe 375-410);
  - aggiungere test su `normalize_csv` per i casi coperti prima e per alcuni nuovi: parola chiave senza prefisso; `_id` conservato; `_select_1` invariato; ordine delle colonne invariato; file vuoto; virgolette raddoppiate dentro un campo; ogni delimitatore; `crlf=True` con a capo dentro le celle invariati; `crlf=False` con righe LF; `keep_names` con `SELECT *`.
  - Il caso «input già CRLF diventa doppio CR» del vecchio test non si riporta: con `NEW_LINE` DuckDB scrive un solo CRLF, e il caso `ascii_rrn` dei file di riferimento fissa il risultato.

#### `tests/test_core_helpers.py` (Modify)

- **Modifiche:** un test che controlla che `_normalize_and_refresh_errors` passi `crlf` a `normalize_csv`, sostituendo `normalize_csv` con `monkeypatch`.

#### `tests/fixtures/golden/cases.toml` (Modify)

- **Modifiche:** togliere `xfail_until = 2` da `keywords_semicolon`.

#### `scripts/bench_large.py` (Modify)

- **Modifiche:** la chiamata per fase a `normalize_csv` passa `crlf=True` quando l'input ha righe CRLF.

**Verifica della fase:** suite verde, file di riferimento identici. La mediana con `bench_large.py` va in `LOG.md`; il guadagno atteso è di circa 54 s, una stima basata sui 40 s del CRLF e sui 14 s dell'header misurati il 2026-11-22.

### Fase tre: conversione UTF-8 a blocchi e spazio su disco

#### `src/csvnorm/encoding.py` (Modify)

- **`convert_to_utf8`:** stessa firma.
  - Il controllo `codecs.lookup` resta per primo, prima di aprire qualsiasi file, così `test_unsupported_encoding` continua a ricevere `LookupError`.
  - Poi legge l'input in binario a blocchi di `CHUNK_SIZE = 4 MiB` (costante di modulo) e decodifica con `codecs.getincrementaldecoder(source_encoding)(errors="strict")`. Dopo il ciclo chiama una volta `decoder.decode(b"", final=True)`. Scrive in UTF-8 in binario.
- **Posizione dell'errore:** prima di ogni chiamata a `decode` si salva `pending = len(decoder.getstate()[0])`. Su `UnicodeDecodeError` la posizione nel file è `offset_blocco - pending + e.start`, dove `offset_blocco` è il numero di byte letti prima del blocco passato a quella chiamata; per la chiamata finale `offset_blocco` è la dimensione del file. Si assegna `e.file_offset = pos` e si rilancia la stessa eccezione.
- **Parziale:** su qualsiasi eccezione il file di output parziale si cancella prima di propagare.

#### `src/csvnorm/core.py` (Modify)

- **`_is_disk_full(exc: BaseException) -> bool`** (nuova, privata): vero per un `OSError` con `errno == errno.ENOSPC`, e per un `duckdb.Error` il cui testo contiene `"errno":"28"` oppure `No space left`.
- **`_warn_if_low_disk_space(input_path: Path, temp_dir: Path, output_dir: Optional[Path], may_convert: bool) -> None`** (nuova, privata):
  - `may_convert` vale `True` se nei primi 64 KiB dell'input c'è un byte `>= 0x80`;
  - stima lo spazio necessario: 2 volte l'input nella directory temporanea se `may_convert`, 2 volte l'input nella directory di output;
  - in modalità stdout `output_dir` è `None` e l'output provvisorio sta nella directory temporanea, quindi si somma lì;
  - se le due directory stanno sullo stesso filesystem (stesso `os.stat().st_dev`), somma le due stime;
  - se `shutil.disk_usage().free` è inferiore, mostra con `show_warning_panel` «Low disk space: about {need} MiB needed, {free} MiB free in {dir}», con numeri interi. Non si ferma.

  Si chiama in `process_csv` dopo lo scaricamento degli URL e l'estrazione degli zip (`core.py:701-722`), quando `local_input_path` è noto, e prima dello `Progress`. Per i gzip non si chiama, perché non c'è conversione e la dimensione decompressa non è nota.
- **Pannello per lo spazio esaurito:** `show_error_panel("No space left on device\n\nFree some space or set TMPDIR to another disk, then retry.")`, exit 1.
- **`_prepare_working_file`** (`core.py:464-471`): le `except` passano in questo ordine:
  - `except (UnicodeDecodeError, LookupError)` con «Encoding conversion failed», seguito, per un `UnicodeDecodeError` con `file_offset`, da «{encoding} cannot decode byte 0x{XX} at file offset {N}»;
  - `except OSError`, con il pannello dello spazio esaurito se `_is_disk_full` è vero, altrimenti «Cannot write temporary file\n{e}»;
  - `except ValueError` come oggi.
- **Gestore della normalizzazione** (`core.py:792-803`): prima degli altri controlli, se `_is_disk_full` è vero mostra il pannello. Copre anche l'esportazione degli scarti nel ramo di riserva di `normalize_csv` (`validation.py:416`).
- **`_validate_csv_with_http_handling`** (`core.py:256-310`): stesso controllo, che copre l'esportazione degli scarti di `validate_csv` (`validation.py:259`).
- **Output provvisorio:**
  - `_setup_output_paths` (`core.py:83-116`) restituisce `tuple[Path, Path, Path, Optional[Path]]`; il quarto valore è `partial_output = output.parent / f".{output.name}.csvnorm-partial"` in modalità file e `None` in modalità stdout. L'unico chiamante, `core.py:684`, spacchetta quattro valori;
  - in modalità file `normalized_file` diventa `partial_output` invece di `temp_dir / "normalized.csv"` (`core.py:778-780`), e si aggiunge a `temp_files`, così `_cleanup_temp_artifacts` lo cancella su errore e sull'uscita di `--strict`;
  - alla fine `os.replace(partial_output, actual_output_file)` sostituisce `shutil.move` (`core.py:816`), e il provvisorio esce da `temp_files`;
  - un provvisorio rimasto da un'esecuzione interrotta viene sovrascritto da DuckDB;
  - in modalità stdout non cambia nulla.

#### `tests/test_encoding.py` (Modify)

- **Modifiche:** nuovi test di `convert_to_utf8`:
  - CR isolato e CRLF dentro una cella in latin-1 passano intatti;
  - un carattere `shift_jis` spezzato fra due blocchi, con `CHUNK_SIZE` ridotto a 7 byte con `monkeypatch`, si converte correttamente;
  - un byte non decodificabile in cp1252 (0x81) a metà file dà `UnicodeDecodeError` con `file_offset` uguale alla sua posizione, e il file parziale non esiste più;
  - con `CHUNK_SIZE` di 7 byte, una sequenza `shift_jis` non valida (`0x81 0x20`) il cui primo byte chiude un blocco dà `file_offset` uguale alla posizione di `0x81`;
  - su un file con soli LF l'output è identico a quello della 1.3.0.
- **Memoria:** con la fixture `make_csv` si genera un file di circa 50 MiB in cp1252 con `0xE9` in una riga ogni cento; il picco di `tracemalloc` durante la conversione resta sotto i 24 MiB, l'obiettivo di memoria. Il conto: il blocco letto (4 MiB), la stringa decodificata (4 MiB, perché `é` sta sotto U+00FF), i byte UTF-8 da scrivere (fino a 8 MiB) e un margine.

#### `tests/test_integration.py` (Modify)

- **Modifiche:**
  - `TestOutputWrittenAtTheEnd` (righe 394-449): `test_normalization_crash_keeps_existing_output` controlla che, dopo l'errore, non resti nessun `.*.csvnorm-partial` in `tmp_path` e che il vecchio output sia intatto;
  - nuovo test per CUJ 5: con `shutil.disk_usage` che restituisce poco spazio, e `normalize_csv` sostituita da una funzione che solleva `duckdb.IOException` con `"errno":"28"`, si controlla che con `--force` compaiano l'avviso «Low disk space» e il pannello «No space left on device», che l'exit code sia 1, che il vecchio `output.csv` sia intatto e che non resti nessun `.*.csvnorm-partial`;
  - stesso controllo per la conversione, con `convert_to_utf8` che solleva `OSError(errno.ENOSPC, ...)`, e per l'esportazione degli scarti, con `validate_csv` che solleva lo stesso `duckdb.IOException`;
  - un `OSError` diverso da `ENOSPC` in conversione dà «Cannot write temporary file» ed exit 1;
  - un `UnicodeDecodeError` in conversione dà «Encoding conversion failed» con la posizione nel file.
  - `TestCrlfPreservation` (righe 347-391) resta e deve passare senza modifiche.

#### `tests/fixtures/golden/cases.toml` e `tests/fixtures/golden/expected/` (Modify)

- **Modifiche:**
  - togliere `xfail_until = 3` da `cp1252_cr_in_cell` e `latin1_crlf_in_cell`;
  - per `cp1252_rrn`, `cp1252_cr_only` e `cp1252_mixed_endings` si confronta il nuovo output con quello della 1.3.0, si aggiornano i file attesi se cambiano e si scrive il motivo in `LOG.md`.

#### `tests/test_core_helpers.py` (Modify)

- **Modifiche:** test diretti di `_is_disk_full` con un `OSError` `ENOSPC`, un `OSError` di altro tipo, un `duckdb.Error` con `"errno":"28"`, uno con `No space left` e uno senza nessuno dei due.

**Verifica della fase:** suite verde, output identici ai file attesi, aggiornati come sopra. La nuova mediana va in `LOG.md`.

### Fase quattro: rilevamento dell'encoding

#### `src/csvnorm/encoding.py` (Modify)

- **Costanti di modulo:**
  - `SCAN_CHUNK = 4 MiB`;
  - `MAX_WINDOWS = 129`: una finestra per il primo errore UTF-8 più al massimo 128 valori di byte;
  - `WINDOW_HALF = 256`: byte per lato;
  - `MAX_CUT_SEARCH = 64`: byte per lato oltre la mezza finestra;
  - `CUT_BYTES`: l'insieme dei byte `< 0x40` esclusi `0x30-0x39`.

  Il campione è al massimo 129 × (2 × (256 + 64)) byte, cioè circa 81 KiB.
- **`_ScanResult`** (`NamedTuple`, privato), con cinque campi:
  - `route: Literal["ascii", "utf-8", "full", "sample"]`;
  - `reason: str`;
  - `sample: bytes`;
  - `windows: int`;
  - `high_values: int`.

  Valori di `reason` per `route="full"`: `"utf-16/32 bom"`, `"nul byte"`, `"utf-8 bom with invalid utf-8"`, `"no cut point for byte 0xXX"`.
- **`_scan(path) -> _ScanResult`**, le due passate.
  - **Primi 4 byte.**
    - Un BOM UTF-32 (`FF FE 00 00`, `00 00 FE FF`) o UTF-16 (`FF FE`, `FE FF`) dà `full`.
    - Un BOM UTF-8 (`EF BB BF`) si ricorda.
    - Un file vuoto dà `utf-8`.
  - **Prima passata,** a blocchi di `SCAN_CHUNK`, con un decoder UTF-8 incrementale stretto.
    - `b"\x00" in chunk` dà `full`.
    - Se tutti i blocchi sono `isascii()`: `ascii`, oppure `utf-8` se c'era il BOM.
    - Se la decodifica finisce senza errori: `utf-8`, anche con il BOM, come oggi (verificato su `test/utf8_sig_bom.csv` il 2026-11-22).
    - Al primo errore si ricorda la sua posizione nel file; con il BOM si va a `full`, altrimenti alla seconda passata.
  - **Seconda passata,** a blocchi, dall'inizio del file.
    - In ogni blocco si controlla prima `b"\x00" in chunk`, che dà `full`: copre i file binari che iniziano con un byte non UTF-8, come `test/binary_file.bin` (`0x89` al byte 0, NUL al byte 8).
    - Poi si trovano i valori alti nuovi con `set(chunk.translate(None, ASCII_BYTES))`, dove `ASCII_BYTES = bytes(range(128))`: un'operazione in C.
    - Per ogni valore nuovo, la prima posizione si trova con `chunk.find(bytes([v]))`.
    - Per la posizione del primo errore UTF-8 e per ogni valore nuovo si ritaglia una finestra:
      - il punto di partenza è `WINDOW_HALF` byte prima e quello di arrivo `WINDOW_HALF` byte dopo;
      - verso l'esterno, per al massimo `MAX_CUT_SEARCH` byte per lato, si cerca un byte di `CUT_BYTES`; la finestra comincia subito dopo quello a sinistra e finisce subito dopo quello a destra;
      - l'inizio e la fine del file valgono come punti di taglio.
    - Le finestre che non si possono completare perché toccano la fine del blocco restano in sospeso fino al blocco successivo. Si tiene una coda di `WINDOW_HALF + MAX_CUT_SEARCH` byte da entrambi i lati.
    - Se una finestra non trova un punto di taglio, quel valore resta senza finestra e si riprova alla sua occorrenza successiva. Un valore entra fra quelli coperti solo quando ha una finestra accettata.
    - Le finestre sovrapposte si uniscono. Il `sample` è l'unione delle finestre separate da `b"\n"`.
    - A fine file, se un valore visto non ha nessuna finestra, la strada è `full` con `reason="no cut point for byte 0xXX"`. Altrimenti è `sample`.
    - Proprietà risultante: con `route="sample"`, ogni valore di byte alto del file compare in almeno una finestra.
- **`_pick_encoding(result: CharsetMatches) -> str`:** lo spareggio di oggi (`encoding.py:61-74`), estratto senza modifiche. Solleva `ValueError("Cannot detect encoding for: ...")` se `result.best()` è `None`.
- **`_detect_encoding_full(path) -> str`:** il rilevamento di oggi, cioè `from_path`, `_pick_encoding` e `normalize_encoding_name`. È privato.
- **`detect_encoding(file_path) -> str`:** stessa firma e stessi valori restituiti.
  - Chiama `_scan` e registra `Encoding route: <route> (<reason>)`, oppure `Encoding route: sample (N windows, M byte values)`, con `logger.debug` sul logger `csvnorm`.
  - Con `ascii` o `utf-8` restituisce quel valore. Con `full` chiama `_detect_encoding_full`.
  - Con `sample` chiama `from_bytes(sample, steps=1, chunk_size=len(sample), cp_exclusion=["utf_8", "ascii"])`, poi `_pick_encoding` e `normalize_encoding_name`.
  - Secondo `api.py:130-139`, con `steps=1, chunk_size=len(sample)` la libreria esamina il campione come un solo pezzo. Sotto i 10 MB decodifica in modo stretto l'intero campione per ogni candidato e scarta quelli che falliscono (`api.py:349-391`).
- **`detect_and_convert(input_path: Path, output_path: Path, on_detected: Callable[[str], None] | None = None) -> str`** (nuova, non esportata in `__init__.py`).
  - Chiama `detect_encoding` e, se c'è, `on_detected(encoding)`.
  - Se `needs_conversion(encoding)`, chiama `convert_to_utf8`.
  - Su `UnicodeDecodeError`, intercettato prima di qualsiasi `ValueError`: registra `Encoding fallback: full detection after conversion error` a livello debug, chiama `_detect_encoding_full`, richiama `on_detected` e riconverte una sola volta.
  - Un secondo `UnicodeDecodeError` si propaga. `LookupError` e `ValueError` di rilevamento si propagano senza ricaduta.
  - Restituisce la codifica usata.

#### `src/csvnorm/core.py` (Modify)

- **`_handle_local_encoding`:** conserva nome e firma, così i 5 test di `tests/test_core_helpers.py` che la sostituiscono (righe 71-190 circa) restano validi.
  - Chiama `detect_and_convert(file_input_path, temp_utf8_file, on_detected=...)`. La funzione `on_detected` aggiorna l'avanzamento con «Detected encoding: X» e, se serve la conversione, «Converting from X to UTF-8...», come oggi.
  - Se `needs_conversion(encoding)` sulla codifica restituita, `working_file` diventa `temp_utf8_file` e si aggiunge a `temp_files`; altrimenti resta l'input, come oggi.
- **Import:** a `core.py:18` si tolgono `convert_to_utf8` e `detect_encoding`, che non si usano più, e si aggiunge `detect_and_convert`. `needs_conversion` resta.

#### `scripts/bench_large.py` (Modify)

- **Modifiche:** nella misura per fase, `detect_and_convert` sostituisce `detect_encoding` più `convert_to_utf8`.

#### `tests/test_encoding.py` (Modify)

- **Modifiche:** i test di rilevamento esistenti (`tests/test_encoding.py:59-138`) restano invariati e devono passare. Nuovi test, con i file generati dalla fixture `make_csv`:
  - un file ASCII di 200.000 righe con un solo `0xE9` a metà dà uno fra `cp1252`, `latin-1` e `iso8859-15`, e la conversione restituisce `é`;
  - lo stesso, con il byte solo nell'ultima riga e senza a capo finale, cioè CUJ 2;
  - un file UTF-8 con `’` (E2 80 99) all'inizio e una riga successiva con un solo `0x92`: il risultato non è `utf-8` e la conversione restituisce `’` per lo `0x92`;
  - un file con `0x81` presente: il risultato non è `cp1252`;
  - `test/binary_file.bin` dà `ValueError` con la strada `full` e il motivo `nul byte`;
  - i BOM UTF-16 e UTF-32 prendono la strada `full`;
  - un BOM UTF-8 dà `utf-8`; un file vuoto dà `utf-8`;
  - un file `shift_jis` di 2 MiB, fatto con `body`, dà `shift-jis` oppure `cp932`, e ogni finestra del campione si decodifica in `shift_jis` in modo stretto;
  - due chiamate sullo stesso file danno lo stesso campione;
  - parametri di `from_bytes`: un campione di 4 KiB tutto `0xE9` più un solo `0x81` dopo il byte 3.000, passato con `steps=1, chunk_size=len(sample)`, non contiene `cp1252` fra i risultati. Se lo contiene, la libreria non si comporta come letto in `api.py:130-139`: la fase si ferma e decide l'autore;
  - ricaduta: su un file cp1252 con `0xFD`, che in `shift_jis` non è definito, con `csvnorm.encoding.detect_encoding` sostituito da una funzione che restituisce `shift-jis`, `detect_and_convert` chiama `_detect_encoding_full` una volta, la seconda conversione riesce e la codifica restituita è uno fra `cp1252`, `latin-1` e `iso8859-15`;
  - i messaggi `Encoding route:` attesi compaiono in `caplog` al livello `DEBUG` del logger `csvnorm`.

#### `tests/test_encoding_equivalence.py` (Modify)

- **Modifiche:** per ogni file in cui il nuovo rilevamento differisce da oggi si aggiorna `EXPECTED` con la codifica attesa e il motivo in un commento. Ogni differenza va verificata a mano.

#### `tests/fixtures/golden/expected/` (Modify)

- **Modifiche:** se una differenza di codifica cambia l'output di un caso di riferimento, si rigenera quel file atteso e si scrive il motivo in `LOG.md`. Alla fine nessun caso ha più `xfail_until`.

#### `openspec/changes/speed-up-large-files/specs/encoding-detection/spec.md` (Modify)

- **Modifiche:** per ogni voce cambiata in `EXPECTED` si aggiunge o si corregge uno scenario.

**Verifica della fase:** suite verde, test di equivalenza verde, mediana finale in `LOG.md`.

### Fase cinque, condizionale: validazione e normalizzazione in un solo `COPY`

- **Condizione:** si apre solo se la mediana dopo la fase quattro resta sopra i 60 s.
- **Se si apre:** prima di scrivere codice si aggiunge a questo documento un piano dettagliato, perché la fase cambia l'ordine di messaggi ed exit code e il comportamento di `--strict`.
- **Se non si apre:** la fase si chiude come non necessaria, con la misura in `LOG.md`.

### Fase sei: documentazione e rilascio

#### `README.md` (Modify)

- **Modifiche:** la sezione «Encoding detection limits» (`README.md:187`) descrive il nuovo rilevamento. Si aggiunge che i fine riga dei file non UTF-8 ora si conservano, che la correzione dell'header vale per ogni delimitatore e che, se il disco si riempie, l'output esistente resta intatto.

#### `CLAUDE.md` (Modify)

- **Modifiche:** la sezione Architecture si allinea:
  - `detect_encoding`, `detect_and_convert`, `convert_to_utf8` e il flusso;
  - il numero di test, preso da `uv run pytest tests/ --collect-only -q | tail -1`;
  - un rimando a `scripts/bench_large.py`.

#### `PRD.md` (Modify)

- **Modifiche:**
  - FR-2 (`PRD.md:42`) cita UTF-8 stretto, il campione di finestre non ASCII e la ricaduta sul rilevamento completo;
  - NFR-2 (`PRD.md:55`) diventa «On local file input with file output, Python passes stay under 24 MiB of memory whatever the file size. Excluded: DuckDB, stdin input, stdout output, `--fix-mojibake`, and the full-detection route (UTF-16/32 BOM, UTF-8 BOM with invalid UTF-8, NUL bytes, high bytes without a cut point, conversion fallback)».

#### `LOG.md` (Modify)

- **Modifiche:** la voce di rilascio riassume le fasi; le voci di fase sono già state scritte.

#### `openspec/changes/add-input-encoding-option/proposal.md` (Modify)

- **Modifiche:** la sezione «Why» si aggiorna con i casi che il nuovo rilevamento ha cambiato, misurati nella fase quattro.

#### `tasks/todo.md` (Modify)

- **Modifiche:** il piano a fasi con le verifiche, spuntato a ogni avanzamento. Nella voce di «Prossimi passi» a `tasks/todo.md:12` l'inciso «misure di memoria e prestazioni» si toglie e si sostituisce con un rimando a questo lavoro.

#### `pyproject.toml` (Modify)

- **Modifiche:** versione `1.4.0`, perché il comportamento visibile cambia. La versione vive solo in `pyproject.toml` e si legge con `importlib.metadata` (`cli.py:11`, `39`). Si seguono `DEPLOYMENT.md` e la lista di controllo pre-rilascio di `CLAUDE.md`. Le note di rilascio citano il nuovo parametro `crlf` di `normalize_csv` (API pubblica, facoltativo, in fondo alla firma).

#### `openspec/changes/speed-up-large-files/` (archiviato dopo il rilascio)

- **Comando:** `openspec archive speed-up-large-files --yes`, che aggiorna le spec di base `encoding-detection`, `processing-pipeline`, `error-handling` e `output-location`.

### Piano di verifica

- **Test:** `uv run pytest tests/ -v` alla fine di ogni fase.
- **Lint e tipi:** `uv run ruff check src tests` e `uv run mypy src`.
- **Copertura:** `uv run pytest --cov=csvnorm.encoding --cov-fail-under=90 tests/` per il modulo del rilevamento; per `validation.py` e `core.py` la copertura non deve scendere rispetto alla misura della fase uno (`uv run pytest --cov=csvnorm --cov-report=term`).
- **Contratto:** `tests/test_golden.py` verde, senza `xfail_until` rimasti nel manifesto.
- **Prestazioni:** `scripts/bench_large.py tmp/comuni_giornaliero_30settembre26.csv`, mediana di tre esecuzioni dopo un riscaldamento. Obiettivo sotto i 60 s; soglia di rilascio almeno 3 volte più veloce della base misurata nella fase uno.
- **Rilascio:** `uv tool install --reinstall --force .`, poi `csvnorm -v`, poi una prova sul file da 826 MB, controllando che non restino né temporanei né file `.csvnorm-partial`.
