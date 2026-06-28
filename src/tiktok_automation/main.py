import json
from pathlib import Path

from .pipeline import AutomationPipeline
from .types import AutomationScope, PipelineConfig


def _validate_scope(scope: AutomationScope) -> None:
    if scope.video_length_seconds <= 0:
        raise ValueError("scope.video_length_seconds must be greater than 0")
    if scope.posting_frequency_per_day <= 0:
        raise ValueError("scope.posting_frequency_per_day must be greater than 0")
    if not scope.niche.strip():
        raise ValueError("scope.niche must not be empty")
    if not scope.voice_style.strip():
        raise ValueError("scope.voice_style must not be empty")


def load_config(config_path: Path) -> PipelineConfig:
    data = json.loads(config_path.read_text())
    scope = AutomationScope(**data["scope"])
    _validate_scope(scope)
    return PipelineConfig(
        scope=scope,
        brand_tone=data["brand_tone"],
        banned_terms=data.get("banned_terms", []),
        max_regeneration_attempts=data.get("max_regeneration_attempts", 1),
        default_music_style=data.get("default_music_style", "ambient"),
    )


def run(config_file: str) -> dict:
    config = load_config(Path(config_file))
    pipeline = AutomationPipeline(config)
    job = pipeline.run_once()
    return {
        "job": pipeline.export_job(job),
        "monitoring": pipeline.export_monitoring_events(),
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run TikTok video automation pipeline once.")
    parser.add_argument(
        "--config",
        default="config/sample_config.json",
        help="Path to JSON configuration file",
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))
