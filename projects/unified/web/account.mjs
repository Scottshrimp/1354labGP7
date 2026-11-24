// Accounts for the public site: header links, the sign-up / log-in dialog
// (with Cloudflare Turnstile) and the run-recording API. Shared by the
// console and the leaderboard page.

const TURNSTILE_SRC = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
const USERNAME = /^[A-Za-z0-9_-]{3,20}$/;

const MESSAGES = {
  bad_username: "Usernames are 3–20 letters, numbers, - or _.",
  bad_password: "Passwords need 8 to 128 characters.",
  username_taken: "That username is taken. Try another one.",
  bad_credentials: "Wrong username or password.",
  captcha_failed: "The human check didn’t pass. Try it again.",
  captcha_unreachable: "Couldn’t reach the human check. Try again in a moment.",
  signup_unavailable: "Accounts aren’t available right now.",
  rate_limited: "Too many attempts. Wait a few minutes and try again.",
  login_required: "Your session ended. Log in again.",
};

export class ApiError extends Error {
  constructor(code, status) {
    super(MESSAGES[code] || "Something went wrong. Try again.");
    this.code = code;
    this.status = status;
  }
}

export async function api(path, body) {
  const init = body === undefined ? { cache: "no-store" } : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  let response;
  try {
    response = await fetch("/api/" + path, init);
  } catch {
    throw new ApiError("offline", 0);
  }
  let payload = {};
  try { payload = await response.json(); } catch { /* empty or non-JSON body */ }
  if (!response.ok) throw new ApiError(payload.error || "server_error", response.status);
  return payload;
}

const ARROW = '<svg class="ext-arrow" viewBox="0 0 12 12" aria-hidden="true"><path d="M3.2 8.8 8.6 3.4M4.4 3.2h4.4v4.4"/></svg>';

let siteKey = "";
let user = null;
const listeners = new Set();

export const currentUser = () => user;
// Accounts stay hidden until the server has Turnstile keys configured.
export const accountsEnabled = () => Boolean(siteKey);

function setUser(next) {
  user = next;
  for (const listener of listeners) listener(user);
}

export function onUserChange(listener) {
  listeners.add(listener);
  listener(user);
}

/* ---------- Turnstile ---------- */

let turnstileLoad = null;

function loadTurnstile() {
  turnstileLoad ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = TURNSTILE_SRC;
    script.async = true;
    script.onload = () => resolve(window.turnstile);
    script.onerror = () => {
      turnstileLoad = null;
      reject(new Error("Couldn’t load the human check. Check your connection and try again."));
    };
    document.head.append(script);
  });
  return turnstileLoad;
}

/* ---------- Dialog ---------- */

let dialog = null;

function field(name, label, type, autocomplete, hint) {
  return `<label class="auth-field" data-field="${name}">
    <span>${label}</span>
    <input name="${name}" type="${type}" autocomplete="${autocomplete}" required
      ${name === "username" ? 'maxlength="20" autocapitalize="none" spellcheck="false"' : 'maxlength="128"'}>
    ${hint ? `<small>${hint}</small>` : ""}
  </label>`;
}

function buildDialog() {
  dialog = document.createElement("dialog");
  dialog.className = "auth";
  dialog.setAttribute("aria-labelledby", "auth-title");
  dialog.innerHTML = `
    <form class="auth-card" method="dialog" novalidate>
      <button type="button" class="auth-close" aria-label="Close">
        <svg viewBox="0 0 16 16" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8"/></svg>
      </button>
      <p class="auth-eyebrow">Rhythm Hit</p>
      <h2 id="auth-title"></h2>
      <p class="auth-lede"></p>
      ${field("username", "Username", "text", "username", "3–20 letters, numbers, - or _")}
      ${field("password", "Password", "password", "new-password", "At least 8 characters")}
      ${field("confirm", "Confirm password", "password", "new-password", "")}
      <div class="auth-captcha" aria-label="Human check"></div>
      <p class="auth-error" role="alert" hidden></p>
      <button type="submit" class="auth-submit"></button>
      <p class="auth-switch"><span></span> <button type="button" class="auth-toggle"></button></p>
    </form>`;
  document.body.append(dialog);

  const form = dialog.querySelector("form");
  const captcha = dialog.querySelector(".auth-captcha");
  const error = dialog.querySelector(".auth-error");
  const submit = dialog.querySelector(".auth-submit");
  let mode = "signup";
  let widget = null;
  let token = "";
  let busy = false;

  const showError = (message) => {
    error.textContent = message;
    error.hidden = !message;
  };

  const resetCaptcha = () => {
    token = "";
    if (widget !== null) window.turnstile?.reset(widget);
  };

  dialog.setMode = (next) => {
    mode = next;
    const signup = mode === "signup";
    dialog.dataset.mode = mode;
    dialog.querySelector("#auth-title").textContent = signup ? "Create your account" : "Log in";
    dialog.querySelector(".auth-lede").textContent = signup
      ? "Save your solo runs and see where you rank on the leaderboard."
      : "Welcome back. Log in to save runs and open the leaderboard.";
    dialog.querySelector('[data-field="confirm"]').hidden = !signup;
    dialog.querySelector('[data-field="username"] small').hidden = !signup;
    dialog.querySelector('[data-field="password"] small').hidden = !signup;
    form.elements.password.autocomplete = signup ? "new-password" : "current-password";
    submit.textContent = signup ? "Create account" : "Log in";
    dialog.querySelector(".auth-switch span").textContent = signup ? "Already have an account?" : "New here?";
    dialog.querySelector(".auth-toggle").textContent = signup ? "Log in" : "Create an account";
    showError("");
  };

  dialog.prepare = async () => {
    if (!siteKey) {
      showError(MESSAGES.signup_unavailable);
      return;
    }
    if (widget !== null) {
      resetCaptcha();
      return;
    }
    try {
      const turnstile = await loadTurnstile();
      widget = turnstile.render(captcha, {
        sitekey: siteKey,
        theme: "light",
        size: "flexible",
        callback: (value) => { token = value; showError(""); },
        "expired-callback": () => { token = ""; },
        "error-callback": () => { token = ""; },
      });
    } catch (failure) {
      showError(failure.message);
    }
  };

  dialog.querySelector(".auth-close").addEventListener("click", () => dialog.close());
  dialog.querySelector(".auth-toggle").addEventListener("click", () => {
    dialog.setMode(mode === "signup" ? "login" : "signup");
    form.elements.username.focus();
  });
  // A click on the backdrop (outside the card) closes the dialog.
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    const { username, password, confirm } = form.elements;
    const name = username.value.trim();
    const signup = mode === "signup";
    if (signup && !USERNAME.test(name)) return showError(MESSAGES.bad_username);
    if (!name || !password.value) return showError("Enter your username and password.");
    if (signup && password.value.length < 8) return showError("Passwords need at least 8 characters.");
    if (signup && password.value !== confirm.value) return showError("The two passwords don’t match.");
    if (!siteKey) return showError(MESSAGES.signup_unavailable);
    if (!token) return showError("Complete the human check first.");
    busy = true;
    submit.disabled = true;
    submit.setAttribute("aria-busy", "true");
    showError("");
    try {
      const result = await api(signup ? "signup" : "login",
        { username: name, password: password.value, turnstile: token });
      form.reset();
      setUser(result.user);
      dialog.close();
    } catch (failure) {
      showError(failure.code === "offline" ? "Can’t reach the server. Check your connection." : failure.message);
      // Turnstile tokens are single-use.
      resetCaptcha();
    } finally {
      busy = false;
      submit.disabled = false;
      submit.removeAttribute("aria-busy");
    }
  });
  return dialog;
}

export function openAuth(mode = "signup") {
  if (!dialog) buildDialog();
  dialog.setMode(mode);
  if (!dialog.open) dialog.showModal();
  dialog.querySelector('input[name="username"]').focus();
  void dialog.prepare();
}

/* ---------- Header links ---------- */

// Fills <nav id="account">: "Leaderboard ↗" plus "Sign up" or the user's name.
export function mountAccountNav(nav, { leaderboard: showLeaderboard = true } = {}) {
  nav.innerHTML = `
    <a class="account-link" href="/leaderboard/" target="_blank" rel="noopener" data-account="leaderboard">Leaderboard${ARROW}</a>
    <button type="button" class="account-link" data-account="signup">Sign up</button>
    <span class="account-user" data-account="user" hidden></span>
    <button type="button" class="account-link" data-account="logout" hidden>Log out</button>`;
  const pick = (name) => nav.querySelector(`[data-account="${name}"]`);
  // The leaderboard is public, so the link always opens it.
  pick("leaderboard").hidden = !showLeaderboard;
  pick("signup").addEventListener("click", () => openAuth("signup"));
  pick("logout").addEventListener("click", async () => {
    try { await api("logout", {}); } catch { /* the cookie expires on its own */ }
    setUser(null);
  });
  onUserChange((next) => {
    pick("signup").hidden = Boolean(next);
    pick("user").hidden = pick("logout").hidden = !next;
    pick("user").textContent = next ? next.name : "";
  });
  nav.hidden = false;
}

export async function loadAccount() {
  const me = await api("me");
  siteKey = me.turnstile_site_key || "";
  setUser(me.user);
  return me.user;
}

/* ---------- Solo run records ---------- */

export async function startRun(songId) {
  return (await api("runs/start", { song_id: songId })).run_id;
}

export function finishRun(runId, { score, miss, best_combo: best }) {
  return api("runs/finish", { run_id: runId, score, miss, best_combo: best });
}
