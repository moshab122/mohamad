import sys
import tempfile
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tiktok_automation.pipeline import AutomationPipeline, MediaAssemblyService
from tiktok_automation.main import load_config, run
from tiktok_automation.types import AutomationScope, PipelineConfig


class BadMediaAssembly(MediaAssemblyService):
    def assemble(self, assets, duration_seconds):
        rendered = super().assemble(assets, duration_seconds)
        rendered.audio_level_db = -40.0
        return rendered


class PipelineTests(unittest.TestCase):
    def test_publishes_without_human_approval(self):
        config = PipelineConfig(
            scope=AutomationScope(
                niche="fitness",
                video_length_seconds=20,
                posting_frequency_per_day=1,
                voice_style="calm",
                require_human_approval=False,
            ),
            brand_tone="motivational",
            banned_terms=[],
        )
        pipeline = AutomationPipeline(config)
        job = pipeline.run_once()
        self.assertEqual(job.status, "published")
        self.assertTrue(job.quality.passed)
        self.assertIsNotNone(job.analytics)

    def test_human_approval_flow(self):
        config = PipelineConfig(
            scope=AutomationScope(
                niche="travel",
                video_length_seconds=25,
                posting_frequency_per_day=1,
                voice_style="fun",
                require_human_approval=True,
            ),
            brand_tone="adventurous",
            banned_terms=[],
        )
        pipeline = AutomationPipeline(config)
        job = pipeline.run_once()
        self.assertEqual(job.status, "awaiting_approval")

    def test_quality_failure_routes_to_failed(self):
        config = PipelineConfig(
            scope=AutomationScope(
                niche="coding",
                video_length_seconds=15,
                posting_frequency_per_day=1,
                voice_style="teaching",
                require_human_approval=False,
            ),
            brand_tone="educational",
            banned_terms=[],
            max_regeneration_attempts=0,
        )
        pipeline = AutomationPipeline(config)
        pipeline.media_assembly = BadMediaAssembly()
        job = pipeline.run_once()
        self.assertEqual(job.status, "failed")
        self.assertFalse(job.quality.passed)

    def test_asset_paths_are_sanitized_and_scope_fields_used(self):
        config = PipelineConfig(
            scope=AutomationScope(
                niche="travel",
                video_length_seconds=20,
                posting_frequency_per_day=3,
                voice_style="energetic",
                require_human_approval=False,
            ),
            brand_tone="friendly",
            banned_terms=[],
        )
        pipeline = AutomationPipeline(config)
        topic = pipeline.topic_generator.generate("travel")
        assets = pipeline.asset_sourcing.source(topic, "lofi")
        self.assertNotIn("#", assets.clips[0])
        self.assertNotIn("#", assets.images[0])
        job = pipeline.run_once()
        self.assertEqual(job.metadata["voice_style"], "energetic")
        self.assertEqual(job.metadata["posting_frequency_per_day"], "3")

    def test_config_validation_rejects_invalid_scope(self):
        invalid = {
            "scope": {
                "niche": "productivity",
                "video_length_seconds": 0,
                "posting_frequency_per_day": 1,
                "voice_style": "calm",
                "require_human_approval": True,
            },
            "brand_tone": "friendly",
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as handle:
            json.dump(invalid, handle)
            handle.flush()
            with self.assertRaises(ValueError):
                load_config(Path(handle.name))

    def test_run_for_day_uses_posting_frequency(self):
        config = PipelineConfig(
            scope=AutomationScope(
                niche="fitness",
                video_length_seconds=20,
                posting_frequency_per_day=3,
                voice_style="calm",
                require_human_approval=False,
            ),
            brand_tone="motivational",
            banned_terms=[],
        )
        pipeline = AutomationPipeline(config)
        jobs = pipeline.run_for_day()
        self.assertEqual(len(jobs), 3)
        self.assertTrue(all(job.script.text for job in jobs))
        self.assertTrue(all(job.status == "published" for job in jobs))

    def test_run_returns_jobs_and_auto_publishes_with_sample_like_config(self):
        sample_like = {
            "scope": {
                "niche": "productivity",
                "video_length_seconds": 30,
                "posting_frequency_per_day": 2,
                "voice_style": "energetic",
                "require_human_approval": False,
            },
            "brand_tone": "friendly expert",
            "banned_terms": ["hate", "violence"],
            "max_regeneration_attempts": 2,
            "default_music_style": "lofi",
        }
        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=True) as handle:
            json.dump(sample_like, handle)
            handle.flush()
            result = run(handle.name)
        self.assertIn("jobs", result)
        self.assertEqual(len(result["jobs"]), 2)
        self.assertTrue(all(job["status"] == "published" for job in result["jobs"]))


if __name__ == "__main__":
    unittest.main()
