"""
Comparative genomics, PhyloG2P and pan-genome graphs on real coding sequences.

  python main.py             one dataset (default: prestin)
  python main.py gapdh       any other dataset
  python main.py --all       every dataset, then a comparison table
  python main.py --list      what is available

A dataset is just a gene, a set of species and a binary phenotype. Accessions
are resolved from NCBI automatically, so a new gene is ~10 lines in DATASETS.
Nothing here is trained or simulated: every run recomputes from real sequence.
"""
import json
import os
import random
import statistics
import sys
import textwrap
import time
import urllib.parse
import urllib.request
from collections import defaultdict

import numpy as np
from Bio.Align import PairwiseAligner, substitution_matrices
from Bio.Phylo.TreeConstruction import DistanceMatrix, DistanceTreeConstructor
from Bio.Seq import Seq

import figures

K_DNA, K_AA = 31, 7                 # k-mer sizes: nucleotide / protein
N_PERM = 10000
EUTILS = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# ------------------------------------------------------------- species ------
# label -> (organism, phenotype 0/1, clade [, pinned accession])
ECHO = {
    "Dolphin":        ("Tursiops truncatus",        1, "Cetacea",        "XM_004320267.4"),
    "SpermWhale":     ("Physeter catodon",          1, "Cetacea",        "XM_024115967.3"),
    "HorseshoeBat":   ("Rhinolophus ferrumequinum", 1, "Chiroptera",     "XM_033088899.1"),
    "LittleBrownBat": ("Myotis lucifugus",          1, "Chiroptera",     "XM_006107698.3"),
    "FruitBat":       ("Pteropus vampyrus",         0, "Chiroptera",     "XM_011365195.2"),
    "Cow":            ("Bos taurus",                0, "Artiodactyla",   "NM_001192878.2"),
    "Horse":          ("Equus caballus",            0, "Perissodactyla", "XM_005609048.4"),
    "Human":          ("Homo sapiens",              0, "Primates",       "NM_198999.3"),
    "Mouse":          ("Mus musculus",              0, "Rodentia",       "NM_030727.5"),
    "Elephant":       ("Loxodonta africana",        0, "Proboscidea",    "XM_064289886.1"),
}
ECHO_AUTO = {k: v[:3] for k, v in ECHO.items()}     # same species, any gene

DIVERS = {
    "SpermWhale": ("Physeter catodon",          1, "Cetacea"),
    "Dolphin":    ("Tursiops truncatus",        1, "Cetacea"),
    "Walrus":     ("Odobenus rosmarus",         1, "Pinnipedia"),
    "MonkSeal":   ("Neomonachus schauinslandi", 1, "Pinnipedia"),
    "Manatee":    ("Trichechus manatus",        1, "Sirenia"),
    "Human":      ("Homo sapiens",              0, "Primates"),
    "Cow":        ("Bos taurus",                0, "Artiodactyla"),
    "Dog":        ("Canis lupus familiaris",    0, "Carnivora"),
    "Horse":      ("Equus caballus",            0, "Perissodactyla"),
    "Mouse":      ("Mus musculus",              0, "Rodentia"),
    "Elephant":   ("Loxodonta africana",        0, "Proboscidea"),
}

ECHO_TRAIT = dict(trait="echolocation", positive="echolocating",
                  negative="not echolocating", reference="Human")

DATASETS = {
    "prestin": dict(gene="SLC26A5", species=ECHO, pdb="7LGU", uniprot="P58743",
                    note="Outer-hair-cell motor protein. The classic PhyloG2P "
                         "test case.", **ECHO_TRAIT),
    "tmc1": dict(gene="TMC1", species=ECHO_AUTO, uniprot="Q8TDI8",
                 note="Pore-forming subunit of the hair-cell mechanotransduction "
                      "channel.", **ECHO_TRAIT),
    "otoferlin": dict(gene="OTOF", species=ECHO_AUTO, uniprot="Q9HC10",
                      note="Calcium sensor for transmitter release at the "
                           "inner-hair-cell synapse.", **ECHO_TRAIT),
    "gapdh": dict(gene="GAPDH", species=ECHO_AUTO,
                  note="NEGATIVE CONTROL: a housekeeping gene with no link to "
                       "hearing. The scan should find nothing.", **ECHO_TRAIT),
    "myoglobin": dict(gene="MB", species=DIVERS, uniprot="P02144",
                      reference="Human", trait="deep diving",
                      positive="deep diver", negative="not a diver",
                      note="Oxygen store of diving mammals - a different gene, "
                           "trait AND species set."),
}


# ====================================================== downloading =========
def _get(url, tries=3):
    for t in range(tries):
        try:
            return urllib.request.urlopen(url, timeout=90).read().decode()
        except Exception:
            if t == tries - 1:
                raise
            time.sleep(2)


def _api(endpoint, **q):
    return _get(EUTILS + endpoint + "?" + urllib.parse.urlencode(q))


def _candidates(gene, organism, pinned=None):
    """Every usable RefSeq CDS of one gene in one species -> {accession: seq}."""
    if pinned:
        ids = [pinned]
    else:
        term = (f'{gene}[Gene Name] AND "{organism}"[Organism] '
                f'AND biomol_mrna[PROP] AND refseq[filter]')
        hits = json.loads(_api("esearch.fcgi", db="nuccore", term=term,
                               retmax=6, retmode="json"))
        ids = hits["esearchresult"]["idlist"]
        if not ids:
            return {}
        d = json.loads(_api("esummary.fcgi", db="nuccore", id=",".join(ids),
                            retmode="json")).get("result", {})
        ids = sorted((d[i]["accessionversion"] for i in d.get("uids", []) if i in d),
                     key=lambda a: not a.startswith("NM_"))       # curated first
    out = {}
    for rec in _api("efetch.fcgi", db="nuccore", id=",".join(ids),
                    rettype="fasta_cds_na", retmode="text").split(">"):
        head = rec.split("\n", 1)[0]
        if f"[gene={gene}]".lower() not in head.lower() or "_cds_" not in head:
            continue
        seq = "".join(rec.split("\n")[1:]).upper()
        acc = head.split("lcl|")[-1].split("_cds_")[0]
        if len(seq) % 3 == 0 and "N" not in seq and "*" not in translate(seq):
            out[acc] = max(out.get(acc, ""), seq, key=len)
    return out


def fetch(name):
    """Download every CDS of a dataset; cache as data/<name>_cds.fasta."""
    cfg, path = DATASETS[name], f"data/{name}_cds.fasta"
    if os.path.exists(path):
        return path
    print(f"downloading {cfg['gene']} for {len(cfg['species'])} species from "
          f"NCBI ...")                          # printed only on a cold run
    cand = {}
    for label, sp in cfg["species"].items():
        try:
            cand[label] = _candidates(cfg["gene"], sp[0],
                                      sp[3] if len(sp) > 3 else None)
        except Exception as exc:                  # one bad species must not stop us
            cand[label] = {}
            print(f"  {label:15s} lookup failed ({exc})")
        if not cand[label]:
            print(f"  {label:15s} {sp[0]:28s} -- no usable CDS, skipped")
        time.sleep(.35)                           # be polite to NCBI

    # Isoform choice: take the longest transcript per species (usually the
    # canonical one), then pick per species the transcript closest to the median
    # of those. Keeps full-length orthologs together instead of mixing isoforms.
    med = statistics.median([max(map(len, v.values())) for v in cand.values() if v]
                            or [0]) or None
    if med is None:
        raise SystemExit(f"no sequences found for {name}")
    rows, picked = [], []
    for label, opts in cand.items():
        if not opts:
            continue
        acc, seq = min(opts.items(), key=lambda kv: abs(len(kv[1]) - med))
        picked.append(len(seq))
        rows.append(f">{label} {acc} len={len(seq)}\n" +
                    "\n".join(seq[i:i + 70] for i in range(0, len(seq), 70)))
    if max(picked) / min(picked) > 1.25:          # orthologs should match in length
        print(f"  !! WARNING: CDS lengths vary {max(picked) / min(picked):.1f}x. "
              f"The species probably have different isoforms annotated for "
              f"{cfg['gene']};\n     hits from this dataset are unreliable - pin "
              f"accessions by hand.")
    open(path, "w").write("\n".join(rows) + "\n")
    return path


def fetch_pdb(pdb):
    path = f"data/{pdb}.pdb"
    if pdb and not os.path.exists(path):
        open(path, "w").write(_get(f"https://files.rcsb.org/download/{pdb}.pdb"))


def topology(uniprot):
    """Transmembrane helices + domains from UniProt -> [(type, start, end, name)]."""
    if not uniprot:
        return []
    path = f"data/{uniprot}_topology.tsv"
    if not os.path.exists(path):
        d = json.loads(_get(f"https://rest.uniprot.org/uniprotkb/{uniprot}.json"))
        open(path, "w").write("\n".join(
            f'{f["type"]}\t{f["location"]["start"]["value"]}'
            f'\t{f["location"]["end"]["value"]}\t{f.get("description", "")}'
            for f in d.get("features", [])
            if f["type"] in ("Transmembrane", "Domain")) + "\n")
    rows = (l.split("\t") for l in open(path).read().splitlines())
    return [(p[0], int(p[1]), int(p[2]), p[3])           # skips any header line
            for p in rows if len(p) == 4 and p[1].isdigit()]


def read_fasta(path):
    seqs, name = {}, None
    for line in open(path):
        if line.startswith(">"):
            name = line[1:].split()[0]
            seqs[name] = []
        else:
            seqs[name].append(line.strip())
    return {k: "".join(v) for k, v in seqs.items()}


def translate(cds):
    return str(Seq(cds).translate()).rstrip("*")


# ======================================================== alignment =========
def star_msa(prot, center):
    """Align everything to one centre sequence and merge the pairwise results
    by the classic 'once a gap, always a gap' rule. ~25 lines, no MAFFT."""
    al = PairwiseAligner(mode="global")
    al.substitution_matrix = substitution_matrices.load("BLOSUM62")
    al.open_gap_score, al.extend_gap_score, al.end_gap_score = -11, -1, 0.0
    ref = prot[center]
    msa = {center: ref}
    for name, s in prot.items():
        if name == center:
            continue
        best = al.align(ref, s)[0]
        r_al, s_al = str(best[0]), str(best[1])
        cur, new = msa[center], {n: [] for n in msa}
        new[name], i, j = [], 0, 0
        while i < len(cur) or j < len(r_al):
            old_gap = i < len(cur) and cur[i] == "-"       # gap already in the MSA
            ins = not old_gap and j < len(r_al) and r_al[j] == "-"   # new insertion
            for n in msa:
                new[n].append("-" if ins else msa[n][i])
            new[name].append("-" if old_gap else s_al[j])
            i, j = i + (not ins), j + (not old_gap)
        msa = {n: "".join(v) for n, v in new.items()}
    return msa


def codon_msa(pmsa, cds):
    """Back-translate a protein MSA to codons, so no gap can shift the frame."""
    out = {}
    for n, aligned in pmsa.items():
        codons = iter([cds[n][i:i + 3] for i in range(0, len(cds[n]), 3)])
        out[n] = "".join("---" if aa == "-" else next(codons) for aa in aligned)
    return out


def distances(msa, names):
    """Jukes-Cantor corrected p-distance over ungapped columns."""
    M = np.array([list(msa[n]) for n in names])
    gap = M == "-"
    D = np.zeros((len(names), len(names)))
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            ok = ~(gap[i] | gap[j])
            p = (M[i][ok] != M[j][ok]).mean()
            D[i, j] = D[j, i] = -0.75 * np.log(1 - 4 * p / 3) if p < .74 else 2.
    return D


def nj_tree(D, names):
    dm = DistanceMatrix(list(names),
                        [[D[i, j] for j in range(i + 1)] for i in range(len(names))])
    t = DistanceTreeConstructor().nj(dm)
    t.root_at_midpoint()
    for c in t.find_clades():                    # hide the auto "Inner1" labels
        if not c.is_terminal():
            c.name = None
    return t


# ========================================================== PhyloG2P ========
def encode(pmsa, names):
    """MSA -> integer matrix (species x columns), gaps = -1, + a column mask."""
    M = np.array([[ord(c) if c != "-" else -1 for c in pmsa[n]] for n in names])
    return M, (M < 0).sum(0) <= 2


def scan(M, keep, fg):
    """PhyloG2P score per column, plus the residue that achieves it.

    score = max over residues r of [ freq_r(foreground) - freq_r(background) ]

    A score of 1.0 means every phenotype-positive species carries a residue that
    no negative species has. Because the foreground is polyphyletic, such a
    residue cannot be inherited - it is convergent.
    """
    F, B = M[fg], M[~fg]
    best = np.full(M.shape[1], -1.0)
    res = np.zeros(M.shape[1], int)
    for row in F:                                # the max is always a foreground residue
        s = (F == row).mean(0) - (B == row).mean(0)
        u = (s > best) & (row >= 0)
        best[u], res[u] = s[u], row[u]
    return np.where(keep, best, np.nan), res


def _n_perfect(M, keep, fg):
    """Fast count of perfect columns - the inner loop of the permutation test."""
    F, B = M[fg], M[~fg]
    return int((keep & (F == F[0]).all(0) & (F[0] >= 0) & (B != F[0]).all(0)).sum())


def permutation_test(M, keep, fg, n=N_PERM, seed=0):
    """Are there more perfect sites than when the phenotype labels are shuffled
    across the very same species?"""
    obs = _n_perfect(M, keep, fg)
    rng = np.random.default_rng(seed)
    null = np.array([_n_perfect(M, keep, rng.permutation(fg)) for _ in range(n)])
    return obs, null, (np.sum(null >= obs) + 1) / (n + 1)


def ref_positions(pmsa, ref):
    """MSA column -> 1-based residue number in the reference (0 where gapped)."""
    p, out = 0, []
    for c in pmsa[ref]:
        p += c != "-"
        out.append(p if c != "-" else 0)
    return np.array(out)


# =================================================== pan-genome graph =======
def variation_graph(msa, names):
    """The data model behind vg / minigraph / PGGB: invariant stretches collapse
    into one shared node, variable stretches open a BUBBLE, one node per allele."""
    cols = list(zip(*[msa[n] for n in names]))
    var = [len(set(c)) > 1 for c in cols]
    blocks, i = [], 0
    while i < len(cols):                                   # run-length encode
        j = i
        while j < len(cols) and var[j] == var[i]:
            j += 1
        blocks.append((i, j, var[i]))
        i = j

    nodes, allset = [], set(names)
    for bi, (s, e, v) in enumerate(blocks):
        if not v:
            nodes.append(dict(block=bi, seq="".join(c[0] for c in cols[s:e]),
                              members=allset))
        else:
            alleles = defaultdict(set)
            for k, n in enumerate(names):
                alleles["".join(cols[c][k] for c in range(s, e)).replace("-", "")].add(n)
            for a, mem in sorted(alleles.items(), key=lambda x: (-len(x[1]), x[0])):
                nodes.append(dict(block=bi, seq=a, members=mem))
    for k, nd in enumerate(nodes):
        m = len(nd["members"])
        nd["id"] = k
        nd["kind"] = "core" if m == len(names) else ("shell" if m > 1 else "cloud")

    edges = [(u["id"], w["id"], len(u["members"] & w["members"]))
             for b in range(len(blocks) - 1)
             for u in nodes if u["block"] == b
             for w in nodes if w["block"] == b + 1 and (u["members"] & w["members"])]

    bubbles = []
    for bi, (s, e, v) in enumerate(blocks):
        alle = [n for n in nodes if n["block"] == bi]
        if v and len(alle) > 1:
            lens = {len(a["seq"]) for a in alle}
            bubbles.append(dict(block=bi, n_alleles=len(alle),
                                kind="indel/SV" if len(lens) > 1 else "substitution",
                                span=max(lens) - min(lens)))
    return dict(nodes=nodes, edges=edges, blocks=blocks, bubbles=bubbles)


def reference_bias(g, ref):
    """bp of real sequence a LINEAR reference simply cannot represent."""
    missing = sum(len(n["seq"]) for n in g["nodes"] if ref not in n["members"])
    return missing, sum(len(n["seq"]) for n in g["nodes"])


# ==================================================== k-mer pan-genome ======
def dna_kmers(seq, k=K_DNA):
    """Canonical k-mers (strand-independent, as real k-mer tools use)."""
    rc = str(Seq(seq).reverse_complement())
    n = len(seq)
    return {min(seq[i:i + k], rc[n - k - i: n - i]) for i in range(n - k + 1)}


def aa_kmers(seq, k=K_AA):
    return {seq[i:i + k] for i in range(len(seq) - k + 1)}


def spectrum(kmers, names):
    """core / shell / cloud - the standard pan-genome partition."""
    spec = defaultdict(int)
    for km in set().union(*kmers.values()):
        spec[sum(km in kmers[n] for n in names)] += 1
    N = len(names)
    return dict(spectrum=dict(spec), core=spec[N], cloud=spec[1],
                shell=sum(v for k, v in spec.items() if 1 < k < N))


def heaps(kmers, names, reps=200, seed=0):
    """Rarefaction: pan (union) and core (intersection) growth, + Heaps exponent."""
    rng = random.Random(seed)
    pan = np.zeros((reps, len(names)))
    core = np.zeros_like(pan)
    for r in range(reps):
        order = names[:]
        rng.shuffle(order)
        u, c = set(), None
        for i, n in enumerate(order):
            u |= kmers[n]
            c = kmers[n] if c is None else (c & kmers[n])
            pan[r, i], core[r, i] = len(u), len(c)
    pan, core = pan.mean(0), core.mean(0)
    n = np.arange(1, len(names) + 1)
    return pan, core, np.polyfit(np.log(n[1:]), np.log(pan[1:]), 1)[0]


# ============================================================= driver =======
def run(name):
    cfg = DATASETS[name]
    cds = read_fasta(fetch(name))
    names = [n for n in cfg["species"] if n in cds]       # stable, biological order
    ref = cfg["reference"]
    if ref not in names:
        raise SystemExit(f"reference {ref} missing from dataset {name}")
    cds = {n: cds[n] for n in names}
    trait = {n: cfg["species"][n][1] for n in names}
    prot = {n: translate(s) for n, s in cds.items()}

    pmsa = star_msa(prot, ref)
    nmsa = codon_msa(pmsa, cds)
    D = distances(nmsa, names)
    M, keep = encode(pmsa, names)
    fg = np.array([trait[n] == 1 for n in names])
    scores, res = scan(M, keep, fg)
    obs, null, pval = permutation_test(M, keep, fg)
    rp = ref_positions(pmsa, ref)

    def sites(cols):
        return [(int(c), int(rp[c]), chr(res[c]), {n: pmsa[n][c] for n in names})
                for c in cols]

    hits = sites(sorted(np.where(scores >= 1.0)[0], key=lambda c: rp[c]))
    top = sites(np.argsort(-np.nan_to_num(scores, nan=-9))[:3])
    g = variation_graph(nmsa, names)
    kd = {n: dna_kmers(s) for n, s in cds.items()}
    ka = {n: aa_kmers(s) for n, s in prot.items()}
    pan_d, core_d, gam_d = heaps(kd, names)
    pan_a, core_a, gam_a = heaps(ka, names)

    return dict(
        name=name, ref=ref, gene=cfg["gene"], trait=trait, k=(K_DNA, K_AA),
        positive=cfg["positive"], negative=cfg["negative"], phenotype=cfg["trait"],
        note=cfg["note"], pdb=cfg.get("pdb"), uniprot=cfg.get("uniprot"),
        topo=topology(cfg.get("uniprot")),
        clade={n: cfg["species"][n][2] for n in names},
        cds=cds, prot=prot, pmsa=pmsa, nmsa=nmsa, names=names,
        D=D, tree=nj_tree(D, names), scores=scores, hits=hits, top=top,
        obs=obs, null=null, pval=pval, graph=g, bias=reference_bias(g, ref),
        pan_dna=pan_d, core_dna=core_d, gamma_dna=gam_d,
        pan_aa=pan_a, core_aa=core_a, gamma_aa=gam_a,
        spec_dna=spectrum(kd, names), spec_aa=spectrum(ka, names))


def report(r):
    g, (miss, tot) = r["graph"], r["bias"]
    nk = lambda k: sum(1 for n in g["nodes"] if n["kind"] == k)
    bk = lambda k: sum(1 for b in g["bubbles"] if b["kind"] == k)
    ks = lambda s: f"core {s['core']}, shell {s['shell']}, cloud {s['cloud']}"
    fg = [n for n in r["names"] if r["trait"][n]]
    clades = sorted({r["clade"][n] for n in fg})
    bar = "=" * 74

    L = [bar, f"{r['name'].upper()}  ({r['gene']})  vs  "
              f"{r['phenotype'].upper()}".center(74), bar,
         textwrap.fill(r["note"], 74),
         "\n1. DATASET (real RefSeq coding sequences)"]
    L += [f"   {n:15s} {len(r['cds'][n]):6d} bp {len(r['prot'][n]):5d} aa  "
          f"{r['clade'][n]:14s} "
          f"{r['positive'].upper() if r['trait'][n] else '-'}" for n in r["names"]]
    L += [f"   codon-aware alignment: {len(r['nmsa'][r['ref']])} nt / "
          f"{len(r['pmsa'][r['ref']])} codons   reference: {r['ref']}",
          "\n2. PHYLOGENY",
          f"   {len(fg)} of {len(r['names'])} species are {r['positive']}, across "
          f"{len(clades)} clades:",
          f"   {', '.join(clades)}",
          f"   -> {r['phenotype']} is polyphyletic here, so a residue shared by\n"
          f"      all of them cannot be inherited: it is convergent."
          if len(clades) > 1 else
          "   -> WARNING: a single clade, so shared residues may simply be\n"
          "      inherited. Any hit below is NOT evidence of convergence.",
          "\n3. PhyloG2P CONVERGENCE SCAN",
          f"   perfectly convergent sites : {r['obs']}",
          f"   permutation p-value        : {r['pval']:.4f} "
          f"({len(r['null']):,} shuffles, null mean {r['null'].mean():.2f})"]
    if r["hits"]:
        L += [f"   -> site {pos}: {r['positive']} = {aa}, others = "
              f"{','.join(sorted({v for k, v in col.items() if not r['trait'][k]}))}"
              for c, pos, aa, col in r["hits"]]
    else:
        L.append("   no perfectly convergent site. Top-scoring sites instead:")
        L += [f"   -> site {pos}: best residue {aa}, score {r['scores'][c]:.2f}"
              for c, pos, aa, col in r["top"]]

    L += ["\n4. PAN-GENOME GRAPH",
          f"   nodes {len(g['nodes'])}  edges {len(g['edges'])}  "
          f"bubbles {len(g['bubbles'])}",
          f"   node classes: core {nk('core')}, shell {nk('shell')}, "
          f"cloud {nk('cloud')}",
          f"   bubbles: {bk('substitution')} substitution, {bk('indel/SV')} indel/SV",
          f"   reference bias: {miss} of {tot} bp ({100 * miss / tot:.1f}%) of the "
          f"graph is NOT",
          f"   on the linear {r['ref']} reference - invisible to a linear pipeline.",
          "\n5. PAN-GENOME OPENNESS (Heaps exponent; 0 = closed, 1 = wide open)",
          f"   DNA {K_DNA}-mers    : gamma = {r['gamma_dna']:.3f}   "
          f"{ks(r['spec_dna'])}",
          f"   protein {K_AA}-mers : gamma = {r['gamma_aa']:.3f}   "
          f"{ks(r['spec_aa'])}", bar]
    return "\n".join(L)


def run_one(name):
    fetch(name)
    fetch_pdb(DATASETS[name].get("pdb"))
    r = run(name)
    figures.make_all(r)
    txt = report(r)
    os.makedirs(f"results/{name}", exist_ok=True)
    open(f"results/{name}/report.txt", "w").write(txt + "\n")
    print("\n" + txt)
    return r


def summary(rs):
    print("\n" + "=" * 74)
    print("COMPARISON ACROSS DATASETS".center(74))
    print("=" * 74)
    print(f"{'dataset':11s} {'gene':7s} {'sp':>3s} {'aa':>5s} {'sites':>5s} "
          f"{'p':>8s}   top hits")
    for r in rs:
        print(f"{r['name']:11s} {r['gene']:7s} {len(r['names']):3d} "
              f"{len(r['prot'][r['ref']]):5d} {r['obs']:5d} {r['pval']:8.4f}   "
              f"{', '.join(f'{h[2]}{h[1]}' for h in r['hits']) or '-'}")
    print("=" * 74)


if __name__ == "__main__":
    for d in ("data", "results"):
        os.makedirs(d, exist_ok=True)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--list" in sys.argv:
        print(f"{'dataset':12s} {'gene':8s} {'species':>7s}  trait")
        for k, c in DATASETS.items():
            print(f"{k:12s} {c['gene']:8s} {len(c['species']):7d}  {c['trait']}")
    elif "--all" in sys.argv:
        done = []
        for n in DATASETS:
            try:
                done.append(run_one(n))
            except Exception as exc:              # keep going through the rest
                print(f"!! {n} failed: {exc}")
        summary(done)
    else:
        run_one(args[0] if args else "prestin")
