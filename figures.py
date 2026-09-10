"""
figures.py - every figure. Standalone: it only reads the result dict from main.

  fig1  3D B-DNA double helix + base-pair ladder + the codon in every species
  fig2  phylogeny + distance matrix    -> is the phenotype polyphyletic?
  fig3  PhyloG2P scan + permutation null + residue table
  fig4  pan-genome variation graph with bubbles (the vg / minigraph data model)
  fig5  pan-genome openness: Heaps curves, core/shell/cloud, reference bias
  fig6  top sites on the real experimental structure (only if the dataset has one)
"""
import os

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Patch
from mpl_toolkits.mplot3d.art3d import Line3DCollection
from Bio import Phylo

BASE = {"A": "#3AA655", "T": "#E03B3B", "G": "#F0A202", "C": "#2E7DD1"}
COMP = {"A": "T", "T": "A", "G": "C", "C": "G"}
FG, BG = "#C1272D", "#3A6EA5"                  # phenotype positive / negative
KIND = {"core": "#2E7DD1", "shell": "#F0A202", "cloud": "#C1272D"}
TMC, DOMC = "#2E7DD1", "#F0A202"               # transmembrane / soluble domain
plt.rcParams.update({"font.size": 9, "axes.titleweight": "bold",
                     "figure.facecolor": "white", "savefig.facecolor": "white"})


def _save(fig, r, stem):
    d = f"results/{r['name']}"
    os.makedirs(d, exist_ok=True)
    fig.savefig(f"{d}/{stem}.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def _clean(ax, *spines):
    for s in spines or ("top", "right"):
        ax.spines[s].set_visible(False)


def _name(ax, x, y, nm, echo, size=8.5):
    ax.text(x, y, nm, ha="right", va="center", fontsize=size,
            color=FG if echo else BG, fontweight="bold" if echo else "normal")


# ================================================================ 1. DNA =====
def bdna(n, rise=3.38, twist=34.3, radius=10.0, groove=140.0, fine=1):
    """Ideal B-DNA backbone coordinates in Angstrom.

    3.38 A rise/bp and 34.3 deg/bp give the canonical ~10.5 bp per turn. The two
    strands sit 140 deg apart, not 180 - that offset is what creates the wide
    major groove and the narrow minor groove.
    """
    i = np.linspace(0, n - 1, (n - 1) * fine + 1) if fine > 1 else np.arange(n)
    th, ph = np.deg2rad(twist) * i, np.deg2rad(groove)
    return (np.c_[radius * np.cos(th), radius * np.sin(th), rise * i],
            np.c_[radius * np.cos(th + ph), radius * np.sin(th + ph), rise * i])


def fig1_dna(r, win=4):
    """3D helix + ladder + the codon of the top site in every species."""
    site = (r["hits"] or r["top"])[0]
    col, pos = site[0], site[1]
    cds = r["cds"][r["ref"]]
    lo = max(0, (pos - 1) * 3 - win * 3)
    seq = cds[lo: lo + (2 * win + 1) * 3]
    cod0, n = (pos - 1) * 3 - lo, len(seq)

    fig = plt.figure(figsize=(14, 7.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1, 1.65], height_ratios=[1, 1.15],
                          wspace=.02, hspace=.30)

    # ---- 3D double helix ---------------------------------------------------
    ax = fig.add_subplot(gs[:, 0], projection="3d")
    for s, c in zip(bdna(n, fine=16), ("#3E4A63", "#93A0B5")):   # backbones
        ax.plot(s[:, 0], s[:, 1], s[:, 2], color=c, lw=3.6, solid_capstyle="round")
    p, q = bdna(n)
    segs, cols, lws = [], [], []
    for i, b in enumerate(seq):
        mid = (p[i] + q[i]) / 2
        segs += [[p[i] * .8 + mid * .2, mid], [q[i] * .8 + mid * .2, mid]]
        cols += [BASE[b], BASE[COMP[b]]]
        lws += [4.2 if b in "GC" else 2.6] * 2       # G:C 3 H-bonds, A:T 2
    ax.add_collection3d(Line3DCollection(segs, colors=cols, linewidths=lws, zorder=3))
    ax.add_collection3d(Line3DCollection(                        # the codon
        [[p[i], q[i]] for i in range(cod0, cod0 + 3)],
        colors=[FG] * 3, linewidths=8, alpha=.3, zorder=1))
    ax.text(0, 15, p[cod0 + 1, 2], f"  codon {pos}", color=FG,
            fontweight="bold", fontsize=10)
    ax.set_axis_off()
    ax.set_xlim(-15, 15); ax.set_ylim(-15, 15)
    ax.set_zlim(-3.38 * 4, 3.38 * (n + 3))           # margin for legend/caption
    ax.set_box_aspect((1, 1, 3.6)); ax.view_init(elev=8, azim=24)
    ax.set_title(f"A  B-DNA double helix\nreal {r['ref']} {r['gene']} CDS, "
                 f"nt {lo + 1}-{lo + n}", pad=-6)
    ax.text2D(.5, .015, "3.38 A rise/bp   34.3 deg/bp   10.5 bp/turn   20 A wide\n"
              "strands offset 140 deg -> major + minor groove",
              transform=ax.transAxes, ha="center", fontsize=7.4, color="#5A6672")
    ax.legend(handles=[Patch(color=v, label=k) for k, v in BASE.items()],
              loc="upper center", ncol=4, frameon=False, fontsize=8.5,
              bbox_to_anchor=(.5, .99), handlelength=1.1, columnspacing=1.0)

    # ---- base-pair ladder --------------------------------------------------
    ax2 = fig.add_subplot(gs[0, 1])
    for i, b in enumerate(seq):
        hb = 3 if b in "GC" else 2
        for k in range(hb):
            x = i + .1 * (k - (hb - 1) / 2)
            ax2.plot([x, x], [.34, .66], color="#B4BCC6", lw=1.2, zorder=1)
        for y, ch in ((.78, b), (.22, COMP[b])):
            ax2.text(i, y, ch, ha="center", va="center", color=BASE[ch],
                     fontweight="bold", fontsize=11, zorder=3)
    for y, c in ((.94, "#3E4A63"), (.06, "#93A0B5")):
        ax2.plot([-.6, n - .4], [y, y], color=c, lw=3.5)
    ax2.add_patch(FancyBboxPatch((cod0 - .42, .10), 2.84, .80, ec=FG, fc="none",
                                 boxstyle="round,pad=0.03,rounding_size=0.06",
                                 lw=2, zorder=4))
    for x, ha, top, bot in ((-1.0, "right", "5'", "3'"), (n, "left", "3'", "5'")):
        ax2.text(x, .94, top, ha=ha, va="center", fontsize=9)
        ax2.text(x, .06, bot, ha=ha, va="center", fontsize=9)
    ax2.set_xlim(-2.2, n + 1.2); ax2.set_ylim(-.02, 1.02); ax2.axis("off")
    ax2.set_title("B  Base-pair ladder of the same window "
                  "(A:T = 2 H-bonds, G:C = 3)", pad=8)

    # ---- the codon in every species ---------------------------------------
    ax3 = fig.add_subplot(gs[1, 1])
    order = sorted(r["names"], key=lambda x: -r["trait"][x])
    nfg = sum(r["trait"].values())
    for j, nm in enumerate(order):
        y, echo = len(order) - j - 1, r["trait"][nm]
        _name(ax3, -.6, y, nm, echo, 9)
        for k, b in enumerate(r["nmsa"][nm][3 * col: 3 * col + 3]):
            ax3.text(k, y, b, ha="center", va="center", fontsize=11,
                     fontweight="bold", color=BASE.get(b, "#888"))
        ax3.text(3.5, y, "→", ha="center", va="center", color="#9AA6B2")
        ax3.add_patch(plt.Rectangle((4.3, y - .36), .8, .72, ec="white", lw=1.4,
                                    fc=FG if echo else "#EDF1F5"))
        ax3.text(4.7, y, r["pmsa"][nm][col], ha="center", va="center", fontsize=11,
                 fontweight="bold", color="white" if echo else "#3B3B3B")
    ax3.axhline(len(order) - nfg - .5, color="#C9D2DC", lw=1, ls="--")
    for yy, lab, c, w in ((len(order) - nfg / 2 - .5, r["positive"], FG, "bold"),
                          ((len(order) - nfg) / 2 - .5, r["negative"], BG, "normal")):
        ax3.text(5.6, yy, lab, color=c, fontsize=8.5, rotation=90, va="center",
                 ha="center", fontweight=w)
    ax3.set_xlim(-4.6, 6.9); ax3.set_ylim(-.7, len(order) - .3); ax3.axis("off")
    ax3.set_title(f"C  Codon {pos} in all {len(order)} species: " +
                  ("the codon change that flips the amino acid" if site in r["hits"]
                   else "best-scoring site (NOT perfectly convergent)"), pad=8)
    _save(fig, r, "fig1_dna_structure")


# ========================================================== 2. phylogeny =====
def fig2_tree(r):
    names = r["names"]
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13, 5.4),
                                  gridspec_kw={"width_ratios": [1.25, 1]})
    Phylo.draw(r["tree"], axes=ax, do_show=False, show_confidence=False,
               label_colors=lambda n: FG if r["trait"].get(n) else BG)
    ax.set_title(f"A  Neighbour-joining tree of {r['gene']} CDS\n"
                 f"red = {r['positive']} (separate clades = independent origins)")
    ax.set_xlabel("substitutions per site (Jukes-Cantor)")
    ax.set_ylabel(""); ax.set_yticks([])
    _clean(ax, "top", "right", "left")

    im = ax2.imshow(r["D"], cmap="viridis_r")
    ax2.set_xticks(range(len(names))); ax2.set_yticks(range(len(names)))
    ax2.set_xticklabels(names, rotation=90); ax2.set_yticklabels(names)
    for get in (ax2.get_xticklabels, ax2.get_yticklabels):
        for t, nm in zip(get(), names):
            t.set_color(FG if r["trait"][nm] else BG)
    ax2.set_title("B  Pairwise genetic distance")
    fig.colorbar(im, ax=ax2, shrink=.8, label="JC distance")
    _save(fig, r, "fig2_phylogeny")


# =========================================================== 3. PhyloG2P =====
def fig3_phylog2p(r):
    names, sc = r["names"], r["scores"]
    x = np.arange(1, len(sc) + 1)
    fig = plt.figure(figsize=(13.5, 7.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.05], hspace=.42, wspace=.24)

    # ---- the scan along the protein ---------------------------------------
    ax = fig.add_subplot(gs[0, :])
    tmx = [(s, e) for t, s, e, d in r["topo"] if t == "Transmembrane"]
    for t, s, e, d in r["topo"]:
        ax.axvspan(s, e, color="#E8EEF6" if t == "Transmembrane" else "#FBF0DA",
                   zorder=0)
        if t == "Domain":
            ax.text((s + e) / 2, -.22, f"{d} domain", ha="center", fontsize=8,
                    color="#8A6D1F")
    if tmx:
        ax.text(np.mean(tmx), -.22, "transmembrane helices (shaded)",
                ha="center", fontsize=8, color="#4A6B93")
    ax.vlines(x, 0, np.nan_to_num(sc), color="#B9C4D0", lw=.8)
    ax.scatter(x, sc, s=9, color="#7C8896", zorder=3)
    for c, pos, res, colmn in r["hits"]:
        ax.scatter([c + 1], [sc[c]], s=90, color=FG, zorder=4, edgecolor="k", lw=.6)
        ax.annotate(f"{res}{pos}", (c + 1, sc[c]), textcoords="offset points",
                    xytext=(0, 11), ha="center", color=FG, fontweight="bold")
    ax.axhline(1.0, ls="--", lw=1, color=FG)
    ax.set_xlim(0, len(sc) + 1); ax.set_ylim(-.32, 1.30)
    ax.set_xlabel(f"residue position in {r['ref']} {r['gene']} "
                  f"({len(r['prot'][r['ref']])} aa)")
    ax.set_ylabel("convergence score")
    ax.set_title(f"A  PhyloG2P scan:  score = freq({r['positive']}) "
                 f"- freq({r['negative']})")

    # ---- permutation null --------------------------------------------------
    ax = fig.add_subplot(gs[1, 0])
    mx = max(r["null"].max(), r["obs"]) + 1
    ax.hist(r["null"], bins=np.arange(-.5, mx + 1), color="#B9C4D0", edgecolor="white")
    ax.axvline(r["obs"], color=FG, lw=2.5)
    left = r["obs"] < mx / 2                          # keep the label on canvas
    ax.annotate(f"observed = {r['obs']}\np = {r['pval']:.4f}",
                xy=(r["obs"], .55), xycoords=("data", "axes fraction"),
                xytext=(9 if left else -9, 0), textcoords="offset points",
                ha="left" if left else "right", va="center",
                color=FG, fontweight="bold")       # y in axes coords: log-safe
    ax.set_yscale("log"); ax.set_xlim(-.6, mx - .4); ax.set_xticks(range(int(mx)))
    ax.set_xlabel("perfectly convergent sites"); ax.set_ylabel("permutations (log)")
    ax.set_title(f"B  Null: {len(r['null']):,} phenotype shuffles")

    # ---- residues at the top sites ----------------------------------------
    ax = fig.add_subplot(gs[1, 1])
    hits = r["hits"] or r["top"]
    for j, nm in enumerate(names):
        y = len(names) - j - 1
        _name(ax, -.35, y, nm, r["trait"][nm])
        for i, (c, pos, res, colmn) in enumerate(hits):
            aa = colmn[nm]
            ax.add_patch(plt.Rectangle((i - .34, y - .38), .68, .76, ec="white",
                                       lw=1.4, fc=FG if aa == res else "#EDF1F5"))
            ax.text(i, y, aa, ha="center", va="center", fontsize=9,
                    fontweight="bold", color="white" if aa == res else "#3B3B3B")
    ax.set_xlim(-2.6, len(hits) - .4); ax.set_ylim(-.7, len(names) - .3)
    ax.set_xticks(range(len(hits)))
    ax.set_xticklabels([f"{h[2]}{h[1]}" for h in hits], fontweight="bold")
    ax.set_yticks([])
    ax.set_title("C  Residues at the convergent sites" if r["hits"]
                 else "C  Residues at the top-scoring sites")
    _clean(ax, *ax.spines)
    _save(fig, r, "fig3_phylog2p")


# =================================================== 4. pan-genome graph =====
def fig4_graph(r):
    """A window of the variation graph around a length-changing bubble."""
    g, N = r["graph"], len(r["names"])
    sv = [b for b in g["bubbles"] if b["kind"] == "indel/SV"]
    focus = (sv or g["bubbles"])[0]["block"]
    b0, b1 = max(0, focus - 4), min(len(g["blocks"]), focus + 5)
    sub = [n for n in g["nodes"] if b0 <= n["block"] < b1]

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(13.5, 8),
                                  gridspec_kw={"height_ratios": [2.1, 1]})
    xp, yp = {}, {}
    for bi in range(b0, b1):
        alle = [n for n in sub if n["block"] == bi]
        for k, nd in enumerate(alle):
            xp[nd["id"]], yp[nd["id"]] = bi - b0, -(k - (len(alle) - 1) / 2) * 1.25

    for u, v, w in g["edges"]:
        if u in xp and v in xp:
            ax.plot([xp[u] + .34, xp[v] - .34], [yp[u], yp[v]], color="#9AA6B2",
                    lw=.5 + 1.6 * w / N, zorder=1, solid_capstyle="round")
    for nd in sub:
        x, y, s = xp[nd["id"]], yp[nd["id"]], nd["seq"]
        ax.add_patch(FancyBboxPatch((x - .34, y - .26), .68, .52, lw=1.6, zorder=2,
                                    boxstyle="round,pad=0.02,rounding_size=0.12",
                                    fc=KIND[nd["kind"]], ec="white"))
        ax.text(x, y, (s if len(s) <= 8 else s[:6] + "..") or "(del)", zorder=3,
                ha="center", va="center", color="white", fontsize=7.5, fontweight="bold")
        if r["ref"] in nd["members"]:                     # the linear reference path
            ax.add_patch(FancyBboxPatch((x - .38, y - .30), .76, .60, lw=1.8, ls=":",
                                        boxstyle="round,pad=0.02,rounding_size=0.12",
                                        fc="none", ec="k", zorder=4))
        ax.text(x, y - .40, f"{len(nd['members'])}/{N}", ha="center", va="top",
                fontsize=6.5, color="#5A6672", zorder=3)
    ylo = min(yp[n["id"]] for n in sub if n["block"] == focus)
    ax.annotate("length-changing bubble\n= structural variant",
                xy=(focus - b0, ylo - .45), xytext=(focus - b0 + 1.1, ylo - 1.5),
                color="#5A3E85", fontweight="bold", fontsize=8.5, ha="center",
                arrowprops=dict(arrowstyle="->", color="#5A3E85", lw=1.6))
    ax.set_xlim(-.9, b1 - b0 - .1); ax.axis("off")
    ax.set_title("A  Pan-genome variation graph (window around a length-changing "
                 "bubble)\ndotted outline = path of the linear reference; "
                 "labels = allele sequence and how many genomes carry it")
    ax.legend(handles=[Patch(color=KIND[k], label=f"{k} node") for k in KIND] +
              [plt.Line2D([], [], color="k", ls=":",
                          label=f"{r['ref']} reference path")],
              loc="lower center", ncol=4, frameon=False, bbox_to_anchor=(.5, -.06))

    miss, tot = r["bias"]
    cnt = [sum(1 for n in g["nodes"] if n["kind"] == k) for k in KIND]
    bub = [sum(1 for b in g["bubbles"] if b["kind"] == k)
           for k in ("substitution", "indel/SV")]
    bars = ax2.bar(["core nodes", "shell nodes", "cloud nodes",
                    "substitution\nbubbles", "indel / SV\nbubbles"], cnt + bub,
                   color=list(KIND.values()) + ["#7C8896", "#5A3E85"], width=.6)
    ax2.bar_label(bars, fontsize=9, fontweight="bold", padding=2)
    ax2.set_ylim(0, max(cnt + bub) * 1.25)
    ax2.set_title(f"B  Graph contents:  {len(g['nodes'])} nodes, "
                  f"{len(g['edges'])} edges, {len(g['bubbles'])} bubbles   |   "
                  f"{miss} of {tot} bp ({100 * miss / tot:.0f}%) are OFF the "
                  f"{r['ref']} reference path")
    _clean(ax2)
    _save(fig, r, "fig4_pangenome_graph")


# ================================================ 5. pan-genome openness =====
def fig5_pangenome(r):
    N = len(r["names"])
    n = np.arange(1, N + 1)
    kd, ka = r["k"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.4))

    ax = axes[0]
    for pan, core, gam, c, lab in (
            (r["pan_dna"], r["core_dna"], r["gamma_dna"], "#C1272D", f"DNA {kd}-mers"),
            (r["pan_aa"], r["core_aa"], r["gamma_aa"], "#2E7DD1", f"protein {ka}-mers")):
        ax.plot(n, pan, "o-", color=c, label=f"pan, {lab} (gamma={gam:.2f})")
        ax.plot(n, core, "s--", color=c, alpha=.5, label=f"core, {lab}")
    ax.set_xlabel("genomes sampled"); ax.set_ylabel("distinct k-mers")
    ax.set_yscale("log"); ax.legend(fontsize=7.2, frameon=False)
    ax.set_title("A  Pan / core rarefaction (Heaps)")

    ax = axes[1]
    for off, spec, c, lab in ((-.19, r["spec_dna"], "#C1272D", "DNA"),
                              (.19, r["spec_aa"], "#2E7DD1", "protein")):
        ax.bar(n + off, [spec["spectrum"].get(i, 0) for i in n], width=.38,
               color=c, label=lab)
    ax.set_xticks(n); ax.set_yscale("log")
    ax.set_xlabel("k-mer present in how many genomes")
    ax.set_ylabel("number of k-mers (log)")
    ax.set_title(f"B  Frequency spectrum\n(1 = cloud ... {N} = core)")
    ax.legend(frameon=False)

    ax = axes[2]
    miss, tot = r["bias"]
    lin, graph = f"linear\n{r['ref']} reference", "pan-genome\ngraph"
    ax.bar([lin, graph], [tot - miss, tot], color=["#9AA6B2", "#2E7DD1"], width=.55)
    ax.bar([graph], [miss], bottom=[tot - miss], color="#C1272D", width=.55,
           label="sequence a linear\nreference cannot represent")
    ax.text(1, tot - miss / 2, f"+{miss} bp\n+{100 * miss / (tot - miss):.0f}%",
            ha="center", va="center", color="white", fontweight="bold", fontsize=9)
    ax.set_ylim(0, tot * 1.30)
    ax.set_ylabel("representable sequence (bp)")
    ax.set_title("C  Reference bias removed by the graph")
    ax.legend(fontsize=7.5, frameon=False, loc="upper left")
    for a in axes:
        _clean(a)
    fig.tight_layout()
    _save(fig, r, "fig5_pangenome_openness")


# ============================================ 6. sites on a real structure ===
def read_ca(path):
    """CA atoms per chain from an experimental PDB file."""
    ch = {}
    for l in open(path):
        if l.startswith("ATOM") and l[12:16].strip() == "CA" and l[16] in " A":
            ch.setdefault(l[21], {})[int(l[22:26])] = (
                float(l[30:38]), float(l[38:46]), float(l[46:54]))
    return ch


def fig6_structure(r):
    ch = read_ca(f"data/{r['pdb']}.pdb")
    keys = sorted(ch, key=lambda k: -len(ch[k]))
    A = ch[keys[0]]
    B = ch[keys[1]] if len(keys) > 1 else {}
    hits = r["hits"] or r["top"]
    tm = [(s, e) for t, s, e, d in r["topo"] if t == "Transmembrane"]
    dom = [(s, e, d) for t, s, e, d in r["topo"] if t == "Domain"]

    def colour(i):
        if any(s <= i <= e for s, e, _ in dom):
            return DOMC
        return TMC if any(s <= i <= e for s, e in tm) else "#B9C4D0"

    fig = plt.figure(figsize=(12.5, 6.6))
    gs = fig.add_gridspec(3, 2, width_ratios=[1, 1.15], height_ratios=[.45, 1, .45])
    ax = fig.add_subplot(gs[:, 0], projection="3d")
    if B:                                              # partner protomer, faded
        ax.plot(*np.array([B[i] for i in sorted(B)]).T, color="#DDE3EA", lw=1.2)
    res = sorted(A)                                    # main protomer, coloured
    xyz = np.array([A[i] for i in res])
    keep = [i for i in range(len(res) - 1) if res[i + 1] - res[i] == 1]
    ax.add_collection3d(Line3DCollection([[xyz[i], xyz[i + 1]] for i in keep],
                                         colors=[colour(res[i]) for i in keep],
                                         linewidths=2.2))
    for c, pos, aa, colmn in hits:
        if pos in A:
            x, y, z = A[pos]
            ax.scatter([x], [y], [z], s=190, color=FG, edgecolor="k", lw=.8, zorder=5)
            ax.text(x + 16, y + 16, z, f"{aa}{pos}", color=FG, fontweight="bold",
                    fontsize=12, zorder=10)
    ctr = np.array([A[i] for i in res] + [B[i] for i in sorted(B)])
    rad = (ctr.max(0) - ctr.min(0)).max() / 2
    ctr = ctr.mean(0)
    ax.set_xlim(ctr[0] - rad * .78, ctr[0] + rad * .78)
    ax.set_ylim(ctr[1] - rad * .78, ctr[1] + rad * .78)
    ax.set_zlim(ctr[2] + rad, ctr[2] - rad)            # flip: cytoplasm at bottom
    ax.set_box_aspect((1.35, 1.35, 1.9)); ax.view_init(elev=6, azim=-72)
    ax.set_axis_off()
    ax.set_title(f"A  Top sites on {r['ref']} {r['gene']}\n"
                 f"experimental structure PDB {r['pdb']}", pad=-10)
    ax.legend(handles=[Patch(color=TMC, label="transmembrane domain"),
                       Patch(color=DOMC, label="soluble domain"),
                       Patch(color="#DDE3EA", label="partner protomer"),
                       plt.Line2D([], [], marker="o", ls="", color=FG,
                                  label="top site")],
              loc="lower center", fontsize=7.8, frameon=False,
              bbox_to_anchor=(.5, -.02))

    # ---- topology bar ------------------------------------------------------
    ax2 = fig.add_subplot(gs[1, 1])
    L = len(r["prot"][r["ref"]])
    ax2.add_patch(plt.Rectangle((1, .40), L, .20, fc="#EDF1F5", ec="none"))
    for y in (.40, .60):
        ax2.plot([1, L], [y, y], color="#C9D2DC", lw=1)
    ax2.text(-10, .62, "extracellular", fontsize=7.5, color="#8892A0", ha="right")
    ax2.text(-10, .38, "cytoplasmic", fontsize=7.5, color="#8892A0", ha="right",
             va="top")
    for s, e in tm:
        ax2.add_patch(plt.Rectangle((s, .38), e - s, .24, fc=TMC, ec="none"))
    for s, e, d in dom:
        ax2.add_patch(plt.Rectangle((s, .16), e - s, .20, fc=DOMC, ec="none"))
        ax2.text((s + e) / 2, .26, d, ha="center", va="center", color="white",
                 fontweight="bold", fontsize=9)
    for c, pos, aa, colmn in hits:
        indom = any(s <= pos <= e for s, e, _ in dom)
        up = not indom
        y0 = .62 if up else .36
        y1 = y0 + (.16 if up else -.16)
        ax2.plot([pos, pos], [y0, y1], color=FG, lw=2)
        ax2.scatter([pos], [y1], s=60, color=FG, zorder=4)
        where = (next(d for s, e, d in dom if s <= pos <= e) + " domain" if indom
                 else "TM helix" if any(s <= pos <= e for s, e in tm)
                 else "loop between TM helices")
        ax2.text(pos, y1 + (.04 if up else -.04), f"{aa}{pos}\n{where}", ha="center",
                 va="bottom" if up else "top", color=FG, fontweight="bold", fontsize=8.5)
    ax2.set_xlim(-120, L + 30); ax2.set_ylim(.02, .98)
    ax2.set_yticks([]); ax2.set_xticks(range(0, L + 1, 100))
    ax2.set_xlabel("residue number")
    ax2.set_title("B  Where those sites sit in the protein\n"
                  f"(UniProt {r['uniprot']} topology)")
    _clean(ax2, "top", "right", "left")
    _save(fig, r, "fig6_structure_mapping")


def make_all(r):
    """Every figure this dataset supports (fig6 needs an experimental structure)."""
    fig1_dna(r)
    fig2_tree(r)
    fig3_phylog2p(r)
    fig4_graph(r)
    fig5_pangenome(r)
    if r["pdb"]:                    # only datasets with a solved structure
        fig6_structure(r)
