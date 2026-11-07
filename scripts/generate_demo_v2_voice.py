"""Generate narrated clips and word timings for the OncoFlow explainer."""

import asyncio
import json
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parents[1]
SCENES = json.loads((ROOT / "scripts/demo_v2_scenes.json").read_text())
OUTPUT = ROOT / "docs/submission/video_v2"
VOICE = "en-IN-PrabhatNeural"


async def generate() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for scene in SCENES:
        audio_path = OUTPUT / f"{scene['id']}.mp3"
        words = []
        communicate = edge_tts.Communicate(
            scene["narration"],
            voice=VOICE,
            rate=scene["rate"],
            boundary="WordBoundary",
        )
        with audio_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    words.append(
                        {
                            "text": chunk["text"],
                            "start": chunk["offset"] / 10_000_000,
                            "duration": chunk["duration"] / 10_000_000,
                        }
                    )
        manifest.append({**scene, "audio": audio_path.name, "words": words})
        print(f"Generated {audio_path.name}: {len(words)} timed words", flush=True)
    (OUTPUT / "voice_manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    asyncio.run(generate())
