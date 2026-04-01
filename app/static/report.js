const form = document.getElementById("report-form");
const submitButton = document.getElementById("submit-button");
const loading = document.getElementById("loading");
const feedback = document.getElementById("feedback");

function buildMessage(message, priority, reporter) {
  const lines = [message.trim(), "", `Priority: ${priority}`];

  if (reporter) {
    lines.push(`Reporter Reference: ${reporter}`);
  }

  if (priority === "high") {
    lines.push("This issue is urgent and needs immediate attention.");
  } else if (priority === "medium") {
    lines.push("This issue should be prioritized soon.");
  }

  return lines.join("\n");
}

function showFeedback(kind, html) {
  feedback.className = `nexus-feedback ${kind}`;
  feedback.innerHTML = html;
  feedback.classList.remove("is-hidden");
}

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(form);
  const message = String(formData.get("message") || "").trim();
  const priority = String(formData.get("priority") || "low");
  const reporter = String(formData.get("reporter") || "").trim();
  const fallbackId = `guest-${crypto.randomUUID()}`;
  const userId = reporter || fallbackId;
  const sessionId = crypto.randomUUID();

  submitButton.disabled = true;
  loading.classList.remove("is-hidden");
  feedback.classList.add("is-hidden");

  try {
    const response = await fetch("/api/v1/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        session_id: sessionId,
        message: buildMessage(message, priority, reporter),
      }),
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || payload.error || "Unable to submit your issue right now.");
    }

    const extra = payload.escalation_case_id
      ? `<p>Case ID: <strong>${payload.escalation_case_id}</strong><br>Status: <strong>${payload.escalation_status || "open"}</strong></p>`
      : "<p>Your report was accepted into the support pipeline.</p>";

    showFeedback(
      "success",
      `<p>Your issue has been submitted and is under review.</p>${extra}`,
    );
    form.reset();
  } catch (error) {
    showFeedback("error", `<p>${error.message}</p>`);
  } finally {
    submitButton.disabled = false;
    loading.classList.add("is-hidden");
  }
});
