from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class AutomationScope:
    niche: str
    video_length_seconds: int
    posting_frequency_per_day: int
    voice_style: str
    require_human_approval: bool


@dataclass
class PipelineConfig:
    scope: AutomationScope
    brand_tone: str
    banned_terms: List[str] = field(default_factory=list)
    max_regeneration_attempts: int = 1
    default_music_style: str = "ambient"


@dataclass
class Topic:
    title: str
    hook: str


@dataclass
class Script:
    text: str
    tone: str
    safe: bool
    copyright_ok: bool


@dataclass
class AssetBundle:
    clips: List[str]
    images: List[str]
    music_track: str
    voiceover_track: str
    subtitles: List[str]


@dataclass
class RenderedVideo:
    path: str
    aspect_ratio: str
    duration_seconds: int
    caption_timing_score: float
    audio_level_db: float


@dataclass
class QualityResult:
    passed: bool
    reasons: List[str]


@dataclass
class VideoJob:
    topic: Topic
    script: Script
    assets: AssetBundle
    rendered_video: RenderedVideo
    quality: QualityResult
    status: str
    metadata: Dict[str, str] = field(default_factory=dict)
    analytics: Optional[Dict[str, float]] = None
