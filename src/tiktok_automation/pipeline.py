import time
import re
from dataclasses import asdict
from typing import Dict, List

from .types import (
    AssetBundle,
    PipelineConfig,
    QualityResult,
    RenderedVideo,
    Script,
    Topic,
    VideoJob,
)


class TopicGenerator:
    def __init__(self) -> None:
        self._counter = 0

    def generate(self, niche: str) -> Topic:
        self._counter += 1
        return Topic(
            title=f"{niche.title()} idea #{self._counter}",
            hook=f"3 quick {niche} tips in under a minute",
        )


class ScriptGenerationService:
    def generate(self, topic: Topic, tone: str, banned_terms: List[str]) -> Script:
        text = f"{topic.hook}. Stay tuned for more."
        lowered = text.lower()
        is_safe = not any(term.lower() in lowered for term in banned_terms)
        has_copyright_risk = "official song" in lowered or "movie clip" in lowered
        return Script(text=text, tone=tone, safe=is_safe, copyright_ok=not has_copyright_risk)


class AssetSourcingService:
    @staticmethod
    def _safe_slug(value: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
        return slug or "untitled"

    def source(self, topic: Topic, music_style: str) -> AssetBundle:
        topic_slug = self._safe_slug(topic.title)
        return AssetBundle(
            clips=[f"stock/{topic_slug}_clip.mp4"],
            images=[f"ai/{topic_slug}_image.png"],
            music_track=f"music/{music_style}_bed.mp3",
            voiceover_track=f"voice/{topic_slug}_voice.mp3",
            subtitles=[topic.hook, "Follow for more"],
        )


class MediaAssemblyService:
    def assemble(self, assets: AssetBundle, duration_seconds: int) -> RenderedVideo:
        return RenderedVideo(
            path=f"output/{int(time.time())}.mp4",
            aspect_ratio="9:16",
            duration_seconds=duration_seconds,
            caption_timing_score=0.93,
            audio_level_db=-14.0,
        )


class QualityChecker:
    def validate(self, rendered: RenderedVideo, target_duration: int) -> QualityResult:
        reasons: List[str] = []
        if rendered.aspect_ratio != "9:16":
            reasons.append("aspect ratio must be 9:16")
        if abs(rendered.duration_seconds - target_duration) > 5:
            reasons.append("duration deviates from target")
        if rendered.caption_timing_score < 0.80:
            reasons.append("caption timing too low")
        if not (-24 <= rendered.audio_level_db <= -6):
            reasons.append("audio level out of acceptable range")
        return QualityResult(passed=not reasons, reasons=reasons)


class SchedulerPublisher:
    def __init__(self) -> None:
        self.queue: List[VideoJob] = []

    def enqueue(self, job: VideoJob) -> None:
        self.queue.append(job)
        job.status = "queued"

    def publish(self, job: VideoJob, require_human_approval: bool) -> None:
        if require_human_approval:
            job.status = "awaiting_approval"
        else:
            job.status = "published"


class AnalyticsService:
    def evaluate(self, job: VideoJob) -> Dict[str, float]:
        title_length_factor = min(len(job.topic.title), 40) / 40
        retention = round(0.45 + (title_length_factor * 0.4), 2)
        watch_time = round(job.rendered_video.duration_seconds * retention, 2)
        likes_rate = round(0.02 + retention * 0.1, 3)
        return {"retention": retention, "watch_time": watch_time, "likes_rate": likes_rate}


class MonitoringService:
    def __init__(self) -> None:
        self.events: List[Dict[str, str]] = []

    def log(self, stage: str, message: str) -> None:
        self.events.append({"stage": stage, "message": message})


class AutomationPipeline:
    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.topic_generator = TopicGenerator()
        self.script_generator = ScriptGenerationService()
        self.asset_sourcing = AssetSourcingService()
        self.media_assembly = MediaAssemblyService()
        self.quality_checker = QualityChecker()
        self.scheduler = SchedulerPublisher()
        self.analytics_service = AnalyticsService()
        self.monitoring = MonitoringService()

    def run_once(self) -> VideoJob:
        attempts = 0
        last_job: VideoJob | None = None

        while attempts <= self.config.max_regeneration_attempts:
            attempts += 1
            self.monitoring.log("topic", f"attempt {attempts}")
            topic = self.topic_generator.generate(self.config.scope.niche)

            script = self.script_generator.generate(
                topic=topic,
                tone=self.config.brand_tone,
                banned_terms=self.config.banned_terms,
            )
            if not script.safe or not script.copyright_ok:
                self.monitoring.log("script", "failed policy checks")
                continue

            assets = self.asset_sourcing.source(topic, self.config.default_music_style)
            rendered = self.media_assembly.assemble(assets, self.config.scope.video_length_seconds)
            quality = self.quality_checker.validate(rendered, self.config.scope.video_length_seconds)

            last_job = VideoJob(
                topic=topic,
                script=script,
                assets=assets,
                rendered_video=rendered,
                quality=quality,
                status="created",
                metadata={
                    "attempt": str(attempts),
                    "voice_style": self.config.scope.voice_style,
                    "posting_frequency_per_day": str(self.config.scope.posting_frequency_per_day),
                },
            )

            if not quality.passed:
                self.monitoring.log("quality", ",".join(quality.reasons))
                continue

            self.scheduler.enqueue(last_job)
            self.scheduler.publish(last_job, self.config.scope.require_human_approval)
            last_job.analytics = self.analytics_service.evaluate(last_job)
            self.monitoring.log("publish", last_job.status)
            return last_job

        if last_job is None:
            topic = Topic(title="no-valid-topic", hook="pipeline exhausted attempts")
            script = Script(text="", tone=self.config.brand_tone, safe=False, copyright_ok=False)
            assets = AssetBundle([], [], "", "", [])
            rendered = RenderedVideo("", "9:16", self.config.scope.video_length_seconds, 0.0, -30.0)
            quality = QualityResult(False, ["pipeline exhausted attempts before rendering"])
            last_job = VideoJob(
                topic=topic,
                script=script,
                assets=assets,
                rendered_video=rendered,
                quality=quality,
                status="failed",
            )
        else:
            last_job.status = "failed"
        return last_job

    def run_for_day(self) -> List[VideoJob]:
        jobs: List[VideoJob] = []
        for _ in range(self.config.scope.posting_frequency_per_day):
            jobs.append(self.run_once())
        return jobs

    def export_monitoring_events(self) -> List[Dict[str, str]]:
        return self.monitoring.events

    def export_job(self, job: VideoJob) -> Dict[str, object]:
        return asdict(job)
