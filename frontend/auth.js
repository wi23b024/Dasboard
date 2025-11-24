// Platzhalter-URLs 
const BASE_URL = "http://localhost:8000";
const REGISTER_API_URL = `${BASE_URL}/registrieren`;
const LOGIN_API_URL    = `${BASE_URL}/login`;

document.addEventListener("DOMContentLoaded", () => {
  const registerForm = document.getElementById("registerForm");
  const loginForm = document.getElementById("loginForm");

  if (registerForm) {
    registerForm.addEventListener("submit", handleRegister);
  }

  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin);
  }
});

async function handleRegister(event) {
  event.preventDefault();

  const firstName = document.getElementById("firstName").value.trim();
  const lastName = document.getElementById("lastName").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;
  const passwordRepeat = document.getElementById("passwordRepeat").value;
  const messageEl = document.getElementById("registerMessage");
  const submitBtn = event.target.querySelector("button[type='submit']");

  messageEl.textContent = "";
  messageEl.className = "form-message";

  // Simple Frontend-Validierung
  if (!firstName || !lastName || !email || !password || !passwordRepeat) {
    messageEl.textContent = "Bitte alle Felder ausfüllen.";
    messageEl.classList.add("error");
    return;
  }

  if (password !== passwordRepeat) {
    messageEl.textContent = "Die Passwörter stimmen nicht überein.";
    messageEl.classList.add("error");
    return;
  }

  const payload = {
    firstName,
    lastName,
    email,
    password,
  };

  // Button während Request deaktivieren
  submitBtn.disabled = true;

  try {
    // Platzhalter-Fetch – URL & Response-Format werden vom Backend definiert
    const response = await fetch(REGISTER_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      credentials: "include",
    });

    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      // Falls Backend kein JSON schickt
    }

    if (response.ok) {
      messageEl.textContent =
        (data && (data.message || data.msg)) ||
        "Registrierung erfolgreich.";
      messageEl.classList.add("success");

      setTimeout(() => {
    window.location.href = "login.html";
  }, 1200);

      // Optional: Felder leeren
      // event.target.reset();
    } else {
      messageEl.textContent =
        (data && (data.error || data.message)) ||
        "Registrierung fehlgeschlagen.";
      messageEl.classList.add("error");
    }
  } catch (error) {
    console.error(error);
    messageEl.textContent =
      "Es ist ein Fehler bei der Verbindung zum Server aufgetreten.";
    messageEl.classList.add("error");
  } finally {
    submitBtn.disabled = false;
  }
}

async function handleLogin(event) {
  event.preventDefault();

  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value;
  const messageEl = document.getElementById("loginMessage");
  const submitBtn = event.target.querySelector("button[type='submit']");

  messageEl.textContent = "";
  messageEl.className = "form-message";

  // Simple Frontend-Validierung
  if (!email || !password) {
    messageEl.textContent = "Bitte E-Mail und Passwort angeben.";
    messageEl.classList.add("error");
    return;
  }

  const payload = {
    email,
    password,
  };

  submitBtn.disabled = true;

  try {
    // Platzhalter-Fetch – URL & Response-Format werden vom Backend definiert
    const response = await fetch(LOGIN_API_URL, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
      credentials: "include",
    });

    let data = null;
    try {
      data = await response.json();
    } catch (e) {
      // Falls Backend kein JSON schickt
    }

    if (response.ok) {
      messageEl.textContent =
        (data && (data.message || data.msg)) || "Login erfolgreich.";
      messageEl.classList.add("success");

      window.location.href = "indexdashboard.html";
    } else {
      messageEl.textContent =
        (data && (data.error || data.message)) || "Login fehlgeschlagen.";
      messageEl.classList.add("error");
    }
  } catch (error) {
    console.error(error);
    messageEl.textContent =
      "Es ist ein Fehler bei der Verbindung zum Server aufgetreten.";
    messageEl.classList.add("error");
  } finally {
    submitBtn.disabled = false;
  }
}

