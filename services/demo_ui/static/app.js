const state = {
  currentScene: "traffic-routing-header",
  region: "east",
  mode: "anonymous",
  consumer: "consumer-standard",
  identityConsumer: "consumer-1",
  identityToken: "",
  ipPreset: "allowed",
  schemaCase: "valid-request",
  sizeCase: "positive",
  meteringScenario: "demo-bank-1",
  datakitScenario: "fallback",
  datakitFallbackMode: "api1-success",
  injectionSubscene: "query-params",
  transportSecurityCase: "http-blocked",
  versionRoutingMode: "path",
  apiVersion: "v1",
  canaryScenario: "40-rollout",
  canaryHeaderMode: "always",
  canaryConsumer: "consumer-pilot",
  deprecationCase: "deprecated-v1",
  resilienceScenario: "weighted-load-balancing",
  links: { logs: "#", requestAudit: "#", audit: "#", trace: "#" },
  scenes: {},
  credentials: [],
  lastRun: null,
  countdownTimer: null,
  countdownEndsAtMs: null,
  resilienceInstances: {},
  onboardingJob: null,
  onboardingPollTimer: null,
};

const SCENE_DEFAULTS = {
  "traffic-routing-header": {
    controlTitle: "Request Builder",
    emptyText: "Run the scene to see the Kong request path, route match, backend selection, and response.",
  },
  "traffic-control-rate-limiting": {
    controlTitle: "Traffic Policy Builder",
    emptyText: "Run the scene to see the Kong rate-limiting policy, per-request decisions, and 429 enforcement point.",
  },
  "resilience-failover-health-checks": {
    controlTitle: "Resilience Controls",
    emptyText: "Run the scene to see weighted distribution, target health state, failover, and recovery through Kong.",
  },
  "identity-azure-token-validation": {
    controlTitle: "Identity Controls",
    emptyText: "Generate an Azure AD token, edit it if needed, decode it, and send it through Kong for validation.",
  },
  "identity-keycloak-authorization": {
    controlTitle: "Identity Controls",
    emptyText: "Generate a Keycloak token for the selected consumer, decode it, and send it through Kong for authorization.",
  },
  "network-policy-ip-allow-deny": {
    controlTitle: "Network Policy Controls",
    emptyText: "Run the scene to see Kong evaluate the forwarded client IP and either proxy or block the request.",
  },
  "data-quality-schema-validation": {
    controlTitle: "Validation Controls",
    emptyText: "Run the scene to see Kong validate the request schema before the upstream is reached.",
  },
  "traffic-control-request-size-limiting": {
    controlTitle: "Payload Controls",
    emptyText: "Run the scene to see Kong enforce the request payload size limit before proxying.",
  },
  "monetization-metering-billing": {
    controlTitle: "Monetization Controls",
    emptyText: "Run the scene to see Kong emit a usage event for the selected authenticated consumer on the single metered route.",
  },
  "datakit-plugin-orchestration": {
    controlTitle: "DataKit Controls",
    emptyText: "Run the scene to see Keycloak-protected Datakit orchestration: conditional fallback, account correlation, or Redis-backed caching with a 30-second TTL.",
  },
  "transformation-gateway-payload-encryption": {
    controlTitle: "Transformation Controls",
    emptyText: "Run the scene to see Kong decrypt the inbound request envelope, proxy plaintext upstream, and return an encrypted response envelope.",
  },
  "security-injection-protection": {
    controlTitle: "Injection Controls",
    emptyText: "Run the scene to see Kong inspect the selected request location and block malicious patterns.",
  },
  "transport-security-http-enforcement": {
    controlTitle: "Transport Controls",
    emptyText: "Run the scene to see Kong reject plain HTTP or issue an HTTPS redirect before the upstream is reached.",
  },
  "api-lifecycle-versioned-routing": {
    controlTitle: "Lifecycle Controls",
    emptyText: "Run the scene to see Kong route requests to v1 or v2 using path-based or header-based version matching.",
  },
  "api-lifecycle-canary-migration": {
    controlTitle: "Canary Controls",
    emptyText: "Run the scene to see Kong shift traffic from v1 to v2 using percentage, time, header override, or consumer-aware canary policy.",
  },
  "api-lifecycle-deprecation": {
    controlTitle: "Deprecation Controls",
    emptyText: "Run the scene to see Kong signal v1 deprecation headers or enforce the sunset policy.",
  },
};

const elements = {
  sceneSelect: document.getElementById("sceneSelect"),
  scenePicker: document.getElementById("scenePicker"),
  scenePickerTrigger: document.getElementById("scenePickerTrigger"),
  scenePickerCurrent: document.getElementById("scenePickerCurrent"),
  sceneMenu: document.getElementById("sceneMenu"),
  sceneTitle: document.getElementById("sceneTitle"),
  controlPanelTitle: document.getElementById("controlPanelTitle"),
  runScenarioButton: document.getElementById("runScenarioButton"),
  onboardApiButton: document.getElementById("onboardApiButton"),
  resetSceneButton: document.getElementById("resetSceneButton"),
  viewCredentialsButton: document.getElementById("viewCredentialsButton"),
  resetPanelButton: document.getElementById("resetPanelButton"),
  viewArchitectureButton: document.getElementById("viewArchitectureButton"),
  viewTraceButton: document.getElementById("viewTraceButton"),
  viewLogsButton: document.getElementById("viewLogsButton"),
  viewRequestAuditButton: document.getElementById("viewRequestAuditButton"),
  consoleDetailButton: document.getElementById("consoleDetailButton"),
  architectureModal: document.getElementById("architectureModal"),
  closeArchitectureButton: document.getElementById("closeArchitectureButton"),
  sceneDetailsModal: document.getElementById("sceneDetailsModal"),
  closeSceneDetailsButton: document.getElementById("closeSceneDetailsButton"),
  sceneDetailsContent: document.getElementById("sceneDetailsContent"),
  detailViewModal: document.getElementById("detailViewModal"),
  closeDetailViewButton: document.getElementById("closeDetailViewButton"),
  detailMeta: document.getElementById("detailMeta"),
  detailSteps: document.getElementById("detailSteps"),
  credentialsModal: document.getElementById("credentialsModal"),
  closeCredentialsButton: document.getElementById("closeCredentialsButton"),
  credentialsContent: document.getElementById("credentialsContent"),
  onboardApiModal: document.getElementById("onboardApiModal"),
  closeOnboardApiButton: document.getElementById("closeOnboardApiButton"),
  onboardApiStatus: document.getElementById("onboardApiStatus"),
  onboardApiCurrentCommand: document.getElementById("onboardApiCurrentCommand"),
  onboardApiCommandList: document.getElementById("onboardApiCommandList"),
  onboardApiLogs: document.getElementById("onboardApiLogs"),
  onboardApiKeyInput: document.getElementById("onboardApiKeyInput"),
  testOnboardedApiButton: document.getElementById("testOnboardedApiButton"),
  onboardApiCurl: document.getElementById("onboardApiCurl"),
  onboardApiResponse: document.getElementById("onboardApiResponse"),
  requestPreviewGrid: document.getElementById("requestPreviewGrid"),
  expectedOutcome: document.getElementById("expectedOutcome"),
  consoleOutput: document.getElementById("consoleOutput"),
  statusKong: document.getElementById("statusKong"),
  statusRoute: document.getElementById("statusRoute"),
  topologyGrid: document.querySelector(".topology-grid"),
  headerRoutingControls: document.getElementById("headerRoutingControls"),
  rateModeControls: document.getElementById("rateModeControls"),
  rateConsumerControls: document.getElementById("rateConsumerControls"),
  rateCounterControls: document.getElementById("rateCounterControls"),
  resilienceScenarioControls: document.getElementById("resilienceScenarioControls"),
  resilienceInstanceControls: document.getElementById("resilienceInstanceControls"),
  identityConsumerControls: document.getElementById("identityConsumerControls"),
  identityTokenControls: document.getElementById("identityTokenControls"),
  identityJwtControls: document.getElementById("identityJwtControls"),
  ipPresetControls: document.getElementById("ipPresetControls"),
  schemaCaseControls: document.getElementById("schemaCaseControls"),
  sizeCaseControls: document.getElementById("sizeCaseControls"),
  meteringScenarioControls: document.getElementById("meteringScenarioControls"),
  datakitScenarioControls: document.getElementById("datakitScenarioControls"),
  datakitFallbackModeControls: document.getElementById("datakitFallbackModeControls"),
  injectionSubsceneControls: document.getElementById("injectionSubsceneControls"),
  transportSecurityCaseControls: document.getElementById("transportSecurityCaseControls"),
  versionRoutingModeControls: document.getElementById("versionRoutingModeControls"),
  versionRoutingVersionControls: document.getElementById("versionRoutingVersionControls"),
  canaryScenarioControls: document.getElementById("canaryScenarioControls"),
  canaryHeaderControls: document.getElementById("canaryHeaderControls"),
  canaryConsumerControls: document.getElementById("canaryConsumerControls"),
  deprecationCaseControls: document.getElementById("deprecationCaseControls"),
  tokenEditor: document.getElementById("tokenEditor"),
  generateTokenButton: document.getElementById("generateTokenButton"),
  decodeTokenButton: document.getElementById("decodeTokenButton"),
  decodedJwtOutput: document.getElementById("decodedJwtOutput"),
  instance1Status: document.getElementById("instance1Status"),
  instance2Status: document.getElementById("instance2Status"),
  clientNodeLabel: document.getElementById("clientNodeLabel"),
  clientNodeTitle: document.getElementById("clientNodeTitle"),
  clientNodeSubtitle: document.getElementById("clientNodeSubtitle"),
  kongNodeLabel: document.getElementById("kongNodeLabel"),
  kongNodeTitle: document.getElementById("kongNodeTitle"),
  kongNodeSubtitle: document.getElementById("kongNodeSubtitle"),
  eastNodeLabel: document.getElementById("eastNodeLabel"),
  eastNodeTitle: document.getElementById("eastNodeTitle"),
  eastNodeSubtitle: document.getElementById("eastNodeSubtitle"),
  westNodeLabel: document.getElementById("westNodeLabel"),
  westNodeTitle: document.getElementById("westNodeTitle"),
  westNodeSubtitle: document.getElementById("westNodeSubtitle"),
};

const regionButtons = Array.from(document.querySelectorAll("[data-region]"));
const modeButtons = Array.from(document.querySelectorAll("[data-mode]"));
const consumerButtons = Array.from(document.querySelectorAll("[data-consumer]"));
const identityConsumerButtons = Array.from(document.querySelectorAll("[data-identity-consumer]"));
const resilienceScenarioButtons = Array.from(document.querySelectorAll("[data-resilience-scenario]"));
const ipPresetButtons = Array.from(document.querySelectorAll("[data-ip-preset]"));
const schemaCaseButtons = Array.from(document.querySelectorAll("[data-schema-case]"));
const sizeCaseButtons = Array.from(document.querySelectorAll("[data-size-case]"));
const meteringScenarioButtons = Array.from(document.querySelectorAll("[data-metering-scenario]"));
const datakitScenarioButtons = Array.from(document.querySelectorAll("[data-datakit-scenario]"));
const datakitFallbackModeButtons = Array.from(document.querySelectorAll("[data-datakit-fallback-mode]"));
const injectionSubsceneButtons = Array.from(document.querySelectorAll("[data-injection-subscene]"));
const transportSecurityCaseButtons = Array.from(document.querySelectorAll("[data-transport-security-case]"));
const versionRoutingModeButtons = Array.from(document.querySelectorAll("[data-version-routing-mode]"));
const apiVersionButtons = Array.from(document.querySelectorAll("[data-api-version]"));
const canaryScenarioButtons = Array.from(document.querySelectorAll("[data-canary-scenario]"));
const canaryHeaderModeButtons = Array.from(document.querySelectorAll("[data-canary-header-mode]"));
const canaryConsumerButtons = Array.from(document.querySelectorAll("[data-canary-consumer]"));
const deprecationCaseButtons = Array.from(document.querySelectorAll("[data-deprecation-case]"));
const instanceActionButtons = Array.from(document.querySelectorAll("[data-instance-action]"));
const nodes = {
  client: document.querySelector('[data-node="client"]'),
  kong: document.querySelector('[data-node="kong"]'),
  east: document.querySelector('[data-node="east"]'),
  west: document.querySelector('[data-node="west"]'),
};

const connectors = {
  clientKong: document.querySelector('[data-connector="client-kong"]'),
  kongEast: document.querySelector('[data-connector="kong-east"]'),
  kongWest: document.querySelector('[data-connector="kong-west"]'),
};

function currentSceneDetails() {
  return state.scenes[state.currentScene] || { title: "Scene", services: [], routes: [], plugins: [] };
}

function setActiveButton(buttons, key, value) {
  for (const button of buttons) {
    button.classList.toggle("active", button.dataset[key] === value);
  }
}

function renderRows(container, rows) {
  container.innerHTML = rows
    .map(
      ([label, value]) => `
        <div class="preview-row">
          <span>${label}</span>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

function computePreviewRows() {
  if (state.currentScene === "network-policy-ip-allow-deny") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/network/ip"],
      [
        "Source IP",
        state.ipPreset === "allowed" ? "10.10.10.8" : state.ipPreset === "denied" ? "10.10.10.66" : "203.0.113.25",
      ],
      ["Policy Preset", state.ipPreset],
    ];
  }
  if (state.currentScene === "data-quality-schema-validation") {
    return [
      ["Method", "POST"],
      ["Path", "/orders/validate/schema"],
      ["Validation Case", state.schemaCase.replaceAll("-", " ")],
      ["Contract", "body + query + header"],
    ];
  }
  if (state.currentScene === "traffic-control-request-size-limiting") {
    return [
      ["Method", "POST"],
      ["Path", "/orders/limits/request-size"],
      ["Case", state.sizeCase === "positive" ? "does not exceed limit" : "exceeds limit"],
      ["Payload Policy", "2 KB max"],
    ];
  }
  if (state.currentScene === "monetization-metering-billing") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/metering/consumer"],
      ["Demo Consumer", state.meteringScenario],
      ["Billable Subject", `Kong Consumer -> ${state.meteringScenario}`],
      ["Policy", "subject = Kong Consumer"],
    ];
  }
  if (state.currentScene === "datakit-plugin-orchestration") {
    if (state.datakitScenario === "fallback") {
      return [
        ["Method", "GET"],
        ["Path", "/orders/datakit/fallback"],
        ["Branch", state.datakitFallbackMode === "api1-success" ? "API1 returns 200" : "API1 returns non-200"],
        ["Auth", "Keycloak JWT + x-authenticated-role"],
      ];
    }
    if (state.datakitScenario === "combine") {
      return [
        ["Method", "GET"],
        ["Path", "/orders/datakit/combine"],
        ["Join", "API1 list + API2 details"],
        ["Join Key", "accountId"],
      ];
    }
    return [
      ["Method", "GET"],
      ["Path", "/orders/datakit/cache"],
      ["Cache Backend", "Redis via DataKit"],
      ["Cache TTL", "30 seconds"],
    ];
  }
  if (state.currentScene === "transformation-gateway-payload-encryption") {
    return [
      ["Method", "POST"],
      ["Path", "/orders/security/payload-crypto"],
      ["Request Format", "encrypted session key + IV + payload"],
      ["Response Format", "encrypted session key + IV + payload"],
    ];
  }
  if (state.currentScene === "security-injection-protection") {
    return [
      ["Method", state.injectionSubscene === "body" ? "POST" : "GET"],
      [
        "Path",
        state.injectionSubscene === "query-params"
          ? "/orders/security/injection/query"
          : state.injectionSubscene === "body"
            ? "/orders/security/injection/body"
            : "/orders/security/injection/headers",
      ],
      ["Inspection", state.injectionSubscene.replaceAll("-", " ")],
      ["Pattern", "sql injection"],
    ];
  }
  if (state.currentScene === "transport-security-http-enforcement") {
    return [
      ["Method", "GET"],
      ["Path", state.transportSecurityCase === "http-blocked" ? "/orders/transport/http-blocked" : "/orders/transport/http-redirect"],
      ["Transport Case", state.transportSecurityCase === "http-blocked" ? "http blocked" : "http to https redirect"],
      ["Entry Protocol", "http"],
    ];
  }
  if (state.currentScene === "api-lifecycle-versioned-routing") {
    return [
      ["Method", "GET"],
      ["Routing Mode", state.versionRoutingMode],
      [
        "Path",
        state.versionRoutingMode === "path"
          ? state.apiVersion === "v1"
            ? "/api/v1/orders"
            : "/api/v2/orders"
          : "/orders/version/header",
      ],
      ["Version", state.apiVersion],
    ];
  }
  if (state.currentScene === "api-lifecycle-canary-migration") {
    return [
      ["Method", "GET"],
      ["Scenario", state.canaryScenario.replaceAll("-", " ")],
      [
        "Input",
        state.canaryScenario === "header-based"
          ? `x-canary-version: ${state.canaryHeaderMode}`
          : state.canaryScenario === "consumer-based"
            ? state.canaryConsumer
            : state.canaryScenario === "time-based"
              ? "2 minute rollout window"
              : "40 percent rollout",
      ],
      ["Target", "v1 primary / v2 canary"],
    ];
  }
  if (state.currentScene === "api-lifecycle-deprecation") {
    return [
      ["Method", "GET"],
      [
        "Path",
        state.deprecationCase === "deprecated-v1"
          ? "/orders/deprecation/v1"
          : state.deprecationCase === "current-v2"
            ? "/orders/deprecation/v2"
            : "/orders/deprecation/v1/sunset",
      ],
      ["Scenario", state.deprecationCase.replaceAll("-", " ")],
      ["Policy", state.deprecationCase === "sunset-enforced" ? "enforcement" : "headers"],
    ];
  }
  if (state.currentScene === "traffic-control-rate-limiting") {
    return [
      ["Method", "GET"],
      ["Path", state.mode === "anonymous" ? "/orders/rate/anonymous" : "/orders/rate/consumer"],
      ["Mode", state.mode],
      ["Consumer", state.mode === "consumer" ? state.consumer : "none"],
      ["Window", "30-second fixed"],
    ];
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    return [
      ["Method", "GET"],
      [
        "Path",
        state.resilienceScenario === "weighted-load-balancing"
          ? "/orders/resilience/weighted"
          : "/orders/resilience/circuit-breaker",
      ],
      [
        "Scenario",
        state.resilienceScenario === "weighted-load-balancing" ? "Weighted Load Balancing" : "Circuit Breaker",
      ],
      [
        "Strategy",
        state.resilienceScenario === "weighted-load-balancing"
          ? "30:70 weighted"
          : "Round robin with active + passive health checks",
      ],
    ];
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/auth/azure"],
      ["Identity Provider", "Azure AD"],
      ["Consumer", state.identityConsumer],
      ["Audience", "Protected API token validation"],
    ];
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return [
      ["Method", "GET"],
      ["Path", "/orders/auth/keycloak"],
      ["Identity Provider", "Keycloak"],
      ["Consumer", state.identityConsumer],
    ];
  }
  return [
    ["Method", "GET"],
    ["Path", "/orders"],
    ["Header", state.region === "missing" ? "x-region: <missing>" : `x-region: ${state.region}`],
  ];
}

function computeExpectedOutcome() {
  if (state.currentScene === "network-policy-ip-allow-deny") {
    return state.ipPreset === "allowed"
      ? "Kong should allow the forwarded client IP because it matches the route-level allow list, so the request reaches the protected API."
      : state.ipPreset === "denied"
        ? "Kong should block the forwarded client IP because it matches the route-level deny list. Enforcement happens at the gateway before any upstream call."
        : "Kong should block the client IP because it is not present in the configured allow list. The protected API should remain untouched.";
  }
  if (state.currentScene === "data-quality-schema-validation") {
    return state.schemaCase === "valid-request"
      ? "Kong should accept the request because the body schema, query contract, required header, and allowed Content-Type all satisfy the request-validator policy."
      : state.schemaCase === "invalid-body"
        ? "Kong should reject the request because the JSON body violates the configured schema before the request reaches the protected API."
        : state.schemaCase === "invalid-query-param"
          ? "Kong should reject the request because the query parameter contract fails validation at the request-validator policy."
          : "Kong should reject the request because the required header or Content-Type does not satisfy the configured request-validator policy.";
  }
  if (state.currentScene === "traffic-control-request-size-limiting") {
    return state.sizeCase === "positive"
      ? "Kong should forward the request because the payload stays within the configured 2 KB request-size-limiting threshold."
      : "Kong should reject the request because the body exceeds the configured 2 KB request-size-limiting threshold before the protected API is reached.";
  }
  if (state.currentScene === "monetization-metering-billing") {
    return `Kong should emit one usage event per authenticated request and set the billable subject to the resolved Kong Consumer. In this run, subject = Kong Consumer and the billable value is ${state.meteringScenario}.`;
  }
  if (state.currentScene === "datakit-plugin-orchestration") {
    if (state.datakitScenario === "fallback") {
      return "Kong should validate the Keycloak bearer token first. Datakit should return API1 when API1 returns 200, and should call API2 only when API1 returns a non-200 response.";
    }
    if (state.datakitScenario === "combine") {
      return "Kong should validate the Keycloak bearer token first. Datakit should call API1 for the account list, call API2 for detail records, and join the two payloads on accountId before returning the composed response.";
    }
    return "Kong should validate the Keycloak bearer token first. Datakit should read Redis-backed cache, populate it on a miss, and serve the cached payload for the full 30-second TTL window.";
  }
  if (state.currentScene === "transformation-gateway-payload-encryption") {
    return "Kong should decrypt the inbound request envelope at the custom plugin using the gateway private key, forward plaintext upstream, then encrypt the upstream response with a new AES session key before returning it to the client.";
  }
  if (state.currentScene === "security-injection-protection") {
    return state.injectionSubscene === "query-params"
      ? "Kong should inspect query parameters with the Injection Protection plugin and block requests that match the configured SQL-style pattern set."
      : state.injectionSubscene === "body"
        ? "Kong should inspect the request body with the Injection Protection plugin and block the request before any upstream call if a malicious pattern is detected."
        : "Kong should inspect request headers with the Injection Protection plugin and reject the request when a configured injection pattern is present.";
  }
  if (state.currentScene === "transport-security-http-enforcement") {
    return state.transportSecurityCase === "http-blocked"
      ? "Kong should reject the plain HTTP request with the route-level HTTPS enforcement policy and return HTTP 426 without forwarding to the protected API."
      : "Kong should return HTTP 308 with a Location header that points the caller to HTTPS. The demo then follows that Location and shows the successful HTTPS call separately.";
  }
  if (state.currentScene === "api-lifecycle-versioned-routing") {
    return state.versionRoutingMode === "path"
      ? `Kong should match the ${state.apiVersion} path route directly and send the request to the ${state.apiVersion} upstream service.`
      : `Kong should keep the shared path and route to ${state.apiVersion} by evaluating the x-api-version header.`;
  }
  if (state.currentScene === "api-lifecycle-canary-migration") {
    if (state.canaryScenario === "header-based") {
      return "Kong should use the canary override header policy. x-canary-version=always forces the request to v2, while x-canary-version=never forces it to stay on v1.";
    }
    if (state.canaryScenario === "consumer-based") {
      return "Kong should authenticate the consumer, evaluate ACL-aware canary policy, and send consumer-pilot to v2 while consumer-standard-lifecycle remains on v1.";
    }
    return state.canaryScenario === "time-based"
      ? "Kong should gradually shift traffic from v1 to v2 across the configured 2-minute rollout window. With duration=120s and steps=20, the rollout advances in 5% increments every 6 seconds."
      : "Kong should apply a fixed 40% canary split on this route, so roughly 40% of requests reach v2 while the rest stay on the v1 primary service. The service counters show the observed distribution.";
  }
  if (state.currentScene === "api-lifecycle-deprecation") {
    return state.deprecationCase === "deprecated-v1"
      ? "Kong should still allow v1 traffic but attach deprecation, sunset, and successor-version headers so clients can see that v1 is in retirement mode."
      : state.deprecationCase === "current-v2"
        ? "Kong should return the current v2 response normally with no deprecation signaling because this route is the active version."
        : "Kong should enforce the sunset policy at the gateway and block deprecated v1 before the upstream is reached.";
  }
  if (state.currentScene === "traffic-control-rate-limiting") {
    if (state.mode === "anonymous") {
      return "Kong should apply the anonymous fixed-window rate limit at the service level: requests 1-20 pass within 30 seconds, and request 21 returns HTTP 429.";
    }
    return state.consumer === "consumer-gold"
      ? "Kong should authenticate consumer-gold and apply the consumer-scoped fixed-window policy: requests 1-10 pass in 30 seconds, and request 11 returns HTTP 429."
      : "Kong should authenticate consumer-standard and apply the stricter consumer-scoped fixed-window policy: requests 1-5 pass in 30 seconds, and request 6 returns HTTP 429.";
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    return state.resilienceScenario === "weighted-load-balancing"
      ? "Kong should distribute traffic across both healthy targets using the configured 30:70 upstream weights, so instance 2 should receive more requests than instance 1 over time."
      : "Kong should use active and passive health checks to remove an unhealthy target from the round-robin pool and fail over to the remaining healthy instance.";
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return `Kong should validate the Azure AD bearer token with the openid-connect plugin, map the appid claim to the Kong Consumer, and only forward valid requests for ${state.identityConsumer}.`;
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return state.identityConsumer === "consumer-1"
      ? "Kong should validate the Keycloak token, map the azp claim to the Kong Consumer, and authorize consumer-1 because its service account token contains the required role."
      : "Kong should validate the Keycloak token but reject consumer-2 at the authorization policy because its service account token does not contain the required role.";
  }
  if (state.region === "missing") {
    return "Kong should match the catch-all route and apply the request-termination policy because the required x-region header is missing.";
  }
  return state.region === "east"
    ? "Kong should evaluate x-region=east and route the request to svc-orders-header-east."
    : "Kong should evaluate x-region=west and route the request to svc-orders-header-west.";
}

function defaultTopologyForScene() {
  if (state.currentScene === "network-policy-ip-allow-deny") {
    return {
      labels: {
        client: ["Client", "IP Caller", state.ipPreset],
        kong: ["Gateway", "Kong Data Plane", "IP restriction policy"],
        east: ["Protected API", "Orders API", "Awaiting policy decision"],
        west: ["Network Policy", "Allow + Deny List", "Awaiting evaluation"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "data-quality-schema-validation") {
    return {
      labels: {
        client: ["Client", "Schema Caller", state.schemaCase.replaceAll("-", " ")],
        kong: ["Gateway", "Kong Data Plane", "Request validator"],
        east: ["Protected API", "Orders API", "Awaiting validation"],
        west: ["Schema Policy", "Body + Query + Headers", "Awaiting evaluation"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "traffic-control-request-size-limiting") {
    return {
      labels: {
        client: [
          "Client",
          "Payload Caller",
          state.sizeCase === "positive" ? "does not exceed limit" : "exceeds limit",
        ],
        kong: ["Gateway", "Kong Data Plane", "2 KB request size limit"],
        east: ["Protected API", "Orders API", "Awaiting size check"],
        west: ["Payload Policy", "Request Size Limit", "Awaiting evaluation"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "monetization-metering-billing") {
    return {
      labels: {
        client: ["Client", "Billable Caller", state.meteringScenario],
        kong: ["Gateway", "Kong Data Plane", "Usage metering plugin"],
        east: ["Protected API", "Orders API", "Awaiting metered request"],
        west: ["Usage Event", state.meteringScenario, "Awaiting event"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "datakit-plugin-orchestration") {
    return {
      labels: {
        client: ["Client", "Keycloak Authenticated Caller", "consumer-1"],
        kong: ["Gateway", "Kong Data Plane", `DataKit ${state.datakitScenario}`],
        east: [
          "API1",
          "Primary Upstream",
          state.datakitScenario === "combine" ? "account list" : state.datakitScenario === "cache" ? "cache source" : "primary decision",
        ],
        west: [
          state.datakitScenario === "cache" ? "Redis Cache" : "API2",
          state.datakitScenario === "cache" ? "DataKit cache store" : "Secondary Upstream",
          state.datakitScenario === "combine"
            ? "detail records"
            : state.datakitScenario === "cache"
              ? "TTL 30 seconds"
              : "fallback target",
        ],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "transformation-gateway-payload-encryption") {
    return {
      labels: {
        client: ["Client", "Encrypted Caller", "encrypted session key + IV + payload"],
        kong: ["Gateway", "Kong Data Plane", "decrypt request + encrypt response"],
        east: ["Upstream", "Orders API", "awaiting plaintext request"],
        west: ["Crypto Policy", "payload-crypto-demo", "AES/CBC/PKCS5Padding"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "security-injection-protection") {
    return {
      labels: {
        client: ["Client", "Injection Caller", state.injectionSubscene.replaceAll("-", " ")],
        kong: ["Gateway", "Kong Data Plane", "Injection protection"],
        east: ["Protected API", "Orders API", "Awaiting inspection"],
        west: ["Inspection Policy", state.injectionSubscene.replaceAll("-", " "), "Awaiting scan"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "transport-security-http-enforcement") {
    return {
      labels: {
        client: ["Client", "HTTP Caller", "plain HTTP attempt"],
        kong: ["Gateway", "Kong Data Plane", "transport security policy"],
        east: ["Protected API", "Orders API", "Not reached"],
        west: ["TLS Policy", "HTTPS Enforcement", state.transportSecurityCase === "http-blocked" ? "blocked" : "redirected"],
      },
      nodes: { west: "static" },
    };
  }
  if (state.currentScene === "api-lifecycle-versioned-routing") {
    return {
      labels: {
        client: ["Client", "Versioned Caller", `${state.versionRoutingMode} routing`],
        kong: ["Gateway", "Kong Data Plane", "version-aware routes"],
        east: ["API Version", "Orders API v1", "deprecated but active"],
        west: ["API Version", "Orders API v2", "current release"],
      },
    };
  }
  if (state.currentScene === "api-lifecycle-canary-migration") {
    return {
      labels: {
        client: ["Client", "Migration Caller", state.canaryScenario.replaceAll("-", " ")],
        kong: ["Gateway", "Kong Data Plane", "Canary Release plugin"],
        east: ["Primary", "Orders API v1", "stable baseline"],
        west: ["Canary", "Orders API v2", "migration target"],
      },
    };
  }
  if (state.currentScene === "api-lifecycle-deprecation") {
    return {
      labels: {
        client: ["Client", "Lifecycle Caller", state.deprecationCase.replaceAll("-", " ")],
        kong: ["Gateway", "Kong Data Plane", "deprecation and sunset policy"],
        east: ["Deprecated", "Orders API v1", "deprecated lifecycle"],
        west: ["Current", "Orders API v2", "preferred successor"],
      },
    };
  }
  if (state.currentScene === "traffic-control-rate-limiting") {
    return {
      labels: {
        client: ["Client", "API Caller", `Mode: ${state.mode}`],
        kong: ["Gateway", "Kong Data Plane", "Rate-limiting enforcement"],
        east: ["Backend", "Orders API", "Allowed: pending"],
        west: ["Policy Window", "Fixed Window Counter", "Request pending"],
      },
      nodes: {
        west: "static",
      },
      connectors: {
        kongWest: "hidden",
      },
    };
  }
  if (state.currentScene === "resilience-failover-health-checks") {
    const instance1Running = state.resilienceInstances["instance-1"]?.running ?? true;
    const instance2Running = state.resilienceInstances["instance-2"]?.running ?? true;
    return {
      labels: {
        client: ["Client", "API Caller", "GET resilience route"],
        kong: [
          "Gateway",
          "Kong Data Plane",
          state.resilienceScenario === "weighted-load-balancing" ? "30:70 weighted" : "Round robin + health checks",
        ],
        east: ["Target", "Service Instance 1", instance1Running ? "Healthy" : "Unhealthy"],
        west: ["Target", "Service Instance 2", instance2Running ? "Healthy" : "Unhealthy"],
      },
      nodes: {
        east: instance1Running ? null : "error",
        west: instance2Running ? null : "error",
      },
    };
  }
  if (state.currentScene === "identity-azure-token-validation") {
    return {
      labels: {
        client: ["Client", "Token Caller", "Bearer token supplied"],
        kong: ["Gateway", "Kong Data Plane", "openid-connect validation"],
        east: ["Protected API", "Orders API", "Awaiting validated request"],
        west: ["Identity Provider", "Azure AD", "Awaiting validation"],
      },
    };
  }
  if (state.currentScene === "identity-keycloak-authorization") {
    return {
      labels: {
        client: ["Client", state.identityConsumer, "Bearer token supplied"],
        kong: ["Gateway", "Kong Data Plane", "openid-connect + roles"],
        east: ["Protected API", "Orders API", "Awaiting authorization"],
        west: ["Identity Provider", "Keycloak", "Awaiting validation"],
      },
    };
  }
  return {
    labels: {
      client: ["Client", "Web Caller", "GET /orders"],
      kong: ["Gateway", "Kong Data Plane", "Header routing policy"],
      east: ["Upstream", "Orders East", "x-region: east"],
      west: ["Upstream", "Orders West", "x-region: west"],
    },
  };
}

function updateStaticPreview() {
  renderRows(elements.requestPreviewGrid, computePreviewRows());
  elements.expectedOutcome.textContent = computeExpectedOutcome();
}

function pendingPreviewRows() {
  return updateRowsValue(computePreviewRows(), "Method", `${computePreviewRows()[0]?.[1] || "Request"} (sending)`);
}

function renderPendingDetailView() {
  elements.detailMeta.innerHTML = `
    <div class="entity-block">
      <p class="label">Execution</p>
      <strong>Scenario request in progress</strong>
    </div>
    <div class="entity-block">
      <p class="label">Scene</p>
      <strong>${escapeHtml(currentSceneDetails().title || "Scenario")}</strong>
    </div>
  `;
  elements.detailSteps.innerHTML = `
    <section class="detail-step">
      <div class="detail-step-header">
        <p class="label">Step 1</p>
        <strong>Gateway evaluation</strong>
      </div>
      <div class="detail-step-grid">
        <div class="detail-pane">
          <p class="label">Command</p>
          <pre class="detail-pre">${escapeHtml("Submitting request to Kong gateway...")}</pre>
        </div>
        <div class="detail-pane">
          <p class="label">Response</p>
          <pre class="detail-pre">${escapeHtml("Waiting for Kong response and topology details...")}</pre>
        </div>
      </div>
    </section>
  `;
}

function waitForNextPaint() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(resolve);
    });
  });
}

function resetTopology() {
  for (const node of Object.values(nodes)) {
    node.classList.remove("active", "error", "static");
  }
  for (const connector of Object.values(connectors)) {
    connector.classList.remove("active", "error", "hidden");
  }
}

function stopCountdown() {
  if (state.countdownTimer) {
    clearInterval(state.countdownTimer);
    state.countdownTimer = null;
  }
  state.countdownEndsAtMs = null;
}

function resetView() {
  stopCountdown();
  state.lastRun = null;
  elements.consoleDetailButton.disabled = true;
  elements.consoleOutput.innerHTML = `
    <div class="console-empty console-empty-wide">
      <p>${SCENE_DEFAULTS[state.currentScene].emptyText}</p>
    </div>
  `;
  elements.statusKong.className = "status-pill neutral";
  elements.statusKong.textContent = "Kong Waiting";
  elements.statusRoute.className = "status-pill neutral";
  elements.statusRoute.textContent = "Route Pending";
  resetTopology();
  renderTopology({ ...defaultTopologyForScene(), statusKong: "Kong Waiting", statusKongClass: "neutral", statusRoute: "Route Pending", statusRouteClass: "neutral" });
  updateStaticPreview();
}

function prepareScenarioRun() {
  stopCountdown();
  state.lastRun = null;
  elements.consoleDetailButton.disabled = true;
}

function showScenarioPending() {
  const baseTopology = defaultTopologyForScene();
  const pendingRows = pendingPreviewRows();
  const pathRow = pendingRows.find(([label]) => label === "Path");
  const topology = {
    ...baseTopology,
    statusKong: "Kong Evaluating",
    statusKongClass: "success",
    statusRoute: "Scenario Running",
    statusRouteClass: "neutral",
    nodes: {
      ...(baseTopology.nodes || {}),
      client: "active",
      kong: "active",
      east: baseTopology.nodes?.east === "static" ? "static" : null,
      west: baseTopology.nodes?.west === "static" ? "static" : null,
    },
    connectors: {
      ...(baseTopology.connectors || {}),
      clientKong: "active",
      kongEast: baseTopology.connectors?.kongEast === "hidden" ? "hidden" : null,
      kongWest: baseTopology.connectors?.kongWest === "hidden" ? "hidden" : null,
    },
  };

  if (topology.labels?.client) {
    topology.labels.client = [
      topology.labels.client[0],
      topology.labels.client[1],
      pathRow ? pathRow[1] : "Request sending",
    ];
  }
  if (topology.labels?.kong) {
    topology.labels.kong = [
      topology.labels.kong[0],
      topology.labels.kong[1],
      "Evaluating request at gateway",
    ];
  }
  if (topology.labels?.east && topology.nodes?.east !== "active") {
    topology.labels.east = [
      topology.labels.east[0],
      topology.labels.east[1],
      "Awaiting Kong decision",
    ];
  }
  if (topology.labels?.west && topology.nodes?.west !== "active") {
    topology.labels.west = [
      topology.labels.west[0],
      topology.labels.west[1],
      "Evaluating policy and route state",
    ];
  }

  renderRows(elements.requestPreviewGrid, pendingRows);
  elements.expectedOutcome.textContent = "Scenario running. Kong is evaluating the request and the final route decision will appear when the response returns.";
  elements.consoleOutput.innerHTML = `
    <div class="console-empty console-empty-wide">
      <p>Running scenario through Kong and collecting the request/response trace.</p>
    </div>
  `;
  renderPendingDetailView();
  renderTopology(topology, { restartAnimations: true });
}

function stringifyPayload(value) {
  if (value == null || value === "") {
    return "None";
  }
  if (typeof value === "string") {
    return value;
  }
  if (
    typeof value === "object" &&
    !Array.isArray(value) &&
    Object.keys(value).length === 1 &&
    typeof value.raw === "string"
  ) {
    return value.raw;
  }
  return JSON.stringify(value, null, 2);
}

function formatHeaders(headers) {
  const entries = Object.entries(headers || {});
  if (!entries.length) {
    return "None";
  }
  return entries
    .map(([key, value]) => `${key}: ${value}`)
    .join("\n");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderConsolePane(title, statusMarkup, sections) {
  return `
    <section class="console-pane">
      <div class="console-pane-header">
        <strong>${escapeHtml(title)}</strong>
        ${statusMarkup || ""}
      </div>
      <div class="console-pane-body">
        ${sections
          .map(
            ([label, value, className = ""]) => `
              <div class="console-section">
                <span class="console-section-label">${escapeHtml(label)}</span>
                <pre class="console-code ${className}">${escapeHtml(value)}</pre>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

function renderConsole(consoleView) {
  const request = consoleView.request || {};
  const response = consoleView.response || {};
  const requestSummary = `${request.method || "GET"} ${request.endpoint || "/"}`;
  const responseStatus = response.status != null ? `HTTP ${response.status}` : "";
  const responseStatusClass = response.status >= 400 ? "error" : "success";
  const responseRows = [
    ["Summary", requestSummary],
    ["Headers", formatHeaders(response.headers)],
    ["Body", stringifyPayload(response.body)],
  ];

  if (response.headers?.location) {
    responseRows.push(["Location Received", response.headers.location]);
  }

  if (response.followUp) {
    const followUpStatus =
      response.followUp.status != null ? `HTTP ${response.followUp.status}` : "Failed";
    const followUpEndpoint = response.followUp.displayEndpoint || response.followUp.endpoint || "";
    responseRows.push(["Follow-Up HTTPS Call", `${response.followUp.method || "GET"} ${followUpEndpoint} -> ${followUpStatus}`]);
    responseRows.push(["Follow-Up Headers", formatHeaders(response.followUp.headers)]);
    responseRows.push(["Follow-Up Body", stringifyPayload(response.followUp.body)]);
  }

  elements.consoleOutput.innerHTML = `
    <div class="console-split">
      ${renderConsolePane("Request", "", [
        ["Method", request.method || "GET"],
        ["Endpoint", request.endpoint || "/"],
        ["Headers", formatHeaders(request.headers)],
        ["Body", stringifyPayload(request.body)],
      ])}
      ${renderConsolePane(
        "Response",
        `<span class="console-status ${responseStatusClass}">${responseStatus}</span>`,
        responseRows,
      )}
    </div>
  `;
}

function renderTopology(topology, options = {}) {
  resetTopology();
  if (options.restartAnimations) {
    void elements.topologyGrid?.offsetWidth;
  }
  const labels = topology.labels || {};
  const labelTargets = {
    client: ["clientNodeLabel", "clientNodeTitle", "clientNodeSubtitle"],
    kong: ["kongNodeLabel", "kongNodeTitle", "kongNodeSubtitle"],
    east: ["eastNodeLabel", "eastNodeTitle", "eastNodeSubtitle"],
    west: ["westNodeLabel", "westNodeTitle", "westNodeSubtitle"],
  };

  for (const [key, values] of Object.entries(labels)) {
    const [labelId, titleId, subtitleId] = labelTargets[key];
    elements[labelId].textContent = values[0];
    elements[titleId].textContent = values[1];
    elements[subtitleId].textContent = values[2];
  }

  for (const [name, stateValue] of Object.entries(topology.nodes || {})) {
    if (!nodes[name]) {
      continue;
    }
    if (stateValue === "active") {
      nodes[name].classList.add("active");
    } else if (stateValue === "error") {
      nodes[name].classList.add("error");
    } else if (stateValue === "static") {
      nodes[name].classList.add("static");
    }
  }
  for (const [name, stateValue] of Object.entries(topology.connectors || {})) {
    if (!connectors[name]) {
      continue;
    }
    if (stateValue === "active") {
      connectors[name].classList.add("active");
    } else if (stateValue === "error") {
      connectors[name].classList.add("error");
    } else if (stateValue === "hidden") {
      connectors[name].classList.add("hidden");
    }
  }

  elements.statusKong.className = `status-pill ${topology.statusKongClass || "neutral"}`;
  elements.statusKong.textContent = topology.statusKong || "Kong Waiting";
  elements.statusRoute.className = `status-pill ${topology.statusRouteClass || "neutral"}`;
  elements.statusRoute.textContent = topology.statusRoute || "Route Pending";
}

function renderSceneDetails() {
  const scene = currentSceneDetails();
  const blocks = [
    ["Control Plane", scene.controlPlane || "Not defined"],
    ["Data Plane", scene.dataPlane || "Not defined"],
    ["Public Path", scene.publicPath || "Not defined"],
    ["Routing Header", scene.routingHeader || "Not defined"],
    ["Services", (scene.services || []).join(", ") || "None"],
    ["Routes", (scene.routes || []).join(", ") || "None"],
    ["Plugins", (scene.plugins || []).join(", ") || "None"],
  ];

  if (scene.consumers?.length) {
    blocks.push(["Consumers", scene.consumers.join(", ")]);
  }
  if (scene.upstreams?.length) {
    blocks.push(["Upstreams", scene.upstreams.join(", ")]);
  }
  if (scene.scenarios?.length) {
    blocks.push(["Scenarios", scene.scenarios.join(", ")]);
  }

  elements.sceneDetailsContent.innerHTML = blocks
    .map(
      ([label, value]) => `
        <div class="entity-block">
          <p class="label">${label}</p>
          <strong>${value}</strong>
        </div>
      `,
    )
    .join("");
}

function renderDetailView(detailView) {
  elements.detailMeta.innerHTML = (detailView.entities || [])
    .map(
      ([label, value]) => `
        <div class="entity-block">
          <p class="label">${escapeHtml(label)}</p>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `,
    )
    .join("");
  const steps = detailView.steps?.length
    ? detailView.steps
    : [
        {
          title: "Command 1",
          command: detailView.curl || "",
          response: detailView.response || {},
        },
      ];
  elements.detailSteps.innerHTML = steps
    .map((step, index) => {
      const command = step.command || "";
      const response = stringifyPayload(step.response || {});
      return `
        <section class="detail-step">
          <div class="detail-step-header">
            <p class="label">Step ${index + 1}</p>
            <strong>${escapeHtml(step.title || `Command ${index + 1}`)}</strong>
          </div>
          <div class="detail-step-grid">
            <div class="detail-pane">
              <p class="label">Command</p>
              <pre class="detail-pre">${escapeHtml(command)}</pre>
            </div>
            <div class="detail-pane">
              <p class="label">Response</p>
              <pre class="detail-pre">${escapeHtml(response)}</pre>
            </div>
          </div>
        </section>
      `;
    })
    .join("");
}

function decodeJwt(token) {
  const parts = (token || "").trim().split(".");
  if (parts.length < 2) {
    throw new Error("Token is not a JWT.");
  }
  const decodePart = (value) => {
    const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - (normalized.length % 4)) % 4);
    return JSON.parse(atob(padded));
  };
  return {
    header: decodePart(parts[0]),
    payload: decodePart(parts[1]),
  };
}

function renderDecodedJwt(decoded) {
  elements.decodedJwtOutput.textContent = JSON.stringify(decoded, null, 2);
}

function updateControlVisibility() {
  const isRateScene = state.currentScene === "traffic-control-rate-limiting";
  const isResilienceScene = state.currentScene === "resilience-failover-health-checks";
  const isIdentityScene =
    state.currentScene === "identity-azure-token-validation" ||
    state.currentScene === "identity-keycloak-authorization";
  const isIpScene = state.currentScene === "network-policy-ip-allow-deny";
  const isSchemaScene = state.currentScene === "data-quality-schema-validation";
  const isSizeScene = state.currentScene === "traffic-control-request-size-limiting";
  const isMeteringScene = state.currentScene === "monetization-metering-billing";
  const isDatakitScene = state.currentScene === "datakit-plugin-orchestration";
  const isCryptoScene = state.currentScene === "transformation-gateway-payload-encryption";
  const isInjectionScene = state.currentScene === "security-injection-protection";
  const isTransportSecurityScene = state.currentScene === "transport-security-http-enforcement";
  const isVersionedRoutingScene = state.currentScene === "api-lifecycle-versioned-routing";
  const isCanaryScene = state.currentScene === "api-lifecycle-canary-migration";
  const isDeprecationScene = state.currentScene === "api-lifecycle-deprecation";
  elements.headerRoutingControls.classList.toggle(
    "hidden",
    isRateScene || isResilienceScene || isIdentityScene || isIpScene || isSchemaScene || isSizeScene || isMeteringScene || isDatakitScene || isCryptoScene || isInjectionScene || isTransportSecurityScene || isVersionedRoutingScene || isCanaryScene || isDeprecationScene,
  );
  elements.rateModeControls.classList.toggle("hidden", !isRateScene);
  elements.rateCounterControls.classList.toggle("hidden", !isRateScene);
  elements.rateConsumerControls.classList.toggle("hidden", !isRateScene || state.mode !== "consumer");
  elements.resilienceScenarioControls.classList.toggle("hidden", !isResilienceScene);
  elements.resilienceInstanceControls.classList.toggle("hidden", !isResilienceScene);
  elements.ipPresetControls.classList.toggle("hidden", !isIpScene);
  elements.schemaCaseControls.classList.toggle("hidden", !isSchemaScene);
  elements.sizeCaseControls.classList.toggle("hidden", !isSizeScene);
  elements.meteringScenarioControls.classList.toggle("hidden", !isMeteringScene);
  elements.datakitScenarioControls.classList.toggle("hidden", !isDatakitScene);
  elements.datakitFallbackModeControls.classList.toggle("hidden", !isDatakitScene || state.datakitScenario !== "fallback");
  // Crypto scene uses the shared run/reset controls only.
  elements.injectionSubsceneControls.classList.toggle("hidden", !isInjectionScene);
  elements.transportSecurityCaseControls.classList.toggle("hidden", !isTransportSecurityScene);
  elements.versionRoutingModeControls.classList.toggle("hidden", !isVersionedRoutingScene);
  elements.versionRoutingVersionControls.classList.toggle("hidden", !isVersionedRoutingScene);
  elements.canaryScenarioControls.classList.toggle("hidden", !isCanaryScene);
  elements.canaryHeaderControls.classList.toggle("hidden", !isCanaryScene || state.canaryScenario !== "header-based");
  elements.canaryConsumerControls.classList.toggle("hidden", !isCanaryScene || state.canaryScenario !== "consumer-based");
  elements.deprecationCaseControls.classList.toggle("hidden", !isDeprecationScene);
  elements.identityTokenControls.classList.toggle("hidden", !isIdentityScene);
  elements.identityJwtControls.classList.toggle("hidden", !isIdentityScene);
  elements.identityConsumerControls.classList.toggle(
    "hidden",
    !(
      state.currentScene === "identity-keycloak-authorization" ||
      state.currentScene === "identity-azure-token-validation"
    ),
  );
  elements.controlPanelTitle.textContent = SCENE_DEFAULTS[state.currentScene].controlTitle;
}

function renderResilienceInstances(instances) {
  state.resilienceInstances = instances || {};
  const instance1 = state.resilienceInstances["instance-1"];
  const instance2 = state.resilienceInstances["instance-2"];
  elements.instance1Status.textContent = instance1 ? (instance1.running ? "healthy" : "unhealthy") : "unknown";
  elements.instance2Status.textContent = instance2 ? (instance2.running ? "healthy" : "unhealthy") : "unknown";

  for (const button of instanceActionButtons) {
    const instance = state.resilienceInstances[button.dataset.instanceId];
    const running = Boolean(instance?.running);
    if (button.dataset.instanceAction === "start") {
      button.disabled = running;
    } else {
      button.disabled = !running;
    }
  }
}

function updateRowsValue(rows, label, value) {
  return rows.map(([rowLabel, rowValue]) => (rowLabel === label ? [rowLabel, value] : [rowLabel, rowValue]));
}

function tickRateLimitCountdown() {
  if (!state.lastRun || state.currentScene !== "traffic-control-rate-limiting") {
    stopCountdown();
    return;
  }

  const result = state.lastRun.result || {};
  if (!state.countdownEndsAtMs) {
    stopCountdown();
    return;
  }

  const secondsLeft = Math.max(0, Math.ceil((state.countdownEndsAtMs - Date.now()) / 1000));
  result.resetSeconds = secondsLeft;

  if (state.lastRun.topology?.labels?.west) {
    state.lastRun.topology.labels.west = [
      state.lastRun.topology.labels.west[0],
      state.lastRun.topology.labels.west[1],
      `Request ${result.executionCount}, reset in ${secondsLeft}s`,
    ];
    renderTopology(state.lastRun.topology);
  }

  if (secondsLeft === 0) {
    stopCountdown();
  }
}

function startRateLimitCountdown() {
  stopCountdown();
  const resetSeconds = state.lastRun?.result?.resetSeconds;
  if (state.currentScene !== "traffic-control-rate-limiting" || resetSeconds == null) {
    return;
  }
  state.countdownEndsAtMs = Date.now() + (Math.max(resetSeconds, 0) * 1000);
  tickRateLimitCountdown();
  state.countdownTimer = window.setInterval(tickRateLimitCountdown, 1000);
}

async function runScenario() {
  elements.runScenarioButton.disabled = true;
  prepareScenarioRun();
  showScenarioPending();
  await waitForNextPaint();
  try {
    let path = "/api/scenes/header-routing/run";
    let body = { region: state.region === "missing" ? "" : state.region };
    if (state.currentScene === "traffic-control-rate-limiting") {
      path = "/api/scenes/rate-limiting/run";
      body = { mode: state.mode, consumer: state.consumer };
    } else if (state.currentScene === "network-policy-ip-allow-deny") {
      path = "/api/scenes/ip-restriction/run";
      body = { preset: state.ipPreset };
    } else if (state.currentScene === "data-quality-schema-validation") {
      path = "/api/scenes/schema-validation/run";
      body = { case: state.schemaCase };
    } else if (state.currentScene === "traffic-control-request-size-limiting") {
      path = "/api/scenes/request-size/run";
      body = { case: state.sizeCase };
    } else if (state.currentScene === "monetization-metering-billing") {
      path = "/api/scenes/metering-billing/run";
      body = { consumer: state.meteringScenario };
    } else if (state.currentScene === "datakit-plugin-orchestration") {
      path = "/api/scenes/datakit/run";
      body = { scenario: state.datakitScenario, fallbackMode: state.datakitFallbackMode };
    } else if (state.currentScene === "transformation-gateway-payload-encryption") {
      path = "/api/scenes/payload-crypto/run";
      body = {};
    } else if (state.currentScene === "security-injection-protection") {
      path = "/api/scenes/injection-protection/run";
      body = { subscene: state.injectionSubscene };
    } else if (state.currentScene === "transport-security-http-enforcement") {
      path = "/api/scenes/transport-security/run";
      body = { case: state.transportSecurityCase };
    } else if (state.currentScene === "api-lifecycle-versioned-routing") {
      path = "/api/scenes/versioned-routing/run";
      body = { mode: state.versionRoutingMode, version: state.apiVersion };
    } else if (state.currentScene === "api-lifecycle-canary-migration") {
      path = "/api/scenes/canary/run";
      body = {
        scenario: state.canaryScenario,
        override: state.canaryHeaderMode,
        consumer: state.canaryConsumer,
      };
    } else if (state.currentScene === "api-lifecycle-deprecation") {
      path = "/api/scenes/deprecation/run";
      body = { case: state.deprecationCase };
    } else if (state.currentScene === "resilience-failover-health-checks") {
      path = "/api/scenes/resilience/run";
      body = { scenario: state.resilienceScenario };
    } else if (state.currentScene === "identity-azure-token-validation") {
      if (!elements.tokenEditor.value.trim()) {
        await generateIdentityToken();
      }
      path = "/api/scenes/identity/azure/run";
      body = { token: elements.tokenEditor.value.trim(), consumer: state.identityConsumer };
    } else if (state.currentScene === "identity-keycloak-authorization") {
      if (!elements.tokenEditor.value.trim()) {
        await generateIdentityToken();
      }
      path = "/api/scenes/identity/keycloak/run";
      body = { token: elements.tokenEditor.value.trim(), consumer: state.identityConsumer };
    }

    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    state.lastRun = payload;
    elements.consoleDetailButton.disabled = false;
    elements.expectedOutcome.textContent = computeExpectedOutcome();
    renderRows(elements.requestPreviewGrid, payload.requestPreview);
    renderConsole(payload.consoleView);
    renderTopology(payload.topology);
    renderDetailView(payload.detailView);
    if (payload.instanceStates) {
      renderResilienceInstances(payload.instanceStates);
    }
    startRateLimitCountdown();
  } catch (error) {
    elements.consoleOutput.innerHTML = `
      <div class="console-empty console-empty-wide">
        <p>${error.message}</p>
      </div>
    `;
  } finally {
    elements.runScenarioButton.disabled = false;
  }
}

async function generateIdentityToken() {
  const path =
    state.currentScene === "identity-keycloak-authorization"
      ? "/api/scenes/identity/keycloak/token"
      : "/api/scenes/identity/azure/token";
  const body =
    state.currentScene === "identity-keycloak-authorization"
      ? { consumer: state.identityConsumer }
      : { consumer: state.identityConsumer };
  elements.generateTokenButton.disabled = true;
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.error || payload.tokenResponse?.error_description || "Token generation failed.");
    }
    state.identityToken = payload.token || "";
    elements.tokenEditor.value = state.identityToken;
    elements.decodedJwtOutput.textContent = "Token generated. Decode the current token to inspect its claims.";
  } finally {
    elements.generateTokenButton.disabled = false;
  }
}

function handleDecodeToken() {
  try {
    const decoded = decodeJwt(elements.tokenEditor.value.trim());
    renderDecodedJwt(decoded);
  } catch (error) {
    elements.decodedJwtOutput.textContent = error.message;
  }
}

async function refreshResilienceStatus() {
  if (state.currentScene !== "resilience-failover-health-checks") {
    return;
  }
  const response = await fetch("/api/scenes/resilience/status");
  const payload = await response.json();
  renderResilienceInstances(payload.instances);
}

async function resetSceneRuntime() {
  if (state.currentScene === "api-lifecycle-canary-migration") {
    await fetch("/api/scenes/canary/reset", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    });
    resetView();
    return;
  }
  if (state.currentScene !== "resilience-failover-health-checks") {
    if (
      state.currentScene === "identity-azure-token-validation" ||
      state.currentScene === "identity-keycloak-authorization"
    ) {
      state.identityToken = "";
      elements.tokenEditor.value = "";
      elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
    }
    resetView();
    return;
  }
  await fetch("/api/scenes/resilience/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  await refreshResilienceStatus();
  resetView();
}

async function changeInstanceState(instanceId, action) {
  const response = await fetch("/api/scenes/resilience/instance", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instance: instanceId, action }),
  });
  const payload = await response.json();
  renderResilienceInstances(payload.instances);
  if (state.currentScene === "resilience-failover-health-checks") {
    resetView();
  }
}

function closeSceneMenu() {
  elements.scenePicker.classList.remove("open");
  elements.sceneMenu.classList.add("hidden");
  elements.scenePickerTrigger.setAttribute("aria-expanded", "false");
}

function openSceneMenu() {
  elements.scenePicker.classList.add("open");
  elements.sceneMenu.classList.remove("hidden");
  elements.scenePickerTrigger.setAttribute("aria-expanded", "true");
}

function renderSceneMenu() {
  const sceneOptions = Array.from(elements.sceneSelect.options).map((option) => ({
    id: option.value,
    label: option.textContent,
  }));
  elements.sceneMenu.innerHTML = sceneOptions
    .map(
      (scene) => `
        <button class="scene-menu-option ${scene.id === state.currentScene ? "active" : ""}" type="button" data-scene-option="${scene.id}">
          ${scene.label}
        </button>
      `,
    )
    .join("");
  elements.scenePickerCurrent.textContent = sceneOptions.find((scene) => scene.id === state.currentScene)?.label || "Select Scene";
}

async function loadConfig() {
  const response = await fetch("/api/config");
  const payload = await response.json();
  state.links = payload.links;
  state.scenes = payload.scenes;
  state.credentials = payload.credentials || [];
  elements.sceneSelect.innerHTML = payload.sceneOptions
    .map((scene) => `<option value="${scene.id}">${scene.label}</option>`)
    .join("");
  renderSceneMenu();
  renderCredentialsModal();
  updateSceneState(payload.sceneOptions[0]?.id || "traffic-routing-header");
}

function updateArchitectureModal() {
  const scene = currentSceneDetails();
  document.getElementById("architectureTitle").textContent = scene.title || "Scene";
  const body = elements.architectureModal.querySelector(".modal-body");
  body.innerHTML = (scene.architecture || [])
    .map((line) => `<p>${line}</p>`)
    .join("");
}

function renderCredentialsModal() {
  const sections = state.credentials || [];
  if (!sections.length) {
    elements.credentialsContent.innerHTML = `
      <div class="entity-block">
        <p class="label">Credentials</p>
        <strong>No credentials are configured for this demo.</strong>
      </div>
    `;
    return;
  }

  elements.credentialsContent.innerHTML = sections
    .map(
      (section) => `
        <section class="credential-section">
          <div class="credential-copy">
            <p class="eyebrow">${escapeHtml(section.title || "Credentials")}</p>
            <p>${escapeHtml(section.description || "")}</p>
          </div>
          <div class="credential-grid">
            ${(section.entries || [])
              .map(
                (entry) => `
                  <article class="credential-card">
                    <strong>${escapeHtml(entry.name || "Entry")}</strong>
                    <div class="credential-fields">
                      ${(entry.fields || [])
                        .map(
                          ([label, value]) => `
                            <div class="credential-row">
                              <span>${escapeHtml(label || "")}</span>
                              <code>${escapeHtml(value || "")}</code>
                            </div>
                          `,
                        )
                        .join("")}
                    </div>
                  </article>
                `,
              )
              .join("")}
          </div>
        </section>
      `,
    )
    .join("");
}

function updateSceneState(sceneId) {
  stopCountdown();
  state.currentScene = sceneId;
  elements.sceneSelect.value = sceneId;
  renderSceneMenu();
  closeSceneMenu();
  const scene = currentSceneDetails();
  elements.sceneTitle.textContent = scene.title || "Scene";
  updateControlVisibility();
  renderSceneDetails();
  updateArchitectureModal();
  resetView();
  if (state.currentScene === "resilience-failover-health-checks") {
    refreshResilienceStatus();
  }
  if (
    state.currentScene === "identity-azure-token-validation" ||
    state.currentScene === "identity-keycloak-authorization"
  ) {
    elements.tokenEditor.value = state.identityToken;
    elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
  }
}

function openLink(url) {
  if (!url || url === "#") {
    return;
  }
  window.open(url, "_blank", "noopener,noreferrer");
}

function pipelineStatusMarkup(status) {
  const normalized = status === "success" ? "success" : status === "error" ? "error" : "neutral";
  const label =
    status === "running"
      ? "Running"
      : status === "success"
        ? "Succeeded"
        : status === "error"
          ? "Failed"
          : "Idle";
  return `<span class="status-pill ${normalized} pipeline-command-status">${label}</span>`;
}

function classifyPipelineLogLine(line) {
  if (line.startsWith("$ ")) {
    return "command";
  }
  if (line.startsWith("[OK]") || line.startsWith("__CMD_DONE__ success")) {
    return "success";
  }
  if (
    line.startsWith("[ERROR]") ||
    line.startsWith("Error:") ||
    line.includes(" failed with ") ||
    line.includes("validation error:")
  ) {
    return "error";
  }
  if (
    line.startsWith("Summary:") ||
    line.startsWith("Rendered decK state") ||
    line.startsWith("Equivalent CI/CD step:") ||
    line.startsWith("Executing real decK command:") ||
    line.startsWith("Kong Admin API is ready") ||
    line.startsWith("Portal publication completed") ||
    line.startsWith("CI/CD onboarding run completed")
  ) {
    return "info";
  }
  return "plain";
}

function renderPipelineLogs(logs) {
  if (!(logs || []).length) {
    return "No pipeline output yet.";
  }
  return logs
    .map((line) => {
      const text = line == null ? "" : String(line);
      return `<div class="pipeline-log-line ${classifyPipelineLogLine(text)}">${escapeHtml(text)}</div>`;
    })
    .join("");
}

function renderPipelineOutputLines(lines) {
  if (!(lines || []).length) {
    return `<div class="pipeline-log-line plain">No output captured for this command yet.</div>`;
  }
  return lines
    .map((line) => {
      const text = line == null ? "" : String(line);
      return `<div class="pipeline-log-line ${classifyPipelineLogLine(text)}">${escapeHtml(text)}</div>`;
    })
    .join("");
}

function renderOnboardingJob(job) {
  state.onboardingJob = job;
  elements.onboardApiStatus.textContent =
    job.status === "running"
      ? "Running"
      : job.status === "success"
        ? "Succeeded"
        : job.status === "error"
          ? "Failed"
          : "Idle";
  elements.onboardApiCurrentCommand.textContent = job.currentCommand || "No run in progress.";
  elements.onboardApiCommandList.innerHTML = (job.commands || []).length
    ? job.commands
        .map(
          (item) => `
            <section class="pipeline-command-card">
              <div class="pipeline-command-row">
                <pre class="pipeline-command-text">${escapeHtml(item.command)}</pre>
                ${pipelineStatusMarkup(item.status)}
              </div>
              <p class="pipeline-command-explanation">${escapeHtml(item.explanation || "No explanation available.")}</p>
              <div class="pipeline-output-block">
                <div class="pipeline-output-header">Command Output</div>
                <div class="pipeline-log-output pipeline-log-output-compact">${renderPipelineOutputLines(item.output || [])}</div>
              </div>
            </section>
          `,
        )
        .join("")
    : `
        <div class="console-empty">
          <p>No pipeline commands have been executed yet.</p>
        </div>
      `;
  elements.onboardApiLogs.innerHTML = renderPipelineLogs(job.logs || []);
  elements.onboardApiLogs.scrollTop = elements.onboardApiLogs.scrollHeight;
  elements.onboardApiButton.disabled = job.status === "running";
}

function stringifyOnboardingResponse(payload) {
  return JSON.stringify(payload, null, 2);
}

function stopOnboardingPolling() {
  if (state.onboardingPollTimer) {
    clearInterval(state.onboardingPollTimer);
    state.onboardingPollTimer = null;
  }
}

async function refreshOnboardingStatus() {
  const response = await fetch("/api/dev-portal/onboarding/status");
  const job = await response.json();
  renderOnboardingJob(job);
  if (job.status !== "running") {
    stopOnboardingPolling();
  }
}

function startOnboardingPolling() {
  stopOnboardingPolling();
  state.onboardingPollTimer = window.setInterval(() => {
    refreshOnboardingStatus().catch(() => {});
  }, 1000);
}

async function openOnboardingModalAndRun() {
  toggleModal(elements.onboardApiModal, true);
  elements.onboardApiStatus.textContent = "Starting";
  elements.onboardApiCurrentCommand.textContent = "Queueing onboarding pipeline";
  elements.onboardApiCommandList.innerHTML = `
    <div class="console-empty">
      <p>Preparing CI/CD pipeline view...</p>
    </div>
  `;
  elements.onboardApiLogs.innerHTML = renderPipelineLogs(["Starting API onboarding pipeline..."]);

  const response = await fetch("/api/dev-portal/onboarding/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  const job = await response.json();
  renderOnboardingJob(job);
  if (job.status === "running") {
    startOnboardingPolling();
  }
}

async function testOnboardedApi() {
  const apiKey = elements.onboardApiKeyInput.value.trim();
  elements.testOnboardedApiButton.disabled = true;
  elements.onboardApiResponse.textContent = "Testing onboarded API through Kong...";
  try {
  const response = await fetch("/api/dev-portal/onboarding/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ apiKey }),
    });
    const payload = await response.json();
    elements.onboardApiCurl.textContent = payload.curlCommand || elements.onboardApiCurl.textContent;
    elements.onboardApiResponse.textContent = stringifyOnboardingResponse(payload);
  } catch (error) {
    elements.onboardApiResponse.textContent = stringifyOnboardingResponse({ error: error.message });
  } finally {
    elements.testOnboardedApiButton.disabled = false;
  }
}

function getCurrentRequestId() {
  const headers = state.lastRun?.consoleView?.request?.headers || {};
  return headers["x-request-id"] || headers["X-Request-Id"] || null;
}

function getCurrentTraceId() {
  return state.lastRun?.traceId || state.lastRun?.result?.traceId || state.lastRun?.detailView?.traceId || null;
}

function getTraceUrl() {
  let baseUrl = state.links.trace;
  if (!baseUrl || baseUrl === "#") {
    return "#";
  }
  try {
    const parsed = new URL(baseUrl, window.location.origin);
    const isTempoPortal =
      parsed.hostname === "localhost" &&
      (parsed.port === "3200" || parsed.port === "3201");
    if (isTempoPortal) {
      baseUrl = "http://localhost:3001/explore";
    }
  } catch (_error) {
    // keep original URL if parsing fails
  }
  const requestId = getCurrentRequestId();
  const traceId = getCurrentTraceId();
  const query = traceId
    ? traceId
    : requestId
      ? `{ span."request.id" = "${requestId}" }`
      : '{ span."request.id" = "your-request-id" }';
  const url = new URL(baseUrl, window.location.origin);
  const paneState = {
    trace: {
      datasource: "tempo",
      queries: [
        {
          refId: "A",
          datasource: { uid: "tempo", type: "tempo" },
          ...(traceId ? {} : { queryType: "traceql" }),
          query,
        },
      ],
      range: {
        from: "now-1h",
        to: "now",
      },
    },
  };
  url.searchParams.set("panes", JSON.stringify(paneState));
  url.searchParams.set("schemaVersion", "1");
  url.searchParams.set("orgId", "1");
  if (requestId) {
    url.searchParams.set("request_id", requestId);
  }
  if (traceId) {
    url.searchParams.set("trace_id", traceId);
  }
  return url.toString();
}

function getLogExplorerUrl() {
  const requestId = getCurrentRequestId();
  const baseUrl = state.links.requestAudit && state.links.requestAudit !== "#"
    ? state.links.requestAudit
    : "http://localhost:3001/explore";
  const url = new URL(baseUrl, window.location.origin);
  const query = requestId
    ? `{service_name="kong-enterprise"} | log_type="access" | request_id="${requestId}"`
    : '{service_name="kong-enterprise"} | log_type="access" | request_id="your-request-id"';
  const paneState = {
    logs: {
      datasource: "loki",
      queries: [
        {
          refId: "A",
          expr: query,
          queryType: "range",
        },
      ],
      range: {
        from: "now-1h",
        to: "now",
      },
    },
  };
  url.searchParams.set("panes", JSON.stringify(paneState));
  url.searchParams.set("schemaVersion", "1");
  url.searchParams.set("orgId", "1");
  if (requestId) {
    url.searchParams.set("request_id", requestId);
  }
  return url.toString();
}

function toggleModal(element, show) {
  element.classList.toggle("hidden", !show);
  element.setAttribute("aria-hidden", String(!show));
}

for (const button of regionButtons) {
  button.addEventListener("click", () => {
    state.region = button.dataset.region;
    setActiveButton(regionButtons, "region", state.region);
    updateStaticPreview();
  });
}

for (const button of modeButtons) {
  button.addEventListener("click", () => {
    state.mode = button.dataset.mode;
    setActiveButton(modeButtons, "mode", state.mode);
    updateControlVisibility();
    updateStaticPreview();
  });
}

for (const button of consumerButtons) {
  button.addEventListener("click", () => {
    state.consumer = button.dataset.consumer;
    setActiveButton(consumerButtons, "consumer", state.consumer);
    updateStaticPreview();
  });
}

for (const button of identityConsumerButtons) {
  button.addEventListener("click", () => {
    state.identityConsumer = button.dataset.identityConsumer;
    setActiveButton(identityConsumerButtons, "identityConsumer", state.identityConsumer);
    state.identityToken = "";
    elements.tokenEditor.value = "";
    elements.decodedJwtOutput.textContent = "Decode the current token to inspect its claims.";
    updateStaticPreview();
    resetView();
  });
}

for (const button of ipPresetButtons) {
  button.addEventListener("click", () => {
    state.ipPreset = button.dataset.ipPreset;
    setActiveButton(ipPresetButtons, "ipPreset", state.ipPreset);
    updateStaticPreview();
    resetView();
  });
}

for (const button of schemaCaseButtons) {
  button.addEventListener("click", () => {
    state.schemaCase = button.dataset.schemaCase;
    setActiveButton(schemaCaseButtons, "schemaCase", state.schemaCase);
    updateStaticPreview();
    resetView();
  });
}

for (const button of sizeCaseButtons) {
  button.addEventListener("click", () => {
    state.sizeCase = button.dataset.sizeCase;
    setActiveButton(sizeCaseButtons, "sizeCase", state.sizeCase);
    updateStaticPreview();
    resetView();
  });
}

for (const button of meteringScenarioButtons) {
  button.addEventListener("click", () => {
    state.meteringScenario = button.dataset.meteringScenario;
    setActiveButton(meteringScenarioButtons, "meteringScenario", state.meteringScenario);
    updateStaticPreview();
    resetView();
  });
}

for (const button of datakitScenarioButtons) {
  button.addEventListener("click", () => {
    state.datakitScenario = button.dataset.datakitScenario;
    setActiveButton(datakitScenarioButtons, "datakitScenario", state.datakitScenario);
    updateControlVisibility();
    updateStaticPreview();
    resetView();
  });
}

for (const button of datakitFallbackModeButtons) {
  button.addEventListener("click", () => {
    state.datakitFallbackMode = button.dataset.datakitFallbackMode;
    setActiveButton(datakitFallbackModeButtons, "datakitFallbackMode", state.datakitFallbackMode);
    updateStaticPreview();
    resetView();
  });
}

for (const button of injectionSubsceneButtons) {
  button.addEventListener("click", () => {
    state.injectionSubscene = button.dataset.injectionSubscene;
    setActiveButton(injectionSubsceneButtons, "injectionSubscene", state.injectionSubscene);
    updateStaticPreview();
    resetView();
  });
}

for (const button of transportSecurityCaseButtons) {
  button.addEventListener("click", () => {
    state.transportSecurityCase = button.dataset.transportSecurityCase;
    setActiveButton(transportSecurityCaseButtons, "transportSecurityCase", state.transportSecurityCase);
    updateStaticPreview();
    resetView();
  });
}

for (const button of versionRoutingModeButtons) {
  button.addEventListener("click", () => {
    state.versionRoutingMode = button.dataset.versionRoutingMode;
    setActiveButton(versionRoutingModeButtons, "versionRoutingMode", state.versionRoutingMode);
    updateStaticPreview();
    resetView();
  });
}

for (const button of apiVersionButtons) {
  button.addEventListener("click", () => {
    state.apiVersion = button.dataset.apiVersion;
    setActiveButton(apiVersionButtons, "apiVersion", state.apiVersion);
    updateStaticPreview();
    resetView();
  });
}

for (const button of canaryScenarioButtons) {
  button.addEventListener("click", () => {
    state.canaryScenario = button.dataset.canaryScenario;
    setActiveButton(canaryScenarioButtons, "canaryScenario", state.canaryScenario);
    updateControlVisibility();
    updateStaticPreview();
    resetView();
  });
}

for (const button of canaryHeaderModeButtons) {
  button.addEventListener("click", () => {
    state.canaryHeaderMode = button.dataset.canaryHeaderMode;
    setActiveButton(canaryHeaderModeButtons, "canaryHeaderMode", state.canaryHeaderMode);
    updateStaticPreview();
    resetView();
  });
}

for (const button of canaryConsumerButtons) {
  button.addEventListener("click", () => {
    state.canaryConsumer = button.dataset.canaryConsumer;
    setActiveButton(canaryConsumerButtons, "canaryConsumer", state.canaryConsumer);
    updateStaticPreview();
    resetView();
  });
}

for (const button of deprecationCaseButtons) {
  button.addEventListener("click", () => {
    state.deprecationCase = button.dataset.deprecationCase;
    setActiveButton(deprecationCaseButtons, "deprecationCase", state.deprecationCase);
    updateStaticPreview();
    resetView();
  });
}

for (const button of resilienceScenarioButtons) {
  button.addEventListener("click", () => {
    state.resilienceScenario = button.dataset.resilienceScenario;
    setActiveButton(resilienceScenarioButtons, "resilienceScenario", state.resilienceScenario);
    updateStaticPreview();
    resetView();
  });
}

for (const button of instanceActionButtons) {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await changeInstanceState(button.dataset.instanceId, button.dataset.instanceAction);
    } finally {
      button.disabled = false;
    }
  });
}

elements.tokenEditor.addEventListener("input", () => {
  state.identityToken = elements.tokenEditor.value;
});
elements.generateTokenButton.addEventListener("click", generateIdentityToken);
elements.decodeTokenButton.addEventListener("click", handleDecodeToken);
elements.scenePickerTrigger.addEventListener("click", () => {
  if (elements.sceneMenu.classList.contains("hidden")) {
    openSceneMenu();
  } else {
    closeSceneMenu();
  }
});
elements.sceneMenu.addEventListener("click", (event) => {
  const option = event.target.closest("[data-scene-option]");
  if (!option) {
    return;
  }
  updateSceneState(option.dataset.sceneOption);
});
elements.onboardApiButton.addEventListener("click", () => {
  openOnboardingModalAndRun().catch((error) => {
    toggleModal(elements.onboardApiModal, true);
    renderOnboardingJob({
      status: "error",
      currentCommand: "Failed to start onboarding pipeline",
      commands: [],
      logs: [error.message],
    });
  });
});
elements.testOnboardedApiButton.addEventListener("click", testOnboardedApi);
elements.runScenarioButton.addEventListener("click", runScenario);
elements.resetSceneButton.addEventListener("click", resetSceneRuntime);
elements.resetPanelButton.addEventListener("click", resetSceneRuntime);
elements.viewCredentialsButton.addEventListener("click", () => {
  renderCredentialsModal();
  toggleModal(elements.credentialsModal, true);
});
elements.viewArchitectureButton.addEventListener("click", () => {
  renderSceneDetails();
  toggleModal(elements.sceneDetailsModal, true);
});
elements.viewTraceButton.addEventListener("click", () => openLink(getTraceUrl()));
elements.viewLogsButton.addEventListener("click", () => openLink(state.links.logs));
elements.viewRequestAuditButton.addEventListener("click", () => openLink(getLogExplorerUrl()));
elements.consoleDetailButton.addEventListener("click", () => {
  if (!state.lastRun) {
    return;
  }
  renderDetailView(state.lastRun.detailView);
  toggleModal(elements.detailViewModal, true);
});
elements.closeArchitectureButton.addEventListener("click", () => toggleModal(elements.architectureModal, false));
elements.closeSceneDetailsButton.addEventListener("click", () => toggleModal(elements.sceneDetailsModal, false));
elements.closeDetailViewButton.addEventListener("click", () => toggleModal(elements.detailViewModal, false));
elements.closeCredentialsButton.addEventListener("click", () => toggleModal(elements.credentialsModal, false));
elements.closeOnboardApiButton.addEventListener("click", () => toggleModal(elements.onboardApiModal, false));

for (const modal of [elements.architectureModal, elements.sceneDetailsModal, elements.detailViewModal, elements.credentialsModal, elements.onboardApiModal]) {
  modal.addEventListener("click", (event) => {
    if (event.target === modal) {
      toggleModal(modal, false);
    }
  });
}

document.addEventListener("click", (event) => {
  if (!elements.scenePicker.contains(event.target)) {
    closeSceneMenu();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeSceneMenu();
    toggleModal(elements.architectureModal, false);
    toggleModal(elements.sceneDetailsModal, false);
    toggleModal(elements.detailViewModal, false);
    toggleModal(elements.credentialsModal, false);
    toggleModal(elements.onboardApiModal, false);
  }
});

loadConfig().then(() => {
  refreshOnboardingStatus().catch(() => {});
  setActiveButton(regionButtons, "region", state.region);
  setActiveButton(modeButtons, "mode", state.mode);
  setActiveButton(consumerButtons, "consumer", state.consumer);
  setActiveButton(identityConsumerButtons, "identityConsumer", state.identityConsumer);
  setActiveButton(ipPresetButtons, "ipPreset", state.ipPreset);
  setActiveButton(schemaCaseButtons, "schemaCase", state.schemaCase);
  setActiveButton(sizeCaseButtons, "sizeCase", state.sizeCase);
  setActiveButton(meteringScenarioButtons, "meteringScenario", state.meteringScenario);
  setActiveButton(datakitScenarioButtons, "datakitScenario", state.datakitScenario);
  setActiveButton(datakitFallbackModeButtons, "datakitFallbackMode", state.datakitFallbackMode);
  setActiveButton(injectionSubsceneButtons, "injectionSubscene", state.injectionSubscene);
  setActiveButton(transportSecurityCaseButtons, "transportSecurityCase", state.transportSecurityCase);
  setActiveButton(versionRoutingModeButtons, "versionRoutingMode", state.versionRoutingMode);
  setActiveButton(apiVersionButtons, "apiVersion", state.apiVersion);
  setActiveButton(canaryScenarioButtons, "canaryScenario", state.canaryScenario);
  setActiveButton(canaryHeaderModeButtons, "canaryHeaderMode", state.canaryHeaderMode);
  setActiveButton(canaryConsumerButtons, "canaryConsumer", state.canaryConsumer);
  setActiveButton(deprecationCaseButtons, "deprecationCase", state.deprecationCase);
  setActiveButton(resilienceScenarioButtons, "resilienceScenario", state.resilienceScenario);
  updateStaticPreview();
  resetView();
});
