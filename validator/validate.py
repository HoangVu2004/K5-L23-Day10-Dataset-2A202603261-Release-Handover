#!/usr/bin/env python3
"""Validator for Day 10 Lab - Dataset Release & Handover.
Standard library only. Uses pngutil for PNG mask decoding.

Usage:
  python validator/validate.py <delivery_dir> --out <errors.json> [--candidates <candidates.json>]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Add scripts directory to path to import pngutil
SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import pngutil  # noqa: E402


def sha256_file(path: Path) -> str:
    """Compute sha256 hex digest of file bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_delivery(delivery_dir: Path):
    """Load core delivery artifacts."""
    manifest_path = delivery_dir / "manifest.json"
    metadata_path = delivery_dir / "metadata.json"
    jobs_path = delivery_dir / "jobs.csv"
    panoptic_path = delivery_dir / "panoptic.json"
    classes_path = delivery_dir / "classes.txt"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["items"]
    metadata = {m["image"]: m for m in json.loads(metadata_path.read_text(encoding="utf-8"))["items"]}
    
    jobs = {}
    with jobs_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            jobs[row["job_id"]] = row

    panoptic = json.loads(panoptic_path.read_text(encoding="utf-8"))
    
    classes_80 = {}
    if classes_path.is_file():
        for line in classes_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                cid, cname = line.split(" ", 1)
                classes_80[int(cid)] = cname.strip()

    return manifest, metadata, jobs, panoptic, classes_80


def check_mask_overlap(args):
    """Worker function to check thing_overlap for a single image mask."""
    mask_path, segments, thing_cat_ids = args
    if not mask_path.is_file():
        return None

    try:
        width, height, pixels = pngutil.read_rgb(mask_path)
    except Exception:
        return None

    counts = {}
    for i in range(0, len(pixels), 3):
        sid = pngutil.segment_id(pixels, i)
        if sid:
            counts[sid] = counts.get(sid, 0) + 1

    for seg in segments:
        if seg.get("category_id") in thing_cat_ids and not seg.get("iscrowd"):
            declared = seg.get("area", 0)
            actual = counts.get(seg["id"], 0)
            # When stolen, donor loses 15-30% of pixels (at least 5-10 pixels)
            if declared > actual and (declared - actual >= 10 or (declared - actual) / max(declared, 1) > 0.05):
                return seg["id"]
    return None


def validate_rules(delivery_dir: Path, manifest, metadata, jobs, panoptic) -> list[dict]:
    """Find all 9 rule-based error types."""
    errors: list[dict] = []
    seen = set()

    def add_error(err_type: str, target: str):
        key = (err_type, target)
        if key not in seen:
            seen.add(key)
            errors.append({"type": err_type, "target": target})

    # 1. missing_image & wrong_hash
    for name, item in manifest.items():
        img_path = delivery_dir / item["image"]
        if not img_path.is_file():
            add_error("missing_image", name)
            continue
        if sha256_file(img_path) != item.get("image_sha256"):
            add_error("wrong_hash", name)
            continue
        # Also verify label and mask hashes if recorded
        label_path = delivery_dir / item["label"]
        if label_path.is_file() and item.get("label_sha256"):
            if sha256_file(label_path) != item["label_sha256"]:
                add_error("wrong_hash", name)
                continue
        mask_path = delivery_dir / item["mask"]
        if mask_path.is_file() and item.get("mask_sha256"):
            if sha256_file(mask_path) != item["mask_sha256"]:
                add_error("wrong_hash", name)
                continue

    # 2. guideline_mismatch
    for name, meta in metadata.items():
        job_id = meta.get("job_id")
        if job_id and job_id in jobs:
            expected = jobs[job_id]["guideline"]
            actual = meta.get("guideline_version")
            if actual != expected:
                add_error("guideline_mismatch", name)

    # 3. scene_leak (target is scene_id!)
    scenes: dict[str, set[str]] = {}
    for name, meta in metadata.items():
        scene_id = meta.get("scene_id")
        split = meta.get("split")
        if scene_id and split:
            scenes.setdefault(scene_id, set()).add(split)
    for scene_id, splits in scenes.items():
        if len(splits) > 1:
            add_error("scene_leak", scene_id)

    # 4. Detection label rules: invalid_class, bbox_out_of_bounds, duplicate_box
    for name, item in manifest.items():
        label_path = delivery_dir / item["label"]
        if not label_path.is_file():
            continue
        content = label_path.read_text(encoding="utf-8")
        rows = [ln.split() for ln in content.splitlines() if ln.strip()]

        for row in rows:
            try:
                c = int(float(row[0]))
            except ValueError:
                add_error("invalid_class", name)
                break
            if not (0 <= c < 80):
                add_error("invalid_class", name)
                break

        for row in rows:
            try:
                x, y, w, h = map(float, row[1:5])
            except ValueError:
                add_error("bbox_out_of_bounds", name)
                break
            # Tolerance 0.005 for numerical edge boundaries
            if (x - w / 2 < -0.005 or y - h / 2 < -0.005 or
                    x + w / 2 > 1.005 or y + h / 2 > 1.005 or w <= 0 or h <= 0):
                add_error("bbox_out_of_bounds", name)
                break

        # duplicate_box: same class, same size, shifted 1-2 pixels
        has_dup = False
        n_boxes = len(rows)
        for i in range(n_boxes):
            if has_dup:
                break
            for j in range(i + 1, n_boxes):
                r1, r2 = rows[i], rows[j]
                if r1[0] == r2[0]:
                    try:
                        x1, y1, w1, h1 = map(float, r1[1:5])
                        x2, y2, w2, h2 = map(float, r2[1:5])
                    except ValueError:
                        continue
                    if abs(w1 - w2) < 1e-4 and abs(h1 - h2) < 1e-4:
                        dx = abs(x1 - x2)
                        dy = abs(y1 - y2)
                        if 0 < max(dx, dy) < 0.02:
                            add_error("duplicate_box", name)
                            has_dup = True
                            break

    # 5. Panoptic rules: invalid_category_id & thing_overlap
    cat_ids = {c["id"] for c in panoptic.get("categories", [])}
    thing_cat_ids = {c["id"] for c in panoptic.get("categories", []) if c.get("isthing")}

    # invalid_category_id
    for ann in panoptic.get("annotations", []):
        stem = Path(ann.get("file_name", "")).stem
        for seg in ann.get("segments_info", []):
            if seg.get("category_id") not in cat_ids:
                add_error("invalid_category_id", stem)
                break

    # thing_overlap via parallel worker pool
    overlap_tasks = []
    ann_by_stem = {}
    for ann in panoptic.get("annotations", []):
        stem = Path(ann.get("file_name", "")).stem
        mask_file = delivery_dir / "masks" / ann.get("file_name", "")
        overlap_tasks.append((mask_file, ann.get("segments_info", []), thing_cat_ids))
        ann_by_stem[mask_file] = stem

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = pool.map(check_mask_overlap, overlap_tasks)
        for task, res in zip(overlap_tasks, results):
            if res is not None:
                stem = ann_by_stem[task[0]]
                add_error("thing_overlap", stem)

    return errors


def box_iou(b1, b2) -> float:
    """Compute IoU between two [xmin, ymin, xmax, ymax] boxes."""
    ix1 = max(b1[0], b2[0])
    iy1 = max(b1[1], b2[1])
    ix2 = min(b1[2], b2[2])
    iy2 = min(b1[3], b2[3])
    inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
    a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
    union = a1 + a2 - inter
    return inter / union if union > 0 else 0.0


def generate_candidates(delivery_dir: Path, manifest, panoptic, classes_80) -> list[dict]:
    """Generate cross-check candidate errors for Phase 2 visual review."""
    candidates: list[dict] = []
    seen = set()

    def add_cand(cand_type: str, target: str, reason: str):
        key = (cand_type, target)
        if key not in seen:
            seen.add(key)
            candidates.append({"type": cand_type, "target": target, "reason": reason})

    cat_by_id = {c["id"]: c for c in panoptic.get("categories", [])}
    images_meta = {Path(im["file_name"]).stem: im for im in panoptic.get("images", [])}
    anns_by_stem = {Path(ann["file_name"]).stem: ann for ann in panoptic.get("annotations", [])}

    for name, item in manifest.items():
        label_path = delivery_dir / item["label"]
        if not label_path.is_file() or name not in anns_by_stem or name not in images_meta:
            continue

        im_meta = images_meta[name]
        W, H = im_meta["width"], im_meta["height"]

        # Parse detection boxes
        raw_rows = [ln.split() for ln in label_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        det_boxes = []
        for row in raw_rows:
            try:
                cid = int(float(row[0]))
                x, y, w, h = map(float, row[1:5])
            except ValueError:
                continue
            if cid not in classes_80:
                continue
            xmin = (x - w / 2) * W
            ymin = (y - h / 2) * H
            xmax = (x + w / 2) * W
            ymax = (y + h / 2) * H
            det_boxes.append({
                "cid": cid,
                "cname": classes_80[cid],
                "bbox": [xmin, ymin, xmax, ymax],
                "area": w * h * W * H,
                "norm": [x, y, w, h]
            })

        # Parse panoptic thing segments
        ann = anns_by_stem[name]
        pan_segs = []
        for s in ann.get("segments_info", []):
            cid = s.get("category_id")
            cat = cat_by_id.get(cid)
            if not cat or not cat.get("isthing") or s.get("iscrowd"):
                continue
            sx, sy, sw, sh = s["bbox"]
            pan_segs.append({
                "id": s["id"],
                "cid": cid,
                "cname": cat["name"],
                "bbox": [sx, sy, sx + sw, sy + sh],
                "area": s.get("area", sw * sh),
                "w": sw,
                "h": sh
            })

        # Check missing_box: significant thing segment with no detection box
        for seg in pan_segs:
            if seg["area"] >= 1024 or (seg["w"] * seg["h"]) >= 0.008 * W * H:
                best_iou = max((box_iou(seg["bbox"], d["bbox"]) for d in det_boxes), default=0.0)
                if best_iou < 0.15:
                    add_cand("missing_box", name, f"Panoptic thing {seg['cname']} (area={seg['area']}) has no matching detection box (best iou={best_iou:.2f})")

        # Check instance_merge: one segment overlaps two detection boxes of same class
        for seg in pan_segs:
            overlapping_dets = [d for d in det_boxes if d["cname"] == seg["cname"] and box_iou(seg["bbox"], d["bbox"]) > 0.25]
            if len(overlapping_dets) >= 2:
                add_cand("instance_merge", name, f"Panoptic segment {seg['cname']} overlaps {len(overlapping_dets)} detection boxes of same class")

        # Check class_swap / category_swap and bbox_drift
        for d in det_boxes:
            for seg in pan_segs:
                iou = box_iou(d["bbox"], seg["bbox"])
                if iou > 0.35:
                    if d["cname"] != seg["cname"]:
                        add_cand("class_swap", name, f"Overlap iou={iou:.2f} but detection is '{d['cname']}' while panoptic is '{seg['cname']}'")
                        add_cand("category_swap", name, f"Overlap iou={iou:.2f} but detection is '{d['cname']}' while panoptic is '{seg['cname']}'")
                elif 0.15 < iou <= 0.35 and d["cname"] == seg["cname"]:
                    add_cand("bbox_drift", name, f"Same class '{d['cname']}' but low iou={iou:.2f} indicates potential bbox drift")

    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dataset delivery batch")
    parser.add_argument("delivery_dir", help="Path to delivery directory")
    parser.add_argument("--out", required=True, help="Output path for errors.json")
    parser.add_argument("--candidates", help="Optional output path for candidates.json")
    args = parser.parse_args()

    delivery_dir = Path(args.delivery_dir)
    if not delivery_dir.is_dir():
        print(f"Error: {delivery_dir} is not a directory", file=sys.stderr)
        return 1

    manifest, metadata, jobs, panoptic, classes_80 = load_delivery(delivery_dir)

    # 1. Detect rule errors
    rule_errors = validate_rules(delivery_dir, manifest, metadata, jobs, panoptic)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"errors": rule_errors}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(rule_errors)} rule errors to {out_path}")

    # 2. Generate candidates if requested
    if args.candidates:
        cands = generate_candidates(delivery_dir, manifest, panoptic, classes_80)
        cand_path = Path(args.candidates)
        cand_path.parent.mkdir(parents=True, exist_ok=True)
        cand_path.write_text(json.dumps({"candidates": cands}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {len(cands)} review candidates to {cand_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
