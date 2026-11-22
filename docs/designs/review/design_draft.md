# csvnorm veloce sui file grandi

* **Autore:** aborruso
* **Stato:** Draft
* **Data:** 2026-11-22

---

## Indice

- Overview
- Il problema
- Obiettivi
- Non obiettivi
- Domande aperte
- Percorsi utente (CUJ)
- Piano tecnico
- Alternative considerate
- Miglioramenti futuri
- Piano di implementazione dettagliato

## Overview

csvnorm valida e normalizza CSV con un percorso fatto di passaggi Python e di due letture DuckDB. Sui file piccoli il costo dei passaggi Python non si vede. Sui file da centinaia di MB domina: un CSV cp1252 da 826 MB richiede circa 220 s, e due terzi del tempo vanno in lavoro Python che legge o riscrive il file intero più volte.

Questo design rende veloce il percorso normale, senza aggiungere una modalità per i file grandi. Il principio è togliere passaggi dove DuckDB può fare lo stesso lavoro mentre scrive l'output, e far lavorare a blocchi quelli che restano in Python. La validazione resta completa: ogni riga viene controllata. Il lavoro corregge anche due difetti esistenti che toccano le stesse funzioni.

## Il problema

Misure del 2026-11-22 su `tmp/comuni_giornaliero_30settembre26.csv` (826 MB, 5,4 milioni di righe, 57 colonne, cp1252, righe CRLF), WSL2, una esecuzione per fase:

| Fase | Tempo | Dove |
| --- | --- | --- |
| Rilevamento encoding, `charset_normalizer` sull'intero file | 106 s | `src/csvnorm/encoding.py` `detect_encoding` |
| Conversione delle righe in CRLF, ciclo byte per byte | 40 s | `src/csvnorm/validation.py` `convert_row_endings_to_crlf` |
| Normalizzazione, `COPY` DuckDB | 24 s | `src/csvnorm/validation.py` `normalize_csv` |
| Validazione, `read_csv` DuckDB con `store_rejects` | 19 s | `src/csvnorm/validation.py` `validate_csv` |
| Riscrittura dell'intero output per correggere l'header | 14 s | `src/csvnorm/validation.py` `_fix_duckdb_keyword_prefix` |
| Conversione in UTF-8, file letto tutto in memoria | 10-14 s | `src/csvnorm/encoding.py` `convert_to_utf8` |
| Conteggio righe e colonne | 3 s | `src/csvnorm/utils.py` |

Quattro problemi ne derivano:

- **Tempo.** Circa 160 s su 220 vanno in passaggi Python che rileggono o riscrivono tutto il file. DuckDB pesa circa 45 s.
- **Memoria.** Conversione UTF-8, correzione dell'header e passaggio CRLF caricano l'intero file in RAM. Per 826 MB il picco è di alcuni GB.
- **Disco.** Il percorso usa un temporaneo UTF-8 grande quanto l'input. Durante le prove il disco si è riempito e la normalizzazione è fallita con «No space left on device».
- **Due difetti esistenti, nelle stesse funzioni.**
  - `convert_to_utf8` apre i file in modalità testo senza `newline=""`. Per i file non UTF-8 i CR dentro le celle diventano LF, e su Windows l'output cambia rispetto a Linux.
  - La correzione dei prefissi delle parole chiave nell'header riconosce solo la virgola come separatore. Con `-d ';'` non fa nulla.

La soluzione proposta in breve:

- rilevamento dell'encoding con una decodifica UTF-8 stretta sull'intero file e, solo se fallisce, `charset_normalizer` su un campione costruito attorno ai byte non ASCII;
- CRLF scritto da DuckDB con `NEW_LINE '\r\n'`, header corretto da DuckDB con alias nella `SELECT`;
- conversione UTF-8 a blocchi, conservando CR e CRLF.

## Obiettivi

- **Tempo:** sul file da 826 MB, mediana di tre esecuzioni dopo un riscaldamento, sotto i 60 s, contro circa 220 s di oggi. Misura con un protocollo ripetibile e tempi per fase visibili con `--verbose`.
- **Memoria:** nessun passaggio Python del percorso su file locale tiene in memoria più di un blocco di dimensione fissa (ordine di qualche MB), escluso DuckDB.
- **Disco:** come oggi, al massimo due copie temporanee grandi quanto l'input per i file non UTF-8 (`utf8.csv` e `normalized.csv`) e una per quelli UTF-8. I temporanei si cancellano anche in caso di errore, e `scripts/bench_large.py` controlla lo spazio libero prima di partire.
- **Correttezza dell'encoding:** il nuovo rilevamento dà lo stesso risultato di quello attuale su tutti i file di `tests/` e `test/`, e non produce mai in silenzio un risultato più debole: un file con byte non ASCII solo a metà o in fondo viene riconosciuto come oggi.
- **Validazione completa:** ogni riga resta controllata, il file degli scarti contiene le stesse righe di oggi.
- **Output:** identico byte per byte alla release 1.3.0 su Linux su un insieme di file di riferimento dichiarato, tranne le due correzioni decise, ciascuna con un test proprio:
  - i CR e i CRLF dentro le celle dei file non UTF-8 restano come nell'input;
  - la correzione dei prefissi delle parole chiave nell'header funziona con ogni delimitatore;
  - nei file in cui il nuovo rilevamento sceglie una codifica migliore di quella di oggi, l'output segue la codifica nuova. Ogni caso è elencato con il motivo in `tests/test_encoding_equivalence.py` e fissato da un test.
- **Contratto invariato:** exit code 0/1/2, input mai sovrascritto, API pubblica `detect_encoding` con la stessa firma.

## Non obiettivi

- **Cambiare libreria**, per esempio Polars: DuckDB pesa circa 45 s su 220, il costo sta altrove.
- **Una modalità per i file grandi**: sarebbero due percorsi da mantenere e testare.
- **Validazione a campione**: requisito dell'autore, nessuna riga malformata deve sfuggire.
- **Memoria limitata per stdin, output su stdout e `--fix-mojibake`**: oggi leggono l'intero file e continuano a farlo. Il guadagno di tempo vale anche per loro dove passano dalle stesse funzioni.
- **Velocizzare l'input gzip**: non passa da rilevamento e conversione.
- **Aggiungere `--encoding`**: è la proposta separata `openspec/changes/add-input-encoding-option`.

## Domande aperte

Nessuna aperta. Le domande emerse durante la stesura sono state decise il 2026-11-22 e sono riportate in «Decisioni prese per questo piano», all'inizio del piano di implementazione dettagliato.

## Percorsi utente (CUJ)

### CUJ 1: file grande non UTF-8 in modalità file

- **Dato** un CSV cp1252 locale da circa 800 MB con righe CRLF e 6 GB di disco libero.
- **Quando** l'utente lancia `csvnorm input.csv -o output.csv`.
- **Allora** csvnorm finisce in meno di 60 s, l'output è UTF-8 con righe CRLF e header in snake_case, la tabella finale riporta encoding cp1252 e il conteggio di righe e colonne, l'exit code è 0, e a fine lavoro non restano temporanei.

### CUJ 2: byte non ASCII solo in fondo al file

- **Dato** un CSV di 500 MB in ASCII puro tranne una riga, vicino alla fine, con un carattere cp1252 accentato.
- **Quando** l'utente lancia `csvnorm input.csv -o output.csv`.
- **Allora** csvnorm riconosce cp1252, come fa oggi analizzando tutto il file, converte la riga correttamente e non la manda fra gli scarti.

### CUJ 3: CR dentro una cella di un file non UTF-8

- **Dato** un CSV latin-1 con un campo quotato che contiene `\r\n`.
- **Quando** l'utente lo normalizza su Linux e poi su Windows.
- **Allora** il campo arriva nell'output con `\r\n` intatto, e i due output sono identici byte per byte.

### CUJ 4: header con parole chiave e delimitatore punto e virgola

- **Dato** un CSV con colonne `select` e `_id`.
- **Quando** l'utente lancia `csvnorm input.csv -d ';' -o output.csv`.
- **Allora** l'header dell'output è `select;_id`, senza il prefisso `_` aggiunto da DuckDB alla parola chiave, e `_id` resta invariato.

### CUJ 5: disco pieno durante la conversione

- **Dato** un disco che si riempie a metà della conversione UTF-8.
- **Quando** csvnorm sta scrivendo il temporaneo.
- **Allora** compare un pannello d'errore che indica lo spazio esaurito, l'exit code è 1, il temporaneo parziale viene cancellato e l'input resta intatto.

## Piano tecnico

### Flusso, prima e dopo

Oggi, per un file locale non UTF-8 con righe CRLF, in modalità file:

```text
input.csv
  │  detect_encoding: charset_normalizer sull'intero file ............ 106 s
  ▼
  │  convert_to_utf8: tutto in memoria, modalità testo ................ 10-14 s
  ▼
utf8.csv (temporaneo)
  │  validate_csv: DuckDB read_csv con store_rejects .................. 19 s
  │  normalize_csv: DuckDB COPY ........................................ 24 s
  ▼
normalized.csv (temporaneo)
  │  _fix_duckdb_keyword_prefix: rilegge e riscrive tutto ............. 14 s
  │  convert_row_endings_to_crlf: byte per byte in memoria ............ 40 s
  ▼
output.csv
```

Dopo:

```text
input.csv
  │  detect_encoding: decodifica UTF-8 stretta a blocchi;
  │  solo se fallisce, charset_normalizer su un campione
  ▼
  │  convert_to_utf8: a blocchi, CR e CRLF conservati
  ▼
utf8.csv (temporaneo)
  │  validate_csv: invariato
  │  normalize_csv: un solo COPY che scrive
  │    - l'header già corretto (alias nella SELECT)
  │    - le righe CRLF se l'input era CRLF (NEW_LINE)
  ▼
output.csv
```

Spariscono due passaggi Python che leggono e riscrivono tutto il file. Gli altri due lavorano a blocchi di dimensione fissa. Le due letture DuckDB restano come sono.

### Rilevamento dell'encoding

`detect_encoding(file_path)` conserva firma e valori restituiti di oggi: `"utf-8"`, `"utf-8-sig"`, `"ascii"` o il nome normalizzato di un'altra codifica.

Un solo passaggio sul file, a blocchi (per esempio 4 MB), raccoglie tre informazioni:

- **BOM UTF-8** nei primi 3 byte.
- **Validità UTF-8:** il blocco passa per un decoder UTF-8 incrementale e stretto (`codecs.getincrementaldecoder("utf-8")`), che gestisce i caratteri multibyte spezzati fra due blocchi. Il passaggio si ferma al primo errore.
- **Presenza di byte non ASCII** (`bytes.isascii()` sul blocco).

Poi si decide così:

- se c'è il BOM e il resto è UTF-8 valido, il risultato è `utf-8-sig`;
- se tutto è ASCII, il risultato è `ascii`;
- se tutto è UTF-8 valido, il risultato è `utf-8`;
- se la decodifica UTF-8 fallisce, si costruisce un **campione mirato**. Comprende l'inizio del file (per esempio 64 KB) e finestre di qualche KB attorno alle sequenze di byte `>= 0x80` trovate in tutto il file, distribuite lungo il file fino a un budget fisso (per esempio 1 MB). Le finestre si allineano a inizio riga. La selezione è deterministica: niente posizioni casuali, quindi due esecuzioni sullo stesso file danno lo stesso risultato. Il campione va a `charset_normalizer.from_bytes`, con lo stesso criterio di spareggio di oggi (coerenza più alta fra i meno caotici, preferenza per le codifiche occidentali in caso di pari merito).

Il punto debole resta quest'ultimo caso: il verdetto di `charset_normalizer` su un campione può differire da quello sull'intero file. Lo mitigano due cose:

- il campione contiene proprio i byte che distinguono le codifiche, cioè quelli non ASCII, e non pezzi presi a caso che possono essere tutti ASCII;
- la conversione successiva è stretta: se la codifica scelta non sa decodificare un byte del file, la conversione fallisce. csvnorm cancella allora il parziale, ripete il rilevamento come oggi con `from_path` sull'intero file e riconverte una sola volta.

Il caso che nessuna delle due mitigazioni copre è una codifica a un byte sbagliata che decodifica comunque tutti i byte, per esempio cp1250 al posto di cp1252. Oggi è protetto dallo spareggio sull'intero file. Con il campione mirato lo spareggio lavora sugli stessi byte significativi, ma va dimostrato con i test di `tests/test_encoding.py` e con un confronto sistematico fra vecchio e nuovo rilevamento su tutti i file di prova.

Con `--verbose` il log dice quale strada è stata presa (UTF-8 valido, ASCII, campione di N byte da M finestre, ritorno all'intero file e perché).

### Conversione in UTF-8

`convert_to_utf8(input_path, output_path, source_encoding)` conserva la firma. Cambia l'interno:

- lettura in binario a blocchi, decodifica con un decoder incrementale stretto della codifica sorgente, scrittura in UTF-8 in binario;
- niente modalità testo, quindi CR, LF e CRLF passano intatti, anche dentro le celle, e l'output è lo stesso su Linux e Windows (correzione decisa);
- in caso di errore (decodifica, disco pieno) il file parziale viene cancellato prima di propagare l'eccezione.

La posizione riportata da un `UnicodeDecodeError` diventa relativa al blocco: la funzione la riporta alla posizione nel file prima di propagarla, così il pannello d'errore resta leggibile.

### Header e CRLF scritti da DuckDB

`normalize_csv` costruisce oggi il `COPY` in tre punti (percorso normale, ritorno alle configurazioni di riserva, `strict_mode=false`). I tre punti passano a usare due elementi comuni.

- **Elenco delle colonne.** Con `normalize_names=True`, al posto di `SELECT *` si usa una sola espressione:

  ```sql
  SELECT COLUMNS('^(?:_(select|from|...)|(.*))$') AS '\1\2' FROM read_csv(...)
  ```

  L'alternanza contiene le parole di `_DUCKDB_KEYWORD_SET`. Una colonna che DuckDB ha rinominato in `_select` esce come `select`. Tutte le altre, compresa una `_id` scritta dall'utente, escono invariate. L'ordine delle colonne resta quello del file. Verificato il 2026-11-22 con DuckDB 2.0.0: un header `select,_id,From,a b,_select` con `-d ';'` dà `select;_id;from;a_b;_select_1`. La regola vale per ogni delimitatore, perché lavora sui nomi delle colonne e non sul testo dell'header (correzione decisa). Con `--keep-names` resta `SELECT *`.
- **Opzioni del COPY.** Si aggiunge `NEW_LINE '\r\n'` quando l'input aveva righe CRLF e l'output va su file. Verificato il 2026-11-22: gli a capo dentro le celle quotate restano invariati (`"a\nb"` resta così, `"d\r\ne"` resta così).

`normalize_csv` riceve un nuovo parametro facoltativo, `crlf: bool = False`. Le chiamate esistenti all'API pubblica continuano a funzionare. `core.py` lo valorizza con `input_has_crlf and not use_stdout`, la stessa condizione di oggi.

`_fix_duckdb_keyword_prefix` e `convert_row_endings_to_crlf` non vengono più chiamate e si tolgono, insieme ai loro test. I test di comportamento equivalenti si spostano sull'output di `normalize_csv` e della CLI.

### Spazio su disco e temporanei

- Il percorso usa ancora due file temporanei grandi quanto l'input: `utf8.csv` e `normalized.csv`, quest'ultimo spostato sull'output alla fine. Oggi le due riscritture Python ne aggiungono altri in memoria. Dopo, al picco ci sono input, `utf8.csv` e `normalized.csv`, come oggi, senza il terzo passaggio.
- I temporanei restano nella directory temporanea di oggi e la pulizia resta in `_cleanup_temp_artifacts`. La conversione cancella da sola il proprio parziale in caso di errore.

### Cosa non cambia

- Validazione con DuckDB: stessa query, stesso file degli scarti.
- Gzip, zip, URL remoti, stdin: passano dalle stesse funzioni e guadagnano tempo dove le usano, ma lo stdin resta letto tutto in memoria (`core.py:662`).
- Output su stdout: nessun CRLF, come oggi. La lettura del temporaneo con `f.read()` a `core.py:359-360` resta.
- `--fix-mojibake`: ftfy lavora sull'intero testo, come oggi.
- Exit code e messaggi, tranne il testo di avanzamento del rilevamento, che con `--verbose` dice quale strada è stata presa.

## Alternative considerate

### Cambiare libreria, per esempio Polars

- **Pro:** lettura parallela e a blocchi, API moderna.
- **Contro:** DuckDB pesa circa 45 s su 220. Il costo sta nei passaggi Python attorno, che Polars non tocca. Bisognerebbe riscrivere validazione e file degli scarti, che si basano su `store_rejects` di DuckDB.
- **Motivo dello scarto:** scartata dall'autore, perché le misure mostrano che il collo di bottiglia non è la lettura del CSV.

### Modalità separata per i file grandi

- **Pro:** nessun rischio per il percorso dei file piccoli.
- **Contro:** due percorsi da mantenere e testare, e un'opzione che l'utente deve conoscere. I passaggi lenti sono lenti per tutti i file, quindi correggerli nel percorso unico basta.
- **Motivo dello scarto:** scartata dall'autore.

### Validazione a campione

- **Pro:** risposta rapida anche sui file enormi.
- **Contro:** le righe malformate nelle zone non lette sfuggono. La validazione costa 19 s e non è il collo di bottiglia.
- **Motivo dello scarto:** scartata dall'autore: nessuna riga malformata deve sfuggire.

### Rinunciare al CRLF in output

- **Pro:** toglie un passaggio.
- **Contro:** perde la fedeltà all'input. L'RFC 4180 indica CRLF, anche se è di tipo Informational e la bozza rfc4180-bis ammette CR, LF e CRLF.
- **Motivo dello scarto:** scartata dall'autore. Il CRLF si tiene e lo scrive DuckDB con `NEW_LINE`, senza costo aggiuntivo.

### Rilevamento su blocchi casuali, con ritorno all'intero file solo se la conversione fallisce

- **Pro:** semplice, costo fisso.
- **Contro:** il ritorno non scatta nei casi pericolosi. `latin_1` decodifica qualsiasi byte e cp1252 fallisce solo su cinque. Una scelta sbagliata fra codifiche a un byte converte senza errori e produce testo alterato con exit 0. Se i blocchi sono tutti ASCII, il verdetto è `ascii`, la conversione non parte e i byte accentati successivi finiscono fra gli scarti.
- **Motivo dello scarto:** scartata dall'autore, perché un errore passerebbe in silenzio. Al suo posto: UTF-8 stretto sull'intero file e campione mirato sui byte non ASCII.

### CRLF e header riscritti in Python a blocchi

- **Pro:** non dipende da opzioni di DuckDB e conserva esattamente la logica di oggi.
- **Contro:** resta una lettura e una scrittura in più dell'intero output, e un secondo file temporaneo grande quanto l'output. Il codice di parità delle virgolette fra blocchi va scritto e testato.
- **Motivo dello scarto:** scartata con l'approvazione del piano tecnico da parte dell'autore, perché DuckDB 2.0.0 fa entrambe le cose durante il `COPY`: `NEW_LINE '\r\n'` e la rinomina con `COLUMNS(...) AS`. Entrambe verificate il 2026-11-22.

### DuckDB che legge direttamente l'originale con `encoding='latin-1'`

- **Pro:** elimina la conversione e il temporaneo UTF-8, quando nel file non ci sono byte 0x80-0x9F e cp1252 coincide con latin-1.
- **Contro:** è un secondo percorso valido solo per alcune codifiche. Per le altre servirebbe un'estensione DuckDB scaricata dalla rete, che rompe l'uso offline.
- **Motivo dello scarto:** non adottata in questo design, proposta emersa dalla revisione e mai discussa con l'autore. Da riconsiderare se, dopo questo lavoro, la conversione resta un costo rilevante.

### Validazione e normalizzazione in un solo `COPY`

- **Pro:** una lettura completa in meno, circa 19 s (stima). Ogni riga resta controllata grazie a `store_rejects`.
- **Contro:** cambia l'ordine di messaggi ed exit code. Con `--strict` l'output verrebbe scritto per poi essere buttato.
- **Motivo dello scarto:** non ancora decisa: è fra le domande aperte. Si valuta come ultima fase, se i 60 s non si raggiungono.

## Miglioramenti futuri

- **Una sola copia temporanea per i file compatibili con latin-1.** Quando nel file non ci sono byte 0x80-0x9F, cp1252 e latin-1 coincidono e DuckDB potrebbe leggere l'originale con `encoding='latin-1'`, senza `utf8.csv`. Risparmio di circa una copia del file e della conversione. Il file da 826 MB del 2026-11-22 rientra nel caso: nessun byte 0x80-0x9F, undici valori non ASCII, tutte vocali accentate. Da verificare prima: che DuckDB 2.0.0 legga `latin-1` senza estensioni esterne e quanto costi la decodifica in lettura, fatta due volte (validazione e normalizzazione). Escluso con `--fix-mojibake` e con le altre codifiche. Da valutare con la base e i tempi per fase misurati da questo lavoro. Va messo in cima se i file grandi abituali sono quasi sempre di questo tipo.

## Piano di implementazione dettagliato

### Decisioni prese per questo piano (2026-11-22)

- **Validazione e normalizzazione in un solo `COPY`:** fase condizionale. Si fa solo se, finite le altre fasi, la mediana sul file da 826 MB resta sopra i 60 s.
- **Ordine:** questo lavoro va prima di `add-input-encoding-option`, la cui proposta andrà aggiornata dopo.
- **Soglia:** si rilascia comunque se il miglioramento è di almeno 3 volte rispetto alla base misurata nella fase uno. Con la base stimata a 220 s, la soglia sarebbe 73 s. I 60 s restano l'obiettivo dichiarato.
- **Interruttore per il rilevamento completo:** nessuno. La via d'uscita sarà `--encoding`.
- **`preserve-crlf-line-endings`:** si archivia prima, come passo zero.
- **Caso `\r\r\n`:** oggi `a,b\r\r\n1,2\r\r\n` dà `a,b\r\n1,2\r\n` (misurato il 2026-11-22 con la 1.3.0). Diventa un file di riferimento.
- **Rilevamento rispetto a oggi:** il nuovo rilevamento deve dare lo stesso risultato di oggi su ogni file di prova, oppure uno migliore, con la differenza documentata e un test che la fissa. Il caso «200.000 righe ASCII più un byte latin-1», che oggi dà cp1006 secondo la proposta `--encoding`, si misura e si registra com'è.

Ogni fase è un commit, o una serie di commit, con i suoi test. La suite intera passa alla fine di ogni fase. Si torna indietro con un revert, perché non c'è stato persistente.

### Fase zero: archiviare `preserve-crlf-line-endings`

#### `openspec/changes/preserve-crlf-line-endings/tasks.md` (Modify, poi archiviato)

- **Ambito:** documentazione OpenSpec.
- **Modifiche:** si verificano una per una le 9 voci sul codice e sui test, con riferimento a commit `107e8e2` e `0c7b8d8`, e si spuntano. Una voce non verificabile resta aperta e blocca l'archiviazione: in quel caso se ne parla prima di andare avanti.
- **Perché:** la change è implementata ma non archiviata, e il delta di questo lavoro deve partire da una spec di base aggiornata.

#### `openspec/specs/output-location/spec.md` (Modify, tramite `openspec archive`)

- **Ambito:** spec di base.
- **Modifiche:** riceve i requisiti CRLF della change archiviata. La cartella della change si sposta sotto `openspec/changes/archive/`.
- **Verifica:** `openspec validate --strict` senza errori.

### Fase uno: file di riferimento e misura

#### `openspec/changes/speed-up-large-files/proposal.md`, `tasks.md`, `design.md` (Create)

- **Ambito:** proposta OpenSpec di questo lavoro.
- **Modifiche:** `proposal.md` riassume perché e cosa cambia, `design.md` rimanda a questo documento, `tasks.md` riprende le fasi qui sotto.
- **Perché:** il rilevamento dell'encoding cambia comportamento e il progetto richiede una proposta per i cambi di comportamento.

#### `openspec/changes/speed-up-large-files/specs/encoding-detection/spec.md` (Create)

- **Ambito:** delta di spec.
- **Modifiche:**
  - MODIFIED «Primary encoding detection uses charset_normalizer»: il fallback `file -b --mime-encoding`, che nel codice non esiste (verificato il 2026-11-22, nessuna chiamata in `src/csvnorm/`), sparisce. Al suo posto entrano i passi descritti nel piano tecnico: decodifica UTF-8 stretta sull'intero file, campione mirato sui byte non ASCII, rilevamento completo se la conversione fallisce.
  - ADDED «UTF-8 conversion preserves line breaks»: CR, LF e CRLF passano intatti, anche dentro le celle, con output uguale su ogni sistema operativo.

#### `openspec/changes/speed-up-large-files/specs/processing-pipeline/spec.md` (Create)

- **Ambito:** delta di spec.
- **Modifiche:** ADDED «Keyword prefix removal works with any output delimiter», con lo scenario `select,_id` e `-d ';'` che dà `select;_id`.

#### `tests/fixtures/golden/` (Create)

- **Ambito:** coppie input e output atteso, piccole, versionate.
- **Contenuto:** cp1252 e UTF-8; righe LF, CRLF e `\r\r\n`; CR isolato e CRLF dentro una cella quotata, sia in UTF-8 sia in latin-1; virgolette dentro le celle; BOM; file vuoto; solo header; header con `select`, `from`, `_id`; un caso per ogni valore di `--delimiter` (`,`, `;`, `|`, tab); un file con righe malformate, con il suo file degli scarti atteso.
- **Come si producono:** gli output attesi si generano con csvnorm 1.3.0 su Linux. Tre famiglie fanno eccezione e si scrivono a mano con il comportamento corretto: CR dentro le celle dei file non UTF-8, header con parole chiave e delimitatore diverso dalla virgola, e i casi che la fase quattro migliora. Il file `tests/fixtures/golden/README.md` elenca queste eccezioni una per una.

#### `tests/test_golden.py` (Create)

- **Ambito:** test di integrazione.
- **Modifiche:** per ogni coppia lancia csvnorm come processo vero (`subprocess`), confronta byte per byte l'output e, dove c'è, il file degli scarti, e controlla l'exit code. I casi delle correzioni sono marcati `xfail(strict=True)` finché la fase che li corregge non li fa passare.
- **Verifica:** sul codice attuale passano tutti, tranne gli `xfail` attesi.

#### `tests/test_encoding_equivalence.py` (Create)

- **Ambito:** test di regressione del rilevamento.
- **Modifiche:** per ogni file di `test/` e `tests/fixtures/golden/` confronta il risultato di `detect_encoding` con una copia congelata del rilevamento di oggi (`charset_normalizer.from_path` più lo spareggio attuale). Le differenze ammesse sono elencate nel test con il motivo.
- **Perché:** è la prova richiesta dall'obiettivo «stesso risultato di oggi o migliore».

#### `scripts/bench_large.py` (Create)

- **Ambito:** script di misura, fuori dalla suite.
- **Modifiche:** prende un file CSV in ingresso, esegue un riscaldamento e poi tre esecuzioni di `csvnorm <file> -o <tmp>`, e stampa la mediana, il picco di RSS (tramite `/usr/bin/time -v` se c'è) e i tempi per fase ricavati dal log `--verbose`. Prima di partire controlla lo spazio libero e si ferma se sono meno di 3 volte la dimensione del file. Alla fine cancella i propri output.
- **Perché:** una sola esecuzione su WSL2 non è una base di confronto, e durante le misure del 2026-11-22 il disco si è riempito.

#### `scripts/make_large_csv.py` (Create)

- **Ambito:** generatore sintetico.
- **Modifiche:** scrive un CSV di dimensione data (per esempio 50 MB o 500 MB) in una codifica a scelta. Opzionalmente mette byte non ASCII solo a metà o solo in fondo al file, e righe CRLF.
- **Perché:** il file da 826 MB non entra nella suite, e i casi limite del rilevamento vanno costruiti apposta.

#### `src/csvnorm/core.py` (Modify)

- **Modifiche:** con `--verbose`, ogni fase registra nel log il proprio tempo (rilevamento, conversione, validazione, normalizzazione, conteggi), con `time.perf_counter`.
- **Perché:** servono a `scripts/bench_large.py` e a chi indaga una lentezza.

#### `pyproject.toml` (Modify)

- **Modifiche:** nuovo marker pytest `slow` per i test su file sintetici grandi, accanto a `network`, e `addopts = "-m 'not slow'"` in `[tool.pytest.ini_options]`, così la suite normale li salta. Oggi non c'è nessun `addopts` (verificato il 2026-11-22).

**Misura di partenza:** `scripts/bench_large.py tmp/comuni_giornaliero_30settembre26.csv` sul codice attuale. La mediana ottenuta sostituisce i 220 s stimati come base di confronto, e si registra in `LOG.md`.

### Fase due: header e CRLF scritti da DuckDB

#### `src/csvnorm/validation.py` (Modify)

- **`normalize_csv`:** nuovo parametro `crlf: bool = False`, dopo quelli attuali, per non rompere chiamate posizionali. Due funzioni private nuove, usate da tutti e tre i punti che oggi costruiscono il `COPY`:
  - `_select_list(normalize_names: bool) -> str`: restituisce `*` oppure l'espressione `COLUMNS('^(?:_(k1|k2|...)|(.*))$') AS '\1\2'`, costruita da `_DUCKDB_KEYWORD_SET` in ordine stabile (ordinato) e con le parole passate per `re.escape`;
  - `_copy_options(delimiter: str, crlf: bool) -> str`: le opzioni di oggi più `NEW_LINE '\r\n'` quando `crlf` è vero.
- **Da togliere:** `_fix_duckdb_keyword_prefix` e la sua chiamata, `convert_row_endings_to_crlf`. `_DUCKDB_KEYWORD_SET` resta.
- **Da verificare in questa fase, prima di proseguire:** con una parola chiave fra i nomi delle colonne, l'espressione `COLUMNS` dà lo stesso header della funzione di oggi su tutti i file di riferimento con la virgola. Il `\b` dell'espressione regolare di oggi lascia per esempio `_select_1` invariato, e così deve fare la nuova. Va verificato anche che i percorsi di riserva (`FALLBACK_CONFIGS`, `strict_mode=false`) usino la stessa espressione.

#### `src/csvnorm/core.py` (Modify)

- **Modifiche:** passa `crlf=input_has_crlf and not use_stdout` a `normalize_csv` tramite `_normalize_and_refresh_errors`. Toglie la chiamata a `convert_row_endings_to_crlf` e il relativo import.

#### `tests/test_validation.py` (Modify)

- **Modifiche:**
  - togliere `TestFixDuckdbKeywordPrefix` e i test di `convert_row_endings_to_crlf`, perché le funzioni spariscono;
  - aggiungere test su `normalize_csv` con la stessa copertura: parola chiave senza prefisso, `_id` conservato, `_select_1` invariato, ordine delle colonne invariato, ogni delimitatore, `crlf=True` con a capo dentro le celle invariati, `crlf=False` con righe LF, `keep_names` con `SELECT *`.

#### `tests/test_golden.py` (Modify)

- **Modifiche:** togliere l'`xfail` dai casi «header con parole chiave e delimitatore diverso dalla virgola».

**Verifica della fase:** suite intera verde, file di riferimento identici, mediana di `bench_large.py` con il miglioramento atteso di circa 54 s (40 s di CRLF più 14 s di header, misurati il 2026-11-22), registrata in `LOG.md`.

### Fase tre: conversione UTF-8 a blocchi

#### `src/csvnorm/encoding.py` (Modify)

- **`convert_to_utf8`:** stessa firma. Legge l'input in binario a blocchi di `CHUNK_SIZE` (costante di modulo, 4 MB), decodifica con `codecs.getincrementaldecoder(source_encoding)(errors="strict")`, chiama `final=True` sull'ultimo blocco e scrive in UTF-8 in binario.
  - Su `UnicodeDecodeError` si ricalcola la posizione assoluta (blocchi già letti più la posizione nel blocco) e si rilancia con la posizione corretta.
  - Su qualsiasi eccezione, compreso `OSError` con `ENOSPC`, si cancella il file parziale prima di propagare.
- **Perché:** memoria limitata e CR, LF e CRLF conservati (correzione decisa).

#### `src/csvnorm/core.py` (Modify)

- **Modifiche:** il pannello d'errore della conversione (`core.py:468-471`) mostra la posizione assoluta. Un `OSError` con `ENOSPC` dà un pannello «spazio su disco esaurito» ed exit 1.

#### `tests/test_encoding.py` (Modify)

- **Modifiche:** nuovi test di `convert_to_utf8`:
  - CR isolato e CRLF dentro una cella in latin-1 passano intatti;
  - un carattere multibyte di una codifica a più byte (per esempio `shift_jis` o `utf-16`) spezzato fra due blocchi, con `CHUNK_SIZE` ridotto con `monkeypatch`;
  - byte non decodificabile a metà file: la posizione riportata è quella assoluta e il file parziale non esiste più;
  - output identico a quello di oggi su un file senza CR dentro le celle.
- **Memoria:** su un file sintetico di circa 50 MB, il picco di `tracemalloc` durante la conversione resta sotto i 32 MB.

#### `tests/test_golden.py` (Modify)

- **Modifiche:** togliere l'`xfail` dai casi «CR dentro le celle dei file non UTF-8».

**Verifica della fase:** suite verde, file di riferimento identici, nuova mediana in `LOG.md`.

### Fase quattro: rilevamento dell'encoding

#### `src/csvnorm/encoding.py` (Modify)

- **`detect_encoding(file_path)`:** stessa firma e stessi valori restituiti. Struttura interna:
  - `_scan_utf8(path) -> ScanResult`: una passata a blocchi. Restituisce se c'è il BOM, se il file è tutto ASCII e se è UTF-8 valido, più la posizione del primo errore UTF-8.
  - `_targeted_sample(path, budget, window) -> bytes`: dall'inizio del file prende 64 KB. Poi, in una seconda passata a blocchi, trova con `re.finditer(rb"[\x80-\xff]+")` le sequenze non ASCII e prende finestre di 4 KB attorno a ciascuna, allineate a inizio e fine riga. Se le finestre superano il budget (1 MB), ne tiene una ogni k, con k scelto per coprire tutto il file in modo uniforme. Non usa nulla di casuale.
  - `_pick_encoding(matches) -> str`: lo spareggio di oggi, estratto senza modifiche, usato sia per il campione sia per il rilevamento completo.
  - `detect_encoding_full(path) -> str`: il rilevamento di oggi (`from_path` più `_pick_encoding`), usato come ricaduta e da `tests/test_encoding_equivalence.py`. Funzione privata, non esportata.
- **Costanti:** `SAMPLE_BUDGET = 1 MiB`, `SAMPLE_WINDOW = 4 KiB`, `HEAD_BYTES = 64 KiB`. Sono valori di partenza: la fase si chiude solo se `tests/test_encoding_equivalence.py` passa con questi valori, altrimenti si alzano e si documenta perché.
- **Log `--verbose`:** quale strada è stata presa (UTF-8 valido, ASCII, campione di N byte da M finestre).

#### `src/csvnorm/core.py` (Modify)

- **`_handle_local_encoding`:** se `convert_to_utf8` fallisce con `UnicodeDecodeError` dopo un rilevamento a campione, il log `--verbose` lo dice, si chiama `detect_encoding_full` e si riconverte una volta sola. Se fallisce anche la seconda conversione, l'errore va all'utente come oggi.
- Il testo di avanzamento «Detecting encoding...» resta invariato.

#### `tests/test_encoding.py` (Modify)

- **Modifiche:** nuovi test:
  - file ASCII con un solo byte cp1252 a metà e un altro solo in fondo, generati con `scripts/make_large_csv.py` o in linea: rilevamento non ASCII e conversione corretta;
  - campione deterministico, stesso risultato su due chiamate;
  - BOM UTF-8 dà `utf-8-sig`;
  - ricaduta: con un `charset_normalizer` sostituito da `monkeypatch` che restituisce una codifica incapace di decodificare il file, `_handle_local_encoding` arriva al rilevamento completo e il risultato finale è corretto.
- I test esistenti (`tests/test_encoding.py:84-138`: italiano, cp1251, file vuoto, file binario) restano e devono passare senza modifiche.

#### `tests/test_encoding_equivalence.py` (Modify)

- **Modifiche:** si aggiornano le differenze ammesse emerse in questa fase, ciascuna con il motivo, compreso l'esito del caso «200.000 righe ASCII più un byte latin-1».

#### `openspec/changes/speed-up-large-files/specs/encoding-detection/spec.md` (Modify)

- **Modifiche:** gli scenari si allineano a eventuali differenze emerse dai test.

**Verifica della fase:** suite verde, test di equivalenza verde, mediana finale in `LOG.md`.

### Fase cinque, condizionale: validazione e normalizzazione in un solo `COPY`

Si apre solo se la mediana dopo la fase quattro resta sopra i 60 s. In quel caso, prima di scrivere codice, si aggiunge a questo documento un piano dettagliato. Serve perché la fase cambia l'ordine di messaggi ed exit code e il comportamento di `--strict`, cose che vanno decise e testate sul contratto della CLI. Se la mediana è sotto i 60 s, la fase si chiude come non necessaria, con la misura in `LOG.md`.

### Fase sei: documentazione e rilascio

#### `README.md` (Modify)

- **Modifiche:** la sezione «Encoding detection limits» (`README.md:187`) descrive il nuovo rilevamento. Un CR dentro le celle dei file non UTF-8 ora si conserva, e la correzione dell'header vale per ogni delimitatore.

#### `CLAUDE.md` (Modify)

- **Modifiche:** la sezione Architecture (`detect_encoding`, `convert_to_utf8`, flusso, numero di test) si allinea, e si cita `scripts/bench_large.py`.

#### `PRD.md` (Modify)

- **Modifiche:** FR-2 (`PRD.md:42`) cita UTF-8 stretto, campione mirato e ricaduta sul rilevamento completo.

#### `LOG.md` (Modify)

- **Modifiche:** una voce per fase, con le mediane misurate.

#### `openspec/changes/add-input-encoding-option/proposal.md` (Modify)

- **Modifiche:** la sezione «Why» si aggiorna con i casi che il nuovo rilevamento ha cambiato, misurati nella fase quattro. Nessun altro cambiamento: la proposta resta da approvare.

#### `tasks/todo.md` (Modify)

- **Modifiche:** il piano a fasi con le verifiche, spuntato a ogni avanzamento. La voce «misure di memoria e prestazioni» di «Prossimi passi» si chiude con un rimando a questo lavoro.

#### `openspec/changes/speed-up-large-files/` (archiviato dopo il rilascio)

- **Modifiche:** `openspec archive speed-up-large-files` dopo il rilascio, che aggiorna le spec di base `encoding-detection` e `processing-pipeline`.

#### `src/csvnorm/__init__.py`, versione in `pyproject.toml` (Modify)

- **Modifiche:** nuova versione minore, perché il comportamento visibile cambia: CR conservati, header con ogni delimitatore, rilevamento diverso in alcuni casi. Le note di rilascio citano il nuovo parametro `crlf` di `normalize_csv` (API pubblica, facoltativo, in fondo alla firma). Si seguono `DEPLOYMENT.md` e la lista di controllo pre-rilascio di `CLAUDE.md`.

### Piano di verifica

- **Test:** `uv run pytest tests/ -v` alla fine di ogni fase; `uv run pytest tests/ -v -m slow` per i test su file sintetici grandi.
- **Lint e tipi:** `uv run ruff check src tests` e `uv run mypy src` (mypy è fra le dipendenze di sviluppo in `pyproject.toml`).
- **Copertura:** le righe nuove di `encoding.py` e `validation.py` coperte dai test, misurate con `uv run pytest --cov=csvnorm --cov-report=term`.
- **Contratto:** `tests/test_golden.py` verde, senza `xfail` rimasti.
- **Prestazioni:** `scripts/bench_large.py tmp/comuni_giornaliero_30settembre26.csv`, mediana di tre esecuzioni dopo un riscaldamento. Obiettivo sotto i 60 s. Soglia di rilascio: almeno 3 volte più veloce della base misurata nella fase uno.
- **Rilascio:** `uv tool install --reinstall --force .`, poi `csvnorm -v`, poi una prova sul file da 826 MB con il controllo che nella directory temporanea non resti nulla.
