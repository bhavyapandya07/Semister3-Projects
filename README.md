# From Trees to Traits — a mini-project in Comparative Genomics & Pan-genomes

A small, self-contained Python project that implements the two review topics on
**real sequence data**, end to end:

1. **PhyloG2P** — using *phylogenetic convergence* to link genotype to phenotype
   across species.
2. **Pan-genome graphs** — replacing a single linear reference with a graph, so
   structural variants become visible and reference bias disappears.

2 Python files, ~1,000 lines. It downloads its own data. No pipelines, no
cluster, no MAFFT/RAxML install.

**It is not a trained model.** Nothing is fitted and reused — every run
recomputes the statistics from scratch for whichever gene, species set and
phenotype you point it at. "Running it on other DNA" just means writing a new
dataset entry.

---

## Run it

```bash
pip install -r requirements.txt
```

```bash
python main.py
```

That does the default dataset (prestin). Other options:

```bash
python main.py --list
```

```bash
python main.py gapdh
```

```bash
python main.py --all
```

Results land in `results/<dataset>/` — the figures plus `report.txt`.

---

## The biological question

**Prestin (gene `SLC26A5`)** is the motor protein of outer hair cells — what
makes mammalian hearing sensitive at high frequency.

Echolocation evolved **independently at least twice**: in toothed whales
(Cetacea) and in laryngeally echolocating bats (Chiroptera). Their last common
ancestor could not echolocate. So if bats and whales share the *same* amino acid
at a site no other mammal has, that residue cannot be inherited — it evolved
**convergently**, and is a candidate for causing the trait.

That is the PhyloG2P logic: *the phylogeny is what turns a correlation into
evidence.*

Two species are deliberate controls: the **fruit bat** is a bat that does *not*
laryngeally echolocate (so it separates "bat" from "echolocating"), and the
**cow** is the closest non-echolocating relative of whales.

---

## Datasets

The gene, the species and the phenotype are all data, not code. Five datasets
ship with the project:

| Dataset | Gene | Species | Phenotype | Role |
|---|---|---|---|---|
| `prestin` | SLC26A5 | 10 mammals | echolocation | main case, has a cryo-EM structure |
| `tmc1` | TMC1 | 10 mammals | echolocation | second hearing gene, same species |
| `otoferlin` | OTOF | 9 mammals | echolocation | third hearing gene, independent of the other two |
| `gapdh` | GAPDH | 10 mammals | echolocation | **negative control** — housekeeping gene, should find nothing |
| `myoglobin` | MB | 11 mammals | deep diving | different gene, trait *and* species set |

### Results

```
dataset     gene     sp    aa sites        p   top hits
prestin     SLC26A5  10   744     2   0.0127   A392, K576
tmc1        TMC1     10   761     2   0.0037   M39, V155
otoferlin   OTOF      9  1997     3   0.0352   E396, L1556, F1983
gapdh       GAPDH    10   335     0   1.0000   -
myoglobin   MB       11   154     0   1.0000   -
```

Read that table carefully — the **negative results matter as much as the
positive ones**:

* **Three independent hair-cell genes are all significant.** Prestin (the
  motor), TMC1 (the mechanotransduction channel) and otoferlin (the synaptic
  calcium sensor) do different jobs in the same cell, and each independently
  shows convergent substitutions in echolocators. Agreement across genes is much
  stronger evidence than any single gene.
* **GAPDH gives exactly 0 sites at p = 1.0.** A housekeeping gene with no link
  to hearing, run through the identical pipeline with the identical species and
  the identical phenotype, finds nothing. That is the control showing the three
  hits above are not an artefact of the method.
* **Myoglobin gives 0 sites** — and that is *correct*. The real published signal
  for diving mammals is an increase in **net surface charge** spread over many
  residues, not one shared amino acid. A per-site identity scan is the wrong
  instrument for that architecture. Good illustration that the method has to
  match the genetics of the trait.

Otoferlin runs on 9 species, not 10: the little brown bat has no usable RefSeq
CDS for OTOF, so the fetcher drops it and says so. The remaining 3 echolocators
still span 2 clades, so the logic holds.

### Prestin in detail

```
perfectly convergent sites : 2
permutation p-value        : 0.0127   (10,000 phenotype shuffles, null mean 0.06)

  site 392: echolocators = A   others = S
  site 576: echolocators = K   others = R
```

At codon 392 the codon is `GCA` (Ala) in all four echolocators and `TCA`/`TCG`
(Ser) in all six others — a single T→G change, hit independently in whales and
in bats. Mapped onto the real cryo-EM structure (PDB **7LGU**, UniProt P58743):

* **S392A** — extracellular loop between transmembrane helices 9 and 10, in the
  transport/motor domain;
* **R576K** — inside the cytoplasmic **STAS** domain.

Pan-genome side:

```
graph : 1615 nodes, 2306 edges, 458 bubbles (455 substitution, 3 indel/SV)
        1260 of 3492 bp (36%) of the graph is NOT on the human reference path

Heaps exponent   DNA 31-mers    gamma = 0.86   core     11 k-mers
                 protein 7-mers gamma = 0.40   core    350 k-mers
```

**36% of the sequence in the graph is invisible to a human-linear-reference
pipeline.** That is reference bias, measured directly.

The two Heaps exponents make a further point: across 100+ My of mammalian
divergence exact nucleotide k-mers are almost entirely genome-specific
(gamma ≈ 0.86, wide open) while protein k-mers keep a solid core (gamma ≈ 0.40).
That is *why* nucleotide-level pan-genome graphs are built **within** a species
(human, microbial) and protein/synteny anchors are used **between** species.

---

## Adding your own gene

Add an entry to `DATASETS` in [main.py](main.py). Accessions are
resolved from NCBI automatically from the gene symbol and organism name:

```python
"rhodopsin": dict(
    gene="RHO", reference="Human",
    trait="nocturnality", positive="nocturnal", negative="diurnal",
    uniprot="P08100",                       # optional: domain track + fig6
    pdb="1F88",                             # optional: 3D structure figure
    species={
        "Human":  ("Homo sapiens",    0, "Primates"),
        "Mouse":  ("Mus musculus",    1, "Rodentia"),
        # label: (organism, phenotype 0/1, clade)
    },
    note="One line describing what this dataset is for."),
```

Then `python main.py rhodopsin`. A 4th tuple element pins an exact accession if
you do not want automatic resolution.

**For the result to mean anything**, the phenotype-positive species must sit in
**more than one clade** — otherwise a shared residue is just inheritance. The
report prints how many clades your foreground spans and warns you if it is one.

---

## Files

Two files:

| File | Lines | What it does |
|---|---|---|
| `main.py` | 569 | Dataset definitions, downloads (NCBI / RCSB / UniProt), alignment, tree, convergence scan, pan-genome graph, k-mer pan-genome, report, CLI |
| `figures.py` | 463 | The six figures, including the 3D DNA helix and the 3D protein structure |

`figures.py` imports nothing from `main.py` — it only reads the result
dictionary — so you can plot from a saved run without re-downloading anything.

---

## What the code actually does

**Alignment.** Each CDS is translated, the proteins are aligned to the reference
species with Biopython's pairwise aligner (BLOSUM62), and the pairwise
alignments are merged into an MSA by the classic *star alignment* rule ("once a
gap, always a gap"). The protein MSA is then back-translated into a
**codon-aware** nucleotide MSA, so no alignment gap can ever shift the frame.

**Phylogeny.** Jukes–Cantor corrected distances → neighbour-joining tree.

**PhyloG2P scan.** For every column,

```
score = max over residues r of [ freq_r(foreground) − freq_r(background) ]
```

A score of **1.0** means every phenotype-positive species shares a residue that
no negative species carries. Significance comes from a **permutation test**:
shuffle the phenotype labels across the same species 10,000 times and ask how
often that many perfect sites appear by chance.

**Pan-genome graph.** From the MSA, invariant stretches collapse into one shared
node; variable stretches open a **bubble** with one node per allele. This is the
data model behind `vg`, `minigraph` and `PGGB`. Nodes are labelled core / shell /
cloud, and bubbles whose alleles differ in *length* are indel/SV bubbles.

**Pan-genome openness.** k-mer rarefaction (Heaps' law) at nucleotide (k=31) and
protein (k=7) level.

---

## The figures

Written to `results/<dataset>/`.

| Figure | Content |
|---|---|
| `fig1_dna_structure.png` | **3D B-DNA double helix** built from the real CDS (3.38 Å rise/bp, 34.3°/bp, 10.5 bp/turn, strands offset 140° so the major and minor grooves are real), the base-pair ladder of the same window, and the top site's codon in every species |
| `fig2_phylogeny.png` | NJ tree + distance matrix, foreground species in red |
| `fig3_phylog2p.png` | Convergence scan along the protein with the domain track behind it, the permutation null, and the residue table at the top sites |
| `fig4_pangenome_graph.png` | The variation graph with its bubbles, the reference path marked, and a length-changing (SV) bubble annotated |
| `fig5_pangenome_openness.png` | Heaps curves, core/shell/cloud spectrum, reference-bias bar |
| `fig6_structure_mapping.png` | The top sites on the **real experimental structure**, plus the topology diagram. Only for datasets that declare a `pdb` |

---

## Honest limitations

Worth stating in a viva — the real gaps between this and a production study:

* **Star alignment**, not a proper progressive/iterative MSA. Fine for
  ~99%-identical orthologs, but it is anchored on the reference species.
* The convergence score is a **presence/absence statistic**, not a model. Real
  tools (RERconverge, PhyloAcc, TRACCER, Forward Genomics) fit substitution-rate
  models along branches and correct for branch length and ancestral state. The
  permutation test here controls for the number of foreground species but not
  for phylogenetic non-independence within a clade.
* **10 species and one gene per run.** A genuine scan uses hundreds of genomes
  genome-wide, with multiple-testing correction.
* Convergent substitution ≠ causation. These are *candidates*; showing causation
  needs functional assays (e.g. patch-clamp on mutant prestin).
* The pan-genome graph is built from one aligned gene, so "core/shell/cloud"
  describes segments of that gene, not whole gene families.
* Automatic accession resolution picks a transcript per species by length. For
  genes with messy isoform annotation this is not good enough — CDH23, for
  example, has human isoforms from 216 to 3354 aa and shorter predicted models
  in other species, so the picker mixes non-comparable transcripts. `main.py`
  prints a warning whenever the chosen CDS lengths vary by more than 25%; if you
  see it, pin the accessions by hand (4th tuple element) before trusting a hit.

---

## Data sources

* Coding sequences — NCBI RefSeq, via E-utilities
* Structure — RCSB PDB **7LGU**, *Structure of human prestin in the presence of NaCl* (cryo-EM)
* Topology & domains — UniProt (e.g. **P58743**, human prestin, 744 aa)

All downloaded at runtime by `main.py`; nothing is hard-coded or simulated.
