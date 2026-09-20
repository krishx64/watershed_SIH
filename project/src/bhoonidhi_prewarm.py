"""
bhoonidhi_prewarm.py — Admin CLI for Pre-warming Bhoonidhi Scenes & MongoDB Raster Cache.

Allows operators and evaluators to pre-cache any target watershed so live demos
and field requests execute at sub-50ms MongoDB speeds.

Usage:
  python src/bhoonidhi_prewarm.py --name Kadwanchi
  python src/bhoonidhi_prewarm.py --bbox 75.95 19.80 76.05 19.90 --date-tag T2
"""

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import os
os.environ["BHOONIDHI_LIVE_DOWNLOAD"] = "true"

import mongo_raster_cache as mrc
from config import AOI_BBOX, AOI_JOBS, DATA_RAW, DATA_PROCESSED
import data_adapter as da


def prewarm_aoi(name: str, bbox: tuple, dates=("T1", "T2")):
    print(f"\n=======================================================")
    print(f"Pre-warming Watershed: {name}")
    print(f"Bounding Box: {bbox}")
    print(f"=======================================================")

    for dt_tag in dates:
        raw_path = DATA_RAW / f"{name}_{dt_tag}_rgbnir.tif"
        stack_path = DATA_PROCESSED / f"{name}_{dt_tag}_6ch.tif"

        t0 = time.time()
        print(f"\n--> Checking / Ingesting {dt_tag}...")
        dt, source = da.load_or_fetch_optical_date(
            bbox=bbox,
            date_tag=dt_tag,
            raw_path=raw_path,
            stack_path=stack_path,
        )
        elapsed = time.time() - t0
        print(f"[OK] Ingestion Complete in {elapsed:.2f}s")
        print(f"  Source: {source}")
        print(f"  Date:   {dt}")

        # Verify MongoDB Cache
        cached = mrc.get_cached_raster(bbox, dt_tag)
        if cached:
            _, _, meta = cached
            print(f"  MongoDB GridFS: ACTIVE (Instant <50ms hit ready)")
        else:
            print(f"  MongoDB GridFS: OFFLINE (Served via disk cache)")


def main():
    parser = argparse.ArgumentParser(description="Pre-warm Bhoonidhi & MongoDB Cache for Watersheds")
    parser.add_argument("--name", type=str, default="Kadwanchi", help="Name of AOI job")
    parser.add_argument("--bbox", nargs=4, type=float, help="Custom bbox: minx miny maxx maxy")
    parser.add_argument("--dates", nargs="+", default=["T1", "T2"], help="Date tags (e.g. T1 T2)")

    args = parser.parse_args()

    if args.bbox:
        bbox = tuple(args.bbox)
        prewarm_aoi("Custom_AOI", bbox, dates=args.dates)
    else:
        # Match from AOI_JOBS or default to Kadwanchi
        matched_job = next((j for j in AOI_JOBS if j["name"].lower() == args.name.lower()), None)
        if matched_job:
            prewarm_aoi(matched_job["name"], matched_job["bbox"], dates=args.dates)
        else:
            prewarm_aoi(args.name, AOI_BBOX, dates=args.dates)


if __name__ == "__main__":
    main()
