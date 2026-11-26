"""Run from any directory. Store identifying results only in research/private."""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from photometaclean.metadata.analysis import analyze

PRIVATE = ROOT / "research/private"
FOLDERS = ["vorm Update", "Nach Update"]


def inventory(path):
    with path.open("rb") as f:
        before = hashlib.file_digest(f,"sha256").hexdigest()
    try:
        row = analyze(path)
    except Exception as exc:
        row = dict(path=str(path), metadata={}, frames=[], blocks=[], error=str(exc),
                   size=path.stat().st_size, sha256=before)
    with path.open("rb") as f:
        after = hashlib.file_digest(f,"sha256").hexdigest()
    if before != after or row["sha256"] != before:
        raise RuntimeError("Input changed during analysis")
    row["path"] = str(path.relative_to(ROOT))
    return row


def evidence(a,b):
    if "fingerprint" not in a or "fingerprint" not in b:
        return None
    x,y = (bytes.fromhex(r["fingerprint"]) for r in (a,b))
    distance = sum(abs(i-j) for i,j in zip(x,y))/len(x)
    key = "ExifIFD:Main:DateTimeOriginal"
    capture = bool(a["metadata"].get(key)) and a["metadata"][key] == b["metadata"].get(key)
    stem = Path(a["path"]).stem.casefold() == Path(b["path"]).stem.casefold()
    pixels = a["frames"][0] == b["frames"][0]
    if distance > 25 and not (capture or stem):
        return None
    return dict(distance=round(distance,3),same_capture=capture,same_stem=stem,
                same_resolution=a["resolution"]==b["resolution"],same_frame=pixels)


def differences(a,b):
    return dict(added={k:b[k] for k in b.keys()-a.keys()},
                removed={k:a[k] for k in a.keys()-b.keys()},
                changed={k:[a[k],b[k]] for k in a.keys() & b.keys() if a[k]!=b[k]})


def compare(before,after):
    candidates = []
    for a in before:
        for b in after:
            e = evidence(a,b)
            if e:
                strong = e["same_frame"] or (e["distance"]<=8 and (e["same_capture"] or e["same_stem"]))
                candidates.append(dict(before=a["path"],after=b["path"],evidence=e,strong=strong))
    left,right = [Counter(c[key] for c in candidates if c["strong"]) for key in ("before","after")]
    lookup = {r["path"]:r for r in before+after}
    for c in candidates:
        c["status"] = "matched" if c["strong"] and left[c["before"]]==right[c["after"]]==1 else "uncertain"
        if c["strong"] or c["evidence"]["same_capture"] or c["evidence"]["same_stem"]:
            a,b = lookup[c["before"]],lookup[c["after"]]
            c["metadata_diff"] = differences(a["metadata"],b["metadata"])
            c["structure_diff"] = differences({k:a.get(k) for k in ("blocks","frames","codestreams","signature","manifest")},
                                               {k:b.get(k) for k in ("blocks","frames","codestreams","signature","manifest")})
    return candidates


def save_json(name,obj):
    temp = PRIVATE/(name+".tmp")
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True),encoding="utf8")
    temp.replace(PRIVATE/name)


def save_csv(name,fields,rows):
    temp = PRIVATE/(name+".tmp")
    with temp.open("w",newline="",encoding="utf8") as f:
        writer = csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(PRIVATE/name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers",type=int,default=6,choices=range(1,17))
    args = parser.parse_args()
    os.umask(0o077)
    PRIVATE.mkdir(parents=True,exist_ok=True)
    paths = []
    for folder in FOLDERS:
        source = ROOT/folder
        if not source.is_dir() or source.is_symlink():
            raise ValueError("Missing or linked research directory")
        for parent,dirs,files in os.walk(source):
            dirs[:] = sorted(d for d in dirs if not (Path(parent)/d).is_symlink())
            paths.extend(p for f in sorted(files) if (p:=Path(parent)/f).is_file() and not p.is_symlink())
    start = time.perf_counter()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(inventory,paths))
    elapsed = time.perf_counter()-start
    save_json("inventory.json",rows)
    save_csv("inventory.csv",["path","format","resolution","size","sha256","signature","error"],rows)
    before,after = [[r for r in rows if Path(r["path"]).parts[0]==folder] for folder in FOLDERS]
    pairs = compare(before,after)
    save_json("pairs.json",pairs)
    save_csv("metadata_changes.csv", ["before_file", "after_file", "status", "change", "tag", "values_json"],
             ({"before_file": pair["before"], "after_file": pair["after"], "status": pair["status"],
               "change": kind, "tag": tag, "values_json": json.dumps(value, ensure_ascii=False)}
              for pair in pairs for kind, values in pair.get("metadata_diff", {}).items()
              for tag, value in sorted(values.items())))
    signed = []
    for row in rows:
        manifest = row.get("manifest")
        if manifest is None:
            continue
        active = manifest["manifests"][manifest["active_manifest"]]
        actions = [action for claim in active.get("assertions", [])
                   if claim["label"].startswith("c2pa.actions")
                   for action in claim["data"].get("actions", [])]
        signed.append({"path": row["path"], "sdk_status": row["signature"],
                       "validation_failures": ", ".join(row.get("validation_failures", [])),
                       "source_types": ", ".join(sorted({a["digitalSourceType"] for a in actions
                                                         if "digitalSourceType" in a})),
                       "action_count": len(actions)})
    save_csv("signed_exports.csv", ["path", "sdk_status", "validation_failures", "source_types", "action_count"], signed)
    save_csv("pairs.csv",["before","after","status","distance","same_capture","same_stem","same_resolution","same_frame"],
             [dict(**c,**c["evidence"]) for c in pairs])
    matched = {c[key] for c in pairs if c["status"]=="matched" for key in ("before","after")}
    save_json("unmatched.json",[r["path"] for r in rows if r["path"] not in matched])
    bench = dict(workers=args.workers,files=len(rows),seconds=round(elapsed,3),files_per_second=round(len(rows)/elapsed,3),
                 mib_per_second=round(sum(r["size"] for r in rows)/2**20/elapsed,3))
    save_json("benchmark.json",bench)
    print(bench)
    print("errors:",sum("error" in r for r in rows),"matched:",len(matched)//2)


if __name__=="__main__":
    main()
