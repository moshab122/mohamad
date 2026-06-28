# TikTok Automation Pipeline

This repository implements an end-to-end automation pipeline for generating and preparing TikTok videos.

## What is implemented

1. **Automation scope** via config (`config/sample_config.json`):
   - Content niche
   - Video length
   - Posting frequency
   - Voice style
   - Human approval vs full automation
2. **Content pipeline stages**:
   - Topic generation
   - Script generation with policy/copyright checks
   - Asset sourcing (clips, images, music, voiceover, subtitles)
   - Media assembly for vertical 9:16 output
   - Quality validation (duration, caption timing, audio)
   - Scheduling and publish state tracking
   - Analytics feedback signals
3. **Monitoring and retry flow**:
   - Stage-level monitoring events
   - Regeneration attempts when checks fail

## Project structure

- `/home/runner/work/mohamad/mohamad/src/tiktok_automation/pipeline.py` – core pipeline and services
- `/home/runner/work/mohamad/mohamad/src/tiktok_automation/types.py` – shared dataclasses
- `/home/runner/work/mohamad/mohamad/src/tiktok_automation/main.py` – CLI entrypoint
- `/home/runner/work/mohamad/mohamad/config/sample_config.json` – sample configuration
- `/home/runner/work/mohamad/mohamad/tests/test_pipeline.py` – automated tests

## Run locally

```bash
cd /home/runner/work/mohamad/mohamad
python -m unittest discover -s tests
python -m src.tiktok_automation.main --config config/sample_config.json
```
