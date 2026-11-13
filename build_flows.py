"""Build Sankey flows from the UCI "Predict Students' Dropout and Academic Success" dataset.

Each student moves through three stages:
    1st semester result  ->  2nd semester result  ->  final outcome

A semester result is based on curricular units approved vs. enrolled:
    Passed all, Passed some, Passed none, or No units (enrolled in nothing that term).

Writes one graph per degree program plus "All programs" to docs/flows.json.

Data: Realinho, V., Vieira Martins, M., Machado, J., & Baptista, L. (2021).
Predict Students' Dropout and Academic Success [Dataset]. UCI Machine Learning
Repository. https://doi.org/10.24432/C5MC89 (CC BY 4.0)
"""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

PROGRAMS = {
    "33": "Biofuel Production Technologies",
    "171": "Animation and Multimedia Design",
    "8014": "Social Service (evening)",
    "9003": "Agronomy",
    "9070": "Communication Design",
    "9085": "Veterinary Nursing",
    "9119": "Informatics Engineering",
    "9130": "Equinculture",
    "9147": "Management",
    "9238": "Social Service",
    "9254": "Tourism",
    "9500": "Nursing",
    "9556": "Oral Hygiene",
    "9670": "Advertising and Marketing Management",
    "9773": "Journalism and Communication",
    "9853": "Basic Education",
    "9991": "Management (evening)",
}
ALL = "All programs"
RESULTS = ["Passed all", "Passed some", "Passed none", "No units"]
OUTCOMES = ["Graduate", "Enrolled", "Dropout"]
# The dataset's outcome is measured at the end of the program's normal duration
# (e.g. 3 years for a 3-year degree), so "Enrolled" means still studying but
# not finished on time.
OUTCOME_LABELS = {"Graduate": "Graduated", "Enrolled": "Still enrolled (behind schedule)",
                  "Dropout": "Dropped out"}


def semester_result(row: dict, sem: str) -> str:
    enrolled = int(row[f"Curricular units {sem} sem (enrolled)"])
    approved = int(row[f"Curricular units {sem} sem (approved)"])
    if enrolled == 0:
        return "No units"
    if approved >= enrolled:
        return "Passed all"
    return "Passed some" if approved > 0 else "Passed none"


def build_graph(rows: list[dict]) -> dict:
    stages = [[f"Sem 1: {r}" for r in RESULTS], [f"Sem 2: {r}" for r in RESULTS],
              [OUTCOME_LABELS[o] for o in OUTCOMES]]
    names = [n for stage in stages for n in stage]
    index = {n: i for i, n in enumerate(names)}

    counts = Counter()
    for row in rows:
        s1 = f"Sem 1: {semester_result(row, '1st')}"
        s2 = f"Sem 2: {semester_result(row, '2nd')}"
        counts[(s1, s2)] += 1
        counts[(s2, OUTCOME_LABELS[row["Target"]])] += 1

    links = [{"source": index[a], "target": index[b], "value": v}
             for (a, b), v in sorted(counts.items(), key=lambda kv: (index[kv[0][0]], index[kv[0][1]]))]
    used = {l["source"] for l in links} | {l["target"] for l in links}
    # Drop unused nodes and re-index so empty categories don't clutter the chart.
    keep = [i for i in range(len(names)) if i in used]
    remap = {old: new for new, old in enumerate(keep)}
    return {
        "students": len(rows),
        "nodes": [{"name": names[i]} for i in keep],
        "links": [{**l, "source": remap[l["source"]], "target": remap[l["target"]]} for l in links],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=Path("data/students.csv"))
    parser.add_argument("--out", type=Path, default=Path("docs/flows.json"))
    args = parser.parse_args()

    with args.input.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f, delimiter=";"))

    by_program: dict[str, list[dict]] = {}
    for row in rows:
        by_program.setdefault(PROGRAMS.get(row["Course"], f"Program {row['Course']}"), []).append(row)

    graphs = {ALL: build_graph(rows)}
    for name in sorted(by_program):
        graphs[name] = build_graph(by_program[name])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(graphs, indent=1) + "\n")

    outcome = Counter(r["Target"] for r in rows)
    print(f"{len(rows)} students, {len(by_program)} programs: " +
          ", ".join(f"{k} {outcome[k]}" for k in OUTCOMES))
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
