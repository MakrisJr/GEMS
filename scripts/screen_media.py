"""Run a minimal first-pass media screen on a draft model.

This is a first-pass media screen on a draft model.
"""

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.cobra_loader import load_cobra_model
from src.logging_utils import get_logger
from src.media_outputs import save_media_plot, save_media_results
from src.media_screen import load_media_library, screen_media


def _growth_key(row):
    value = row.get("predicted_growth")
    return float("-inf") if value is None else value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="This is a first-pass media screen on a draft model."
    )
    parser.add_argument("--model-dir", required=True, help="Directory containing the exported model.")
    parser.add_argument("--media", required=True, help="Path to the YAML media library.")
    args = parser.parse_args()

    logger = get_logger(__name__)
    model_dir = Path(args.model_dir)
    media_path = Path(args.media)

    if not model_dir.exists():
        logger.error("Model directory not found: %s", model_dir)
        return 1

    if not media_path.exists():
        logger.error("Media library not found: %s", media_path)
        return 1

    model, model_path, _ = load_cobra_model(str(model_dir))
    media_library = load_media_library(str(media_path))
    results = screen_media(model, media_library)
    results = sorted(results, key=_growth_key, reverse=True)

    save_media_results(results, str(model_dir))
    save_media_plot(results, str(model_dir))

    best = results[0] if results else {"condition": "", "predicted_growth": None}
    print("This is a first-pass media screen on a draft model.")
    print(f"Model path: {model_path}")
    print(f"Number of conditions: {len(results)}")
    print(f"Best condition: {best['condition']}")
    print(f"Best predicted growth: {best['predicted_growth']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
