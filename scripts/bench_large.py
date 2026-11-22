"""Benchmark csvnorm on a large CSV.

Usage: uv run python scripts/bench_large.py <file.csv> [--runs 3]

Prints the median wall time of the CLI (after one warm-up run), the time of
each pipeline stage measured around the library calls, and the peak RSS.
All outputs go to a temporary directory that is removed at the end.
"""

import argparse
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from csvnorm.encoding import detect_and_convert, detect_encoding, needs_conversion
from csvnorm.utils import get_column_count, get_row_count, has_crlf_line_endings
from csvnorm.validation import normalize_csv, validate_csv


def check_environment(src: Path, tmp: Path) -> None:
    size = src.stat().st_size
    free = shutil.disk_usage(tmp).free
    if free < 3 * size:
        sys.exit(f"Not enough free space in {tmp}: {free >> 20} MiB, need {3 * size >> 20} MiB")
    fstype = subprocess.run(
        ["findmnt", "-n", "-o", "FSTYPE", "-T", str(tmp)],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    if fstype == "tmpfs":
        sys.exit(f"{tmp} is on tmpfs: set TMPDIR to a directory on disk")
    print(f"temp dir: {tmp} ({fstype or 'unknown fs'}), free {free >> 20} MiB")


def cli_run(src: Path, out: Path) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        ["uv", "run", "csvnorm", str(src), "-o", str(out), "--force"],
        check=False, capture_output=True,
    )
    elapsed = time.perf_counter() - start
    if result.returncode not in (0, 1):
        sys.exit(f"csvnorm failed with exit {result.returncode}:\n{result.stderr.decode()}")
    return elapsed


def stage_times(src: Path, work: Path) -> None:
    def timed(name, fn):
        start = time.perf_counter()
        result = fn()
        print(f"  {name:22s} {time.perf_counter() - start:7.1f} s", flush=True)
        return result

    crlf = has_crlf_line_endings(src)
    timed("detect_encoding", lambda: detect_encoding(src))
    utf8 = work / "utf8.csv"
    encoding = timed("detect_and_convert", lambda: detect_and_convert(src, utf8))
    working = utf8 if needs_conversion(encoding) else src
    timed("validate_csv", lambda: validate_csv(working, work / "rejects.csv"))
    out = work / "stage_out.csv"
    timed("normalize_csv", lambda: normalize_csv(
        input_path=working, output_path=out, delimiter=",", normalize_names=True,
        crlf=crlf,
    ))
    if working != src:
        working.unlink()
    timed("counts", lambda: (get_row_count(out), get_column_count(out)))
    print(f"  encoding: {encoding}, input CRLF: {crlf}")


def peak_rss(src: Path, out: Path) -> None:
    """Peak RSS of one CLI run, from the kernel accounting of child processes."""
    import resource

    subprocess.run(
        [sys.executable, "-m", "csvnorm", str(src), "-o", str(out), "--force"],
        check=False, capture_output=True,
    )
    kib = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    print(f"peak RSS (largest child process): {kib >> 10} MiB")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path)
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()

    tmp = Path(tempfile.gettempdir())
    check_environment(args.file, tmp)
    work = Path(tempfile.mkdtemp(prefix="csvnorm_bench_"))
    try:
        out = work / "out.csv"
        print("warm-up run...", flush=True)
        cli_run(args.file, out)
        times = []
        for i in range(args.runs):
            times.append(cli_run(args.file, out))
            print(f"run {i + 1}: {times[-1]:.1f} s", flush=True)
        print(f"median: {statistics.median(times):.1f} s")
        out.unlink(missing_ok=True)
        print("stages:")
        stage_times(args.file, work)
        peak_rss(args.file, out)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
