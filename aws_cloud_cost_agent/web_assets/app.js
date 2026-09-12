const statusNode = document.getElementById("run-status");
const form = document.getElementById("run-form");
const runButton = document.getElementById("run-button");
const runId = statusNode?.dataset.runId;

if (form) {
  form.addEventListener("submit", () => {
    runButton.disabled = true;
    runButton.textContent = "Starting...";
  });
}

async function pollRun() {
  if (!runId) return;

  try {
    const response = await fetch(`/api/status?id=${encodeURIComponent(runId)}`, {
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Run status is unavailable.");
    const state = await response.json();

    statusNode.className = `run-status status-${state.status}`;
    statusNode.querySelector("span:last-child").textContent =
      state.status === "running"
        ? `Running: ${state.steps.join(", ")}`
        : state.status.charAt(0).toUpperCase() + state.status.slice(1);

    if (state.status === "complete") {
      const artifact = state.artifacts[0];
      window.location.replace(artifact ? `/?artifact=${encodeURIComponent(artifact)}` : "/");
      return;
    }
    if (state.status === "failed") {
      let errorBanner = document.querySelector(".error-banner");
      if (!errorBanner) {
        errorBanner = document.createElement("div");
        errorBanner.className = "error-banner";
        errorBanner.setAttribute("role", "alert");
        document.querySelector(".topbar").after(errorBanner);
      }
      errorBanner.textContent = state.error || "The workflow failed.";
      runButton.disabled = false;
      runButton.textContent = "Run selected steps";
      return;
    }
  } catch (error) {
    statusNode.querySelector("span:last-child").textContent = error.message;
  }

  window.setTimeout(pollRun, 2000);
}

pollRun();
