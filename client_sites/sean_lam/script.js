const enquiryMessages = {
  protection: "Hi Sean，我从你的疾病保障页面过来，想了解一下适合 KL 上班族的疾病保障。",
  existing: "Hi Sean，我已经有保险，想先检查现有保障有没有重复或缺口。",
  budget: "Hi Sean，我想先按自己的预算了解可以考虑多少疾病保障。",
  general: "Hi Sean，我想先了解一下疾病保障，还没有决定要买。",
};

function positiveNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function calculateExposure(essentials, commitments, months) {
  return Math.round(
    (positiveNumber(essentials) + positiveNumber(commitments))
    * positiveNumber(months)
  );
}

function buildWhatsAppUrl(intent) {
  const message = enquiryMessages[intent] || enquiryMessages.general;
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}

function initialiseSite() {
  document.querySelectorAll("[data-whatsapp-intent]").forEach((link) => {
    link.href = buildWhatsAppUrl(link.dataset.whatsappIntent);
  });

  const intentLink = document.getElementById("intent-whatsapp");
  document.querySelectorAll("[data-intent]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-intent]").forEach((option) => {
        option.setAttribute("aria-pressed", String(option === button));
      });
      intentLink.href = buildWhatsAppUrl(button.dataset.intent);
      intentLink.focus();
    });
  });

  const calculator = document.getElementById("exposure-form");
  const result = document.getElementById("exposure-result");
  calculator.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!calculator.reportValidity()) return;
    const data = new FormData(calculator);
    const total = calculateExposure(
      data.get("essentials"),
      data.get("commitments"),
      data.get("months")
    );
    result.querySelector("strong").textContent = `RM ${total.toLocaleString("en-MY")}`;
  });

  document.querySelectorAll(".faq-question").forEach((button) => {
    button.addEventListener("click", () => {
      const answer = document.getElementById(button.getAttribute("aria-controls"));
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      button.querySelector(".faq-icon").textContent = expanded ? "＋" : "−";
      answer.hidden = expanded;
    });
  });
}

if (typeof document !== "undefined") {
  initialiseSite();
}

if (typeof module !== "undefined") {
  module.exports = { calculateExposure, buildWhatsAppUrl };
}
