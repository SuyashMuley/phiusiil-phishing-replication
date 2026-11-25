# Final report outline (draft 1, 2026-11-25; report due 2026-12-08)

Working title: **Replicating and Critiquing PhiUSIIL Phishing URL Detection Under Dataset Shift**

Framing from the 11/20 feedback: the transfer study is the main contribution; the reproduction is the baseline; shortcut vs label leakage is the motivation; a larger dataset alone does not fix the source differences; thresholds stay fixed from source validation.

## 1. Introduction (about 0.75 page)
- The problem: a 99% number on one benchmark says little about a new source of URLs.
- Two questions: (Q1) does the paper's headline reproduce, and what does it depend on? (Q2) does a URL-only detector keep its operating point on independent sources?
- Contributions: (1) faithful reproduction of Tables 3, 5, 6, 7 and the finding that the headline is reproducible from URL form alone; (2) shortcut vs label leakage, stated precisely; (3) a transfer study with matched pools, domain-disjoint splits, validation-fixed thresholds and three independent sources; (4) an explanation of what differs between sources (form, provenance, time) and a test that normalizing URL form does not fix transfer.

## 2. Background and related work (about 1 page)
- PhiUSIIL (Prasad and Chandra 2024): data, USI, prequential protocol, voting profiles.
- Related work, each with what it shows and how this report differs: Ahamed et al. 2026; Misiek and Hyla 2026; Rashid et al. 2024; Rahman et al. 2026 (two features suffice); Arp et al. 2022 (pitfalls); PhreshPhish (Dalton et al. 2025) as data.
- Gap: the sources are never compared at a fixed operating point with matched size and class mix, nor are source differences measured directly.

## 3. Data (about 1 page)
- Table: PhiUSIIL, GramBeddings, PhreshPhish, PhishTank snapshot: rows, classes, collection period, what is documented about provenance.
- URL-form profile (homepage share, trailing slash, www, https by source and class).

## 4. Part A: reproduction (about 1.25 pages)
- Protocol as in the paper (prequential, three voting profiles, pre-training experiment, batch baselines); deviations stated.
- Results: Tables 5/6 (file order and shuffled orders), Table 7, Table 3 (appendix).
- Feature-group ablation: dropping USI changes BestSecurity accuracy by 0.0001; URL-only features still reach 0.987.

## 5. Shortcut check on URLSimilarityIndex (about 0.75 page)
- USI uses no labels; legit URLs come from the list it is matched against; legit USI = 100 for all 134,850.
- Redundant artifacts: URL form, empty page captures; ablation table; what this does not show.

## 6. Part B: transfer study (about 2.25 pages)
- Design: 22 URL-only features, matched pools (11,666 rows, 50% phishing), registered-domain-disjoint splits, threshold at 95% recall on source validation, target rows seen in training removed, URL-type slices, five models, three feature sets, five seeds.
- Main result: Table (HistGB mean±sd, range over five models) and operating-point figure.
- Slices (homepage vs deep), PhishTank recall with the caveat, cross-model agreement and instability of pair-level AUROC.

## 7. Why transfer fails: source differences (about 1.25 pages)
- A1 form profile; A2 source discriminator (sources separable within class); A3 canonical URLs do not fix transfer (and in-source accuracy falls); A4 score distributions explain the opposite failure directions; A5 provenance (what GramBeddings documents and does not).
- Why a larger dataset alone does not resolve it.

## 8. Limitations (about 0.5 page)
- Small matched pools and lumpy domain splits; 22 lexical features only; source, period and hosting mix confounded; domain-disjoint filtering removes hosting-platform phishing; PhishTank phishing only; GramBeddings sampled to 100k; undocumented provenance; no content features in Part B.

## 9. Conclusion (about 0.4 page)
- What reproduces, what does not transfer, what to report instead (fixed-threshold FPR on an independent source, source-vs-class check).

## Appendix
- A. Table 3 batch baselines; B. URL-type slice table; C. score-distribution figure; D. hardware, timing, commands (reproducibility).

## Items I cannot verify and will flag in the draft
- GramBeddings paper authors, venue and year (the repository README gives only the title and a ScienceDirect link).
- Related-work numbers are quoted at the verification level recorded in `MD/sota_verified_table.md` (abstract-level for most).
- Claims about how PhreshPhish benign URLs were collected are NOT made (not verified).
