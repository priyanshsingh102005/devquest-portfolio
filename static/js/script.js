// ===== ELEMENTS =====

const contactModal = document.getElementById("contact-modal");
const contactForm = document.getElementById("contact-form");
const openContactButtons = document.querySelectorAll(".contact-trigger");
const closeContactButtons = document.querySelectorAll("[data-close-contact]");
const firstInput = document.getElementById("contact-name");

const videoModal = document.getElementById("video-modal");
const aboutVideoFrame = document.getElementById("about-video-frame");
const videoTriggers = document.querySelectorAll("[data-video-embed]");
const closeVideoButtons = document.querySelectorAll("[data-close-video]");


// ===== BODY SCROLL LOCK =====

function syncBodyLock() {
  const shouldLock =
    contactModal.classList.contains("is-open") ||
    videoModal.classList.contains("is-open");

  document.body.classList.toggle("modal-open", shouldLock);
}


// ===== CONTACT MODAL =====

function openContactModal(e) {
  if (e) e.preventDefault();

  contactModal.classList.add("is-open");
  contactModal.setAttribute("aria-hidden", "false");

  syncBodyLock();

  if (firstInput) firstInput.focus();
}

function closeContactModal() {
  contactModal.classList.remove("is-open");
  contactModal.setAttribute("aria-hidden", "true");

  syncBodyLock();
}


// ===== VIDEO MODAL =====

function openVideoModal(videoUrl) {
  aboutVideoFrame.src = videoUrl;

  videoModal.classList.add("is-open");
  videoModal.setAttribute("aria-hidden", "false");

  syncBodyLock();
}

function closeVideoModal() {
  videoModal.classList.remove("is-open");
  videoModal.setAttribute("aria-hidden", "true");

  aboutVideoFrame.src = "";

  syncBodyLock();
}


// ===== EVENT LISTENERS =====

// open contact modal
openContactButtons.forEach((btn) => {
  btn.addEventListener("click", openContactModal);
});

// close contact modal
closeContactButtons.forEach((btn) => {
  btn.addEventListener("click", closeContactModal);
});

// video triggers
videoTriggers.forEach((trigger) => {
  trigger.addEventListener("click", (e) => {
    e.preventDefault();

    const videoUrl = trigger.getAttribute("data-video-embed");

    if (videoUrl) {
      openVideoModal(videoUrl);
    }
  });
});

// close video modal
closeVideoButtons.forEach((btn) => {
  btn.addEventListener("click", closeVideoModal);
});


// ===== ESC KEY HANDLING =====

window.addEventListener("keydown", (event) => {

  if (event.key === "Escape") {

    if (contactModal.classList.contains("is-open")) {
      closeContactModal();
    }

    if (videoModal.classList.contains("is-open")) {
      closeVideoModal();
    }

  }

});


// ===== CONTACT FORM SUBMISSION =====

contactForm.addEventListener("submit", async (event) => {

  event.preventDefault();

  const name = document.getElementById("contact-name").value.trim();
  const email = document.getElementById("contact-email").value.trim();
  const message = document.getElementById("contact-message").value.trim();

  const submitButton = contactForm.querySelector(".contact-submit");

  const originalText = submitButton.textContent;

  submitButton.disabled = true;
  submitButton.textContent = "Sending...";

  try {

    const response = await fetch("/contact", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        name,
        email,
        message
      })
    });

    const result = await response.json().catch(() => ({}));

    if (!response.ok || !result.ok) {
      const rateLimitMessage = "Too many requests right now. Please wait a few seconds and try again.";
      const errorMessage = response.status === 429
        ? rateLimitMessage
        : (result.error || "Message failed.");
      throw new Error(errorMessage);
    }

    alert("Message sent successfully!");

    contactForm.reset();

    closeContactModal();

  } catch (err) {

    alert(err.message || "Could not send message.");

  } finally {

    submitButton.disabled = false;
    submitButton.textContent = originalText;

  }

});
