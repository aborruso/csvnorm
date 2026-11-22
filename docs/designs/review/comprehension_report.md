### What this proposes

Il design rende csvnorm veloce sui CSV da centinaia di MB senza aggiungere una modalità per i file grandi, e continua a controllare ogni riga. Cambia quattro cose:

- **Rilevamento dell'encoding.** Al posto di `charset_normalizer` sull'intero file c'è una decodifica UTF-8 stretta e incrementale dell'intero file. Solo se fallisce entra `charset_normalizer`, su un campione deterministico a budget fisso: i primi 64 KB del file più finestre attorno alle sequenze di byte non ASCII. Se poi la conversione con la codifica scelta fallisce, il rilevamento torna una volta al metodo di oggi sull'intero file.
- **Conversione in UTF-8.** Diventa a blocchi e binaria, così CR, LF e CRLF passano invariati, anche dentro le celle.
- **Header e fine riga.** Spariscono le due riscritture Python dell'intero file. Il `COPY` di DuckDB scrive da solo l'header corretto, con un alias `COLUMNS(regex) AS '\1\2'` che toglie il `_` aggiunto da DuckDB ai nomi di colonna che sono parole chiave. Scrive anche i fine riga CRLF con `NEW_LINE '\r\n'`.
- **Due difetti esistenti vengono corretti.** La conversione in modalità testo non trasforma più in LF i CR dentro le celle, e la correzione delle parole chiave nell'header funziona con ogni delimitatore.

Il lavoro procede per fasi: archiviazione di una vecchia change, file di riferimento e benchmark, header e CRLF scritti da DuckDB, conversione a blocchi, nuovo rilevamento, unione facoltativa di validazione e normalizzazione in un solo `COPY`, documentazione e rilascio. Gli obiettivi sono una mediana sotto i 60 s sul file da 826 MB, oppure almeno 3 volte più veloce della base misurata, con output identico byte per byte alla 1.3.0 salvo le eccezioni elencate.

### How the existing system works, per this document

Per un file locale non UTF-8 con output su file, csvnorm oggi:

1. esegue `charset_normalizer` sull'intero file (106 s);
2. converte in UTF-8 in modalità testo, tutto in memoria (10-14 s), scrivendo il temporaneo `utf8.csv`;
3. valida con `read_csv` di DuckDB e `store_rejects` (19 s);
4. normalizza con il `COPY` di DuckDB nel temporaneo `normalized.csv` (24 s);
5. rilegge e riscrive in Python l'intero output per togliere il prefisso `_` che DuckDB aggiunge ai nomi di colonna che sono parole chiave (14 s, solo con la virgola come delimitatore);
6. converte i fine riga in CRLF byte per byte in memoria (40 s);
7. conta righe e colonne (3 s).

Circa 160 dei 220 s vanno in passaggi Python. La memoria arriva a diversi GB, e durante un'esecuzione il disco si è riempito. Con l'output su stdout non c'è CRLF. Stdin, stdout e `--fix-mojibake` leggono l'intero file in memoria.

---

# Rapporto della fase 6: test di comprensione

* **Documento:** `docs/designs/speed-up-large-files.md`, FeatureRange righe 1-277, DetailedRange righe 278-502
* **Data:** 2026-11-22
* **Revisore:** egm-comprehension, con il solo documento e senza altri file di contesto

## Indice

- Esito
- Rilievi Major
- Rilievi minori (Nit)

## Esito

Nessun Blocker: il revisore ha potuto riformulare ogni sezione con parole sue. Ci sono cinque Major e otto Nit.

## Rilievi Major

1. **Stato contraddittorio del `COPY` unico** (righe 81, 272, 282). La riga 81 dice che non ci sono domande aperte. La riga 272 dice che il `COPY` unico è «non ancora decisa: è fra le domande aperte». La riga 282 lo dà per deciso, come fase condizionale. La riga 272 è rimasta alla formulazione di prima della decisione.
2. **«Codifica migliore» non definita** (righe 62, 64-67, 288, 342). L'obiettivo «Output» parla di «due correzioni decise» e poi ne elenca tre. La terza, i file in cui il nuovo rilevamento sceglie una codifica «migliore», è molto più ampia delle due correzioni, e il documento non dice cosa renda migliore una codifica né chi lo giudichi. Serve un criterio, per esempio «decodifica tutti i byte dove la scelta di oggi fallisce» oppure «coincide con una codifica attesa verificata a mano».
3. **Disco: problema elencato, obiettivo «come oggi»** (righe 46, 61, 213, 259). Il lettore deve ricavare da solo che la risposta è pulizia in caso di errore più controllo dello spazio nello script di benchmark, non meno disco. La riga 213 mescola temporanei su disco e memoria («ne aggiungono altri in memoria») e cita un «terzo passaggio» mai definito. La riga 259 lascia intendere che le riscritture di oggi usino disco in più. Va detto chiaramente qual è oggi il picco di disco, quale sarà, e quale parte del problema del disco il design risolve.
4. **OpenSpec non spiegato** (righe 77, 283, 294-324, 451, 479-489). Change, change archiviate, spec di base, delta MODIFIED e ADDED, `openspec archive`, `openspec validate --strict`: niente è definito o collegato. Non si capisce perché `preserve-crlf-line-endings` vada archiviata prima, né cosa abbia introdotto. Servono una riga di definizione di OpenSpec con un link e una frase su cosa ha introdotto quella change.
5. **Mancano i passi per i casi di riferimento del nuovo rilevamento** (righe 330, 335, 389, 417, 500). La fase uno scrive a mano gli output attesi per «i casi che la fase quattro migliora», ma quei casi si scoprono solo misurando nella fase quattro. Le fasi due e tre tolgono ciascuna il proprio `xfail`. La fase quattro non dice mai di aggiungere casi di riferimento o di togliere `xfail` per i miglioramenti del rilevamento. Il piano di verifica però richiede zero `xfail` rimasti.

## Rilievi minori (Nit)

6. **`test/` e `tests/`** (righe 62, 341): due cartelle con nomi quasi uguali, e `test/` non viene mai spiegata. Anche l'insieme del controllo di equivalenza cambia: alla riga 62 è «tutti i file di `tests/` e `test/`», alla riga 341 è «`test/` e `tests/fixtures/golden/`».
7. **Uno o due passaggi** (righe 162, 427): il piano tecnico dice «un solo passaggio», il piano dettagliato aggiunge una seconda passata per le sequenze non ASCII. Né la discussione dei tempi né lo schema del flusso la citano.
8. **Somma dei tempi mancante:** il documento non somma il tempo che resta, cioè 24 + 19 + 3 + 10-14 s più la scansione UTF-8, già 56-60 s prima della scansione. Scriverla spiegherebbe perché i 60 s sono al limite e perché esistono la soglia a 3 volte e la fase cinque.
9. **«Modalità file»** (righe 85, 119): sembra voler dire «output su file con `-o`, non stdout», ma non viene detto.
10. **Espressione dell'header** (righe 204, 375):
    - nell'esempio `_select` diventa `_select_1`, ma non si dice che `_1` è il suffisso di DuckDB per i nomi duplicati, dovuto alla collisione con `select`;
    - la riga 375 si appoggia al «`\b` dell'espressione regolare di oggi» senza mostrarla;
    - `FALLBACK_CONFIGS` e `strict_mode=false` sono nominati ma non spiegati.
11. **`input_has_crlf`** (riga 207): «la stessa condizione di oggi» dà per scontato che il lettore sappia come csvnorm decide che l'input ha righe CRLF: prima riga, file intero o maggioranza. Decide quando si applica `NEW_LINE`, quindi merita una frase.
12. **Caso cp1006** (riga 288): non si dice se cp1006 (una codepage urdu) sia la risposta sbagliata, né che risultato conti come superato.
13. **Termini non spiegati** (righe 173, 260): caos e coerenza sono le misure di `charset_normalizer`, ma non sono presentate come tali. «Il codice di parità delle virgolette fra blocchi» è citato senza contesto.
