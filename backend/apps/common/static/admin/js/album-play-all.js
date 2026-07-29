(() => {
  const initialize = (root) => {
    if (root.dataset.initialized === "true") return;
    root.dataset.initialized = "true";
    const audio = root.querySelector("[data-audio]");
    if (!audio) return;

    const tracks = JSON.parse(root.dataset.tracks || "[]");
    const playAll = root.querySelector("[data-play-all]");
    const play = root.querySelector("[data-play]");
    const previous = root.querySelector("[data-previous]");
    const next = root.querySelector("[data-next]");
    const title = root.querySelector("[data-current-title]");
    const status = root.querySelector("[data-status]");
    let index = 0;
    let loadedTrackId = null;

    const current = () => tracks[index];
    const source = () => {
      const track = current();
      return (
        track?.qualities.find((item) => item.quality === "low") ||
        track?.qualities[0]
      );
    };
    const setStatus = (message, isError = false) => {
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };
    const loadCurrent = async () => {
      const track = current();
      const selected = source();
      if (!track || !selected) throw new Error("This track has no playable rendition.");
      title.textContent = track.title;
      if (loadedTrackId === track.id && audio.src) return;
      setStatus(`Requesting secure preview for ${track.title}…`);
      const response = await fetch(selected.url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.url) {
        throw new Error(payload.detail || "Audio preview is unavailable.");
      }
      audio.src = payload.url;
      loadedTrackId = track.id;
      setStatus(`${track.title} is ready.`);
    };
    const start = async () => {
      try {
        await loadCurrent();
        await audio.play();
      } catch (error) {
        setStatus(error.message || "Audio preview is unavailable.", true);
      }
    };
    const select = (nextIndex) => {
      audio.pause();
      audio.removeAttribute("src");
      loadedTrackId = null;
      index = (nextIndex + tracks.length) % tracks.length;
      title.textContent = current().title;
      setStatus("Press play to request this track.");
    };

    playAll.addEventListener("click", () => {
      index = 0;
      loadedTrackId = null;
      start();
    });
    play.addEventListener("click", () => {
      if (audio.paused) start();
      else audio.pause();
    });
    previous.addEventListener("click", () => select(index - 1));
    next.addEventListener("click", () => select(index + 1));
    audio.addEventListener("play", () => {
      play.textContent = "Pause";
    });
    audio.addEventListener("pause", () => {
      play.textContent = "Play";
    });
    audio.addEventListener("ended", () => {
      if (index < tracks.length - 1) {
        select(index + 1);
        start();
      } else {
        setStatus("Album preview complete.");
      }
    });
    title.textContent = current().title;
  };

  const initializeAll = () => {
    document.querySelectorAll("[data-album-play-all]").forEach(initialize);
  };
  document.addEventListener("DOMContentLoaded", initializeAll);
  document.addEventListener("htmx:afterSwap", initializeAll);
})();
