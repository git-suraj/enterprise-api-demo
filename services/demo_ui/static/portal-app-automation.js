(function () {
  const BACKEND_BASE = "http://localhost:8080";
  const ONBOARD_URL = `${BACKEND_BASE}/api/dev-portal/app-automation/onboard-existing`;
  const PENDING_KEY = "portalShowcasePendingApp";
  const LAST_RESULT_KEY = "portalShowcaseLastAppAutomationResult";
  const HANDLED_PREFIX = "portalShowcaseHandledApp:";

  function parseJson(value) {
    try {
      return JSON.parse(value);
    } catch (_error) {
      return null;
    }
  }

  function handledKey(applicationId) {
    return `${HANDLED_PREFIX}${applicationId}`;
  }

  function markHandled(applicationId) {
    window.sessionStorage.setItem(handledKey(applicationId), "1");
  }

  function alreadyHandled(applicationId) {
    return window.sessionStorage.getItem(handledKey(applicationId)) === "1";
  }

  function savePending(application) {
    window.sessionStorage.setItem(
      PENDING_KEY,
      JSON.stringify({
        id: application.id,
        name: application.name || "Application",
        savedAt: Date.now(),
      }),
    );
  }

  function clearPending() {
    window.sessionStorage.removeItem(PENDING_KEY);
  }

  function saveResult(result) {
    window.sessionStorage.setItem(LAST_RESULT_KEY, JSON.stringify(result));
  }

  function readPending() {
    return parseJson(window.sessionStorage.getItem(PENDING_KEY));
  }

  function readResult() {
    return parseJson(window.sessionStorage.getItem(LAST_RESULT_KEY));
  }

  function renderBanner(message, tone) {
    if (!message) {
      return;
    }
    let banner = document.getElementById("portal-showcase-app-automation-banner");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "portal-showcase-app-automation-banner";
      banner.style.position = "fixed";
      banner.style.right = "20px";
      banner.style.bottom = "20px";
      banner.style.maxWidth = "420px";
      banner.style.padding = "14px 16px";
      banner.style.borderRadius = "10px";
      banner.style.boxShadow = "0 12px 30px rgba(0,0,0,0.18)";
      banner.style.zIndex = "9999";
      banner.style.fontFamily = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif";
      banner.style.fontSize = "14px";
      banner.style.lineHeight = "1.45";
      banner.style.border = "1px solid rgba(0,0,0,0.08)";
      document.body.appendChild(banner);
    }

    if (tone === "success") {
      banner.style.background = "#e8fff0";
      banner.style.color = "#114b28";
    } else if (tone === "warning") {
      banner.style.background = "#fff8dd";
      banner.style.color = "#5f4b00";
    } else {
      banner.style.background = "#ffe8e8";
      banner.style.color = "#6f1d1d";
    }

    banner.textContent = message;
  }

  function classifyResult(result) {
    if (!result) {
      return null;
    }
    if (result.status === "ready") {
      return { tone: "success", message: result.message || "Portal app automation completed." };
    }
    if (
      result.status === "consumer_patch_unsupported" ||
      result.status === "patched_after_credentials" ||
      result.status === "managed_create_internal_consumer"
    ) {
      return { tone: "warning", message: result.message || "Portal app automation finished with limitations." };
    }
    if (result.error) {
      return { tone: "error", message: result.error };
    }
    return { tone: "warning", message: result.message || "Portal app automation completed." };
  }

  async function onboardApplication(application) {
    if (!application || !application.id || alreadyHandled(application.id)) {
      return;
    }

    savePending(application);

    try {
      const url = new URL(ONBOARD_URL);
      url.searchParams.set("applicationId", application.id);
      const response = await window.fetch(url.toString(), {
        method: "GET",
        mode: "cors",
        credentials: "omit",
      });
      const payload = await response.json();
      saveResult(payload);

      if (response.ok) {
        markHandled(application.id);
        clearPending();
      }

      const classified = classifyResult(payload);
      if (classified) {
        renderBanner(classified.message, classified.tone);
      }
    } catch (error) {
      const payload = { error: `Portal app automation failed: ${error.message}` };
      saveResult(payload);
      renderBanner(payload.error, "error");
    }
  }

  function maybeHandleCreateResponse(method, url, payload) {
    if (!payload || typeof payload !== "object" || !payload.id) {
      return;
    }
    if (String(method || "").toUpperCase() !== "POST") {
      return;
    }
    if (!/\/applications(?:\?|$)/.test(String(url || ""))) {
      return;
    }
    if (/application_instances|credentials\//.test(String(url || ""))) {
      return;
    }

    onboardApplication(payload);
  }

  function patchFetch() {
    if (typeof window.fetch !== "function") {
      return;
    }
    const originalFetch = window.fetch.bind(window);
    window.fetch = async function patchedFetch(input, init) {
      const response = await originalFetch(input, init);
      try {
        const method = (init && init.method) || "GET";
        const url = typeof input === "string" ? input : input && input.url;
        const contentType = response.headers.get("content-type") || "";
        if (response.ok && contentType.includes("application/json")) {
          const payload = await response.clone().json();
          maybeHandleCreateResponse(method, url, payload);
        }
      } catch (_error) {
        // Best effort only.
      }
      return response;
    };
  }

  function patchXHR() {
    if (!window.XMLHttpRequest) {
      return;
    }
    const originalOpen = window.XMLHttpRequest.prototype.open;
    const originalSend = window.XMLHttpRequest.prototype.send;

    window.XMLHttpRequest.prototype.open = function patchedOpen(method, url) {
      this.__portalShowcaseMethod = method;
      this.__portalShowcaseUrl = url;
      return originalOpen.apply(this, arguments);
    };

    window.XMLHttpRequest.prototype.send = function patchedSend() {
      this.addEventListener("load", function onLoad() {
        try {
          const contentType = this.getResponseHeader("content-type") || "";
          if (this.status >= 200 && this.status < 300 && contentType.includes("application/json")) {
            maybeHandleCreateResponse(
              this.__portalShowcaseMethod,
              this.__portalShowcaseUrl,
              parseJson(this.responseText),
            );
          }
        } catch (_error) {
          // Best effort only.
        }
      });
      return originalSend.apply(this, arguments);
    };
  }

  function resumePending() {
    const pending = readPending();
    if (pending && pending.id && !alreadyHandled(pending.id)) {
      onboardApplication(pending);
      return;
    }

    const lastResult = readResult();
    const classified = classifyResult(lastResult);
    if (classified) {
      renderBanner(classified.message, classified.tone);
    }
  }

  patchFetch();
  patchXHR();

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", resumePending, { once: true });
  } else {
    resumePending();
  }
})();
