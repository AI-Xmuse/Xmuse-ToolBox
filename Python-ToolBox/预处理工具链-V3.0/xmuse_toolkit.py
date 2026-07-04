"""XMuse EEG preprocessing toolkit.
参数位于config.json文件中，命令行选择要运行的模块
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.json"


def load_config(config_path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def project_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else ROOT / path


def get_sampling_rate(df: pd.DataFrame, time_col: str = "time") -> float:
    if time_col not in df.columns or len(df) < 2:
        return 0.0
    diffs = np.diff(pd.to_numeric(df[time_col], errors="coerce").dropna())
    diffs = diffs[diffs > 0]
    if len(diffs) == 0:
        return 0.0
    return float(1 / np.mean(diffs))


def write_quality_summary(
    df: pd.DataFrame,
    channels: list[str],
    output_path: Path,
    source_file: str,
    stage: str,
) -> None:
    """Save a compact quality-check table for one processed file."""
    rows: list[dict[str, Any]] = []
    fs = get_sampling_rate(df)
    for channel in channels:
        if channel not in df.columns:
            rows.append(
                {
                    "source_file": source_file,
                    "stage": stage,
                    "channel": channel,
                    "exists": False,
                    "samples": len(df),
                    "missing_count": "",
                    "mean": "",
                    "std": "",
                    "min": "",
                    "max": "",
                    "sampling_rate_hz": round(fs, 4) if fs else "",
                }
            )
            continue

        data = pd.to_numeric(df[channel], errors="coerce")
        rows.append(
            {
                "source_file": source_file,
                "stage": stage,
                "channel": channel,
                "exists": True,
                "samples": len(df),
                "missing_count": int(data.isna().sum()),
                "mean": round(float(data.mean()), 6) if data.notna().any() else "",
                "std": round(float(data.std()), 6) if data.notna().any() else "",
                "min": round(float(data.min()), 6) if data.notna().any() else "",
                "max": round(float(data.max()), 6) if data.notna().any() else "",
                "sampling_rate_hz": round(fs, 4) if fs else "",
            }
        )

    ensure_dir(output_path.parent)
    pd.DataFrame(rows).to_csv(output_path, index=False, encoding="utf-8-sig")


def clean_eeg_frame(df: pd.DataFrame, raw_columns: dict[str, str]) -> pd.DataFrame:
    missing = [col for col in raw_columns if col not in df.columns]
    if missing:
        raise ValueError(f"missing raw columns: {missing}")

    cleaned = df[list(raw_columns)].rename(columns=raw_columns).copy()
    channels = [col for col in raw_columns.values() if col != "time"]
    cleaned.dropna(subset=channels, how="all", inplace=True)
    cleaned.reset_index(drop=True, inplace=True)

    if "time" in cleaned.columns and not cleaned.empty:
        cleaned["time"] = pd.to_numeric(cleaned["time"], errors="coerce")
        cleaned["time"] = cleaned["time"] - cleaned["time"].iloc[0]
    return cleaned


def apply_baseline(
    df: pd.DataFrame,
    channels: list[str],
    baseline_window_sec: list[float],
    fs: float,
) -> pd.DataFrame:
    corrected = df.copy()
    if fs <= 0:
        return corrected

    start = max(0, int(baseline_window_sec[0] * fs))
    end = min(len(df), int(baseline_window_sec[1] * fs))
    if end <= start:
        end = min(len(df), start + 1)

    for channel in channels:
        if channel in corrected.columns:
            baseline_mean = pd.to_numeric(corrected[channel], errors="coerce").iloc[start:end].mean()
            corrected[channel] = pd.to_numeric(corrected[channel], errors="coerce") - baseline_mean
    return corrected


def _butter_filter(data: np.ndarray, fs: float, cutoff: float | list[float], btype: str, order: int = 5) -> np.ndarray:
    from scipy.signal import butter, filtfilt

    nyq = 0.5 * fs
    normal_cutoff = np.asarray(cutoff) / nyq
    b, a = butter(order, normal_cutoff, btype=btype, analog=False)
    return filtfilt(b, a, data)


def apply_filters(df: pd.DataFrame, channels: list[str], cfg: dict[str, Any], fs: float) -> pd.DataFrame:
    filtered = df.copy()
    if fs <= 0:
        return filtered

    highpass = float(cfg["highpass_hz"])
    lowpass = float(cfg["lowpass_hz"])
    notch = cfg.get("notch_hz", [49.0, 51.0])

    for channel in channels:
        if channel not in filtered.columns:
            continue
        signal = pd.to_numeric(filtered[channel], errors="coerce").interpolate("linear").bfill().ffill()
        if signal.isna().all() or len(signal) < 20:
            continue
        values = signal.to_numpy()
        try:
            values = _butter_filter(values, fs, highpass, "high")
            values = _butter_filter(values, fs, lowpass, "low")
            values = _butter_filter(values, fs, notch, "bandstop")
            filtered[channel] = values
        except ImportError:
            print("[warn] scipy is not installed; filter step skipped.")
            return filtered
        except ValueError as exc:
            print(f"[warn] filter skipped for {channel}: {exc}")
    return filtered


def interpolate_outliers(df: pd.DataFrame, channels: list[str], threshold: float) -> tuple[pd.DataFrame, int]:
    fixed = df.copy()
    total = 0
    for channel in channels:
        if channel not in fixed.columns:
            continue
        signal = pd.to_numeric(fixed[channel], errors="coerce")
        bad = signal.abs() > threshold
        total += int(bad.sum())
        if bad.any():
            signal.loc[bad] = np.nan
            fixed[channel] = signal.interpolate("linear", limit_direction="both")
    return fixed, total


def scale_channels(df: pd.DataFrame, channels: list[str], method: str) -> pd.DataFrame:
    scaled = df.copy()
    for channel in channels:
        if channel not in scaled.columns:
            continue
        data = pd.to_numeric(scaled[channel], errors="coerce")
        if method == "minmax":
            denom = data.max() - data.min()
            scaled[channel] = (data - data.min()) / denom if denom else data
        else:
            std = data.std()
            scaled[channel] = (data - data.mean()) / std if std else data - data.mean()
    return scaled


def create_epochs(df: pd.DataFrame, fs: float, window_sec: float, overlap_rate: float) -> pd.DataFrame:
    if window_sec <= 0:
        raise ValueError("epoch.window_sec must be greater than 0")
    if overlap_rate < 0 or overlap_rate >= 1:
        raise ValueError("epoch.overlap_rate must be >= 0 and < 1")
    if fs <= 0:
        raise ValueError("sampling rate is invalid")

    samples_per_epoch = int(round(window_sec * fs))
    if samples_per_epoch <= 0:
        raise ValueError("window is shorter than one sample")

    step_size = max(1, int(round(samples_per_epoch * (1 - overlap_rate))))
    epochs = []
    epoch_id = 0
    for start in range(0, len(df) - samples_per_epoch + 1, step_size):
        epoch = df.iloc[start : start + samples_per_epoch].copy()
        epoch["epoch_id"] = epoch_id
        epochs.append(epoch)
        epoch_id += 1

    if not epochs:
        return pd.DataFrame()
    return pd.concat(epochs, ignore_index=True)


def run_preprocess(config: dict[str, Any]) -> None:
    paths = config["paths"]
    cfg = config["preprocess"]
    input_dir = project_path(paths["preprocess_input_dir"])
    output_dir = project_path(paths["output_dir"]) / "preprocess"
    summary_dir = output_dir / "quality_summary"
    ensure_dir(output_dir)
    ensure_dir(summary_dir)

    channels = cfg["channels"]
    for file_name in cfg["files"]:
        input_path = input_dir / file_name
        if not input_path.exists():
            print(f"[skip] missing file: {input_path}")
            continue

        print(f"[preprocess] {file_name}")
        df = pd.read_csv(input_path, na_values=[""], low_memory=False)
        df = clean_eeg_frame(df, cfg["raw_columns"])
        fs = get_sampling_rate(df)
        df = apply_baseline(df, channels, cfg["baseline_window_sec"], fs)
        df = apply_filters(df, channels, cfg, fs)
        df, fixed_count = interpolate_outliers(df, channels, float(cfg["amplitude_threshold"]))
        df = scale_channels(df, channels, cfg.get("scale_method", "zscore"))

        base = Path(file_name).stem
        processed_path = output_dir / f"{base}_preprocessed.csv"
        df.to_csv(processed_path, index=False, encoding="utf-8-sig")
        write_quality_summary(df, channels, summary_dir / f"{base}_quality_summary.csv", file_name, "preprocessed")

        print(f"  saved: {processed_path}")
        print(f"  sampling_rate_hz: {fs:.2f}; fixed_outliers: {fixed_count}")

        epoch_cfg = cfg.get("epoch", {})
        if epoch_cfg.get("enabled", False):
            epoched = create_epochs(
                df,
                fs,
                float(epoch_cfg["window_sec"]),
                float(epoch_cfg["overlap_rate"]),
            )
            if epoched.empty:
                print("  epoch skipped: data is too short")
            else:
                epoched_path = output_dir / f"{base}_preprocessed_epoched.csv"
                epoched.to_csv(epoched_path, index=False, encoding="utf-8-sig")
                print(f"  epoch saved: {epoched_path}")
                print(f"  epoch_count: {epoched['epoch_id'].nunique()}")


def organize_direct_csv(input_path: Path, output_dir: Path) -> None:
    df = pd.read_csv(input_path)
    required = {"Timestamp", "PacketType", "Data"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{input_path.name} missing columns: {sorted(missing)}")

    file_out = output_dir / input_path.stem
    ensure_dir(file_out)
    for packet_type, group in df.groupby("PacketType"):
        split_data = group["Data"].astype(str).str.replace('"', "", regex=False).str.split(",", expand=True)
        split_data.columns = [f"data_{i + 1}" for i in range(split_data.shape[1])]
        result = pd.concat([group[["Timestamp"]].reset_index(drop=True), split_data.reset_index(drop=True)], axis=1)
        out_path = file_out / f"{input_path.stem}_{packet_type}.csv"
        result.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  saved: {out_path}")


def run_direct_data(config: dict[str, Any]) -> None:
    paths = config["paths"]
    input_dir = project_path(paths["direct_input_dir"])
    output_dir = project_path(paths["output_dir"]) / "direct_data"
    ensure_dir(output_dir)

    for file_name in config["direct_data"]["files"]:
        input_path = input_dir / file_name
        if not input_path.exists():
            print(f"[skip] missing file: {input_path}")
            continue
        print(f"[direct] {file_name}")
        organize_direct_csv(input_path, output_dir)


def edf_to_csv(edf_path: Path, output_dir: Path) -> None:
    try:
        import mne
    except ImportError as exc:
        raise ImportError("EDF conversion needs mne. Install it with: pip install mne") from exc

    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    df = raw.to_data_frame()
    out_path = output_dir / f"{edf_path.stem}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  saved: {out_path}")


def csv_to_mat(csv_path: Path, output_dir: Path) -> None:
    from scipy.io import savemat

    df = pd.read_csv(csv_path)
    out_path = output_dir / f"{csv_path.stem}.mat"
    savemat(out_path, {col: df[col].values for col in df.columns})
    print(f"  saved: {out_path}")


def run_convert(config: dict[str, Any]) -> None:
    paths = config["paths"]
    input_dir = project_path(paths["convert_input_dir"])
    output_dir = project_path(paths["output_dir"]) / "convert"
    ensure_dir(output_dir)

    for file_name in config["convert"].get("edf_files", []):
        input_path = input_dir / file_name
        if not input_path.exists():
            print(f"[skip] missing file: {input_path}")
            continue
        print(f"[convert edf] {file_name}")
        try:
            edf_to_csv(input_path, output_dir)
        except ImportError as exc:
            print(f"[warn] {exc}; skipped {file_name}")

    for file_name in config["convert"].get("csv_to_mat_files", []):
        input_path = project_path(file_name)
        if not input_path.exists():
            print(f"[skip] missing file: {input_path}")
            continue
        print(f"[convert mat] {file_name}")
        try:
            csv_to_mat(input_path, output_dir)
        except ImportError as exc:
            print(f"[warn] {exc}; skipped {file_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="XMuse preprocessing toolkit")
    parser.add_argument(
        "command",
        choices=["preprocess", "direct", "convert", "all"],
        help="module to run",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG), help="config json path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)

    if args.command in {"convert", "all"}:
        run_convert(config)
    if args.command in {"direct", "all"}:
        run_direct_data(config)
    if args.command in {"preprocess", "all"}:
        run_preprocess(config)


if __name__ == "__main__":
    main()
