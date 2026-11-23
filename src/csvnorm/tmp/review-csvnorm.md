# Review di csvnorm

## Sintesi

L'idea è valida e il perimetro è utile: normalizzare la struttura dei CSV prima dell'analisi, senza diventare un motore ETL. L'implementazione ha una base leggibile e una suite veloce, ma presenta difetti nel contratto pubblico della CLI che meritano precedenza sulle nuove funzionalità.

**Giudizio:** consolidare affidabilità, trasparenza e documentazione prima di ampliare il prodotto. Non emergono motivi per una riscrittura.

## Perimetro e metodo

- Stato analizzato: working tree basato su commit `107e8e2950703a9d5bc6d0afb3b5d8a205af9d91`.
- Versione del pacchetto nell'ambiente: `1.2.18`.
- Ambiente delle verifiche: Python `3.13.9`, DuckDB `1.5.2`, Linux/WSL.
- Modifiche già presenti all'inizio di questa review: `src/csvnorm/core.py`, `src/csvnorm/validation.py`; `uv.lock` non tracciato. I risultati si riferiscono al working tree, non al solo commit.
- Ispezionati: moduli Python, README, PRD, LOG, valutazione precedente, idee future, sorgente della pagina web, test e workflow di pubblicazione.
- Eseguita nuovamente la suite locale: **189 passed, 3 deselected**, in 4,05 secondi. I test marcati `network` sono stati esclusi.
- Riprodotti separatamente i problemi di `--strict`, exit code dell'entry point modulo, output verbose e conteggi multilinea, con file temporanei isolati.
- Nessuna modifica al codice applicativo.

I percorsi nei rilievi sono relativi alla radice del repository. Le righe indicano lo stato ispezionato e possono cambiare.

### Scala di priorità

- **P1 — alta:** violazione di garanzie di sicurezza dei dati o del contratto usato dalle pipeline.
- **P2 — media:** risultati diagnostici errati, documentazione funzionale inesatta o limiti operativi rilevanti.
- **P3 — evoluzione:** miglioramento utile ma non necessario a correggere un difetto dimostrato.

Non sono stati eseguiti benchmark, verifiche su Windows/macOS, matrici di versioni DuckDB o controlli sul sito pubblicato. La lettura del sito riguarda i sorgenti, non una verifica visuale o di accessibilità.

## Rilievi verificati

### R1 — P1: l'entry point modulo perde gli exit code

**Riferimento:** `src/csvnorm/__main__.py:6`.

Il file chiama `main()` ma non passa il risultato a `sys.exit()`. Il ritorno `1` della CLI non diventa quindi l'exit status del processo.

**Verifica:** con un CSV malformato e `--strict`, la chiamata a `main()` con propagazione esplicita restituisce `1`; `python -m csvnorm` restituisce `0`, pur mostrando il fallimento della validazione.

**Impatto:** script e CI possono interpretare come riuscita un'operazione fallita. Il problema riguarda l'invocazione modulo; non va attribuito indistintamente al comando installato, il cui entry point è configurato separatamente.

**Correzione attesa:** propagare il codice restituito da `main()`.

**Accettazione:** entrambi gli entry point devono restituire codici coerenti almeno per input valido, CSV invalido e file inesistente. Verificare con subprocess, non soltanto invocando `main()` nei test.

### R2 — P1: `--strict` non impedisce la scrittura su file

**Riferimenti:** `src/csvnorm/core.py:523-531`; help di `--strict` in `src/csvnorm/cli.py`.

Il controllo `if strict: return 1` è annidato nel ramo `if use_stdout and has_validation_errors`. Con `-o`, l'esecuzione continua verso la normalizzazione.

**Verifica:** sullo stesso CSV malformato:

| Modalità | Codice restituito da main | CSV normalizzato |
|---|---:|---|
| `--strict` verso stdout | 1 | Nessun contenuto emesso |
| `--strict -o out.csv` | 1 | File creato, 40 byte nel caso riprodotto |

Il file prodotto non è una copia integrale dell'input: la lettura può escludere record rifiutati. Il codice di uscita finale resta `1`; il difetto è la produzione dell'output nonostante il flag che promette di impedirla.

**Impatto:** un processo che osserva il file, oppure una procedura che non controlla correttamente lo status, può consumare un risultato non ammesso dalla modalità strict.

**Correzione attesa:** applicare il blocco strict indipendentemente dalla destinazione, prima della normalizzazione; conservare il report degli errori.

**Accettazione:** con errori e strict, stdout vuoto e nessun nuovo CSV di output. Con output preesistente e `--force`, il contenuto preesistente deve rimanere invariato. La modalità non strict può continuare a esportare i record accettati, dichiarandolo esplicitamente.

### R3 — P1: `--verbose` contamina stdout

**Riferimenti:** `src/csvnorm/cli.py:19-23,225`; `src/csvnorm/utils.py:58-60`.

Il banner usa una `Console()` destinata a stdout. Anche `RichHandler` viene creato senza una console esplicitamente destinata a stderr.

**Verifica:** l'output di `csvnorm input.csv -V` comincia con il banner `csvnorm` e messaggi `DEBUG`, prima dei dati CSV.

**Impatto:** redirect e pipe ricevono un contenuto diverso dal CSV promesso. La separazione dati/diagnostica è un requisito del prodotto, non un dettaglio estetico.

**Correzione attesa:** inviare banner verbose, log e diagnostica a stderr quando stdout trasporta i dati. Controllare anche warning ed errori generati direttamente dalla CLI.

**Accettazione:** per input valido, stdout deve essere identico con e senza `-V`; i messaggi aggiuntivi devono essere osservabili soltanto su stderr.

### R4 — P2: il riepilogo conta righe fisiche, non record CSV

**Riferimenti:** `src/csvnorm/utils.py:303` e uso in `_compute_and_show_output()`.

`get_row_count()` salta una riga e conta le successive righe del file. Un campo quotato può però contenere newline senza introdurre nuovi record.

**Input verificato:**

```csv
id,note
1,"hello
world"
2,plain
```

**Risultato:** CSV esportato correttamente, due record dati; riepilogo `Rows: 3`.

**Impatto:** le statistiche non sono attendibili su CSV multilinea, ostacolando il controllo delle quantità esportate.

**Correzione attesa:** usare il conteggio dei record del parser, oppure un lettore CSV configurato con il dialetto dell'output.

**Accettazione:** due record nel caso sopra, inclusi test con newline nelle intestazioni e nei campi.

### R5 — P1: esempio documentale potenzialmente distruttivo

**Riferimento:** `README.md`, sezione iniziale sulla migrazione a v1.0.

L'esempio seguente usa lo stesso percorso per input e redirect:

```bash
csvnorm data.csv > data.csv
```

La shell apre e tronca il file di destinazione prima di avviare il programma. La protezione interna di csvnorm non può impedire questo comportamento.

**Evidenza:** presenza dell'esempio nel README e semantica del redirect della shell. Non è stato eseguito un comando distruttivo sul repository.

**Correzione attesa:** utilizzare due nomi diversi e chiarire che la protezione dell'input riguarda il percorso esplicito passato tramite `-o`, non i redirect gestiti dalla shell.

## Osservazioni tecniche da approfondire

Queste osservazioni derivano dall'ispezione del codice. Non sono presentate come benchmark o bug riprodotti end-to-end.

### P2: report degli errori trattato come testo non strutturato

`src/csvnorm/validation.py:680` usa `split(",")` per interpretare le righe del report. I conteggi dei reject si basano inoltre sulle righe fisiche. Un report CSV può contenere delimitatori quotati e newline; non è garantita la corrispondenza tra righe fisiche, errori e record originali rifiutati.

**Suggerimento:** leggere lo schema reale del report, contare record CSV e distinguere il numero di errori dal numero di record sorgente coinvolti. Aggiungere test con report generati realmente da DuckDB, oltre ai report sintetici.

### P2: uso della memoria e scansioni ripetute

Letture integrali sono presenti in conversione encoding, riparazione mojibake, acquisizione stdin ed emissione stdout. Anche la riscrittura CRLF lavora su buffer completi. La pipeline valida e poi rilegge per normalizzare; ulteriori letture servono per statistiche e riscritture.

Il requisito del PRD relativo a file fino a 1 GB non risulta dimostrato dalle verifiche svolte. Non è corretto dedurre le prestazioni end-to-end dalle sole prestazioni di DuckDB.

**Suggerimento:** misurare tempo, picco RSS e spazio temporaneo su casi rappresentativi; introdurre elaborazione a blocchi dove i risultati mostrano un beneficio. L'output su stdout è attualmente compatibile con le pipe, ma non è uno streaming immediato dei record.

### P2: inferenze e fallback devono essere tracciabili

I fallback possono scegliere delimitatori, saltare righe e usare parsing permissivo. `_detect_header_anomaly()` conta delimitatori nelle prime righe fisiche, senza interpretare il quoting CSV.

**Suggerimento:** rendere visibili dialetto scelto, righe saltate e fallback applicati; consentire override espliciti. Non modificare in questa review la politica di default senza una decisione di prodotto.

### P2: compatibilità dichiarata da verificare

`pyproject.toml` dichiara `duckdb>=0.9.0`, mentre il codice usa opzioni specifiche del lettore CSV e della gestione reject. La verifica corrente usa esclusivamente DuckDB 1.5.2.

**Suggerimento:** testare il minimo dichiarato e una versione recente; aggiornare il vincolo minimo se necessario. Non è stato dimostrato qui quale sia la prima versione pienamente compatibile.

### P3: separazione tra logica e presentazione

Il core chiama direttamente funzioni Rich e trasporta numerosi parametri tra helper. La suddivisione attuale resta comprensibile; non richiede un framework aggiuntivo.

**Suggerimento:** se si introduce un report strutturato, usare un risultato tipizzato essenziale per conteggi, trasformazioni e diagnostica. Separare gradualmente il rendering, senza un refactoring generalizzato preventivo.

## Valutazione dell'idea e del posizionamento

### Punti di forza

- Problema frequente e concreto: CSV utilizzabili ma eterogenei per encoding, delimitatori, intestazioni e struttura.
- Interfaccia semplice che evita di ricostruire ogni volta una pipeline di preparazione.
- DuckDB delega il parsing a un motore specialistico.
- `all_varchar=true` evita conversioni automatiche di tipo e aiuta a conservare rappresentazioni come gli zeri iniziali.
- `--check`, stdin, URL e report degli scarti rispondono a flussi reali.
- Fixture reali, moduli leggibili e test veloci sono una buona base di manutenzione.

### Confine consigliato

Presentare csvnorm come **passo zero strutturale prima dell'analisi**, non come garanzia generale di qualità del dataset. CSV sintatticamente leggibile non significa contenuto corretto, completo o semanticamente valido.

L'uso di `all_varchar` evita conversioni di tipo, ma non dimostra da solo la preservazione integrale di tutti i valori: gestione di null, quoting e riparazioni opzionali richiedono test specifici. Evitare promesse assolute non verificate.

Non prioritizzare trasformazioni di date e numeri, plugin generici o regole di business: allargherebbero molto il prodotto e renderebbero meno netto il suo vantaggio.

## Review della documentazione

**P2: sincronizzazione necessaria tra descrizione e comportamento.**

- README e sito descrivono elaborazione remota senza download preliminare; `_download_remote_if_needed()` scarica sempre gli URL.
- Il README non documenta `-O/--auto-output` nella tabella delle opzioni.
- Il riepilogo viene presentato come esclusivo della modalità file, ma è prodotto anche su stderr con output CSV su stdout.
- Il prima/dopo del sito mostra `ZÃ¼rich` che diventa `Zürich` senza esplicitare `--fix-mojibake`. Conversione dell'encoding e riparazione di testo già decodificato male non sono la stessa operazione.
- Un separatore `;` non è di per sé un errore: è una variante che lo strumento può uniformare.
- `Homepage` e `Issues` in `pyproject.toml` puntano a `aborruso/prepare_data`, mentre README e CLI presentano `aborruso/csvnorm`.
- Il PRD conserva un requisito di output basato su directory che non descrive il default stdout attuale.
- La tabella degli exit code dovrebbe distinguere il fallimento di validazione dagli errori di utilizzo di argparse, che può restituire `2`.

**Proposta editoriale:** aprire il README con problema, installazione e un esempio minimo; spostare l'avviso storico su v1.0 in una sezione migrazione. Esplicitare cosa viene normalizzato, cosa può essere escluso e cosa non viene verificato.

Una formulazione possibile:

> Normalizza i CSV prima dell'analisi: UTF-8, separatori coerenti, intestazioni uniformi e report degli errori strutturali, senza conversione automatica dei tipi.

## Test e integrazione continua

La suite locale eseguita passa, ma non intercetta i quattro difetti operativi riprodotti. Il risultato positivo non equivale quindi alla verifica completa del contratto pubblico.

Il workflow `.github/workflows/publish-pypi.yml` contiene già test su Python 3.9–3.12, mypy e pubblicazione condizionata al successo. Non è corretto descrivere il repository come privo di CI. Questo workflow è però attivato su tag e manualmente: servirebbe anche un controllo ordinario sulle PR.

### Test prioritari proposti

1. Parità degli exit code fra comando installato e `python -m csvnorm`.
2. Matrice strict/non-strict × stdout/file × input valido/invalido.
3. Output preesistente invariato quando strict impedisce la normalizzazione.
4. Invarianza del CSV su stdout con verbose attivo.
5. Conteggi su record multilinea e report reject reali.
6. Conservazione di zeri iniziali, stringhe vuote, null, Unicode e campi quotati.
7. Idempotenza della normalizzazione per un insieme dichiarato di input e opzioni.
8. Separazione esplicita dei test di rete dai test locali riproducibili.

## Riproduzione delle verifiche operative

Eseguire dalla radice del repository con un ambiente che contenga le dipendenze. Il comando seguente usa la virtualenv esistente e crea soltanto materiale temporaneo sotto `tmp/`, eliminato automaticamente.

```bash
.venv/bin/python3 - <<'PY'
import os
import subprocess
import sys
import tempfile
from pathlib import Path

root = Path.cwd()
env = dict(os.environ, PYTHONPATH=str(root / "src"))
entry = [
    sys.executable, "-c",
    "import sys; from csvnorm.cli import main; sys.exit(main())",
]
with tempfile.TemporaryDirectory(dir=root / "tmp", prefix="review_") as tmp:
    work = Path(tmp)
    bad = work / "bad.csv"
    bad.write_text("a,b,c\n1,2,3\n4,5\n6,7,8,9\n", encoding="utf-8")
    multiline = work / "multiline.csv"
    multiline.write_text('id,note\n1,"hello\nworld"\n2,plain\n', encoding="utf-8")
    out = work / "out.csv"
    cases = [
        ("strict_stdout", entry + [str(bad), "--strict"]),
        ("strict_file", entry + [str(bad), "--strict", "-o", str(out)]),
        ("module_strict", [sys.executable, "-m", "csvnorm", str(bad), "--strict"]),
        ("multiline", entry + [str(multiline)]),
        ("verbose", entry + [str(multiline), "-V"]),
    ]
    for name, command in cases:
        result = subprocess.run(
            command, cwd=work, env=env, capture_output=True, text=True
        )
        print(name, "exit=", result.returncode)
        if name == "strict_file":
            print("output_exists=", out.exists())
        print("stdout:", repr(result.stdout[:500]))
        print("stderr:", result.stderr)
PY
```

Suite locale eseguita:

```bash
.venv/bin/python3 -m pytest tests/ -q -m 'not network' -p no:cacheprovider
```

## Evoluzioni consigliate, non ancora implementate

Ordine suggerito, non piano di lavoro approvato:

1. Correggere R1, R2, R3 e R5, quindi R4 e il trattamento strutturato dei reject.
2. Sincronizzare README, sito, help e metadati con il comportamento effettivo.
3. Introdurre report JSON opzionale: conteggi, dialetto, encoding, trasformazioni, fallback e scarti.
4. Consentire override espliciti delle inferenze, almeno encoding e delimitatore di input.
5. Esportare la mappatura intestazioni originali/normalizzate, comprese collisioni e rinominazioni.
6. Misurare prestazioni e spazio temporaneo prima di ottimizzare o ampliare i formati supportati.

Report JSON e override renderebbero il progetto più utile anche per agenti e pipeline automatiche, senza cambiarne la natura.

## Riepilogo conclusivo

- [x] Ispezione di codice, descrizione e test.
- [x] Nuova esecuzione dei test locali.
- [x] Riproduzione isolata dei quattro problemi operativi principali.
- [x] Distinzione fra difetti dimostrati, rischi da verificare e idee di evoluzione.
- [x] Nessuna correzione applicata al codice.

**Priorità di prodotto:** aumentare la fiducia nell'output e la visibilità delle decisioni automatiche. Più verificabile, prima che più potente.
