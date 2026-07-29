(() => {
  const formatTime = (seconds) => {
    if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
    const whole = Math.floor(seconds);
    const hours = Math.floor(whole / 3600);
    const minutes = Math.floor((whole % 3600) / 60);
    const remainder = whole % 60;
    return hours
      ? `${hours}:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`
      : `${minutes}:${String(remainder).padStart(2, "0")}`;
  };

  const initialize = (root) => {
    if (root.dataset.initialized === "true") return;
    root.dataset.initialized = "true";

    const audio = root.querySelector("[data-audio]");
    if (!audio) return;

    const sources = JSON.parse(root.dataset.sources || "[]");
    const available = sources.filter((source) => source.available);
    let selected = available.find((source) => source.quality === "low") || available[0];
    let delivery = null;
    let deliveryExpiresAt = null;

    const play = root.querySelector("[data-play]");
    const seek = root.querySelector("[data-seek]");
    const volume = root.querySelector("[data-volume]");
    const speed = root.querySelector("[data-speed]");
    const currentTime = root.querySelector("[data-current-time]");
    const duration = root.querySelector("[data-duration]");
    const status = root.querySelector("[data-status]");
    const qualityButtons = [...root.querySelectorAll("[data-quality]")];

    const setStatus = (message, isError = false) => {
      status.textContent = message;
      status.classList.toggle("is-error", isError);
    };

    const updateQualityButtons = () => {
      qualityButtons.forEach((button) => {
        const isSelected = button.dataset.quality === selected?.quality;
        button.classList.toggle("is-selected", isSelected);
        button.setAttribute("aria-pressed", String(isSelected));
      });
    };

    const deliveryIsFresh = () =>
      delivery &&
      (!deliveryExpiresAt || deliveryExpiresAt.getTime() - Date.now() > 5000);

    const requestDelivery = async () => {
      if (deliveryIsFresh()) return delivery;
      setStatus(`Requesting secure ${selected.label.toLowerCase()} preview…`);
      const response = await fetch(selected.url, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.url) {
        throw new Error(payload.detail || "Audio preview is unavailable.");
      }
      delivery = payload;
      deliveryExpiresAt = payload.expiresAt ? new Date(payload.expiresAt) : null;
      audio.src = payload.url;
      setStatus(`${selected.label} preview is ready.`);
      return payload;
    };

    play.addEventListener("click", async () => {
      if (!audio.paused) {
        audio.pause();
        return;
      }
      try {
        await requestDelivery();
        await audio.play();
      } catch (error) {
        setStatus(error.message || "Audio preview is unavailable.", true);
      }
    });

    audio.addEventListener("play", () => {
      play.textContent = "Pause";
      play.setAttribute("aria-label", "Pause audio");
    });
    audio.addEventListener("pause", () => {
      play.textContent = "Play";
      play.setAttribute("aria-label", "Play audio");
    });
    audio.addEventListener("loadedmetadata", () => {
      seek.max = String(audio.duration || 0);
      duration.textContent = formatTime(audio.duration);
    });
    audio.addEventListener("durationchange", () => {
      if (Number.isFinite(audio.duration)) {
        seek.max = String(audio.duration);
        duration.textContent = formatTime(audio.duration);
      }
    });
    audio.addEventListener("timeupdate", () => {
      currentTime.textContent = formatTime(audio.currentTime);
      seek.value = String(audio.currentTime);
    });
    audio.addEventListener("ended", () => {
      play.textContent = "Play";
      play.setAttribute("aria-label", "Play audio");
    });
    audio.addEventListener("error", () => {
      setStatus("The selected audio preview could not be played.", true);
    });

    seek.addEventListener("input", () => {
      audio.currentTime = Number(seek.value);
      currentTime.textContent = formatTime(audio.currentTime);
    });
    volume.addEventListener("input", () => {
      audio.volume = Number(volume.value);
    });
    speed.addEventListener("change", () => {
      audio.playbackRate = Number(speed.value);
    });

    qualityButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const next = available.find(
          (source) => source.quality === button.dataset.quality,
        );
        if (!next || next.quality === selected?.quality) return;
        audio.pause();
        audio.removeAttribute("src");
        audio.load();
        selected = next;
        delivery = null;
        deliveryExpiresAt = null;
        seek.value = "0";
        currentTime.textContent = "0:00";
        setStatus(`${selected.label} selected. Press play to request audio.`);
        updateQualityButtons();
      });
    });

    updateQualityButtons();
  };

  const initializeAll = () => {
    document.querySelectorAll("[data-secure-audio-preview]").forEach(initialize);
  };

  document.addEventListener("DOMContentLoaded", initializeAll);
  document.addEventListener("htmx:afterSwap", initializeAll);
})();
