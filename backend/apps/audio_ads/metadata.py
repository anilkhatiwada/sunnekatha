from pathlib import Path
from shutil import copyfileobj
from tempfile import TemporaryDirectory

from apps.catalog.audio_processing import AudioProcessingError, AudioProcessingService


class AudioAdvertisementMetadataService:
    """Read trusted metadata from an advertisement's stored audio file."""

    def detect_duration(self, advertisement) -> int:
        if not advertisement.audio_file:
            raise AudioProcessingError("metadata", "Advertisement audio is missing.")

        with TemporaryDirectory(prefix="sunnekatha-ad-metadata-") as directory:
            source_path = Path(directory) / "advertisement-audio"
            with (
                advertisement.audio_file.open("rb") as source,
                source_path.open("wb") as destination,
            ):
                copyfileobj(source, destination, length=1024 * 1024)
            return AudioProcessingService()._duration(source_path)


audio_advertisement_metadata_service = AudioAdvertisementMetadataService()
