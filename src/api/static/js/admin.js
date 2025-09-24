const STORAGE_KEY = "ai_invoice_admin_token";
const BOOLEAN_TRUE = new Set(["true", "1", "yes", "y", "on"]);
const BOOLEAN_FALSE = new Set(["false", "0", "no", "n", "off"]);

const tokenInput = document.getElementById("admin-token");
const rememberToggle = document.getElementById("remember-token");
const loadButton = document.getElementById("load-settings");
const refreshButton = document.getElementById("refresh-settings");
const resetButton = document.getElementById("reset-form");
const settingsCard = document.getElementById("settings-card");
const authError = document.getElementById("auth-error");
const statusMessage = document.getElementById("status-message");
const form = document.getElementById("settings-form");

let adminToken = "";
let lastPayload = null;
let lastOverrides = {};

function setStatus(message, type) {
  statusMessage.textContent = message || "";
  statusMessage.className = "status-message";
  if (type) {
    statusMessage.classList.add(type);
  }
}

function clearStatus() {
  setStatus("", "");
}

function setAuthError(message) {
  authError.textContent = message;
  authError.classList.remove("hidden");
}

function clearAuthError() {
  authError.textContent = "";
  authError.classList.add("hidden");
}

function updateRememberStorage() {
  if (rememberToggle.checked && adminToken) {
    window.localStorage.setItem(STORAGE_KEY, adminToken);
  } else {
    window.localStorage.removeItem(STORAGE_KEY);
  }
}

function initializeToken() {
  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored) {
    rememberToggle.checked = true;
    tokenInput.value = stored;
    adminToken = stored;
  }
}

function clearValidationIndicators() {
  document.querySelectorAll(".form-row").forEach((row) => {
    row.classList.remove("invalid");
  });
}

function applyOverrides(overrides) {
  lastOverrides = overrides || {};
  document.querySelectorAll(".form-row").forEach((row) => {
    row.classList.remove("overridden");
  });
  document.querySelectorAll(".override-note").forEach((note) => {
    note.classList.add("hidden");
  });
  Object.entries(lastOverrides).forEach(([field, isOverride]) => {
    if (!isOverride) {
      return;
    }
    const row = document.querySelector(`.form-row[data-field="${field}"]`);
    const note = document.querySelector(`.override-note[data-override="${field}"]`);
    if (row) {
      row.classList.add("overridden");
    }
    if (note) {
      note.classList.remove("hidden");
    }
  });
}

function markFieldError(fieldName, message) {
  setStatus(message, "error");
  const row = document.querySelector(`.form-row[data-field="${fieldName}"]`);
  if (row) {
    row.classList.add("invalid");
  }
}

function readIntField(id, { required }) {
  const input = document.getElementById(id);
  const text = input.value.trim();
  if (!text) {
    if (required) {
      markFieldError(id, "This value is required.");
      return { ok: false };
    }
    return { ok: true, value: null };
  }
  const value = Number(text);
  if (!Number.isInteger(value) || value < 0) {
    markFieldError(id, "Enter a non-negative integer.");
    return { ok: false };
  }
  return { ok: true, value };
}

function parseList(id) {
  const value = document.getElementById(id).value;
  if (!value.trim()) {
    return [];
  }
  const separators = /[,\n]/;
  return value
    .split(separators)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function parseCorsOrigins(rawValue) {
  if (!rawValue.trim()) {
    return { ok: true, value: [] };
  }
  const entries = [];
  for (const line of rawValue.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed) {
      continue;
    }
    const [originPart, flagPart] = trimmed.split("|", 2);
    const origin = originPart.trim();
    if (!origin) {
      return { ok: false, message: "Each origin must include a value." };
    }
    let allowCredentials = false;
    if (flagPart !== undefined) {
      const normalizedFlag = flagPart.trim().toLowerCase();
      if (BOOLEAN_TRUE.has(normalizedFlag)) {
        allowCredentials = true;
      } else if (BOOLEAN_FALSE.has(normalizedFlag) || normalizedFlag === "") {
        allowCredentials = false;
      } else {
        return {
          ok: false,
          message: `Unable to parse credentials flag for ${origin}. Use true/false.`,
        };
      }
    }
    entries.push({ origin, allow_credentials: allowCredentials });
  }

  const wildcardEntries = entries.filter((entry) => entry.origin === "*");
  if (wildcardEntries.length > 0) {
    if (entries.length > wildcardEntries.length) {
      return {
        ok: false,
        message: "Wildcard origin cannot be combined with other origins.",
      };
    }
    if (wildcardEntries.some((entry) => entry.allow_credentials)) {
      return {
        ok: false,
        message: "Wildcard origin cannot require credentials.",
      };
    }
  }

  return { ok: true, value: entries };
}

function populateForm(values) {
  lastPayload = JSON.parse(JSON.stringify(values));
  document.getElementById("classifier_path").value = values.classifier_path || "";
  document.getElementById("predictive_path").value = values.predictive_path || "";
  document.getElementById("api_key").value = values.api_key || "";
  document.getElementById("admin_api_key").value = values.admin_api_key || "";
  document.getElementById("allow_anonymous").checked = Boolean(values.allow_anonymous);
  document.getElementById("license_public_key_path").value = values.license_public_key_path || "";
  document.getElementById("license_public_key").value = values.license_public_key || "";
  document.getElementById("license_algorithm").value = values.license_algorithm || "";
  document.getElementById("license_revoked_jtis").value = (values.license_revoked_jtis || []).join("\n");
  document.getElementById("license_revoked_subjects").value = (values.license_revoked_subjects || []).join("\n");
  document.getElementById("max_upload_bytes").value = values.max_upload_bytes ?? "";
  document.getElementById("max_text_length").value = values.max_text_length ?? "";
  document.getElementById("max_feature_fields").value = values.max_feature_fields ?? "";
  document.getElementById("max_json_body_bytes").value = values.max_json_body_bytes ?? "";
  document.getElementById("rate_limit_per_minute").value = values.rate_limit_per_minute ?? "";
  document.getElementById("rate_limit_burst").value = values.rate_limit_burst ?? "";

  const corsLines = (values.cors_trusted_origins || []).map((entry) =>
    entry.allow_credentials ? `${entry.origin}|true` : entry.origin,
  );
  document.getElementById("cors_trusted_origins").value = corsLines.join("\n");
}

function buildPayload() {
  clearStatus();
  clearValidationIndicators();
  let failed = false;

  function requiredText(id, label) {
    const value = document.getElementById(id).value.trim();
    if (!value) {
      markFieldError(id, `${label} is required.`);
      failed = true;
    }
    return value;
  }

  const payload = {
    classifier_path: requiredText("classifier_path", "Classifier model path"),
    predictive_path: requiredText("predictive_path", "Predictive model path"),
    api_key: document.getElementById("api_key").value.trim() || null,
    admin_api_key: document.getElementById("admin_api_key").value.trim() || null,
    allow_anonymous: document.getElementById("allow_anonymous").checked,
    license_public_key_path: document.getElementById("license_public_key_path").value.trim() || null,
    license_public_key: document.getElementById("license_public_key").value.trim() || null,
    license_algorithm: document.getElementById("license_algorithm").value.trim().toUpperCase(),
    license_revoked_jtis: parseList("license_revoked_jtis"),
    license_revoked_subjects: parseList("license_revoked_subjects"),
  };

  if (!payload.license_algorithm) {
    markFieldError("license_algorithm", "License algorithm is required.");
    failed = true;
  }

  const maxUpload = readIntField("max_upload_bytes", { required: true });
  const maxText = readIntField("max_text_length", { required: true });
  const maxFeatures = readIntField("max_feature_fields", { required: true });
  const maxJson = readIntField("max_json_body_bytes", { required: false });
  const ratePerMinute = readIntField("rate_limit_per_minute", { required: false });
  const rateBurst = readIntField("rate_limit_burst", { required: false });

  if (!maxUpload.ok || !maxText.ok || !maxFeatures.ok || !maxJson.ok || !ratePerMinute.ok || !rateBurst.ok) {
    failed = true;
  }

  const corsValue = parseCorsOrigins(document.getElementById("cors_trusted_origins").value);
  if (!corsValue.ok) {
    markFieldError("cors_trusted_origins", corsValue.message || "Invalid CORS configuration.");
    failed = true;
  }

  if (failed) {
    return null;
  }

  payload.max_upload_bytes = maxUpload.value;
  payload.max_text_length = maxText.value;
  payload.max_feature_fields = maxFeatures.value;
  payload.max_json_body_bytes = maxJson.value;
  payload.rate_limit_per_minute = ratePerMinute.value;
  payload.rate_limit_burst = rateBurst.value;
  payload.cors_trusted_origins = corsValue.value;

  return payload;
}

async function fetchSettings(showNotification = false) {
  if (!adminToken) {
    setAuthError("Enter the administrative token before loading settings.");
    return;
  }
  clearAuthError();
  setStatus("Loading settings…", "info");
  loadButton.disabled = true;
  if (refreshButton) {
    refreshButton.disabled = true;
  }
  try {
    const response = await fetch("/admin/settings", {
      headers: {
        "X-Admin-Token": adminToken,
        Accept: "application/json",
      },
    });
    if (response.status === 401) {
      settingsCard.classList.add("hidden");
      lastPayload = null;
      setStatus("", "");
      setAuthError("Admin token rejected. Verify the secret and try again.");
      return;
    }
    if (response.status === 503) {
      settingsCard.classList.add("hidden");
      lastPayload = null;
      setStatus("", "");
      setAuthError("Administrative API is not enabled on this deployment.");
      return;
    }
    if (!response.ok) {
      const detail = await response.text();
      setStatus(`Failed to load settings (${response.status}): ${detail}`, "error");
      return;
    }
    const payload = await response.json();
    populateForm(payload.values);
    applyOverrides(payload.overrides);
    settingsCard.classList.remove("hidden");
    updateRememberStorage();
    if (showNotification) {
      setStatus("Settings refreshed.", "success");
    } else {
      setStatus("", "");
    }
  } catch (error) {
    setStatus(`Unable to reach the server: ${error.message}`, "error");
  } finally {
    loadButton.disabled = false;
    if (refreshButton) {
      refreshButton.disabled = false;
    }
  }
}

async function submitSettings(event) {
  event.preventDefault();
  if (!adminToken) {
    setAuthError("Enter the administrative token before saving settings.");
    return;
  }
  const payload = buildPayload();
  if (!payload) {
    return;
  }
  clearAuthError();
  setStatus("Saving changes…", "info");
  const desiredAdminKey = payload.admin_api_key;
  try {
    const response = await fetch("/admin/settings", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": adminToken,
      },
      body: JSON.stringify(payload),
    });
    if (response.status === 401) {
      setStatus("Save failed: admin token rejected.", "error");
      settingsCard.classList.add("hidden");
      setAuthError("Admin token rejected. Verify the secret and try again.");
      return;
    }
    if (!response.ok) {
      const detail = await response.text();
      setStatus(`Save failed (${response.status}): ${detail}`, "error");
      return;
    }
    const data = await response.json();
    populateForm(data.values);
    applyOverrides(data.overrides);
    const effectiveAdminKey =
      (desiredAdminKey && desiredAdminKey.trim()) ||
      (data.values.admin_api_key && data.values.admin_api_key.trim()) ||
      (data.values.api_key && data.values.api_key.trim()) ||
      adminToken;
    if (effectiveAdminKey) {
      adminToken = effectiveAdminKey;
      tokenInput.value = effectiveAdminKey;
    }
    updateRememberStorage();
    setStatus("Settings saved successfully.", "success");
  } catch (error) {
    setStatus(`Save failed: ${error.message}`, "error");
  }
}

function resetForm() {
  if (lastPayload) {
    populateForm(lastPayload);
    applyOverrides(lastOverrides);
    setStatus("Form reset to the last saved values.", "info");
  } else {
    form.reset();
    applyOverrides({});
    clearValidationIndicators();
    setStatus("Form cleared.", "info");
  }
}

loadButton.addEventListener("click", async () => {
  const provided = tokenInput.value.trim();
  if (!provided) {
    setAuthError("Enter the administrative token before loading settings.");
    return;
  }
  adminToken = provided;
  await fetchSettings(true);
});

if (refreshButton) {
  refreshButton.addEventListener("click", () => fetchSettings(true));
}

if (resetButton) {
  resetButton.addEventListener("click", resetForm);
}

form.addEventListener("submit", submitSettings);
rememberToggle.addEventListener("change", updateRememberStorage);

document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible" && lastPayload) {
    applyOverrides(lastOverrides);
  }
});

initializeToken();
