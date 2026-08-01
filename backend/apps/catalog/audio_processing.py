import math
import subprocess
import uuid
from array import array
from dataclasses import dataclass
from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files import File

from apps.common.storage import processed_audio_storage


class AudioProcessingError(RuntimeError):
    def __init__(self, stage, summary, technical=""):
        self.stage = stage
        self.summary = summary
        self.technical = technical
        super().__init__(summary)


@dataclass(frozen=True)
class ProcessedAudio:
    high_name: str
    low_name: str
    duration_seconds: int
    waveform: list[float]


class AudioProcessingService:
    def process(self, track) -> ProcessedAudio:
        if not track.audio_master_file:
            raise AudioProcessingError("upload", "Audio master file is missing.")
        storage = processed_audio_storage()
        saved_names = []
        try:
            with TemporaryDirectory(prefix="sunnekatha-audio-") as directory:
                root = Path(directory)
                source_path = root / "master"
                high_path = root / "high.mp3"
                low_path = root / "low.mp3"
                with (
                    track.audio_master_file.open("rb") as source,
                    source_path.open("wb") as destination,
                ):
                    copyfileobj(source, destination, length=1024 * 1024)

                duration = self._duration(source_path)
                self._transcode(source_path, high_path, bitrate="128k")
                self._transcode(source_path, low_path, bitrate="64k")
                waveform = self._waveform(source_path)
                token = uuid.uuid4().hex
                prefix = f"processed/audio/audiotrack/{track.pk}"
                for quality, path in (("high", high_path), ("low", low_path)):
                    with path.open("rb") as handle:
                        saved_names.append(
                            storage.save(
                                f"{prefix}/{token}-{quality}.mp3", File(handle)
                            )
                        )
                return ProcessedAudio(
                    high_name=saved_names[0],
                    low_name=saved_names[1],
                    duration_seconds=duration,
                    waveform=waveform,
                )
        except AudioProcessingError:
            for name in saved_names:
                storage.delete(name)
            raise
        except Exception as exc:
            for name in saved_names:
                storage.delete(name)
            raise AudioProcessingError(
                "finalizing", "Audio processing could not be completed.", str(exc)
            ) from exc

    def _duration(self, source_path):
        result = self._run(
            [
                settings.FFPROBE_BINARY,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(source_path),
            ],
            stage="metadata",
            binary_output=False,
        )
        try:
            return max(1, math.ceil(float(result.stdout.strip())))
        except (TypeError, ValueError):
            raise AudioProcessingError(
                "metadata", "Audio duration could not be determined."
            ) from None

    def _transcode(self, source_path, output_path, *, bitrate):
        self._run(
            [
                settings.FFMPEG_BINARY,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(source_path),
                "-map_metadata",
                "-1",
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-b:a",
                bitrate,
                str(output_path),
            ],
            stage="transcoding",
            binary_output=True,
        )

    def _waveform(self, source_path):
        result = self._run(
            [
                settings.FFMPEG_BINARY,
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source_path),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "1000",
                "-f",
                "s16le",
                "pipe:1",
            ],
            stage="waveform",
            binary_output=True,
        )
        samples = array("h")
        samples.frombytes(result.stdout)
        if not samples:
            return []
        bucket_size = max(1, math.ceil(len(samples) / 1000))
        return [
            round(
                max(abs(value) for value in samples[index : index + bucket_size])
                / 32768,
                4,
            )
            for index in range(0, len(samples), bucket_size)
        ]

    @staticmethod
    def _run(command, *, stage, binary_output):
        try:
            return subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=not binary_output,
                timeout=settings.AUDIO_PROCESSING_COMMAND_TIMEOUT_SECONDS,
            )
        except FileNotFoundError as exc:
            raise AudioProcessingError(
                stage, "Required audio-processing software is unavailable.", str(exc)
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AudioProcessingError(
                stage, "Audio processing exceeded the allowed time.", str(exc)
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (
                exc.stderr.decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else exc.stderr
            )
            raise AudioProcessingError(
                stage, "The audio file could not be processed.", (detail or "")[-4000:]
            ) from exc


audio_processing_service = AudioProcessingService()
