const WHATSAPP_NUMBER = "60166396106";

const enquiryMessages = {
  protection: "Hi Sean，我想了解疾病保障，想先看看自己目前有没有缺口。",
  existing: "Hi Sean，我已经有保险了，想请你帮我看看现有保障有没有缺口。",
  budget: "Hi Sean，我想先了解一下，以我的预算大概可以怎样规划保障。",
  general: "Hi Sean，我想先问问疾病保障，还没有决定要买。",
};

const campaignContent = {
  cashflow: {
    title: "如果生病半年不能工作，你的现金流够吗？",
    summary: "把每月开销和家庭责任填进去，先看看休养期间大概要准备多少现金。",
    label: "算算我的现金流",
    href: "#calculator",
  },
  "medical-card": {
    title: "已经有 Medical Card，就代表保障够了吗？",
    summary: "Medical Card 和疾病保障处理的问题不同。先了解两者差别，再看看自己有没有现金流缺口。",
    label: "了解两种保障的差别",
    href: "#coverage",
  },
};

const defaultCampaignContent = {
  title: null,
  summary: null,
  label: null,
  href: null,
};

function positiveNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : 0;
}

function formatMoney(value) {
  return positiveNumber(value).toLocaleString("en-MY");
}

function calculateCashflow(essentials, commitments, months, savings, benefits) {
  const required = Math.round(
    (positiveNumber(essentials) + positiveNumber(commitments))
    * positiveNumber(months)
  );
  const available = Math.round(positiveNumber(savings) + positiveNumber(benefits));
  return {
    required,
    available,
    gap: Math.max(required - available, 0),
  };
}

function buildWhatsAppUrl(intent, context = {}) {
  let message = enquiryMessages[intent] || enquiryMessages.general;
  if (intent === "calculator") {
    message = "Hi Sean，我刚刚在网站算了一下。如果我暂时不能工作 "
      + positiveNumber(context.months)
      + " 个月，预计需要 RM"
      + formatMoney(context.required)
      + "，扣除现有储蓄和保障后，缺口大约是 RM"
      + formatMoney(context.gap)
      + "。可以帮我看看现有保障够不够吗？";
  }
  return "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + encodeURIComponent(message);
}

function getCampaignContent(name) {
  return campaignContent[name] || defaultCampaignContent;
}

function getReachedScrollDepths(percent, seen) {
  return [25, 50, 75, 100].filter((depth) => percent >= depth && !seen.has(depth));
}

function trackEvent(name, parameters = {}) {
  if (typeof window === "undefined") return;
  window.dataLayer = window.dataLayer || [];
  const payload = { event: name, ...parameters };
  window.dataLayer.push(payload);
  if (typeof window.gtag === "function") {
    window.gtag("event", name, parameters);
  }
  if (typeof window.fbq === "function") {
    window.fbq("trackCustom", name, parameters);
  }
}

function initialiseWhatsAppLinks() {
  document.querySelectorAll("[data-whatsapp-intent]").forEach((link) => {
    link.href = buildWhatsAppUrl(link.dataset.whatsappIntent);
  });
}

function initialiseCampaign() {
  const campaign = new URLSearchParams(window.location.search).get("campaign");
  const content = getCampaignContent(campaign);
  if (!content.href) return;

  document.getElementById("hero-title").textContent = content.title;
  document.getElementById("hero-summary").textContent = content.summary;
  const primary = document.getElementById("hero-primary");
  primary.textContent = content.label + " →";
  primary.href = content.href;
}

function initialiseCalculator() {
  const form = document.getElementById("exposure-form");
  const requiredOutput = document.getElementById("cashflow-required");
  const gapOutput = document.getElementById("cashflow-gap");
  const calculatorLink = document.getElementById("calculator-whatsapp");

  form.addEventListener("input", () => {
    calculatorLink.hidden = true;
    if (!form.dataset.trackedStarted) {
      trackEvent("calculator_started");
      form.dataset.trackedStarted = "true";
    }
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;

    const data = new FormData(form);
    const result = calculateCashflow(
      data.get("essentials"),
      data.get("commitments"),
      data.get("months"),
      data.get("savings"),
      data.get("benefits")
    );

    requiredOutput.textContent = "RM " + formatMoney(result.required);
    gapOutput.textContent = "RM " + formatMoney(result.gap);
    calculatorLink.href = buildWhatsAppUrl("calculator", {
      months: data.get("months"),
      required: result.required,
      gap: result.gap,
    });
    calculatorLink.hidden = false;

    if (!form.dataset.trackedCompleted) {
      trackEvent("calculator_completed", {
        recovery_months: positiveNumber(data.get("months")),
        estimated_required: result.required,
        estimated_gap: result.gap,
      });
      form.dataset.trackedCompleted = "true";
    }
  });
}

function initialiseQuestionSelector() {
  const intentLink = document.getElementById("intent-whatsapp");
  document.querySelectorAll("[data-intent]").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll("[data-intent]").forEach((option) => {
        option.setAttribute("aria-pressed", String(option === button));
      });
      intentLink.href = buildWhatsAppUrl(button.dataset.intent);
      intentLink.textContent = button.dataset.label;
      trackEvent("question_selected", { question: button.dataset.intent });
    });
  });
}

function initialiseFaq() {
  document.querySelectorAll(".faq-question").forEach((button) => {
    button.addEventListener("click", () => {
      const answer = document.getElementById(button.getAttribute("aria-controls"));
      const expanded = button.getAttribute("aria-expanded") === "true";
      button.setAttribute("aria-expanded", String(!expanded));
      button.querySelector(".faq-icon").textContent = expanded ? "＋" : "−";
      answer.hidden = expanded;
      if (!expanded) {
        trackEvent("faq_opened", {
          faq_question: button.dataset.faqQuestion,
        });
      }
    });
  });

  const moreButton = document.getElementById("faq-more");
  moreButton.addEventListener("click", () => {
    document.querySelectorAll(".faq-extra").forEach((item) => {
      item.hidden = false;
    });
    moreButton.setAttribute("aria-expanded", "true");
    moreButton.hidden = true;
  });
}

function initialiseCtaTracking() {
  document.querySelectorAll("[data-whatsapp-source]").forEach((link) => {
    link.addEventListener("click", () => {
      const source = link.dataset.whatsappSource;
      if (link.getAttribute("href").startsWith("https://wa.me/")) {
        trackEvent("whatsapp_click", { source });
      }
      if (source === "existing_policy") {
        trackEvent("existing_policy_click");
      }
      if (source === "footer") {
        trackEvent("final_cta_click");
      }
    });
  });
}

function initialiseScrollTracking() {
  const seen = new Set();
  let ticking = false;

  function reportDepth() {
    const maximum = document.documentElement.scrollHeight - window.innerHeight;
    const percent = maximum <= 0 ? 100 : Math.round((window.scrollY / maximum) * 100);
    getReachedScrollDepths(percent, seen).forEach((depth) => {
      seen.add(depth);
      trackEvent("scroll_" + depth);
    });
    ticking = false;
  }

  window.addEventListener("scroll", () => {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(reportDepth);
  }, { passive: true });
  reportDepth();
}

function initialiseSite() {
  initialiseWhatsAppLinks();
  initialiseCampaign();
  initialiseCalculator();
  initialiseQuestionSelector();
  initialiseFaq();
  initialiseCtaTracking();
  initialiseScrollTracking();
}

if (typeof document !== "undefined") {
  initialiseSite();
}

if (typeof module !== "undefined") {
  module.exports = {
    calculateCashflow,
    buildWhatsAppUrl,
    getCampaignContent,
    getReachedScrollDepths,
    trackEvent,
  };
}
