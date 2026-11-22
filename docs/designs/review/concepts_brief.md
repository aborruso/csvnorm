# csvnorm veloce sui file grandi, senza una modalità separata

* **Author:** aborruso
* **Date:** 2026-11-22

## Indice

- Overview
- Analysis
- Goals vs. Non-Goals
- Alternatives Weighed
- Key Decisions & Staging for Next Steps

## Overview

csvnorm è lento sui CSV grandi: un file cp1252 da 826 MB (5,4 milioni di righe, 57 colonne, righe CRLF) richiede circa 220 s. L'ipotesi di partenza è rendere veloce il percorso normale, senza una "modalità file grandi", con tre interventi in Python: rilevamento dell'encoding su campioni con ritorno al file intero se la conversione fallisce; conversione UTF-8, correzione dell'header e conversione CRLF in streaming a blocchi, con memoria limitata e output identico byte per byte a oggi; validazione DuckDB sempre sull'intero file. Obiettivo: meno di 60 s, con test che confrontano l'output prima e dopo.

Il brief raccoglie sette letture indipendenti dell'ipotesi. In sintesi: la direzione è giusta e due dei tre interventi reggono. Il rilevamento a campioni, così come è formulato, ha un buco di sicurezza. Il requisito "identico a oggi" va definito meglio. Esistono strade più semplici, cioè eliminare dei passaggi invece di ottimizzarli, e conviene valutarle prima di scrivere codice in streaming.

### Stato delle letture

| Lente | Stato |
| --- | --- |
| egm-design | completed |
| egm-codebase-details | completed |
| egm-zoom-out | completed |
| egm-comprehension | completed |
| egm-implementation-readiness | completed |
| egm-structural | completed |
| egm-inventive-catalyst | completed |

### Livelli di evidenza usati nel brief

- **Misurato**: i tempi per fase del 2026-11-22, una sola esecuzione per fase, su WSL2, senza profiler. Sono indicativi, non una baseline.
- **Verificato nel codice**: affermazioni con riferimento `file:riga`, controllate da almeno una lente e, dove indicato, riscontrate anche nella sintesi.
- **Da verificare**: ipotesi delle lenti sul comportamento di DuckDB o sui tempi attesi. Le stime in secondi delle lenti non sono misure.

## Analysis

### Il ritorno al file intero non scatta proprio nei casi pericolosi (Blocker)

Segnalato da tutte e sette le lenti. Verificato nel codice.

- Il ritorno al rilevamento sul file intero scatta solo quando la decodifica fallisce. `latin_1` decodifica qualsiasi byte; `cp1252` fallisce solo su cinque byte non definiti (0x81, 0x8D, 0x8F, 0x90, 0x9D). Una scelta sbagliata fra codifiche a un byte, per esempio cp1250 al posto di cp1252 (il caso per cui esiste lo spareggio in `src/csvnorm/encoding.py:67-74`), converte senza errori e produce testo storpiato con exit 0.
- Il caso peggiore: se i campioni sono tutti ASCII, il verdetto è `ascii`, `needs_conversion` restituisce False (`src/csvnorm/core.py:183`), la conversione non parte e il ritorno al file intero non può scattare. Un 0xE9 a metà file arriva a DuckDB come UTF-8 non valido e finisce fra le righe rifiutate, invece di essere ricodificato.
- I test che proteggono questi casi esistono già: `tests/test_encoding.py:84-98` (testo italiano in file del ministero e latin1), `:100` (cp1251 non deve diventare una codifica occidentale), `:123` (file vuoto), `:135` (file binario: `ValueError`).
- Proposta che ricorre in quattro lenti (zoom-out, design, inventive-catalyst, implementation-readiness): prima una decodifica UTF-8 stretta e incrementale sull'intero file, a velocità C. Se passa, il file è UTF-8 o ASCII e charset_normalizer non serve. Se fallisce, il campione si costruisce attorno ai byte `>= 0x80` (a partire dal primo punto di errore, o dalle finestre trovate con `re.finditer(rb'[\x80-\xff]+')`), più l'inizio del file per il BOM, e lo si passa a `charset_normalizer.from_bytes` con lo stesso spareggio di oggi. L'insieme esatto dei byte alti presenti, calcolabile su tutto il file con `bytes.translate`, scarta le codifiche che li lasciano indefiniti. Il costo atteso (circa 1-2 s per GB) è da verificare.

### "Identico byte per byte a oggi" non è definito (Blocker)

Segnalato da sei lenti. Verificato nel codice.

- `convert_to_utf8` (`src/csvnorm/encoding.py:125-129`) apre lettura e scrittura in modalità testo senza `newline=""`. In lettura CRLF e CR isolati, anche dentro i campi quotati, diventano LF. In scrittura si usa `os.linesep`, quindi su Windows LF torna CRLF. Oggi l'output dei file non UTF-8 dipende dalla piattaforma e perde i CR interni alle celle, mentre i file già UTF-8 li conservano (correzione del commit 7485a3d). Nessun test controlla oggi cosa fa `convert_to_utf8` con CR e LF.
- La regex dell'header (`src/csvnorm/validation.py:478`, `(^|,)_(...)`) gestisce solo la virgola: con `-d ';'` la correzione delle parole chiave non fa nulla. Anche questo, con l'identità stretta, andrebbe conservato.
- `readline()` con `newline=""` (`src/csvnorm/validation.py:463`) chiude la prima riga anche su un CR isolato: una riscrittura binaria deve riprodurlo.
- Va deciso: identico all'output della release attuale, su quale piattaforma e su quale insieme di file di prova, e riferito all'output finale e al file degli scarti, non ai file intermedi. Per ognuno dei comportamenti sopra va scelto in modo esplicito se conservarlo o correggerlo; una correzione è un cambiamento di comportamento con test propri.

### Obiettivo dei 60 s stretto, misure deboli (Major)

Segnalato da sei lenti. Calcolo sulle misure.

- Validazione (19 s), normalizzazione (24 s) e conteggi (3 s) fanno già 46 s e restano. Restano circa 14 s per rilevamento, conversione, header e CRLF.
- Una sola esecuzione su WSL2 non è una baseline: page cache e filesystem possono far variare i tempi anche di due volte (da verificare). Serve un protocollo: file su ext4 e non su `/mnt/*`, un'esecuzione di riscaldamento, poi la mediana di almeno tre, cache calda dichiarata, picco di RSS (`/usr/bin/time -v`) e picco di spazio temporaneo. Servono anche tempi per fase con `--verbose` (oggi nessuna fase registra un tempo).
- Va detto cosa succede se i 60 s non si raggiungono ma ogni fase migliora.

### Eliminare passaggi invece di ottimizzarli (Major)

Segnalato da zoom-out, design, inventive-catalyst. Le soluzioni sono da verificare.

- **Header**: `_fix_duckdb_keyword_prefix` (`src/csvnorm/validation.py:451`, chiamata a `:444`) riscrive 826 MB per correggere una riga, 14 s misurati. In alternativa si leggono i nomi delle colonne con `DESCRIBE` su `read_csv(... normalize_names=true)`, si tolgono i prefissi in Python e si fa `COPY (SELECT "_select" AS "select", ...)`. DuckDB scrive l'header giusto e il passaggio sparisce, anche in modalità stdout. Da verificare: virgolettatura dei nomi identica a oggi, nomi duplicati, percorsi di fallback, comportamento con delimitatore diverso dalla virgola.
- **CRLF**: verificato il 2026-11-22 con DuckDB 2.0.0: `COPY ... TO 'x.csv' (FORMAT csv, NEW_LINE '\r\n')` scrive `a,b\r\n1,x\r\n2,y\r\n`, e lascia invariati gli a capo dentro le celle quotate (`"a\nb"` resta `"a\nb"`, `"d\r\ne"` resta `"d\r\ne"`), come fa oggi `convert_row_endings_to_crlf`. Il passaggio Python da 40 s può sparire.
- **Validazione e normalizzazione in un solo passaggio**: eseguire il COPY con `store_rejects=true` ed esportare gli scarti subito dopo (il fallback di `normalize_csv` lo fa già, `src/csvnorm/validation.py:395-417`). Ogni riga resta controllata, quindi il requisito "mai perdere una riga malformata" tiene. Si risparmierebbero circa 19 s, stima. Cambia però l'ordine di messaggi ed exit code, e `--strict` scriverebbe su un temporaneo da buttare (in modalità file l'output già passa da un temporaneo: `src/csvnorm/core.py:778`, `:816`). È una scelta di perimetro dell'autore, non un default.
- **Conteggio righe**: ricavarlo dal risultato del COPY invece di rileggere l'output (`src/csvnorm/utils.py:318`). Da verificare.
- **DuckDB che decodifica da solo**: se nel file non ci sono byte 0x80-0x9F, cp1252 e latin-1 coincidono e DuckDB può leggere l'originale con `encoding='latin-1'`. Così si elimina la conversione e il temporaneo da 826 MB. Per altre codifiche servirebbe un'estensione scaricata dalla rete, il che rompe l'uso offline. Introduce un secondo percorso. Da verificare.

### CRLF veloce in Python puro (Major)

Segnalato da sei lenti. Verificato nel codice.

- Il ciclo byte per byte (`src/csvnorm/validation.py:645-661`) va in streaming senza rischi: 0x22 e 0x0A non compaiono mai dentro sequenze UTF-8 multibyte, e l'unico stato da portare da un blocco all'altro è "dentro le virgolette sì/no".
- Versione rapida: un blocco senza `"` passa per `chunk.replace(b"\n", b"\r\n")`. Altrimenti si fa `split(b'"')` e la sostituzione solo nei segmenti pari, cioè fuori dalle virgolette, portando la parità al blocco successivo. Le virgolette raddoppiate `""` danno segmenti vuoti e mantengono la parità. Va conservato il comportamento attuale su CR già presente prima di LF (oggi diventa `\r\r\n`).
- Unire correzione dell'header e CRLF in un unico passaggio, se l'header non sparisce del tutto.

### Spazio su disco e pulizia (Major)

Segnalato da design, comprehension, implementation-readiness, structural.

- Oggi header e CRLF lavorano in memoria. In streaming serve un secondo file, quasi 0,9 GB in più al picco, con 5,9 GB liberi. Criterio deciso il 2026-11-22: come oggi, al massimo due copie temporanee per i file non UTF-8 e una per quelli UTF-8; la copia unica tramite lettura `latin-1` di DuckDB va fra i miglioramenti futuri. Si scrive nella stessa directory e poi si fa `os.replace`; il temporaneo UTF-8 si cancella appena non serve, controllando prima che `_compute_and_show_output` non lo usi più.
- Se la conversione in streaming fallisce a metà, il file parziale va cancellato prima del ritorno al file intero. Va definito anche il comportamento con disco pieno (ENOSPC): pannello d'errore, exit 1, pulizia garantita.
- Il ritorno al file intero, se scatta tardi, costa più di oggi: conversione parziale, poi rilevamento completo (106 s), poi seconda conversione.
- Con la conversione a blocchi, la posizione riportata da `UnicodeDecodeError` diventa relativa al blocco e il testo del pannello d'errore (`src/csvnorm/core.py:468-471`) cambia.

### Perimetro per tipo di input (Major)

Verificato nel codice dalla lente codebase-details.

| Input | Rilevamento encoding | Conversione | CRLF | Memoria limitata |
| --- | --- | --- | --- | --- |
| File locale | sì | sì | sì, se input CRLF e non stdout | sì |
| URL remoto | sì, sempre scaricato prima (`core.py:131-146`) | sì | sì | sì |
| Zip | sì, estratto prima (`core.py:713-717`) | sì | sì | sì |
| Gzip | no (`core.py:447-455`) | no | no (`core.py:727`) | da DuckDB |
| Stdin | sì, dopo il salvataggio | sì | sì | no: letto tutto in memoria (`core.py:662`) |
| Output su stdout | come sopra | come sopra | mai (`core.py:812`) | no: `f.read()` a `core.py:359-360` |
| `--fix-mojibake` | come sopra | come sopra | come sopra | no: ftfy sull'intero testo (`mojibake.py:66-75`) |

Il ramo "remoto" a `core.py:440-445` sembra irraggiungibile, perché gli URL vengono sempre scaricati. `detect_encoding` è API pubblica (`src/csvnorm/__init__.py:4`, `:7`): la firma resta.

### Campionamento non specificato (Major)

Segnalato da comprehension, codebase-details, structural, design.

- "Blocchi casuali" va reso deterministico: posizioni fisse o seme ricavato dalla dimensione, numero e dimensione dei blocchi dichiarati, tagli allineati a inizio riga, offset 0 sempre incluso per il BOM. Con il campionamento mirato sui byte alti descritto sopra la questione si semplifica.
- Sotto una soglia di dimensione (per esempio due volte il budget del campione) si può restare sul percorso di oggi, così tutti i fixture esistenti si comportano come ora. È però un secondo percorso da testare su entrambi i lati della soglia (lente structural).
- Va scritto cosa vede l'utente: con `--verbose`, quale percorso è stato usato, quali regioni sono state lette e se il ritorno al file intero è scattato e perché; se la tabella finale dice che l'encoding è stato campionato.

### Stato del repository OpenSpec (Major)

Segnalato da structural, riscontrato nella sintesi (esistono le cartelle in `openspec/changes/`).

- `openspec/changes/add-input-encoding-option` aggiunge `--encoding`, che salta del tutto il rilevamento: è il rimedio più economico ai 106 s quando l'utente conosce l'encoding. Tocca le stesse funzioni, quindi va stabilito l'ordine fra le due proposte.
- `openspec/changes/preserve-crlf-line-endings` è implementata (commit `107e8e2` e `0c7b8d8`, codice a `core.py:724-813`) ma non archiviata, e il suo `tasks.md` ha ancora tutte e 9 le voci non spuntate (verificato il 2026-11-22). Questo lavoro cambia il modo in cui il CRLF viene scritto: la change va archiviata prima, o il suo spec aggiornato insieme.
- `openspec/specs/encoding-detection/spec.md` cita un fallback `file -b --mime-encoding` che nel codice non c'è (segnalato da structural, non riscontrato nella sintesi).

### Nit

- Il limite di memoria va espresso con un numero (dimensione del blocco, per esempio 1-8 MB, e picco di RSS delle fasi Python), escludendo DuckDB.
- Un file da 826 MB non entra nella suite: serve un generatore sintetico e un marker pytest per i test lenti.
- Nessun interruttore per forzare il rilevamento completo: va deciso se esiste (variabile d'ambiente nascosta) o se basta `--encoding` della proposta pendente; la sezione del README sui limiti del rilevamento va aggiornata.
- Il testo di avanzamento a `core.py:179` potrebbe dire "campionato".

## Goals vs. Non-Goals

* **In-Scope Goals:**
  - Percorso unico, senza modalità separata, più veloce sui file grandi, con exit code 0/1/2 invariati e input mai sovrascritto.
  - Rilevamento encoding che non dia mai un risultato sbagliato in silenzio: decodifica UTF-8 stretta sull'intero file, poi campione mirato solo se serve.
  - Conversione UTF-8, header e CRLF in streaming o eliminati, con memoria limitata sul percorso file locale.
  - Validazione di ogni riga sull'intero file.
  - Output finale e file degli scarti identici alla release 1.3.0 su Linux su un insieme di file di prova dichiarato, tranne le correzioni decise (CR conservati nella conversione, header con ogni delimitatore) e i file in cui il nuovo rilevamento sceglie una codifica migliore, elencati uno per uno con motivo e test (deciso il 2026-11-22).
  - Protocollo di misura ripetibile e tempi per fase con `--verbose`.
* **Out-of-Scope Non-Goals:**
  - Cambiare libreria (Polars o altre): DuckDB pesa circa 45 s su 220.
  - Memoria limitata per stdin, output su stdout e `--fix-mojibake`, che restano letture dell'intero file.
  - Velocizzare gzip, che non passa da rilevamento e CRLF.
  - Validazione a campione.

## Alternatives Weighed

- **Libreria diversa (Polars):** scartata dall'autore. Le misure dicono che DuckDB vale circa 45 s su 220, il costo è altrove.
- **Modalità "file grandi" separata:** scartata dall'autore. Sarebbero due percorsi da mantenere e testare.
- **Validazione a campione:** scartata dall'autore. Requisito: mai perdere una riga malformata.
- **Rinunciare al CRLF in output:** scartata dall'autore. È una scelta di fedeltà (RFC 4180 indica CRLF ma è Informational; la bozza rfc4180-bis ammette CR, LF e CRLF): si tiene, ma va resa veloce.
- **Campionamento a blocchi casuali con ritorno solo su errore di decodifica:** messo in discussione da tutte le lenti per il buco descritto nell'analisi. Scartato dall'autore: una codifica sbagliata fra quelle a un byte converte senza errori e passerebbe in silenzio. Scelta al suo posto: UTF-8 stretto sull'intero file e campione mirato sui byte alti.
- **Riscrittura dell'header in streaming:** alternativa proposta, alias nella SELECT del COPY. Da verificare.
- **CRLF in Python a blocchi:** alternativa preferita, opzione `NEW_LINE` del COPY di DuckDB, che esiste in 2.0.0 e non tocca gli a capo dentro le celle (verificato il 2026-11-22).
- **Validazione e normalizzazione separate:** alternativa proposta, un solo COPY con `store_rejects`. Decisione di perimetro dell'autore aperta.
- **Conversione UTF-8 in Python:** alternativa proposta, lettura diretta con `encoding='latin-1'` di DuckDB quando i byte 0x80-0x9F sono assenti. Da verificare, introduce un secondo percorso.

## Key Decisions & Staging for Next Steps

### Decisioni già prese dall'autore

- Validazione sempre sull'intero file.
- CRLF conservato in output quando l'input è CRLF.
- Rilevamento encoding (deciso il 2026-11-22): decodifica UTF-8 stretta e incrementale sull'intero file; se fallisce, campione costruito attorno ai byte `>= 0x80` più l'inizio del file, passato a `charset_normalizer.from_bytes` con lo spareggio di oggi.
- Difetti attuali (deciso il 2026-11-22): si correggono in questo lavoro, non si congelano. `convert_to_utf8` deve conservare CR e CRLF come sono (`newline=""` in lettura e scrittura), con output uguale su Linux e Windows; la correzione dei prefissi delle parole chiave nell'header deve funzionare con ogni delimitatore. I file di riferimento della fase preliminare registrano quindi il comportamento corretto, e le differenze rispetto a oggi sono documentate una per una.
- Vincoli: Python puro, multipiattaforma, complessità minima, exit code 0/1/2, input mai sovrascritto.

### Decisioni da prendere prima di scrivere codice

- Fissare la base di confronto: release 1.3.0 su Linux, con l'elenco delle differenze volute (CR conservati, header con ogni delimitatore) e la decisione sul caso `\r\r\n`.
- Accettare o no l'unione di validazione e normalizzazione in un solo COPY.
- Ordine rispetto a `add-input-encoding-option`.
- Soglia d'accettazione se i 60 s non si raggiungono.

### Fasi proposte, ciascuna rilasciabile da sola

- **Fase preliminare (solo test):** prima di toccare il codice, registrare i file di riferimento con l'output atteso: quello della 1.3.0 su Linux, tranne i casi toccati dalle correzioni decise (CR conservati nella conversione, header con ogni delimitatore), dove il riferimento è il comportamento corretto, documentato caso per caso. Casi: cp1252 e UTF-8; CRLF, LF e CR isolati; a capo e virgolette dentro le celle; BOM; file vuoto; solo header; header con parole chiave e `_id`; ogni valore di `--delimiter`. Poi script di misura con mediana e tempi per fase, generatore sintetico di file grandi, marker pytest per i test lenti. Verifica: i test di riferimento passano sul codice attuale, salvo quelli delle correzioni, che falliscono finché non vengono fatte.
- **CRLF in streaming e header:** `NEW_LINE` di DuckDB (verificato) e alias nella SELECT da verificare; se non bastano, un solo passaggio a blocchi con parità delle virgolette. Rischio più basso, risparmio fino a 54 s misurati. Verifica: uguaglianza di byte con i file di riferimento, con blocchi di dimensione 1, 2, 3, 7 e quella di default; confronto con la vecchia funzione su input casuali; picco di tracemalloc limitato su un file di circa 50 MB.
- **Conversione UTF-8 a blocchi:** `open()` con `newline=""` in lettura e scrittura (decisione presa), con ciclo su `f.read(CHUNK)`, cancellazione del parziale in caso di errore e scrittura atomica. Verifica: blocchi che spezzano `\r\n` e caratteri multibyte.
- **Rilevamento encoding:** ultima fase, perché è l'unico cambiamento di comportamento e il risparmio più grande (106 s misurati). Delta OpenSpec su `encoding-detection`, che corregge anche il disallineamento con la spec. Verifica: per ogni file in `tests/` il rilevamento nuovo dà lo stesso risultato di quello completo; un caso sintetico con byte non ASCII solo a metà e solo in fondo al file.
- **Opzionale:** unione di validazione e normalizzazione, solo se l'autore la accetta e se dopo le fasi precedenti i 60 s non sono raggiunti.

Ogni fase va in un commit con i suoi test; il ritorno indietro è un revert, perché non c'è stato persistente.

### Domande aperte

- `add-input-encoding-option` va prima o dopo?
- Serve un interruttore per forzare il rilevamento completo, o basta `--encoding`?
- Validazione e normalizzazione in un solo passaggio: sì o no?
