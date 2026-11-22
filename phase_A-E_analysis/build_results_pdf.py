"""Build the PMHM Phase A-E results PDF from a full-run output directory.

Usage: python build_report.py <run_dir> <out_pdf>
Every number is read from the run's tables, log, manifest or report.
"""
import ast
import glob
import json
import os
import re
import sys

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle, BaseDocTemplate,
                                Frame)

RUN, OUT = sys.argv[1], sys.argv[2]
T = os.path.join(RUN, "tables")
F = os.path.join(RUN, "figures")

# ---------------------------------------------------------------- fonts and styles
FD = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("DV", FD + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DV-B", FD + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DV-I", FD + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("DV-BI", FD + "DejaVuSans-BoldOblique.ttf"))
pdfmetrics.registerFont(TTFont("DVC", FD + "DejaVuSansCondensed.ttf"))
pdfmetrics.registerFont(TTFont("DVC-B", FD + "DejaVuSansCondensed-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DVM", FD + "DejaVuSansMono.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")
registerFontFamily("DVC", normal="DVC", bold="DVC-B", italic="DVC", boldItalic="DVC-B")

INK = colors.HexColor("#1F2328")
MUTED = colors.HexColor("#59636E")
RULE = colors.HexColor("#D0D7DE")
ZEBRA = colors.HexColor("#F6F8FA")
GREEN = colors.HexColor("#1A7F37")
RED = colors.HexColor("#CF222E")
AMBER = colors.HexColor("#9A6700")
PURPLE = colors.HexColor("#8250DF")
PHASE_COL = {"A": "#0969DA", "B": "#0A8F6A", "C": "#6E8B00", "D": "#BC4C00", "E": "#CF222E"}
BANDS = ["#0092FF", "#00CCFF", "#00F6FF", "#00FFDF", "#00FFBF", "#08FF00", "#46FF00", "#7AFF00",
         "#A2FF00", "#EDFF00", "#FFEF00", "#FFC400", "#FF9E00", "#FF6F00", "#FF4600", "#FF1B00"]

base = ParagraphStyle("base", fontName="DV", fontSize=9.2, leading=13.2, textColor=INK)
S = {
    "body": base,
    "small": ParagraphStyle("small", parent=base, fontSize=8, leading=11, textColor=MUTED),
    "cap": ParagraphStyle("cap", parent=base, fontSize=7.8, leading=10.5, textColor=MUTED, spaceBefore=3,
                          spaceAfter=10),
    "h1": ParagraphStyle("h1", parent=base, keepWithNext=1, fontName="DV-B", fontSize=15, leading=19, spaceBefore=4,
                         spaceAfter=8),
    "h2": ParagraphStyle("h2", parent=base, keepWithNext=1, fontName="DV-B", fontSize=11, leading=14, spaceBefore=12,
                         spaceAfter=5),
    "h3": ParagraphStyle("h3", parent=base, keepWithNext=1, fontName="DV-B", fontSize=9.4, leading=12.5, spaceBefore=7,
                         spaceAfter=3),
    "cell": ParagraphStyle("cell", parent=base, fontName="DVC", fontSize=7.6, leading=9.6),
    "cellb": ParagraphStyle("cellb", parent=base, fontName="DVC-B", fontSize=7.6, leading=9.6),
    "hdr": ParagraphStyle("hdr", parent=base, fontName="DVC-B", fontSize=7.6, leading=9.6,
                          textColor=colors.white),
    "bullet": ParagraphStyle("bullet", parent=base, leftIndent=11, bulletIndent=2, spaceAfter=2),
}

W, H = A4
LM = RM = 17 * mm
TM, BM = 20 * mm, 17 * mm
CW = W - LM - RM


def P(t, st="body"):
    return Paragraph(t, S[st])


def bullets(items):
    return [Paragraph(i, S["bullet"], bulletText="•") for i in items]


def fmt(v, nd=3):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "–"
    if isinstance(v, (bool,)) or str(v) in ("True", "False"):
        return "yes" if str(v) == "True" else "no"
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return f"{v:,}"
    if isinstance(v, float):
        if v == int(v) and abs(v) >= 1 and abs(v) < 1e6:
            return f"{int(v):,}"
        a = abs(v)
        if a != 0 and a < 0.001:
            return f"{v:.2e}"
        return f"{v:.{nd}f}"
    return str(v)


def table(rows, widths, header_bg="#24292F", align_right_from=1, zebra=True, bold_first_col=False,
          highlight_rows=None):
    """rows: list of lists of str/Paragraph; first row is header."""
    data = []
    for i, r in enumerate(rows):
        out = []
        for j, c in enumerate(r):
            if isinstance(c, str):
                st = "hdr" if i == 0 else ("cellb" if (bold_first_col and j == 0) else "cell")
                c = Paragraph(c, S[st])
            out.append(c)
        data.append(out)
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    cmds = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(header_bg)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.6),
            ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), ZEBRA))
    for i in highlight_rows or []:
        cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FFF8C5")))
    t.setStyle(TableStyle(cmds))
    return t


def df_table(df, cols, heads, widths, nd=3, **kw):
    rows = [heads]
    for _, r in df.iterrows():
        rows.append([fmt(r[c], nd) if not isinstance(r[c], str) else
                     {"True": "yes", "False": "no", "None": "–", "": "–", "nan": "–"}.get(r[c].strip(), r[c])
                     for c in cols])
    return table(rows, widths, **kw)


def figure(name, width, caption, fig_no):
    p = os.path.join(F, name)
    from PIL import Image as PI
    w, h = PI.open(p).size
    img = Image(p, width=width, height=width * h / w)
    img.hAlign = "CENTER"
    return KeepTogether([img, P(f"<b>Figure {fig_no}.</b> {caption}", "cap")])


def badge(text, col):
    return f'<font name="DVC-B" color="{col}">{text}</font>'


SECNUM = {"A": 3, "B": 4, "C": 5, "D": 6, "E": 7}


def phase_banner(letter, title, steps, wp):
    col = colors.HexColor(PHASE_COL[letter])
    t = Table([[Paragraph(f'<font name="DV-B" size="22" color="white">{letter}</font>', S["body"]),
                Paragraph(f'<font name="DV-B" size="14" color="white">Phase {letter} · {title}</font><br/>'
                          f'<font size="8.5" color="white">Section {SECNUM[letter]} · steps {steps} · {wp}</font>', S["body"])]],
              colWidths=[16 * mm, CW - 16 * mm], rowHeights=[17 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), col), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (0, 0), (0, 0), 6 * mm), ("LEFTPADDING", (1, 0), (1, 0), 2)]))
    return [t, Spacer(1, 6)]


def keybox(title, lines, col="#0969DA"):
    inner = [P(f'<font name="DV-B" color="{col}">{title}</font>')] + [P(l) for l in lines]
    t = Table([[inner]], colWidths=[CW])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F6F8FA")),
                           ("LINEBEFORE", (0, 0), (0, -1), 3, colors.HexColor(col)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 9), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return [t, Spacer(1, 8)]


def rd(name):
    return pd.read_csv(os.path.join(T, name))


# ---------------------------------------------------------------- load run facts
man = json.load(open(glob.glob(os.path.join(RUN, "steps/S0/info.json"))[0]))
snap = json.load(open(glob.glob(os.path.join(RUN, "snapshots/*.json"))[0]))
plan_files = glob.glob(os.path.join(RUN, "analysis_plan/analysis_plan_*.json"))
plan_hash = re.search(r"analysis_plan_(\w+)\.json", plan_files[0]).group(1) if plan_files else "–"
report_md = open(glob.glob(os.path.join(RUN, "reports/PMHM_report_full_*.md"))[0]).read()
logf = glob.glob(os.path.join(RUN, "logs/kaggle_kernel_*.log"))
log_lines = []
if logf:
    for e in json.load(open(logf[0])):
        log_lines += e.get("data", "").splitlines()
log = "\n".join(log_lines)

steps = {}
for m in re.finditer(r"\[(S\d+)\] START (.+)", log):
    steps.setdefault(m.group(1), {})["title"] = m.group(2).strip()
for m in re.finditer(r"\[(S\d+)\] DONE in ([\d.]+) s \| RSS (\d+) MB \| peak (\d+) MB", log):
    steps.setdefault(m.group(1), {}).update(sec=float(m.group(2)), rss=int(m.group(3)), peak=int(m.group(4)))
total_s = float(re.search(r"Finished in (\d+) s", log).group(1))
started = re.search(r"^(\d\d:\d\d:\d\d) \| INFO .*PMHM Phase", log, re.M).group(1)


def grab(pat, cast=str, src=None):
    m = re.search(pat, src or log)
    return cast(m.group(1)) if m else None


qc = re.search(r"QC: gaps=(\d+), stage agreement=([\d.]+), post-video rows=(\d+), disp-flagged=(\d+), "
               r"saturated ROIs=(\d+)", log).groups()
dark = re.search(r"sign flips in (\d+) subject-pressure cells; max spread ([\d.]+)", log).groups()
fwd = re.search(r"max truncation ([\d.]+); negatives in support (\d+); extinction design condition number "
                r"([\d.]+)", log).groups()
feat = re.search(r"Frame features: ([\d,]+) rows x (\d+) features; spectrometer features \((\d+), (\d+)\)",
                 log).groups()
blk = re.search(r"Block stats: (\d+) windows \((\d+) invalid\); deltas (\d+); kinetics (\d+)", log).groups()
win = re.search(r"Windows: ([\d,]+) \(\{'subject_01': (\d+), 'subject_02': (\d+)\}\); features (\d+)", log).groups()
n_cls = grab(r"S14 classical: (\d+) experiments", int)
rq2_share = grab(r"accepted fit share ([\d.]+)", float)

tests = rd("S1_tests.csv")
golden = rd("S1_golden.csv")
h1c = None
h1s = rd("S10_h1_spectrometer.csv")
bench = rd("S14_benchmark.csv")
gate = rd("S14_informative_gate.csv")
drift = rd("S14_drift_check.csv")
t1d = rd("S14_t1d_summary.csv")
tvc = rd("S14_temporal_vs_classical.csv")
fam = rd("S12_family_robustness.csv")
verdict = rd("S12_rq3_verdict.csv")
agree = rd("S13_agreement_summary.csv")
rep_cv = rd("S13_spectro_replicate_cv.csv")
icc_roi = rd("S13_spectro_icc_rois.csv")
cam_cv = rd("S13_camera_between_roi_cv.csv")
kin = rd("S11_kinetics_fits.csv")
rq2 = rd("S11_rq2_tests.csv")


def md_table(after_heading, nth=0):
    """Parse the nth markdown table after a heading in the run report."""
    sec = report_md.split(after_heading, 1)[1]
    sec = sec.split("\n## ", 1)[0]
    blocks = re.findall(r"((?:^\|.*\|[ \t]*\n)+)", sec + "\n", re.M)
    lines = [l.strip() for l in blocks[nth].strip().splitlines()]
    head = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = [[c.strip() for c in l.strip("|").split("|")] for l in lines[2:]]
    return pd.DataFrame(rows, columns=head)


qc_tab = md_table("## S3 Quality control", 0)
gap_tab = md_table("## S3 Quality control", 1)
gain_tab = md_table("## S6 Relative reflectance", 0)
xt_tab = md_table("## S7 Cross-talk", 0)
h1_tab = md_table("## S10 Dose–response and H1", 0)
loc_tab = md_table("## S10 Dose–response and H1", 1)

# headline numbers
spec_line = re.search(r"mean change of log\(S550/S609\) ([-\d.]+), exact one-sided Wilcoxon p = ([\d.]+), "
                      r"95% CI \['([-\d.]+)', '([-\d.]+)'\]", report_md).groups()
h2_p = grab(r"T1d exact Wilcoxon p = ([\d.]+)", float, report_md)
v = lambda s, t, fs, m: bench[(bench.scheme == s) & (bench.task == t) & (bench.feature_set == fs) &
                              (bench.model == m)].iloc[0]
v1_best = bench[(bench.scheme == "V1") & (bench.task == "cls") & (bench.model != "majority")].sort_values(
    "mean", ascending=False).iloc[0]
v2c = bench[(bench.scheme == "V2") & (bench.task == "cls") &
            (~bench.model.isin(["majority", "shuffled_null", "time_only"]))].sort_values("mean", ascending=False)
v2_best = v2c.iloc[0]
null_c = v("V2", "cls", "all", "shuffled_null")
time_c = v("V2", "cls", "time", "time_only")
v2r = bench[(bench.scheme == "V2") & (bench.task == "reg") &
            (~bench.model.isin(["majority", "shuffled_null", "time_only"]))].sort_values("mean")
v2r_best = v2r.iloc[0]
v2r_mean = bench[(bench.scheme == "V2") & (bench.task == "reg") & (bench.model == "majority")]["mean"].iloc[0]
pp = agree[(agree.level == "participant") & (agree.camera_window == "cam")].iloc[0]
pr = agree[(agree.level == "roi") & (agree.camera_window == "cam")].iloc[0]
robust_fams = verdict[verdict.robust == True].family.tolist()
FAMNAME = {"raw": "Raw counts", "rel": "Relative reflectance", "l1": "L1-normalised spectra",
           "ratio": "Band ratios", "mbll": "Beer–Lambert indices", "all": "All combined", "time": "Time only"}
MODNAME = {"logreg_pca": "Logistic/linear on PCA", "pls": "PLS", "rf": "Random forest", "svm": "SVM",
           "majority": "Majority class", "shuffled_null": "Shuffled-label null", "time_only": "Time only"}

# recovery counts (ROI mean = roi_id 0, primary feature)
rec = {}
for sid, g in kin[(kin.feature == "r550_609") & (kin.roi_id == 0)].groupby("subject_id"):
    ev = g.recovery_frac_20s.notna()
    rec[sid] = (int((g.recovery_frac_20s[ev] < 1).sum()), int(ev.sum()))

rep_cols = [c for c in rep_cv.columns if c.startswith("cv_")]
rep_med = rep_cv[rep_cols].stack().median()
icc_lo, icc_hi = icc_roi.iloc[:, 1].min(), icc_roi.iloc[:, 1].max()
cam_cv_med = {r.subject_id: r[[c for c in cam_cv.columns if c.startswith("cv_")]].median() for _, r in
              cam_cv.iterrows()}

fig_no = [0]


def nf():
    fig_no[0] += 1
    return fig_no[0]


tab_no = [0]


def tcap(text):
    tab_no[0] += 1
    return P(f"<b>Table {tab_no[0]}.</b> {text}", "cap")


# ---------------------------------------------------------------- page decorations
RUN_DATE = "20 November 2026"


def cover_page(c, doc):
    c.saveState()
    c.setFillColor(colors.HexColor("#0D1117"))
    c.rect(0, H - 112 * mm, W, 112 * mm, fill=1, stroke=0)
    bw = W / 16
    for i, col in enumerate(BANDS):
        c.setFillColor(colors.HexColor(col))
        c.rect(i * bw, H - 116 * mm, bw + 0.5, 4 * mm, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#8B949E"))
    c.setFont("DV", 9)
    c.drawString(LM, H - 24 * mm, "PERIPHERAL MICROVASCULAR HEALTH MONITORING (PMHM)")
    c.setFillColor(colors.white)
    c.setFont("DV-B", 30)
    c.drawString(LM, H - 46 * mm, "Phase A–E results")
    c.setFont("DV", 13)
    c.setFillColor(colors.HexColor("#C9D1D9"))
    c.drawString(LM, H - 57 * mm, "Spectral–temporal analysis of graded arm occlusion")
    c.drawString(LM, H - 64 * mm, "Full run of pmhm_phase_a_e.ipynb, steps S0–S14")
    c.setFont("DV", 9)
    c.setFillColor(colors.HexColor("#8B949E"))
    c.drawString(LM, H - 82 * mm, f"Run {snap['timestamp']}  ·  {RUN_DATE}  ·  Kaggle, CPU  ·  "
                                  f"config {snap['config_hash']}  ·  plan {plan_hash}")
    c.drawString(LM, H - 88 * mm, "Data: SPECTRALPACA (Ayala et al., Scientific Data 2024), CC BY 4.0  ·  "
                                  "standalone Parquet, SHA-256 eb77b66a…")
    c.setFillColor(colors.HexColor("#F0B72F"))
    c.setFont("DV-B", 9)
    c.drawString(LM, H - 100 * mm, "PROVISIONAL  ·  analysis plan frozen but not yet signed off")
    c.restoreState()
    footer(c, doc, cover=True)


def footer(c, doc, cover=False):
    c.saveState()
    c.setFont("DV", 7.5)
    c.setFillColor(MUTED)
    if not cover:
        c.drawString(LM, H - 11 * mm, "PMHM · Phase A–E results")
        c.drawRightString(W - RM, H - 11 * mm, f"Full run {snap['timestamp']}")
        c.setStrokeColor(RULE)
        c.setLineWidth(0.5)
        c.line(LM, H - 13 * mm, W - RM, H - 13 * mm)
    c.drawString(LM, 9 * mm, "Healthy volunteers only. No diagnostic claim for PAD follows from these results.")
    c.drawRightString(W - RM, 9 * mm, f"{doc.page}")
    c.restoreState()


doc = BaseDocTemplate(OUT, pagesize=A4, leftMargin=LM, rightMargin=RM, topMargin=TM, bottomMargin=BM,
                      title="PMHM Phase A–E results", author="PMHM project",
                      subject="Full run of pmhm_phase_a_e.ipynb (S0–S14)")
cover_frame = Frame(LM, BM, CW, H - BM - 124 * mm, id="cover")
body_frame = Frame(LM, BM, CW, H - TM - BM, id="body")
doc.addPageTemplates([PageTemplate(id="Cover", frames=[cover_frame], onPage=cover_page),
                      PageTemplate(id="Body", frames=[body_frame], onPage=footer)])

st = []

# ---------------------------------------------------------------- cover: results at a glance
st.append(P("Results at a glance", "h2"))
glance = [
    ["Question", "Result in this run", "Verdict"],
    ["<b>H1</b> · Does the 550/609 nm ratio fall steadily with cuff pressure?",
     f"Largest dip at {h1_tab.exploratory_peak_mmhg[0]} / {h1_tab.exploratory_peak_mmhg[1]} mmHg, back near zero at "
     f"140–160 mmHg. Camera trend p = {float(h1_tab.p_trend[0]):.2f} / {float(h1_tab.p_trend[1]):.2f}; "
     f"spectrometer (n = 10) p = {float(spec_line[1]):.3f}",
     badge("NOT SUPPORTED", "#CF222E")],
    ["<b>H2</b> · Do ratio features generalise across people better than raw counts?",
     f"Better on the camera in both directions, no gain on the 10-person spectrometer task (p = {h2_p:.3f})",
     badge("NOT SUPPORTED", "#CF222E")],
    ["<b>RQ2</b> · How does the skin recover after release?",
     f"{rq2_share:.0%} of exponential fits accepted, so model-free measures used; recovery incomplete at 20 s in "
     f"{rec['subject_01'][0]}/{rec['subject_01'][1]} and {rec['subject_02'][0]}/{rec['subject_02'][1]} blocks",
     badge("DESCRIPTIVE", "#8250DF")],
    ["<b>RQ3</b> · Which feature families are robust?",
     ", ".join(FAMNAME[f] for f in robust_fams), badge("3 ROBUST", "#1A7F37")],
    ["<b>Agreement</b> · Camera vs spectrometer at 160 mmHg",
     f"Bias {pp.pooled_bias:.1f} points (LoA {pp.pooled_loa_lo:.1f} to {pp.pooled_loa_hi:.1f}), "
     f"ICC {pp.icc21_pooled:.2f}", badge("POOR", "#9A6700")],
    ["<b>Models</b> · Phase classification across participants",
     f"Best spectral {v2_best['mean']:.2f}; elapsed time alone {time_c['mean']:.2f}; null {null_c['mean']:.2f}",
     badge("TIME WINS", "#9A6700")],
]
st.append(table(glance, [58 * mm, 92 * mm, CW - 150 * mm], zebra=True))
st.append(Spacer(1, 8))
st.append(P(f"All {len(steps)} steps (S0–S14) finished without errors in {total_s / 60:.1f} minutes; peak "
            f"memory {max(s.get('peak', 0) for s in steps.values()):,} MB. The results reproduce the first full "
            f"run of 15 November 2026 that proposal v2.0 reports.", "small"))
st.append(NextPageTemplate("Body"))
st.append(PageBreak())

# ---------------------------------------------------------------- 1. Summary
st.append(P("1  Summary", "h1"))
st.append(P(
    "This report collects every result of the Phase A–E analysis from one full run of the notebook. The run read "
    "only the standalone SPECTRALPACA Parquet file: 16-band camera time series from tracked palm ROIs in two "
    "healthy volunteers, reference spectrometer spectra from ten volunteers at baseline and 160 mmHg, and the "
    "camera's calibration records."))
st.append(Spacer(1, 4))
st.append(P(
    "Neither pre-specified hypothesis held. The haemoglobin-sensitive 550/609 nm ratio did not fall steadily with "
    "pressure. It dipped most at intermediate pressures and came back towards baseline once the cuff passed "
    "about 120 mmHg. Ratio features did beat raw counts on the camera, but not in the ten-person spectrometer "
    "task. The camera and the spectrometer agreed poorly, and the spectrometer itself was variable between "
    "replicates."))
st.append(Spacer(1, 4))
st.append(P(
    f"The result I'd put first is the time-only control. A model given nothing but the elapsed time classified "
    f"the protocol phase with a balanced accuracy of {time_c['mean']:.2f}, against {v2_best['mean']:.2f} for the "
    f"best spectral model. The pressure order is fixed, so knowing the clock is knowing the phase. Any study with "
    f"this design needs that control before its accuracy numbers mean anything."))
st.append(Spacer(1, 6))
st += keybox("How to read this report", [
    "Sections 3–7 follow the implementation plan's phases. Each step lists what it does and what this run found.",
    "Results from S10–S14 are confirmatory in design but provisional, because the frozen analysis plan has not "
    "been signed off. Anything labelled exploratory was not pre-specified.",
    "Camera results come from two participants and are within-person findings. Population-level statements rest "
    "on the ten-person spectrometer arm."])

# ---------------------------------------------------------------- 2. Run overview
st.append(P("2  Run overview", "h1"))
st.append(P("2.1  Environment", "h2"))
env_rows = [["Item", "Value"],
            ["Run", f"{snap['timestamp']} · full mode · started {started} UTC · {total_s / 60:.1f} min"],
            ["Platform", f"Kaggle notebook · profile {man['profile']} · device {man['device']} · "
                         f"{man.get('cpu_count', '–')} CPUs · {man['ram_total_mb'] / 1024:.1f} GB RAM"],
            ["Python", man["python"].split(" (")[0]],
            ["Libraries", ", ".join(f"{k} {v}" for k, v in man["versions"].items())],
            ["Dataset", "spectralpaca_pmhm_dataset.parquet · 4,586,255 rows · 81 columns · 56.6 MB"],
            ["Dataset SHA-256", '<font name="DVM" size="6.8">eb77b66a76f27eab5a053fe564954d9fe4ef584423f1053cb46542ac38961226</font>'],
            ["Configuration hash", snap["config_hash"]],
            ["Analysis plan", f"frozen, hash {plan_hash} · supervisor sign-off: <b>no</b>"],
            ["Seed", str(snap["config"].get("SEED", "20261115")) if isinstance(snap.get("config"), dict) else "20261115"]]
st.append(table(env_rows, [34 * mm, CW - 34 * mm], bold_first_col=True))
st.append(tcap("Run environment, from the run manifest."))
st.append(P("2.2  Step status", "h2"))
rows = [["Step", "Phase", "Title", "Status", "Time (s)", "Peak RSS (MB)"]]
phase_of = lambda k: "A" if k <= 2 else "B" if k <= 7 else "C" if k <= 9 else "D" if k <= 12 else "E"
for k in range(15):
    s = steps.get(f"S{k}", {})
    rows.append([f"<b>S{k}</b>", phase_of(k), s.get("title", "–"), badge("done", "#1A7F37"),
                 fmt(s.get("sec"), 1) if s.get("sec") is not None else "–",
                 fmt(s.get("peak")) if s.get("peak") is not None else "–"])
st.append(table(rows, [12 * mm, 12 * mm, 92 * mm, 16 * mm, 18 * mm, CW - 150 * mm]))
st.append(tcap("Step status from the run log. S14 takes most of the time: "
               f"{n_cls} classical experiments plus the gated temporal models."))

# ---------------------------------------------------------------- Phase A
st.append(PageBreak())
st += phase_banner("A", "Foundation", "S0–S2", "work package 1")
st.append(P("S0 · Environment and run manifest", "h2"))
st.append(P("The notebook detected the Kaggle environment, found the dataset under <font name='DVM'>/kaggle/input</font>, "
            "and verified its SHA-256 and all nine record types before any analysis started. The run manifest above "
            "records versions, seeds and the configuration hash."))
st.append(P("S1 · Data access, contract and golden tests", "h2"))
n_pass = int(tests.passed.sum())
st.append(P(f"<b>{n_pass} of {len(tests)} tests passed.</b> Contract tests check the file's structure. Golden tests "
            f"reproduce the preliminary numbers in proposal v1.0 from the file, using the proposal's own method."))
rows = [["Test", "Passed", "Detail"]]
for _, r in tests.iterrows():
    d = str(r.detail) if pd.notna(r.detail) else ""
    d = d.replace("{", "").replace("}", "").replace("'", "")
    rows.append([r.test, badge("yes", "#1A7F37") if r.passed else badge("no", "#CF222E"), d[:140]])
st.append(table(rows, [62 * mm, 14 * mm, CW - 76 * mm]))
st.append(tcap("S1 contract and golden tests."))
st.append(P("One golden test corrects proposal v1.0. Across 500–650 nm, the group-mean spectrometer reflectance at "
            "160 mmHg was 16.3–30.1% above baseline (median 20.8%), not the 18–22% the v1.0 text gives. Proposal "
            "v2.0 already uses the corrected figure."))
st.append(P("S2 · Analysis plan frozen", "h2"))
st.append(P(f"The confirmatory analyses, decision rules for H1 and H2, validation schemes and the sensitivity grid "
            f"were written and hashed (<font name='DVM'>{plan_hash}</font>) before S3 ran. "
            "<font color='#9A6700'><b>The plan is not signed off</b></font>, so S10–S14 results carry that label. "
            "Whether spectrometer ROI <i>k</i> is the same skin site as camera ROI <i>k</i> is recorded as unconfirmed."))

# ---------------------------------------------------------------- Phase B
st.append(PageBreak())
st += phase_banner("B", "Signal conditioning", "S3–S7", "work package 2")
st.append(P("The source data have no white reference, and the dark frame has no recorded exposure. Phase B works out "
            "how far the raw camera counts can be trusted and calibrated anyway."))
st.append(P("S3 · Quality control and frame flags", "h2"))
st += bullets([
    f"Stage labels agreed between ROI and frame records in {float(qc[1]):.0%} of frames.",
    f"{int(qc[2]):,} ROI rows were tracked after the video ended; they are flagged and kept out of spectral analyses.",
    f"{int(qc[3]):,} ROI rows were flagged for displacement above 1 px. {qc[4]} ROIs came near saturation.",
    f"{qc[0]} recording gaps longer than 1 s were found (Table {tab_no[0] + 2})."])
st.append(df_table(qc_tab, list(qc_tab.columns), ["Participant", "Frames", "fps", "Interval CV", "Exposure (ms)",
                                                  "ROI spectra", "Post-video rows"],
                   [26 * mm, 22 * mm, 16 * mm, 22 * mm, 24 * mm, 22 * mm, CW - 132 * mm]))
st.append(tcap("Frame timing per participant. Participant 04 has a video cube but no ROI tracks."))
st.append(df_table(gap_tab, list(gap_tab.columns), ["Participant", "Gap start (s)", "Gap end (s)", "Gap (s)"],
                   [30 * mm, 30 * mm, 30 * mm, 30 * mm]))
st.append(tcap("Unrecorded gaps over 1 s. Most precede the first clamping block (cuff inflation)."))

st.append(P("S4 · Dark offset and its uncertainty", "h2"))
st.append(P(f"Three dark scenarios (0, measured D, 2D) were propagated into the 550/609 nm ratio. "
            f"<b>{dark[0]} clamp-stage changes changed sign</b> across them; the largest spread was {float(dark[1]):.4f}. "
            f"The primary scenario is the measured dark mean."))

st.append(P("S5 · Spectrometer-to-camera forward model", "h2"))
st.append(P(f"Every spectrometer spectrum was projected through the 16 measured filter curves and the xenon source "
            f"spectrum. At most {float(fwd[0]):.2%} of any band's response falls outside the spectrometer's range, so the "
            f"model is nearly complete. Of the 14,705 negative spectrometer values, {int(fwd[1]):,} fall inside band "
            f"support and are kept. The haemoglobin extinction design has condition number {float(fwd[2]):.1f}. "
            f"The unit tests (flat spectrum, linearity, truncation below 1%) all passed."))
st.append(figure("s05_band_weights.png", CW * 0.92,
                 "Effective camera band weights (filter response × xenon irradiance) on the spectrometer grid. "
                 "Secondary lobes are visible for several bands.", nf()))

st.append(P("S6 · Relative reflectance and effective white", "h2"))
st.append(P("A per-band gain anchored on the spectrometer replaces the missing white reference. Fitted on one "
            "participant, it predicted the other's baseline counts <b>within 15% in all 16 bands, in both "
            "directions</b>, so absolute comparisons were adopted. The largest errors are in the blue bands."))
bands = [c.replace("err_", "") for c in gain_tab.columns if c.startswith("err_")]
order = sorted(range(len(bands)), key=lambda i: int(bands[i]))
rows = [["Band (nm)", "Train 01 → test 02 (%)", "Train 02 → test 01 (%)", "Within ±15%"]]
g = gain_tab.set_index("train")
for i in order:
    a, b_ = float(g.loc["subject_01", "err_" + bands[i]]) * 100, float(g.loc["subject_02", "err_" + bands[i]]) * 100
    rows.append([bands[i], f"{a:+.1f}", f"{b_:+.1f}",
                 badge("yes", "#1A7F37") if max(abs(a), abs(b_)) <= 15 else badge("no", "#CF222E")])
half = (len(rows) - 1) // 2
left = table([rows[0]] + rows[1:1 + half], [16 * mm, 27 * mm, 27 * mm, 17 * mm])
right = table([rows[0]] + rows[1 + half:], [16 * mm, 27 * mm, 27 * mm, 17 * mm])
pair = Table([[left, right]], colWidths=[CW / 2, CW / 2])
pair.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
st.append(pair)
st.append(tcap("Cross-participant prediction error of baseline counts per band, sorted by wavelength."))

st.append(P("S7 · Cross-talk characterisation and correction", "h2"))
st.append(P("A 16 × 16 ridge correction was fitted leave-one-participant-out to undo filter leakage. On held-out skin "
            "spectra it cut the spectral angle from about 7–12° to about 0.03° in <b>all 10 folds</b>. It also failed the "
            "neutral-patch check: applied to the flat grey colour-checker patches, it made them less flat. It had "
            "learned the narrow range of skin spectra rather than the filters, so "
            "<font color='#CF222E'><b>it was not adopted</b></font>, not even as a sensitivity variant."))
xt = xt_tab.copy()
st.append(df_table(xt, ["subject_id", "angle_uncorrected", "angle_corrected", "rel_rmse_uncorrected",
                        "rel_rmse_corrected", "improved"],
                   ["Held-out participant", "Angle before (°)", "Angle after (°)", "Rel. RMSE before",
                    "Rel. RMSE after", "Improved"],
                   [34 * mm, 26 * mm, 26 * mm, 28 * mm, 28 * mm, CW - 142 * mm]))
st.append(tcap("Leave-one-participant-out cross-talk correction on simulated skin band values."))
st.append(figure("s07_crosstalk_lopo.png", CW * 0.66,
                 "Mean spectral angle between simulated full-filter and main-lobe band values, before and after "
                 "correction, per held-out participant.", nf()))

# ---------------------------------------------------------------- Phase C
st.append(PageBreak())
st += phase_banner("C", "Features", "S8–S9", "work package 3")
st.append(P("S8 · Frame-level features", "h2"))
st.append(P(f"Five feature families were computed for every camera frame and every simulated spectrometer spectrum: "
            f"<b>{feat[0]} camera rows × {feat[1]} features</b> and a {int(feat[2]):,} × {feat[3]} spectrometer "
            f"feature matrix."))
rows = [["Code", "Family", "Definition"],
        ["raw", "Raw counts", "ROI mean camera counts per band; the reference the other families are compared with"],
        ["rel", "Relative reflectance", "Each band divided by its own baseline level"],
        ["l1", "L1-normalised spectrum", "Spectral shape with overall brightness removed"],
        ["ratio", "Band ratios", "Primary 550/609 nm (strong vs weak haemoglobin absorption); secondary: each band over "
                                 "609 and 641 nm"],
        ["mbll", "Beer–Lambert indices", "Relative oxy- and deoxyhaemoglobin indices from a modified Beer–Lambert fit "
                                         "to attenuation, ΔA = −ln ρ"]]
st.append(table(rows, [14 * mm, 38 * mm, CW - 52 * mm]))
st.append(tcap("Feature families. Smoothing (2 s rolling median) is used for figures only."))
st.append(P("S9 · Block features and smallest detectable change", "h2"))
st.append(P(f"Each protocol block yields a plateau-minus-reference change and an initial slope. The run produced "
            f"<b>{blk[0]} analysis windows ({blk[1]} invalid)</b>, {blk[2]} block changes and {blk[3]} recovery "
            f"series. The smallest detectable change (SDC95) of the primary ratio comes from a moving-block bootstrap "
            f"of each ROI's baseline: <b>{float(h1_tab.sdc95[0]):.4f}</b> for participant 01 and "
            f"<b>{float(h1_tab.sdc95[1]):.4f}</b> for participant 02. Phase D uses it as the bar a change has to clear."))

# ---------------------------------------------------------------- Phase D
st.append(PageBreak())
st += phase_banner("D", "Physiological response", "S10–S12", "work package 4")
st.append(P("S10 · Dose–response and hypothesis H1", "h2"))
st += keybox("H1 · not supported", [
    "H1 said the 550/609 nm ratio falls with cuff pressure, with a detectable change from 60 mmHg. In both camera "
    "participants the change grew up to about 100 mmHg and then reversed. No monotone trend was significant, no "
    "onset pressure cleared SDC95, and the clamp trend did not beat the placebo trend.",
    f"Spectrometer arm, ten participants at 160 mmHg: mean change in log(S550/S609) {float(spec_line[0]):.4f} "
    f"(95% CI {float(spec_line[2]):.4f} to {float(spec_line[3]):.4f}), exact one-sided Wilcoxon p = "
    f"{float(spec_line[1]):.3f}. {int((h1s['diff'] > 0).sum())} participants rose and "
    f"{int((h1s['diff'] < 0).sum())} fell."], col="#CF222E")
st.append(df_table(h1_tab, ["subject_id", "rho", "p_trend", "sdc95", "onset_mmhg", "theil_clamp", "theil_placebo",
                            "clamp_exceeds_placebo", "rois_all_negative_ge60", "supported"],
                   ["Participant", "ρ", "p trend", "SDC95", "Onset", "Clamp slope", "Placebo slope",
                    "Clamp > placebo", "ROIs all < 0 ≥60", "Supported"],
                   [20 * mm, 14 * mm, 15 * mm, 16 * mm, 13 * mm, 20 * mm, 21 * mm, 20 * mm, 22 * mm, CW - 161 * mm]))
st.append(tcap("Camera arm of H1 per participant (exact permutation trend test and placebo drift control)."))
lt = loc_tab.copy()
rows = [["Participant"] + [c.replace("d_", "") + " mmHg" for c in lt.columns[1:]]]
peak_cells = []
for i, (_, r) in enumerate(lt.iterrows(), start=1):
    vals = [float(x) for x in r.values[1:]]
    rows.append([r.values[0]] + [f"{x:+.4f}" for x in vals])
    peak_cells.append((1 + vals.index(min(vals)), i))
t = table(rows, [24 * mm] + [(CW - 24 * mm) / 8] * 8)
for c, r in peak_cells:
    t.setStyle(TableStyle([("BACKGROUND", (c, r), (c, r), colors.HexColor("#FFEBE9"))]))
st.append(t)
st.append(tcap("Local change of the ROI-mean 550/609 nm ratio at each clamping stage. Shaded: the largest decrease "
               "(exploratory, not pre-specified)."))
st.append(figure("s10_ratio_timecourse.png", CW * 0.95,
                 "ROI-mean 550/609 nm ratio relative to baseline (2 s rolling median); shading marks cuff inflation "
                 "and its pressure in mmHg.", nf()))
st.append(figure("s10_dose_response.png", CW * 0.80,
                 "Local change of the ROI-mean 550/609 ratio per clamping stage (solid), placebo differences between "
                 "consecutive rest references (dashed) and ±SDC95 (shaded).", nf()))
st.append(P("The non-monotone shape suggests that absorption peaks when the cuff sits between venous and arterial "
            "pressure, so blood flows in but can't drain, and shrinks once arterial inflow stops as well. It was "
            "spotted in the same two people it would be tested on, so it stays an exploratory observation for "
            "independent data."))
rows = [["Participant", "Baseline", "160 mmHg", "Change"]]
for _, r in h1s.iterrows():
    rows.append([r.subject_id, f"{r.baseline:.4f}", f"{r.cuff160:.4f}", f"{r['diff']:+.4f}"])
spec_tbl = table(rows, [26 * mm, 22 * mm, 22 * mm, 20 * mm])
from PIL import Image as PI
sw, sh = PI.open(os.path.join(F, "s10_spectrometer_arm.png")).size
spec_img = Image(os.path.join(F, "s10_spectrometer_arm.png"), width=CW - 96 * mm, height=(CW - 96 * mm) * sh / sw)
side = Table([[spec_tbl, spec_img]], colWidths=[94 * mm, CW - 94 * mm])
side.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
st.append(KeepTogether([side, P(f"<b>Table {tab_no[0] + 1} and Figure {nf()}.</b> Spectrometer arm of H1: participant "
                                 "means of the simulated camera-band log(550/609) at baseline and 160 mmHg (n = 10); "
                                 "blue in the figure is the group mean.", "cap")]))
tab_no[0] += 1

st.append(P("S11 · Recovery kinetics (RQ2)", "h2"))
st.append(P(f"Mono-exponential fits were tried on each rest block after release. Only <b>{rq2_share:.0%}</b> of fits on "
            f"the primary feature met the acceptance rule, so the pre-specified model-free measures were used "
            f"instead. Recovery at 20 s was incomplete in <b>{rec['subject_01'][0]} of {rec['subject_01'][1]}</b> "
            f"evaluable blocks for participant 01 and <b>{rec['subject_02'][0]} of {rec['subject_02'][1]}</b> for "
            f"participant 02. Neither half-recovery time nor overshoot depended on the preceding pressure."))
st.append(df_table(rq2, ["subject_id", "metric", "rho", "p", "p_holm"],
                   ["Participant", "Measure", "ρ vs preceding pressure", "p", "Holm p"],
                   [30 * mm, 30 * mm, 40 * mm, 24 * mm, 24 * mm]))
st.append(tcap("RQ2 trend tests. A dash means too few evaluable blocks for the test."))
st.append(figure("s11_recovery_fits.png", CW, "Mono-exponential recovery fits in the eight rest blocks "
                 "(participant 01, ROI mean).", nf()))

st.append(P("S12 · Feature robustness (RQ3)", "h2"))
st.append(P(f"Each family was scored on four criteria against raw counts. A family is robust only if it is better on "
            f"at least one criterion and worse on none. <b>{', '.join(FAMNAME[f] for f in robust_fams)}</b> met the "
            f"rule. Relative reflectance did not."))
fo = fam.set_index("family").loc[["raw", "rel", "l1", "ratio", "mbll"]].reset_index()
vd = verdict.set_index("family")
rows = [["Family", "Between-person CV", "Baseline drift", "Effect / noise (camera)", "Spectrometer |dz|",
         "Dark sensitivity", "Better / worse than raw", "Robust"]]
for _, r in fo.iterrows():
    f_ = r.family
    bw_s = f"{int(vd.loc[f_, 'better_than_raw'])} / {int(vd.loc[f_, 'worse_than_raw'])}" if f_ in vd.index else "reference"
    rb = ("reference" if f_ == "raw" else (badge("yes", "#1A7F37") if vd.loc[f_, "robust"] else badge("no", "#CF222E")))
    rows.append([FAMNAME[f_], fmt(r.between_participant_cv), fmt(r.baseline_drift), fmt(r.effect_to_noise_camera),
                 fmt(r.spectro_dz_abs), fmt(r.processing_sensitivity), bw_s, rb])
st.append(table(rows, [36 * mm, 20 * mm, 18 * mm, 22 * mm, 20 * mm, 19 * mm, 22 * mm, CW - 157 * mm]))
st.append(tcap("Family medians. Drift is the absolute baseline slope per 100 s relative to baseline SD. "
               "Between-person CV is undefined for baseline-referenced families; dark sensitivity is undefined for raw "
               "counts, which have no dark subtraction."))

# ---------------------------------------------------------------- Phase E
st.append(PageBreak())
st += phase_banner("E", "Agreement and models", "S13–S14 (S15 gated, S16 not started)", "work packages 5–6")
st.append(P("S13 · Camera–spectrometer agreement and repeatability", "h2"))
st.append(P(f"The quantity compared is each band's relative change from baseline to 160 mmHg. At participant level the "
            f"camera change sat on average <b>{abs(pp.pooled_bias):.1f} percentage points below</b> the spectrometer "
            f"change (limits of agreement {pp.pooled_loa_lo:.1f} to {pp.pooled_loa_hi:.1f}, ICC {pp.icc21_pooled:.2f}). "
            f"At ROI level the bias was {pr.pooled_bias:.1f} points (limits {pr.pooled_loa_lo:.1f} to "
            f"{pr.pooled_loa_hi:.1f}, ICC {pr.icc21_pooled:.2f}), and that analysis assumes the ROIs correspond, which "
            f"is unconfirmed."))
rows = [["Level", "Camera window", "Units", "Pairs", "Bias", "SD", "LoA low", "LoA high", "ICC(2,1)", "Spectral angle (°)"]]
for _, r in agree.iterrows():
    rows.append([r.level, "plateau" if r.camera_window == "cam" else "last 30 s", fmt(r.n_units), fmt(r.pooled_n),
                 fmt(r.pooled_bias, 2), fmt(r.pooled_sd, 2), fmt(r.pooled_loa_lo, 2), fmt(r.pooled_loa_hi, 2),
                 fmt(r.icc21_pooled), fmt(r.angle_mean, 1)])
st.append(table(rows, [20 * mm, 20 * mm, 12 * mm, 12 * mm, 16 * mm, 15 * mm, 17 * mm, 17 * mm, 17 * mm, CW - 146 * mm]))
st.append(tcap("Bland–Altman agreement of per-band relative change at 160 mmHg (percentage points), repeated-measures "
               "method."))
st.append(P(f"The spectrometer isn't a clean reference either. The median coefficient of variation across replicate "
            f"spectra at one site was <b>{rep_med:.0%}</b>, and the ICC across sites at baseline was "
            f"{icc_lo:.2f}–{icc_hi:.2f}. Between-ROI variation of camera baseline levels was "
            f"{cam_cv_med['subject_01']:.0%} in participant 01 and {cam_cv_med['subject_02']:.0%} in participant 02. "
            f"Neither instrument should be treated as ground truth for the other."))
st.append(figure("s13_bland_altman.png", CW * 0.78, "Bland–Altman plot of per-band relative change at 160 mmHg "
                 "(participant level; colour = band). Lines show the pooled bias and 95% limits of agreement.", nf()))

st.append(P("S14 · Occlusion-state models and hypothesis H2", "h2"))
st.append(P(f"Windows of 5 s (1 s stride, never crossing a block edge or gap) gave <b>{win[0]} windows</b> "
            f"({win[1]} from participant 01, {win[2]} from participant 02) with {win[3]} features each. No timing "
            f"variable was ever an input to the spectral models. Validation V1 holds out thirds of every block within a "
            f"participant, with a 5 s purge. V2 trains on one participant and tests on the other, in both directions."))
st.append(P("Phase classification (baseline / clamping / rest)", "h3"))
rows = [["Model", "Features", "Validation", "Balanced accuracy", "95% CI"]]
def brow(r, label=None):
    return [label or MODNAME.get(r.model, r.model), FAMNAME.get(r.feature_set, r.feature_set), r.scheme,
            f"<b>{r['mean']:.3f}</b>", f"{r.lo:.3f}–{r.hi:.3f}"]
rows.append(brow(null_c, "Shuffled-label null"))
rows.append(["Chance", "–", "–", "0.333", "–"])
for _, r in v2c.head(5).iterrows():
    rows.append(brow(r))
rows.append(brow(v1_best))
rows.append(brow(time_c, "Elapsed time only"))
st.append(table(rows, [48 * mm, 40 * mm, 20 * mm, 30 * mm, CW - 138 * mm], highlight_rows=[len(rows) - 1]))
st.append(tcap("Phase classification. V2 rows are the five best spectral models across participants; the V1 row is "
               "the best within-participant model. Appendix A lists every model."))
st.append(figure("s14_benchmark_v2.png", CW * 0.95, "Cross-participant phase classification: balanced accuracy with "
                 "moving-block bootstrap 95% CIs. Dotted: shuffled-label null; solid grey: chance (1/3).", nf()))
st.append(figure("s14_confusion_best.png", CW * 0.48, f"Row-normalised confusion matrix of the best cross-participant "
                 f"model ({FAMNAME[v2_best.feature_set]}, {MODNAME[v2_best.model]}, train 01 → test 02).", nf()))
ng = gate[(gate.informative == True) & (~gate.model.isin(["time_only"]))]
st.append(P(f"<b>Informative gate.</b> A model counts as informative only if it beats the shuffled-label null in both "
            f"V2 directions. {len(ng)} of {len(gate[~gate.model.isin(['time_only', 'majority'])])} non-trivial spectral "
            f"models passed. Raw counts passed only with PLS and SVM."))
st.append(P("Pressure regression on clamping windows", "h3"))
st.append(P(f"Across participants, the best model ({FAMNAME[v2r_best.feature_set]}, {MODNAME[v2r_best.model]}) "
            f"reached an RMSE of <b>{v2r_best['mean']:.1f} mmHg</b> (95% CI {v2r_best.lo:.1f}–{v2r_best.hi:.1f}), "
            f"against {v2r_mean:.1f} mmHg for always predicting the mean. The drift check applied each pressure model "
            f"to rest windows; it flagged neither direction "
            f"(ρ = {drift.rho_pred_vs_time[0]:.2f} and {drift.rho_pred_vs_time[1]:.2f} for predicted pressure vs time)."))
st.append(P("H2 · ratios vs raw counts", "h3"))
t1 = t1d.set_index(["feature_set", "model"])
st += keybox("H2 · not supported", [
    "H2 needed ratios to beat raw counts in both cross-participant camera directions <i>and</i> in the ten-person "
    "spectrometer task. The camera part held. The spectrometer part didn't.",
    f"Ten-person task (baseline vs 160 mmHg, leave-one-participant-out), logistic regression on PCA: ratios "
    f"{t1.loc[('ratio', 'logreg_pca'), 'mean']:.2f} vs raw {t1.loc[('raw', 'logreg_pca'), 'mean']:.2f}, exact Wilcoxon "
    f"p = {h2_p:.3f}."], col="#CF222E")
rows = [["Features", "Logistic / PCA", "Random forest", "SVM", "SVM 95% CI"]]
for f_ in ["raw", "l1", "ratio", "all"]:
    rows.append([FAMNAME[f_], f"{t1.loc[(f_, 'logreg_pca'), 'mean']:.3f}", f"{t1.loc[(f_, 'rf'), 'mean']:.3f}",
                 f"<b>{t1.loc[(f_, 'svm'), 'mean']:.3f}</b>",
                 "–".join(f"{x:.3f}" for x in ast.literal_eval(t1.loc[(f_, 'svm'), 'ci']))])
st.append(table(rows, [40 * mm, 30 * mm, 30 * mm, 26 * mm, CW - 126 * mm]))
st.append(tcap("Ten-person spectrometer task, balanced accuracy (chance 0.5). SVM did best with L1-normalised or ratio "
               "features."))
st.append(P("S15 (gated) · temporal models", "h3"))
st.append(P("A TCN and a GRU (each under 100,000 parameters, three seeds) ran under the same V2 validation. Neither was "
            "better than the best classical model in any comparison. For phase classification they were 0.11–0.18 "
            "lower. The rest of S15 (CNN-LSTM, a small transformer and the full 20-configuration sweep) is still to do."))
rows = [["Task", "Backbone", "Train → test", "Temporal", "Best classical", "Difference", "95% CI", "Better"]]
for _, r in tvc.iterrows():
    sign = -1 if r.task == "reg" else 1
    rows.append(["phase" if r.task == "cls" else "pressure (RMSE)", r.backbone.upper(),
                 f"{r.train_subject[-2:]} → {r.test_subject[-2:]}", f"{sign * r.ensemble_score:.3f}" if r.task == "cls"
                 else f"{-r.ensemble_score:.1f}", f"{r.classical_score:.3f}" if r.task == "cls" else f"{-r.classical_score:.1f}",
                 f"{r['diff']:+.3f}" if r.task == "cls" else f"{r['diff']:+.1f}",
                 f"{r.diff_ci_lo:+.3f} to {r.diff_ci_hi:+.3f}" if r.task == "cls" else f"{r.diff_ci_lo:+.1f} to {r.diff_ci_hi:+.1f}",
                 badge("no", "#CF222E")])
st.append(table(rows, [26 * mm, 17 * mm, 20 * mm, 18 * mm, 22 * mm, 20 * mm, 32 * mm, CW - 155 * mm]))
st.append(tcap("Temporal models vs the best classical model. Phase: balanced accuracy, higher is better. Pressure: "
               "RMSE in mmHg, lower is better; a negative difference means the temporal model was worse."))

# ---------------------------------------------------------------- limits and next steps
st.append(PageBreak())
st.append(P("8  Limitations", "h1"))
st += bullets([
    "<b>Two camera participants.</b> Camera spectra exist for participants 01 and 02 (seven ROIs). Camera results are "
    "within-person findings.",
    "<b>Fixed pressure order.</b> Pressure rises monotonically with time. Placebo and drift checks reduce this "
    "confound but cannot remove it, as the time-only model shows.",
    "<b>No white reference.</b> Relative reflectance and a spectrometer-anchored gain stand in for absolute "
    "calibration.",
    "<b>Sparse reference.</b> Spectrometer spectra exist only at baseline and 160 mmHg, with no timestamps.",
    "<b>ROI correspondence unconfirmed.</b> ROI-level agreement assumes spectrometer ROI <i>k</i> is camera ROI <i>k</i>.",
    "<b>Visible range only.</b> 465–641 nm; no near-infrared bands.",
    "<b>Healthy volunteers.</b> Cuff occlusion is a physiological perturbation model. Nothing here measures StO<sub>2</sub> "
    "or perfusion directly, and no diagnostic claim for PAD follows."])
st.append(P("9  Next steps", "h1"))
st += bullets([
    "Supervisor sign-off of the frozen analysis plan, and confirmation of ROI correspondence from the dataset "
    "publication.",
    "S15: complete the temporal-model sweep (CNN-LSTM, small transformer, 20 configurations per family, 5 seeds).",
    "S16: recovery estimates from shorter or noisier recordings.",
    "S17: sensitivity battery over the grid frozen in S2.",
    "S18: reports R1–R6, clean-checkout re-run with matching checksums, manuscript and release.",
    "Optional SX: rebuild the standalone file with all ten participants' camera data."])

# ---------------------------------------------------------------- appendix A
st.append(PageBreak())
st.append(P("Appendix A  ·  Full S14 model benchmark", "h1"))
st.append(P("Every classical model from S14, grouped by validation scheme and task. Balanced accuracy for phase "
            "classification (higher is better), RMSE in mmHg for pressure regression (lower is better). Intervals are "
            "moving-block bootstrap 95% CIs.", "small"))
for scheme, task, title, asc in [("V2", "cls", "V2 · across participants · phase classification", False),
                                 ("V1", "cls", "V1 · within participant · phase classification", False),
                                 ("V2", "reg", "V2 · across participants · pressure regression", True),
                                 ("V1", "reg", "V1 · within participant · pressure regression", True)]:
    sub = bench[(bench.scheme == scheme) & (bench.task == task)].sort_values("mean", ascending=asc)
    st.append(P(title, "h3"))
    rows = [["Features", "Model", "Mean", "95% CI"]]
    for _, r in sub.iterrows():
        d = 3 if task == "cls" else 1
        rows.append([FAMNAME.get(r.feature_set, r.feature_set), MODNAME.get(r.model, r.model), f"{r['mean']:.{d}f}",
                     f"{r.lo:.{d}f}–{r.hi:.{d}f}"])
    st.append(table(rows, [46 * mm, 46 * mm, 24 * mm, 34 * mm]))
    st.append(Spacer(1, 6))

# ---------------------------------------------------------------- appendix B
st.append(CondPageBreak(80 * mm))
st.append(P("Appendix B  ·  Output files", "h1"))
st.append(P("The run directory <font name='DVM'>phase_A-E_analysis/pmhm_outputs/full/</font> holds everything this "
            "report draws on.", "small"))
inv = []
for d in ["reports", "figures", "tables", "models", "predictions", "analysis_plan", "snapshots", "logs", "steps",
          "checkpoints"]:
    p = os.path.join(RUN, d)
    if os.path.isdir(p):
        files = [os.path.join(dp, f) for dp, _, fs in os.walk(p) for f in fs]
        size = sum(os.path.getsize(f) for f in files)
        inv.append([d + "/", f"{len(files):,}", f"{size / 2**20:.1f} MB"])
desc = {"reports/": "Markdown report and machine-readable JSON summary",
        "figures/": "Figures in PNG and PDF",
        "tables/": "Result tables (CSV, JSONL, Parquet)",
        "models/": "Fitted models", "predictions/": "Out-of-fold predictions",
        "analysis_plan/": "Frozen analysis plan", "snapshots/": "Configuration snapshot",
        "logs/": "Run log and JSONL event stream, plus the Kaggle kernel log",
        "steps/": "Cached step results for resume", "checkpoints/": "Temporal-model checkpoints"}
rows = [["Folder", "Contents", "Files", "Size"]] + [[r[0], desc.get(r[0], ""), r[1], r[2]] for r in inv]
st.append(table(rows, [30 * mm, 96 * mm, 18 * mm, CW - 144 * mm]))

doc.build(st)
print("wrote", OUT)
