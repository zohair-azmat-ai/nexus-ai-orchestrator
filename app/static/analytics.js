const statElements = {
  total_tickets: document.querySelector('[data-stat="total_tickets"]'),
  total_escalations: document.querySelector('[data-stat="total_escalations"]'),
  escalation_rate: document.querySelector('[data-stat="escalation_rate"]'),
  avg_response_time_seconds: document.querySelector('[data-stat="avg_response_time_seconds"]'),
};

const summary = document.getElementById("analytics-summary");
const errorElement = document.getElementById("analytics-error");

function animateValue(element, value, formatter) {
  const duration = 700;
  const start = performance.now();
  const numericValue = Number(value) || 0;

  function frame(now) {
    const progress = Math.min((now - start) / duration, 1);
    const current = numericValue * progress;
    element.textContent = formatter(current, progress === 1);
    if (progress < 1) {
      requestAnimationFrame(frame);
    }
  }

  requestAnimationFrame(frame);
}

async function loadAnalytics() {
  try {
    const response = await fetch("/api/v1/analytics/summary");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to load analytics.");
    }

    animateValue(statElements.total_tickets, payload.total_tickets, (value, done) => `${Math.round(done ? payload.total_tickets : value)}`);
    animateValue(statElements.total_escalations, payload.total_escalations, (value, done) => `${Math.round(done ? payload.total_escalations : value)}`);
    animateValue(statElements.escalation_rate, payload.escalation_rate, (value, done) => `${(done ? payload.escalation_rate : value).toFixed(1)}%`);
    animateValue(statElements.avg_response_time_seconds, payload.avg_response_time_seconds, (value, done) => `${(done ? payload.avg_response_time_seconds : value).toFixed(1)}s`);

    summary.textContent = `Escalations currently represent ${payload.escalation_rate.toFixed(1)}% of all submitted tickets, with an average response time of ${payload.avg_response_time_seconds.toFixed(1)} seconds.`;
  } catch (error) {
    errorElement.textContent = error.message;
    errorElement.className = "nexus-feedback error";
    errorElement.classList.remove("is-hidden");
    summary.textContent = "Analytics are temporarily unavailable.";
  }
}

loadAnalytics();
