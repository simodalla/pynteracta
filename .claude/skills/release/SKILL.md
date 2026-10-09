---
name: release
description: Cut a pynteracta release — phase RELEASE of WORKFLOW.md, after the version's specs are verified (/sddpa:verifica) and merged to main. Flips the ROADMAP row(s) to ✅ Shipped, then drives the version bump + tag with python-semantic-release (Option A) and regenerates the CHANGELOG with git-cliff. Use when finishing/shipping a version ("rilascia vX.Y", "chiudi il minor", "release vX.Y.0", "taglia la release"). Never pushes or publishes without an explicit request. Not for planning or implementing (that is the /sddpa:* cycle).
---

# release — taglia la versione (fase RELEASE)

Automatizza la fase **RELEASE** di [`WORKFLOW.md`](../../../WORKFLOW.md) per `pynteracta`. È la
**sola operazione che committa su `main`**: la disciplina dei branch (regola STOP di `CLAUDE.md`,
sezione 5 del metodo `sddpa`) vale per il lavoro delle spec; i commit di release atterrano su `main`
dopo il merge. L'hook `PreToolUse` avvisa che sei su `main` quando modifichi `ROADMAP.md`: qui è
atteso.

## Posizione nel metodo

Dall'adozione del metodo `sddpa` (CLAUDE.md, "Metodo") le fasi PLAN → LOG sono svolte dal ciclo
`/sddpa:*`. In particolare:

- la spec è una cartella `specs/<nn>-<nome>/` con `spec.md`, `plan.md`, `tasks.md`, `verifica.md`;
- `/sddpa:verifica` chiude la spec (`Stato: chiusa` in `spec.md`), scrive la sezione `M<n>` in
  `PROGRESS.md` e propone il merge `--no-ff` su `main`. **Il congelamento della spec è quello**: la
  release non tocca più le intestazioni delle spec;
- una versione può raccogliere **più spec** (es. 0.10.0 = spec 01 + 02, M27–M28): la riga di
  `ROADMAP.md` le elenca tutte nella colonna Spec.

Questa skill fa solo ciò che resta: ROADMAP → ✅, bump + tag, CHANGELOG.

## Modello di release — Opzione A (guida semantic-release)

La versione del pacchetto è **dinamica**: hatchling legge `__version__` da
`src/pynteracta/__init__.py` (`[tool.hatch.version]`). Chi possiede cosa:

| Cosa | Chi | Note |
|---|---|---|
| Numero di versione + tag git + bump di `__version__` | **python-semantic-release** | Calcolato dai Conventional Commits dall'ultimo tag. `tag_format = "v{version}"`, `major_on_zero = false`, `allow_zero_version = true`. |
| `CHANGELOG.md` | **git-cliff** | Per CLAUDE.md. semantic-release gira con `--no-changelog` così i due non si pestano. |
| Riga/e di ROADMAP | **questa skill** (un commit `docs:`) | Solo `ROADMAP.md`. |

> **Invariante:** tra una release e l'altra `__version__` è uguale all'ultimo tag. semantic-release
> lo ristabilisce a ogni release. Se è andato fuori sincrono, riallinealo prima con un commit
> `chore:`; mai far uscire una build con versione vecchia.

## Pre-flight (abortisci se uno fallisce: riporta, non forzare)

1. **Merge fatto.** I branch delle spec della versione sono già uniti su `main` (`git log main`
   mostra i merge `--no-ff`). Questa skill **non** fa merge.
2. **Su main.** `git branch --show-current` == `main`.
3. **Albero pulito.** `git status --porcelain` vuoto. Se sporco, fermati: mai trascinare modifiche
   estranee nella release.
4. **Spec chiuse.** Per ogni spec elencata nella riga ⏳ di ROADMAP, `spec.md` ha `Stato: chiusa`
   ed esiste `verifica.md` senza problemi aperti. Se una spec è `approvata` o `bozza`, fermati:
   serve prima `/sddpa:verifica <nn>`.
5. **Loggato.** `PROGRESS.md` ha la sezione `M<n>` di **ogni** milestone della riga (le scrive
   `verifica`). Se manca, fermati.
6. **Gate verde.** I controlli bloccanti e quelli di verifica della "Configurazione SDD" di CLAUDE.md:
   ```bash
   uv run ruff check . && uv run ruff format --check . && uv run mypy src \
     && uv run pytest -m "not integration and not contract" --cov --cov-fail-under=85 \
     && uv run pytest -m contract \
     && uv run mkdocs build --strict && uv run pre-commit run --all-files
   ```
7. **Invariante di versione.** `__version__` in `src/pynteracta/__init__.py` è uguale all'ultimo
   tag (`git describe --tags --abbrev=0`). Se no, riallinea con un commit `chore:` prima.
8. **Nessuna release precedente lasciata aperta.** Nessun'altra riga ⏳ in ROADMAP il cui tag esiste
   già (`git tag`). Se c'è, chiudila con un commit `docs:` separato prima di procedere.

## Azioni

Calcola la **prossima versione** per prima cosa, mai a occhio:

```bash
uv run semantic-release version --print        # stampa la versione calcolata, senza effetti
```

Usa quel `vX.Y.0` e la **data di oggi** (YYYY-MM-DD) qui sotto.

### 1. Commit documentale: ROADMAP → ✅ (un solo file)

- Nella tabella **Versions** di [`ROADMAP.md`](../../../ROADMAP.md) cambia solo la cella Status
  della riga di questa versione: `⏳ In progress` → `✅ Shipped <oggi>`. Nessun'altra riga.
- Aggiorna, se serve, la nota sotto la tabella ("last used: M<n>").
- **Non toccare** `specs/`: le spec sono già chiuse da `verifica` e non si modificano.
- Commit su `main`, con il solo file indicato (percorso esplicito, mai `git add -A`):
  ```
  docs: release vX.Y.0, riga di ROADMAP a shipped
  ```
  seguito dalla riga `Co-Authored-By` prevista dall'ambiente.

### 2. Bump + tag (semantic-release)

```bash
uv run semantic-release version --no-changelog --no-push --no-vcs-release --skip-build
```

- `--no-changelog` → `CHANGELOG.md` è di git-cliff (passo 3), non di semantic-release.
- `--no-push --no-vcs-release` → **niente esce dalla macchina**; il push è un passo separato.
- `--skip-build` → la wheel la costruisce la CI.

Bumpa `__version__`, crea il proprio commit di versione e tagga `vX.Y.0`. Verifica con
`git show --stat HEAD` e `git tag --points-at HEAD`.

### 3. CHANGELOG (git-cliff)

Rigenera e committa a parte, mai a mano:

```bash
uv run git-cliff --tag vX.Y.0 -o CHANGELOG.md
git commit -m "docs: aggiornamento del CHANGELOG per vX.Y.0" CHANGELOG.md
```

(Il changelog è stato a volte rigenerato a **lotti** per più versioni: se è l'intento, dillo e
fai un commit solo.)

### 4. Consegna

Riporta lo SHA del commit documentale, il commit di versione + tag di semantic-release e il commit
del changelog. **Non fare push e non creare release remote** senza richiesta esplicita; su richiesta:
`git push origin main --follow-tags`. Il push del tag avvia `release.yml` (GitHub Release + PyPI con
trusted publishing): verificare che entrambi siano atterrati prima di annunciare la versione.
Dopo il push su GitHub, lo specchio GitLab si aggiorna a mano con `scripts/mirror_to_gitlab.sh`.

## Guardrail

- Il commit documentale = **esattamente un file** (`ROADMAP.md`). Il bump è il commit separato di
  semantic-release: mai fonderli.
- Mai `semantic-release version` senza `--no-push --no-vcs-release` se non su richiesta di
  pubblicare: il comportamento di default pusha e crea la release remota.
- Mai modificare a mano `CHANGELOG.md`; mai modificare una spec chiusa o una spec in `specs/legacy/`.
- Commit su `main` solo per i commit di release; tutto il resto su branch.
- Messaggi di commit: Conventional Commits con descrizione in italiano (deroga della
  Configurazione SDD).
