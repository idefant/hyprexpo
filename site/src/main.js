import "./styles.css";

const copyButton = document.querySelector("[data-copy]");
const command = document.querySelector("#install-command");
const copyStatus = document.querySelector(".copy-status");
let resetCopy;

copyButton?.addEventListener("click", async () => {
  window.clearTimeout(resetCopy);
  try {
    await navigator.clipboard.writeText(command.textContent.trim());
    copyButton.textContent = "Copied";
    copyStatus.textContent = "Install command copied.";
    resetCopy = window.setTimeout(() => {
      copyButton.textContent = "Copy";
      copyStatus.textContent = "";
    }, 2000);
  } catch {
    copyButton.textContent = "Copy";
    copyStatus.textContent =
      "Copy unavailable. Select and copy the command above.";
  }
});

const video = document.querySelector(".hero-video");
video?.addEventListener("error", () => {
  document.querySelector(".video-fallback").hidden = false;
});
