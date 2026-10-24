/**
 * AI Job Hunter - Enterprise Application Controller.
 */

// Global Authenticated Fetch Wrapper (Seamless Bearer Token attachment)
const _nativeFetch = window.fetch;
window.fetch = function(url, options = {}) {
  const token = localStorage.getItem("jobhunter_token");
  if (token && typeof url === "string" && url.startsWith("/api/")) {
    options = options || {};
    options.headers = options.headers || {};
    if (options.headers instanceof Headers) {
      if (!options.headers.has("Authorization")) {
        options.headers.set("Authorization", `Bearer ${token}`);
      }
    } else {
      if (!options.headers["Authorization"]) {
        options.headers["Authorization"] = `Bearer ${token}`;
      }
    }
  }
  return _nativeFetch(url, options);
};

// Application State
const AppState = {
  jobs: [],
  stats: {},
  profile: null,
  currentUser: null,
  selectedJobId: null,
  activeFilter: {
    query: "",
    source: "",
    scoreCategory: "" // "high", "mid", "unscored", or ""
  },
  ws: null
};

// DOM Cache
const UI = {
  // Counters
  navCounterTotal: document.getElementById("nav-counter-total"),
  kpiTotal: document.getElementById("kpi-total"),
  kpiEvaluated: document.getElementById("kpi-evaluated"),
  kpiHighMatches: document.getElementById("kpi-high-matches"),
  kpiApplied: document.getElementById("kpi-applied"),
  kpiEvalSub: document.getElementById("kpi-eval-sub"),
  sidebarActiveModel: document.getElementById("sidebar-active-model"),

  // Table
  jobsTbody: document.getElementById("jobs-tbody"),

  // Search & Filter
  globalSearchInput: document.getElementById("global-search-input"),
  filterAtsSource: document.getElementById("filter-ats-source"),
  filterPills: document.querySelectorAll(".filter-pill"),

  // Actions
  btnMasterAutopilot: document.getElementById("btn-master-autopilot"),
  btnSyncAll: document.getElementById("btn-sync-all"),
  btnBatchEval: document.getElementById("btn-batch-eval"),
  btnAutoDiscoverTop: document.getElementById("btn-auto-discover-top"),
  btnRunAutoDiscover: document.getElementById("btn-run-auto-discover"),
  inputDiscoverLocation: document.getElementById("input-discover-location"),
  btnClearTerminal: document.getElementById("btn-clear-terminal"),
  terminalOutput: document.getElementById("terminal-output"),

  // Settings & Profile
  profileEditor: document.getElementById("profile-editor"),
  btnSaveProfile: document.getElementById("btn-save-profile"),
  settingProvider: document.getElementById("setting-provider"),
  settingProviderBadge: document.getElementById("setting-provider-badge"),
  settingModel: document.getElementById("setting-model"),
  settingModelPresets: document.getElementById("setting-model-presets"),
  settingHost: document.getElementById("setting-host"),
  settingApiKey: document.getElementById("setting-api-key"),
  settingKeyLabel: document.getElementById("setting-key-label"),
  settingKeyStatus: document.getElementById("setting-key-status"),
  settingPortalLink: document.getElementById("setting-portal-link"),
  providerKeyGroup: document.getElementById("provider-key-group"),
  ollamaHostGroup: document.getElementById("ollama-host-group"),
  btnToggleKeyVisibility: document.getElementById("btn-toggle-key-visibility"),
  btnTestConnection: document.getElementById("btn-test-connection"),
  testConnectionResult: document.getElementById("test-connection-result"),
  mobilityHomeCountry: document.getElementById("mobility-home-country"),
  btnSaveSettings: document.getElementById("btn-save-settings"),

  // Inspector Drawer
  inspectorDrawer: document.getElementById("inspector-drawer"),
  btnCloseDrawer: document.getElementById("btn-close-drawer"),
  drawerJobTitle: document.getElementById("drawer-job-title"),
  drawerJobCompany: document.getElementById("drawer-job-company"),
  drawerSourceBadge: document.getElementById("drawer-source-badge"),
  drawerLocation: document.getElementById("drawer-location"),
  drawerExternalLink: document.getElementById("drawer-external-link"),
  drawerGauge: document.getElementById("drawer-gauge"),
  drawerVerdict: document.getElementById("drawer-verdict"),
  drawerRationale: document.getElementById("drawer-rationale"),
  drawerStrengths: document.getElementById("drawer-strengths"),
  drawerGaps: document.getElementById("drawer-gaps"),
  drawerCoverLetter: document.getElementById("drawer-cover-letter"),
  btnGenerateLetter: document.getElementById("btn-generate-letter"),
  btnDrawerOpenPortal: document.getElementById("btn-drawer-open-portal"),
  btnDrawerMarkApplied: document.getElementById("btn-drawer-mark-applied"),
  btnDrawerVerifyLive: document.getElementById("btn-drawer-verify-live"),
  drawerGhostPill: document.getElementById("drawer-ghost-pill"),
  drawerGhostScore: document.getElementById("drawer-ghost-score"),
  drawerGhostSummary: document.getElementById("drawer-ghost-summary"),
  drawerGhostSignals: document.getElementById("drawer-ghost-signals"),
  drawerLivenessBadge: document.getElementById("drawer-liveness-badge"),
  bannerCandidateName: document.getElementById("banner-candidate-name"),
  bannerCandidateHeadline: document.getElementById("banner-candidate-headline"),
  bannerCandidateSkillsPreview: document.getElementById("banner-candidate-skills-preview"),
  bannerCvInitial: document.getElementById("banner-cv-initial"),
  bannerCvFileInput: document.getElementById("banner-cv-file-input"),
  bannerCvDropzone: document.getElementById("banner-cv-dropzone"),
  bannerCvStatusText: document.getElementById("banner-cv-status-text"),
  btnReRankCv: document.getElementById("btn-re-rank-cv"),
  barReq: document.getElementById("bar-req"),
  barSkills: document.getElementById("bar-skills"),
  barTitle: document.getElementById("bar-title"),
  barSeniority: document.getElementById("bar-seniority"),
  txtBarReq: document.getElementById("txt-bar-req"),
  txtBarSkills: document.getElementById("txt-bar-skills"),
  txtBarTitle: document.getElementById("txt-bar-title"),
  txtBarSeniority: document.getElementById("txt-bar-seniority"),
  drawerMatchedSkills: document.getElementById("drawer-matched-skills"),
  drawerMissingSkills: document.getElementById("drawer-missing-skills"),
  btnCopyLetter: document.getElementById("btn-copy-letter"),
  drawerQuickCopyChips: document.getElementById("drawer-quick-copy-chips"),
  drawerEmailApplyBanner: document.getElementById("drawer-email-apply-banner"),
  drawerDetectedEmail: document.getElementById("drawer-detected-email"),
  btnCopyDetectedEmail: document.getElementById("btn-copy-detected-email"),
  btnSendEmailApp: document.getElementById("btn-send-email-app")
};

// Clipboard Copy Helper with Visual Feedback
window.copyToClipboard = function(text, label, btnElem) {
  if (!text) return;
  navigator.clipboard.writeText(text).then(() => {
    appendTerminalLine("CLIPBOARD", `Copied ${label} to clipboard: "${text}"`, "success");
    if (btnElem) {
      const origText = btnElem.innerHTML;
      btnElem.innerHTML = "✓ Copied!";
      btnElem.style.borderColor = "var(--accent-emerald)";
      setTimeout(() => {
        btnElem.innerHTML = origText;
        btnElem.style.borderColor = "";
      }, 1800);
    }
  }).catch(err => {
    console.error("Clipboard error:", err);
  });
};

// Auth State & Controller
async function checkAuthStatus() {
  const token = localStorage.getItem("jobhunter_token");
  const userBadge = document.getElementById("user-badge-name");
  const btnLogout = document.getElementById("btn-user-logout");

  if (!token) {
    AppState.currentUser = null;
    if (userBadge) userBadge.textContent = "Sign In / Register";
    if (btnLogout) btnLogout.style.display = "none";
    return null;
  }

  try {
    const res = await fetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      AppState.currentUser = data.user;
      if (userBadge) {
        userBadge.textContent = data.user.full_name || data.user.email.split("@")[0];
      }
      if (btnLogout) btnLogout.style.display = "inline-flex";
      return data.user;
    } else {
      localStorage.removeItem("jobhunter_token");
      AppState.currentUser = null;
      if (userBadge) userBadge.textContent = "Sign In / Register";
      if (btnLogout) btnLogout.style.display = "none";
      return null;
    }
  } catch (e) {
    return null;
  }
}

function setupAuthUI() {
  const modalOverlay = document.getElementById("auth-modal-overlay");
  const btnOpenModal = document.getElementById("btn-open-auth-modal");
  const btnCloseModal = document.getElementById("btn-close-auth-modal");
  const tabLogin = document.getElementById("tab-auth-login");
  const tabRegister = document.getElementById("tab-auth-register");
  const nameGroup = document.getElementById("auth-name-group");
  const modalTitle = document.getElementById("auth-modal-title");
  const btnSubmit = document.getElementById("btn-auth-submit");
  const errorMsg = document.getElementById("auth-error-msg");
  const btnLogout = document.getElementById("btn-user-logout");

  let isRegisterMode = false;

  function setMode(register) {
    isRegisterMode = register;
    if (errorMsg) errorMsg.style.display = "none";
    if (register) {
      if (tabRegister) {
        tabRegister.style.background = "rgba(99, 102, 241, 0.25)";
        tabRegister.style.color = "#fff";
        tabRegister.style.border = "1px solid rgba(99, 102, 241, 0.5)";
      }
      if (tabLogin) {
        tabLogin.style.background = "transparent";
        tabLogin.style.color = "#94a3b8";
        tabLogin.style.border = "none";
      }
      if (nameGroup) nameGroup.style.display = "block";
      if (modalTitle) modalTitle.textContent = "Create an Account";
      if (btnSubmit) btnSubmit.textContent = "Sign Up";
    } else {
      if (tabLogin) {
        tabLogin.style.background = "rgba(99, 102, 241, 0.25)";
        tabLogin.style.color = "#fff";
        tabLogin.style.border = "1px solid rgba(99, 102, 241, 0.5)";
      }
      if (tabRegister) {
        tabRegister.style.background = "transparent";
        tabRegister.style.color = "#94a3b8";
        tabRegister.style.border = "none";
      }
      if (nameGroup) nameGroup.style.display = "none";
      if (modalTitle) modalTitle.textContent = "Sign In to AI Job Hunter";
      if (btnSubmit) btnSubmit.textContent = "Sign In";
    }
  }

  if (btnOpenModal) {
    btnOpenModal.addEventListener("click", () => {
      if (localStorage.getItem("jobhunter_token")) {
        window.switchTab("tab-profile");
      } else {
        setMode(false);
        if (modalOverlay) modalOverlay.style.display = "flex";
      }
    });
  }

  if (btnCloseModal && modalOverlay) {
    btnCloseModal.addEventListener("click", () => {
      modalOverlay.style.display = "none";
    });
    modalOverlay.addEventListener("click", (e) => {
      if (e.target === modalOverlay) modalOverlay.style.display = "none";
    });
  }

  if (tabLogin) tabLogin.addEventListener("click", () => setMode(false));
  if (tabRegister) tabRegister.addEventListener("click", () => setMode(true));

  if (btnSubmit) {
    btnSubmit.addEventListener("click", async () => {
      const email = document.getElementById("auth-email-input").value.trim();
      const password = document.getElementById("auth-password-input").value.trim();
      const name = document.getElementById("auth-name-input") ? document.getElementById("auth-name-input").value.trim() : "";

      if (!email || !password) {
        if (errorMsg) {
          errorMsg.textContent = "Please fill in all required fields.";
          errorMsg.style.display = "block";
        }
        return;
      }

      btnSubmit.disabled = true;
      btnSubmit.textContent = "Processing...";

      try {
        const endpoint = isRegisterMode ? "/api/auth/register" : "/api/auth/login";
        const body = { email, password };
        if (isRegisterMode && name) body.full_name = name;

        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body)
        });
        const data = await res.json();

        if (res.ok && data.access_token) {
          localStorage.setItem("jobhunter_token", data.access_token);
          if (modalOverlay) modalOverlay.style.display = "none";
          await checkAuthStatus();
          await refreshAllData();
          appendTerminalLine("AUTH", `Signed in as ${email}`, "success");
        } else {
          if (errorMsg) {
            errorMsg.textContent = data.detail || "Authentication failed. Please check credentials.";
            errorMsg.style.display = "block";
          }
        }
      } catch (err) {
        if (errorMsg) {
          errorMsg.textContent = err.message;
          errorMsg.style.display = "block";
        }
      } finally {
        btnSubmit.disabled = false;
        btnSubmit.textContent = isRegisterMode ? "Sign Up" : "Sign In";
      }
    });
  }

  if (btnLogout) {
    btnLogout.addEventListener("click", async () => {
      localStorage.removeItem("jobhunter_token");
      await checkAuthStatus();
      await refreshAllData();
      appendTerminalLine("AUTH", "You have signed out.", "info");
    });
  }
}

// Bootstrap
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupKeyboardShortcuts();
  setupWebSocket();
  setupAuthUI();
  checkAuthStatus();
  setupEventListeners();
  refreshAllData();
});

// Global Tab Navigation
window.switchTab = function(tabId) {
  if (!tabId.startsWith("tab-")) tabId = `tab-${tabId}`;
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(n => {
    if (n.getAttribute("data-tab") === tabId) n.classList.add("active");
    else n.classList.remove("active");
  });
  document.querySelectorAll(".tab-pane").forEach(p => {
    if (p.id === tabId) p.classList.add("active");
    else p.classList.remove("active");
  });
  const titleMap = {
    "tab-radar": "Job Radar & Discovery",
    "tab-terminal": "Live Agent Telemetry Stream",
    "tab-crawlers": "ATS Crawlers Ingestion Hub",
    "tab-profile": "Candidate Background Profile",
    "tab-settings": "Inference Engine & Candidate Mobility"
  };
  const hl = document.getElementById("page-headline");
  if (hl && titleMap[tabId]) hl.textContent = titleMap[tabId];
};

function setupNavigation() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      if (tabId) window.switchTab(tabId);
    });
  });

  window.addEventListener("hashchange", () => {
    const raw = window.location.hash.replace("#", "").trim();
    if (raw) window.switchTab(raw);
  });

  const initial = window.location.hash.replace("#", "").trim();
  if (initial) window.switchTab(initial);
}

// Global Keyboard Shortcuts (⌘K to focus search)
function setupKeyboardShortcuts() {
  document.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      UI.globalSearchInput.focus();
    }
    if (e.key === "Escape") {
      closeDrawer();
    }
  });
}

// WebSocket Live Telemetry
function setupWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`;

  AppState.ws = new WebSocket(wsUrl);

  AppState.ws.onopen = () => {
    appendTerminalLine("SYSTEM", "Connected to Agent cluster WebSocket stream.", "info");
  };

  AppState.ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const type = msg.type || "INFO";
      const text = msg.message || JSON.stringify(msg);

      let level = "info";
      if (type.includes("ERROR")) level = "error";
      else if (type.includes("SUCCESS") || type.includes("COMPLETED") || type.includes("FINISHED")) level = "success";
      else if (type.includes("WARN")) level = "warn";

      appendTerminalLine(type, text, level);

      // Auto reload on state changes
      if (
        type === "CRAWLER_FINISHED" ||
        type === "EVALUATION_COMPLETED" ||
        type === "BATCH_EVAL_FINISHED" ||
        type === "AUTOPILOT_COMPLETED" ||
        type === "AUTOPILOT_DISCOVERED" ||
        type === "PIPELINE_RESET" ||
        type === "PREFERENCES_UPDATED"
      ) {
        refreshAllData(false);
      }
    } catch {
      appendTerminalLine("STREAM", event.data, "info");
    }
  };

  AppState.ws.onclose = () => {
    appendTerminalLine("SYSTEM", "WebSocket connection closed. Reconnecting in 3s...", "warn");
    setTimeout(setupWebSocket, 3000);
  };
}

function appendTerminalLine(tag, text, level = "info") {
  const line = document.createElement("div");
  line.className = "t-line";
  const time = new Date().toLocaleTimeString();
  line.innerHTML = `<span class="t-time">[${time}]</span> <span class="t-${level}">[${tag}]</span> ${escapeHtml(text)}`;
  UI.terminalOutput.appendChild(line);
  UI.terminalOutput.scrollTop = UI.terminalOutput.scrollHeight;
}

// Data Fetching
async function refreshAllData(showLog = true) {
  if (showLog) appendTerminalLine("SYNC", "Refreshing local pipeline & telemetry...", "info");
  await Promise.all([fetchJobs(), fetchStats(), fetchProfile(), fetchPreferences()]);
}

async function fetchJobs() {
  try {
    const res = await fetch("/api/jobs?limit=250");
    if (!res.ok) throw new Error("Failed to load jobs");
    AppState.jobs = await res.json();
    UI.navCounterTotal.textContent = AppState.jobs.length;
    renderDataGrid();
  } catch (err) {
    console.error("Error fetching jobs:", err);
  }
}

async function fetchStats() {
  try {
    const res = await fetch("/api/stats");
    if (!res.ok) throw new Error("Failed to load stats");
    AppState.stats = await res.json();

    UI.kpiTotal.textContent = AppState.stats.total_jobs || 0;
    UI.kpiEvaluated.textContent = AppState.stats.evaluated_jobs || 0;
    UI.kpiHighMatches.textContent = AppState.stats.high_matches || 0;
    UI.kpiApplied.textContent = AppState.stats.applied_jobs || 0;
    UI.kpiEvalSub.textContent = `${AppState.stats.pending_evaluation || 0} unscored remaining`;
  } catch (err) {
    console.error("Error fetching stats:", err);
  }
}

async function fetchProfile() {
  try {
    const [resProfile, resSettings] = await Promise.all([
      fetch("/api/profile"),
      fetch("/api/settings")
    ]);

    if (resProfile.ok) {
      const data = await resProfile.json();
      AppState.profile = data.profile;
      if (UI.profileEditor) {
        UI.profileEditor.value = JSON.stringify(data.profile, null, 2);
      }
      if (data.profile) {
        const p = data.profile;
        const info = p.personal_information || {};
        const elName = document.getElementById("vis-cand-name");
        const elTitle = document.getElementById("vis-cand-title");
        const elEmail = document.getElementById("vis-cand-email");
        const elLoc = document.getElementById("vis-cand-location");
        const elSkills = document.getElementById("vis-cand-skills");
        const elSum = document.getElementById("vis-cand-summary");

        if (elName && (info.first_name || info.last_name)) {
          elName.value = `${info.first_name || ""} ${info.last_name || ""}`.trim();
        }
        if (elTitle && info.headline) elTitle.value = info.headline;
        if (elEmail && info.email) elEmail.value = info.email;
        if (elLoc && (info.city || info.country)) {
          elLoc.value = `${info.city || ""}, ${info.country || ""}`.replace(/^, |, $/g, "");
        }
        if (elSkills && p.skills) {
          const allSkills = [
            ...(p.skills.languages || []),
            ...(p.skills.frameworks_and_backend || []),
            ...(p.skills.ai_and_data || [])
          ];
          if (allSkills.length) elSkills.value = allSkills.join(", ");
        }
        if (elSum && p.summary) elSum.value = p.summary.trim();

        // Update Top Candidate CV Match Banner
        const fullName = `${info.first_name || "Alex"} ${info.last_name || "Rivera"}`.trim();
        if (UI.bannerCandidateName) UI.bannerCandidateName.textContent = fullName;
        if (UI.bannerCvInitial) UI.bannerCvInitial.textContent = fullName.charAt(0).toUpperCase();
        if (UI.bannerCandidateHeadline && info.headline) {
          UI.bannerCandidateHeadline.textContent = info.headline;
        }
        if (UI.bannerCandidateSkillsPreview && p.skills) {
          const allSkills = [
            ...(p.skills.languages || []),
            ...(p.skills.frameworks_and_backend || []),
            ...(p.skills.ai_and_data || [])
          ];
          if (allSkills.length) {
            UI.bannerCandidateSkillsPreview.innerHTML = allSkills.slice(0, 7)
              .map(s => `<span class="cv-pill">${escapeHtml(s)}</span>`).join("") +
              (allSkills.length > 7 ? `<span class="cv-pill" style="color: var(--accent-indigo); font-weight: 700;">+${allSkills.length - 7} more</span>` : "");
          }
        }
      }
    }

    if (resSettings.ok) {
      const s = await resSettings.json();
      AppState.settingsData = s;
      if (UI.sidebarActiveModel) {
        UI.sidebarActiveModel.textContent = `${s.provider}/${s.model}`;
      }

      // Update quick API Key status button in header
      const elKeyLabel = document.getElementById("header-api-key-label");
      const elKeyDot = document.getElementById("header-api-key-dot");
      const currentProv = (s.providers && s.providers[s.provider]) ? s.providers[s.provider] : null;
      const isConfigured = currentProv ? currentProv.configured : (s.provider === "ollama");

      if (elKeyLabel) {
        elKeyLabel.textContent = isConfigured
          ? `${s.provider.toUpperCase()}: Active`
          : `API Key: Not Set (Click to Add)`;
      }
      if (elKeyDot) {
        elKeyDot.style.background = isConfigured ? "#34d399" : "#fbbf24";
        elKeyDot.style.boxShadow = isConfigured ? "0 0 8px rgba(52, 211, 153, 0.8)" : "0 0 8px rgba(251, 191, 36, 0.8)";
      }

      if (UI.settingProvider) UI.settingProvider.value = s.provider;
      if (UI.settingModel) UI.settingModel.value = s.model;
      if (UI.settingHost && s.ollama_host) UI.settingHost.value = s.ollama_host;
      if (UI.mobilityHomeCountry && s.home_country) {
        UI.mobilityHomeCountry.textContent = s.home_country;
      }
      updateProviderUI(s.provider, s);
    }
  } catch (err) {
    console.error("Error fetching profile/settings:", err);
  }
}

const PROVIDERS_CATALOG = {
  groq: {
    name: "Groq Cloud (Free LPU)",
    badge: "Groq Cloud Recommended (~500 t/s)",
    badgeColor: "#34d399",
    keyLabel: "Groq API Key",
    portalText: "Get Free Key ↗",
    portalUrl: "https://console.groq.com/keys",
    defaultModel: "llama-3.3-70b-versatile",
    presets: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768", "gemma2-9b-it"],
    placeholder: "gsk_..."
  },
  openai: {
    name: "OpenAI Commercial",
    badge: "Commercial High Accuracy",
    badgeColor: "#60a5fa",
    keyLabel: "OpenAI API Key",
    portalText: "Get OpenAI Key ↗",
    portalUrl: "https://platform.openai.com/api-keys",
    defaultModel: "gpt-4o-mini",
    presets: ["gpt-4o-mini", "gpt-4o", "o3-mini"],
    placeholder: "sk-..."
  },
  anthropic: {
    name: "Anthropic Claude",
    badge: "Superior Reasoning",
    badgeColor: "#c084fc",
    keyLabel: "Anthropic API Key",
    portalText: "Get Claude Key ↗",
    portalUrl: "https://console.anthropic.com/settings/keys",
    defaultModel: "claude-3-5-sonnet-20241022",
    presets: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    placeholder: "sk-ant-..."
  },
  gemini: {
    name: "Google Gemini",
    badge: "Next-Gen Flash & Multimodal",
    badgeColor: "#38bdf8",
    keyLabel: "Google Gemini API Key",
    portalText: "Get Gemini Key ↗",
    portalUrl: "https://aistudio.google.com/app/apikey",
    defaultModel: "gemini-2.0-flash",
    presets: ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
    placeholder: "AIzaSy..."
  },
  deepseek: {
    name: "DeepSeek API",
    badge: "Ultra Low Cost Deep Reasoning",
    badgeColor: "#818cf8",
    keyLabel: "DeepSeek API Key",
    portalText: "Get DeepSeek Key ↗",
    portalUrl: "https://platform.deepseek.com/api_keys",
    defaultModel: "deepseek-chat",
    presets: ["deepseek-chat", "deepseek-reasoner"],
    placeholder: "sk-..."
  },
  openrouter: {
    name: "OpenRouter Unified",
    badge: "200+ Unified Models",
    badgeColor: "#f472b6",
    keyLabel: "OpenRouter API Key",
    portalText: "Get OpenRouter Key ↗",
    portalUrl: "https://openrouter.ai/keys",
    defaultModel: "openrouter/auto",
    presets: ["openrouter/auto", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-r1"],
    placeholder: "sk-or-..."
  },
  ollama: {
    name: "Ollama Local Private",
    badge: "Local Machine (Private)",
    badgeColor: "#fbbf24",
    keyLabel: "Ollama Host",
    portalText: "Download Ollama ↗",
    portalUrl: "https://ollama.ai",
    defaultModel: "llama3.3",
    presets: ["llama3.3", "mistral", "deepseek-r1:8b", "qwen2.5"],
    placeholder: "http://localhost:11434"
  }
};

// ── Live Model Picker ────────────────────────────────────────────────────────
let _modelFetchTimer = null;

async function fetchModelsForProvider(provider, apiKey, ollamaHost) {
  const container = document.getElementById("setting-model-presets");
  if (!container) return;

  // Show loading spinner
  container.innerHTML = `
    <span style="font-size:0.72rem;color:var(--text-muted);display:flex;align-items:center;gap:0.4rem;">
      <span style="display:inline-block;width:10px;height:10px;border:2px solid #6366f1;border-top-color:transparent;border-radius:50%;animation:spin 0.7s linear infinite;"></span>
      Fetching live models for ${provider.toUpperCase()}...
    </span>`;

  try {
    const payload = { provider };
    if (apiKey && apiKey.trim()) payload.api_key = apiKey.trim();
    if (ollamaHost && ollamaHost.trim()) payload.ollama_host = ollamaHost.trim();

    const res = await fetch("/api/settings/list-models", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Server error");
    const data = await res.json();
    const models = data.models || [];
    const isLive = data.source === "live";

    container.innerHTML = "";

    // Source badge
    const sourceBadge = document.createElement("div");
    sourceBadge.style.cssText = "display:flex;align-items:center;gap:0.4rem;margin-bottom:0.4rem;flex-wrap:wrap;";
    sourceBadge.innerHTML = `
      <span style="font-size:0.69rem;color:${isLive ? '#34d399' : '#fbbf24'};font-weight:600;">
        ${isLive ? '⚡ Live Models from ' + provider.toUpperCase() + ' API' : '📋 Curated Static List'}
      </span>
      <span style="font-size:0.69rem;color:var(--text-muted);">(${models.length} available)</span>
    `;
    container.appendChild(sourceBadge);

    // Search filter input
    const searchWrap = document.createElement("div");
    searchWrap.style.cssText = "display:flex;gap:0.4rem;align-items:center;margin-bottom:0.4rem;";
    const searchInput = document.createElement("input");
    searchInput.type = "text";
    searchInput.placeholder = "Search models...";
    searchInput.style.cssText = "font-size:0.74rem;padding:0.3rem 0.6rem;background:var(--bg-input,#1e293b);border:1px solid var(--border-subtle);border-radius:6px;color:var(--text-primary);width:100%;outline:none;";
    searchWrap.appendChild(searchInput);
    container.appendChild(searchWrap);

    // Model chips container (scrollable)
    const chipsEl = document.createElement("div");
    chipsEl.id = "model-chips-inner";
    chipsEl.style.cssText = "display:flex;flex-wrap:wrap;gap:0.35rem;max-height:110px;overflow-y:auto;padding:0.25rem 0;";
    container.appendChild(chipsEl);

    function renderChips(filter) {
      chipsEl.innerHTML = "";
      const filtered = filter
        ? models.filter(m => m.id.toLowerCase().includes(filter.toLowerCase()) || (m.name || "").toLowerCase().includes(filter.toLowerCase()))
        : models;

      if (!filtered.length) {
        chipsEl.innerHTML = `<span style="font-size:0.72rem;color:var(--text-muted);">No models match your search.</span>`;
        return;
      }

      filtered.forEach(m => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.title = m.id;
        const isActive = m.active || (UI.settingModel && UI.settingModel.value === m.id);
        chip.style.cssText = `
          font-size: 0.71rem; padding: 0.22rem 0.6rem; border-radius: 5px; cursor: pointer;
          border: 1px solid ${isActive ? '#6366f1' : 'rgba(99,102,241,0.25)'};
          background: ${isActive ? 'rgba(99,102,241,0.18)' : 'rgba(30,41,59,0.7)'};
          color: ${isActive ? '#a5b4fc' : 'var(--text-muted)'};
          transition: all 0.15s; font-weight: ${isActive ? '600' : '400'};
          white-space: nowrap; max-width: 220px; overflow: hidden; text-overflow: ellipsis;
        `;
        chip.textContent = m.name || m.id;
        chip.onmouseenter = () => { chip.style.borderColor = "#6366f1"; chip.style.color = "#c7d2fe"; };
        chip.onmouseleave = () => { if (UI.settingModel?.value !== m.id) { chip.style.borderColor = "rgba(99,102,241,0.25)"; chip.style.color = "var(--text-muted)"; } };
        chip.onclick = () => {
          if (UI.settingModel) UI.settingModel.value = m.id;
          // Highlight selected chip
          chipsEl.querySelectorAll("button").forEach(b => {
            b.style.background = "rgba(30,41,59,0.7)";
            b.style.borderColor = "rgba(99,102,241,0.25)";
            b.style.color = "var(--text-muted)";
            b.style.fontWeight = "400";
          });
          chip.style.background = "rgba(99,102,241,0.18)";
          chip.style.borderColor = "#6366f1";
          chip.style.color = "#a5b4fc";
          chip.style.fontWeight = "600";
          appendTerminalLine("ROUTER", `Model selected: '${m.id}' (${provider.toUpperCase()})`, "info");
        };
        chipsEl.appendChild(chip);
      });
    }

    renderChips("");
    searchInput.addEventListener("input", (e) => renderChips(e.target.value));

  } catch (err) {
    container.innerHTML = `<span style="font-size:0.72rem;color:#f87171;">⚠ Could not load models: ${err.message}</span>`;
  }
}

function updateProviderUI(provider, settingsData) {
  const p = (provider || "groq").toLowerCase();
  const meta = PROVIDERS_CATALOG[p] || PROVIDERS_CATALOG.groq;
  const s = settingsData || AppState.settingsData || {};
  const provInfo = (s.providers && s.providers[p]) ? s.providers[p] : null;

  if (UI.settingProviderBadge) {
    UI.settingProviderBadge.textContent = meta.badge;
    UI.settingProviderBadge.style.color = meta.badgeColor;
    UI.settingProviderBadge.style.borderColor = meta.badgeColor;
    UI.settingProviderBadge.style.background = `${meta.badgeColor}18`;
    UI.settingProviderBadge.style.borderColor = `${meta.badgeColor}55`;
  }

  if (p === "ollama") {
    if (UI.providerKeyGroup) UI.providerKeyGroup.style.display = "none";
    if (UI.ollamaHostGroup) UI.ollamaHostGroup.style.display = "flex";
    // Fetch local Ollama models
    const host = UI.settingHost ? UI.settingHost.value.trim() : "";
    fetchModelsForProvider(p, "", host);
  } else {
    if (UI.providerKeyGroup) UI.providerKeyGroup.style.display = "flex";
    if (UI.ollamaHostGroup) UI.ollamaHostGroup.style.display = "none";

    if (UI.settingKeyLabel) UI.settingKeyLabel.textContent = meta.keyLabel;
    if (UI.settingPortalLink) {
      UI.settingPortalLink.href = meta.portalUrl;
      UI.settingPortalLink.textContent = meta.portalText;
    }
    if (UI.settingApiKey) {
      UI.settingApiKey.placeholder = meta.placeholder;
      UI.settingApiKey.value = "";
    }

    if (UI.settingKeyStatus) {
      if (provInfo && provInfo.configured) {
        UI.settingKeyStatus.textContent = `✓ Active API Key saved in secrets.yaml (${provInfo.masked_key})`;
        UI.settingKeyStatus.style.color = "#34d399";
        // Auto-fetch models if key is already configured
        fetchModelsForProvider(p, provInfo.masked_key);
      } else {
        UI.settingKeyStatus.textContent = `✕ No key configured. Enter your ${meta.name} key above.`;
        UI.settingKeyStatus.style.color = "#fbbf24";
        // Show static list even without key
        fetchModelsForProvider(p, "");
      }
    }
  }

  // Update model input to provider default
  if (UI.settingModel) {
    UI.settingModel.value = meta.defaultModel;
  }
}

async function fetchPreferences() {
  try {
    const res = await fetch("/api/profile/preferences");
    if (!res.ok) return;
    const pref = await res.json();

    const inputRoles = document.getElementById("mission-input-roles");
    const inputLocs = document.getElementById("mission-input-locations");
    const selectAge = document.getElementById("mission-select-freshness");
    const chkRemote = document.getElementById("mission-chk-remote");
    const chkBd = document.getElementById("mission-chk-bd");
    const chkVisa = document.getElementById("mission-chk-visa");

    if (inputRoles && pref.positions && pref.positions.length) {
      inputRoles.value = pref.positions.join(", ");
    }
    if (inputLocs && pref.locations && pref.locations.length) {
      inputLocs.value = pref.locations.join(", ");
    }
    if (selectAge && pref.max_age_days) {
      selectAge.value = String(pref.max_age_days);
    }
    if (pref.mobility) {
      if (chkRemote && pref.mobility.accept_remote_worldwide !== undefined) {
        chkRemote.checked = pref.mobility.accept_remote_worldwide;
      }
      if (chkBd && pref.mobility.accept_home_country_onsite !== undefined) {
        chkBd.checked = pref.mobility.accept_home_country_onsite;
      }
      if (chkVisa && pref.mobility.accept_foreign_onsite_with_visa !== undefined) {
        chkVisa.checked = pref.mobility.accept_foreign_onsite_with_visa;
      }
    }
  } catch (err) {
    console.error("Error fetching preferences:", err);
  }
}

// Company Dynamic Gradient Generator
function getCompanyGradient(company) {
  let hash = 0;
  const str = company || "Tech";
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const h1 = Math.abs(hash) % 360;
  const h2 = (h1 + 40) % 360;
  return `linear-gradient(135deg, hsl(${h1}, 75%, 45%) 0%, hsl(${h2}, 80%, 35%) 100%)`;
}

// Master View Toggle (List vs Kanban)
window.setMasterView = function(view) {
  const tablePanel = document.getElementById("table-view-panel");
  const kanbanContainer = document.getElementById("kanban-container");
  const btnList = document.getElementById("btn-view-list");
  const btnKanban = document.getElementById("btn-view-kanban");

  if (view === "kanban") {
    if (tablePanel) tablePanel.style.display = "none";
    if (kanbanContainer) kanbanContainer.classList.add("active");
    if (btnList) btnList.classList.remove("active");
    if (btnKanban) btnKanban.classList.add("active");
    renderKanbanBoard();
  } else {
    if (tablePanel) tablePanel.style.display = "block";
    if (kanbanContainer) kanbanContainer.classList.remove("active");
    if (btnList) btnList.classList.add("active");
    if (btnKanban) btnKanban.classList.remove("active");
  }
};

// Render Master Data Grid (CV-Centric Personal Matchmaker)
function renderDataGrid() {
  const query = AppState.activeFilter.query.toLowerCase();
  const source = AppState.activeFilter.source.toLowerCase();
  const scoreCat = AppState.activeFilter.scoreCategory;

  const filtered = AppState.jobs.filter(job => {
    // Query
    const matchesQuery = !query ||
      job.title.toLowerCase().includes(query) ||
      job.company.toLowerCase().includes(query) ||
      (job.location && job.location.toLowerCase().includes(query)) ||
      (job.cv_match && job.cv_match.matched_skills && job.cv_match.matched_skills.some(s => s.toLowerCase().includes(query)));

    // Source
    const matchesSource = !source || (job.source && job.source.toLowerCase() === source);

    // Faceted Match Filters
    let matchesScore = true;
    const cvScore = (job.cv_match && job.cv_match.score) || (job.evaluation ? job.evaluation.score : 0);
    const ghost = job.ghost_analysis;
    const stage = (job.application ? job.application.status : (job.status || "DISCOVERED")).toUpperCase();

    if (scoreCat === "top") matchesScore = cvScore >= 80;
    else if (scoreCat === "good") matchesScore = cvScore >= 65 && cvScore < 80;
    else if (scoreCat === "fresh") matchesScore = ghost && ghost.reality_class === "fresh";
    else if (scoreCat === "ghost") matchesScore = ghost && ghost.is_ghost;
    else if (scoreCat === "applied") matchesScore = stage !== "DISCOVERED";

    return matchesQuery && matchesSource && matchesScore;
  });

  // Sort descending by candidate CV Match Score (best matches first)
  filtered.sort((a, b) => {
    const sa = (a.cv_match && a.cv_match.score) || (a.evaluation ? a.evaluation.score : 0);
    const sb = (b.cv_match && b.cv_match.score) || (b.evaluation ? b.evaluation.score : 0);
    return sb - sa;
  });

  // Update candidate match stats banner
  const allScores = AppState.jobs.map(j => (j.cv_match && j.cv_match.score) || 0);
  const highCount = allScores.filter(s => s >= 80).length;
  const avgFit = allScores.length ? Math.round(allScores.reduce((a, b) => a + b, 0) / allScores.length) : 0;
  
  const elHighBadge = document.getElementById("banner-high-match-count");
  const elAvgFit = document.getElementById("banner-avg-fit");
  if (elHighBadge) elHighBadge.textContent = `🌟 ${highCount} Best Fits (≥80%)`;
  if (elAvgFit) elAvgFit.textContent = `Avg Fit: ${avgFit}%`;

  // Always update Kanban and Studio Select
  renderKanbanBoard();
  populateStudioJobSelect();

  if (filtered.length === 0) {
    UI.jobsTbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 4rem;">
          No matching listings found for this filter. Try adjusting criteria or upload your CV to recalculate.
        </td>
      </tr>
    `;
    return;
  }

  UI.jobsTbody.innerHTML = filtered.map(job => {
    const isSelected = job.id === AppState.selectedJobId;
    const initial = (job.company || "C").charAt(0).toUpperCase();

    // Source Badge Class
    const s = (job.source || "greenhouse").toLowerCase();
    const sourceClass = `badge-${s}`;

    // CV Match Score & Pill
    const cv = job.cv_match || { score: 75, verdict_label: "Match" };
    const cvScore = cv.score;
    const scoreClass = cvScore >= 80 ? "score-high" : (cvScore >= 65 ? "score-mid" : "score-low");
    const cvPill = `<span class="score-pill ${scoreClass}" title="${escapeHtml(cv.highlights ? cv.highlights.join(' • ') : '')}">${cvScore}% Fit</span>`;

    // Skills Overlap Chips
    const matchedChips = (cv.matched_skills || []).slice(0, 3)
      .map(s => `<span class="skill-chip-match">✓ ${escapeHtml(s)}</span>`).join("");
    const missingChips = (cv.missing_skills || []).slice(0, 2)
      .map(s => `<span class="skill-chip-gap">! ${escapeHtml(s)}</span>`).join("");

    // Ghost Reality Badge & Link Vitality
    const ghostBadge = getGhostBadgeHtml(job.ghost_analysis);
    const vitalityBadge = job.status === "EXPIRED"
      ? `<span class="badge" style="background: rgba(248, 113, 113, 0.15); color: #f87171; font-size: 0.65rem;">🔴 Closed</span>`
      : `<span class="badge" style="background: rgba(52, 211, 153, 0.12); color: #34d399; font-size: 0.65rem;">✓ Live</span>`;

    // Stage
    const stage = job.application ? job.application.status : (job.status || "DISCOVERED");

    return `
      <tr class="clickable-row ${isSelected ? 'selected' : ''}" onclick="selectJob(${job.id})">
        <td>
          <div class="company-cell">
            <div class="company-avatar" style="background: ${getCompanyGradient(job.company)}; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">${initial}</div>
            <div class="job-identity">
              <div style="display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap;">
                <span class="job-role">${escapeHtml(job.title)}</span>
                ${ghostBadge}
              </div>
              <span class="job-company">${escapeHtml(job.company)}</span>
              <div style="display: flex; gap: 0.25rem; flex-wrap: wrap; margin-top: 0.25rem;">
                ${matchedChips}
                ${missingChips}
              </div>
            </div>
          </div>
        </td>
        <td>
          <div style="display: flex; flex-direction: column; gap: 0.25rem; align-items: flex-start;">
            <span class="badge ${sourceClass}">${escapeHtml(job.source || "ATS")}</span>
            ${vitalityBadge}
          </div>
        </td>
        <td>
          <span style="font-size: 0.82rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.35rem;">
            ${job.remote ? '<span style="color: #34d399; font-weight: 700;">🌐 Remote</span>' : escapeHtml(job.location || "On-site")}
          </span>
        </td>
        <td>
          <div style="display: flex; flex-direction: column; gap: 0.25rem; align-items: flex-start;">
            ${cvPill}
            <span style="font-size: 0.68rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">${escapeHtml(cv.verdict_label || 'Evaluated')}</span>
          </div>
        </td>
        <td>
          <span style="font-size: 0.74rem; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); background: rgba(255,255,255,0.03); padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
            ${escapeHtml(stage)}
          </span>
        </td>
        <td style="text-align: right;">
          <div class="row-actions-group">
            <button class="row-action-btn btn-portal-fast" title="Open official company career portal directly" onclick="event.stopPropagation(); openCareerPortal(${job.id});">
              ↗ Portal
            </button>
            <button class="row-action-btn" title="Toggle Application Status" onclick="event.stopPropagation(); trackJobStage(${job.id}, '${stage === 'APPLIED' ? 'DISCOVERED' : 'APPLIED'}');">
              ${stage === 'APPLIED' ? '✓ Applied' : 'Mark Applied'}
            </button>
            <button class="row-action-btn" title="AI Cover Letter Studio" onclick="event.stopPropagation(); openCoverLetterStudioForJob(${job.id});">
              📄 Letter
            </button>
            <button class="row-action-btn" title="Inspect Full CV Fit Breakdown" onclick="event.stopPropagation(); selectJob(${job.id});">
              👁️
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

// Render Kanban Pipeline Board
window.renderKanbanBoard = function() {
  const buckets = {
    discovered: [],
    highfit: [],
    review: [],
    applied: []
  };

  AppState.jobs.forEach(job => {
    const status = (job.application ? job.application.status : (job.status || "DISCOVERED")).toUpperCase();
    const score = job.evaluation ? job.evaluation.score : null;

    if (status === "SUBMITTED" || status === "APPLIED" || status === "DRY_RUN_COMPLETED") {
      buckets.applied.push(job);
    } else if (score !== null && score >= 80) {
      buckets.highfit.push(job);
    } else if (score !== null && score >= 60 && score < 80) {
      buckets.review.push(job);
    } else {
      buckets.discovered.push(job);
    }
  });

  function renderCard(job) {
    const initial = (job.company || "C").charAt(0).toUpperCase();
    const sc = job.evaluation ? job.evaluation.score : null;
    let scoreBadge = `<span class="score-pill score-none" style="font-size: 0.68rem; padding: 0.15rem 0.4rem;">Unscored</span>`;
    if (sc !== null) {
      const cls = sc >= 80 ? "score-high" : (sc >= 60 ? "score-mid" : "score-low");
      scoreBadge = `<span class="score-pill ${cls}" style="font-size: 0.68rem; padding: 0.15rem 0.4rem;">${sc}% Match</span>`;
    }

    return `
      <div class="kanban-card" onclick="selectJob(${job.id})">
        <div class="kanban-card-top">
          <div style="flex: 1;">
            <div class="kanban-card-title">${escapeHtml(job.title)}</div>
            <div class="kanban-card-company">
              <span class="company-avatar" style="width: 20px; height: 20px; font-size: 0.65rem; border-radius: 4px; background: ${getCompanyGradient(job.company)}; color: #fff;">${initial}</span>
              <span>${escapeHtml(job.company)}</span>
            </div>
          </div>
          ${scoreBadge}
        </div>
        <div class="kanban-card-footer">
          <span style="font-size: 0.72rem; color: var(--text-muted);">
            ${job.remote ? '🌐 Remote' : escapeHtml((job.location || 'Global').split(',')[0])}
          </span>
          <button class="row-action-btn btn-portal-fast" style="padding: 0.2rem 0.55rem; font-size: 0.68rem;" onclick="event.stopPropagation(); openCareerPortal(${job.id});">
            ↗ Apply on Portal
          </button>
        </div>
      </div>
    `;
  }

  // Populate both radar kanban and full page kanban
  const targetPrefixes = ["kanban-", "fkanban-"];
  targetPrefixes.forEach(p => {
    const elDiscovered = document.getElementById(`${p}list-discovered`);
    const elHighfit = document.getElementById(`${p}list-highfit`);
    const elReview = document.getElementById(`${p}list-review`);
    const elApplied = document.getElementById(`${p}list-applied`);

    if (elDiscovered) elDiscovered.innerHTML = buckets.discovered.slice(0, 30).map(renderCard).join("") || `<div style="text-align: center; color: var(--text-faint); padding: 2rem; font-size: 0.78rem;">Queue Empty</div>`;
    if (elHighfit) elHighfit.innerHTML = buckets.highfit.slice(0, 30).map(renderCard).join("") || `<div style="text-align: center; color: var(--text-faint); padding: 2rem; font-size: 0.78rem;">No &ge;80% Matches Yet</div>`;
    if (elReview) elReview.innerHTML = buckets.review.slice(0, 30).map(renderCard).join("") || `<div style="text-align: center; color: var(--text-faint); padding: 2rem; font-size: 0.78rem;">No Items</div>`;
    if (elApplied) elApplied.innerHTML = buckets.applied.slice(0, 30).map(renderCard).join("") || `<div style="text-align: center; color: var(--text-faint); padding: 2rem; font-size: 0.78rem;">No Applications Yet</div>`;

    const cD = document.getElementById(`${p}count-discovered`);
    const cH = document.getElementById(`${p}count-highfit`);
    const cR = document.getElementById(`${p}count-review`);
    const cA = document.getElementById(`${p}count-applied`);
    if (cD) cD.textContent = buckets.discovered.length;
    if (cH) cH.textContent = buckets.highfit.length;
    if (cR) cR.textContent = buckets.review.length;
    if (cA) cA.textContent = buckets.applied.length;
  });
};

// Select Job & Populate Inspector Drawer
window.selectJob = function(jobId) {
  AppState.selectedJobId = jobId;
  renderDataGrid();

  const job = AppState.jobs.find(j => j.id === jobId);
  if (!job) return;

  UI.drawerJobTitle.textContent = job.title;
  UI.drawerJobCompany.textContent = job.company;
  UI.drawerLocation.textContent = job.remote ? "Remote Position" : (job.location || "Location not specified");
  UI.drawerExternalLink.href = job.url;

  const s = (job.source || "ATS").toLowerCase();
  UI.drawerSourceBadge.className = `badge badge-${s}`;
  UI.drawerSourceBadge.textContent = job.source || "ATS";

  // 4-Tier CV Match Matrix & Alignment
  const cv = job.cv_match || { score: 75, verdict_label: "Matched" };
  const score = cv.score;
  UI.drawerGauge.textContent = score;
  UI.drawerGauge.style.borderColor = score >= 80 ? "var(--accent-emerald)" : (score >= 65 ? "var(--accent-amber)" : "var(--accent-rose)");
  UI.drawerGauge.style.color = score >= 80 ? "var(--accent-emerald)" : (score >= 65 ? "var(--accent-amber)" : "var(--accent-rose)");
  UI.drawerVerdict.textContent = `${cv.verdict_label || 'Evaluated'} (${score}% Match with CV)`;
  UI.drawerRationale.textContent = (cv.highlights && cv.highlights.length > 0)
    ? cv.highlights.join(" • ")
    : (job.evaluation ? job.evaluation.full_rationale : "Fit evaluated directly against your uploaded CV.");

  // Update Match Breakdown Progress Bars
  if (cv.breakdown) {
    const b = cv.breakdown;
    if (UI.barReq) UI.barReq.style.width = `${b.requirements_coverage}%`;
    if (UI.txtBarReq) UI.txtBarReq.textContent = `${b.requirements_coverage}%`;
    if (UI.barSkills) UI.barSkills.style.width = `${b.skills_match}%`;
    if (UI.txtBarSkills) UI.txtBarSkills.textContent = `${b.skills_match}%`;
    if (UI.barTitle) UI.barTitle.style.width = `${b.title_alignment}%`;
    if (UI.txtBarTitle) UI.txtBarTitle.textContent = `${b.title_alignment}%`;
    if (UI.barSeniority) UI.barSeniority.style.width = `${b.seniority_fit}%`;
    if (UI.txtBarSeniority) UI.txtBarSeniority.textContent = `${b.seniority_fit}%`;
  }

  // Matched Skills Chip Cloud
  if (UI.drawerMatchedSkills) {
    const matched = cv.matched_skills || [];
    UI.drawerMatchedSkills.innerHTML = matched.length > 0
      ? matched.map(s => `<span class="skill-chip-match">✓ ${escapeHtml(s)}</span>`).join("")
      : `<span style="font-size: 0.76rem; color: var(--text-muted);">Transferable software engineering foundation</span>`;
  }

  // Missing Skills Gaps
  if (UI.drawerMissingSkills) {
    const missing = cv.missing_skills || [];
    UI.drawerMissingSkills.innerHTML = missing.length > 0
      ? missing.map(s => `<span class="skill-chip-gap">! ${escapeHtml(s)}</span>`).join("")
      : `<span style="font-size: 0.76rem; color: #34d399; font-weight: 600;">✓ No critical tech gaps found for your profile</span>`;
  }

  // Cover Letter
  if (job.application && job.application.cover_letter) {
    UI.drawerCoverLetter.textContent = job.application.cover_letter;
  } else {
    UI.drawerCoverLetter.textContent = "Click 'Draft Letter' to generate a targeted letter aligned with this job.";
  }

  // Ghost Job & Reality Radar
  if (job.ghost_analysis) {
    const g = job.ghost_analysis;
    if (UI.drawerGhostPill) {
      UI.drawerGhostPill.textContent = g.label;
      UI.drawerGhostPill.className = `badge ${g.reality_class === 'fresh' ? 'badge-ghost-fresh' : (g.reality_class === 'stale' ? 'badge-ghost-stale' : 'badge-ghost-warning')}`;
    }
    if (UI.drawerGhostScore) {
      UI.drawerGhostScore.textContent = `${g.authenticity_score}%`;
      UI.drawerGhostScore.style.color = g.authenticity_score >= 80 ? "var(--accent-emerald)" : (g.authenticity_score >= 60 ? "var(--accent-amber)" : "var(--accent-rose)");
    }
    if (UI.drawerGhostSummary) {
      UI.drawerGhostSummary.textContent = g.summary;
    }
    if (UI.drawerGhostSignals) {
      if (g.signals && g.signals.length > 0) {
        UI.drawerGhostSignals.innerHTML = g.signals.map(s => `<li>${escapeHtml(s)}</li>`).join("");
      } else {
        UI.drawerGhostSignals.innerHTML = `<li>No evergreen phrases detected</li>`;
      }
    }
  }

  // Liveness Status indicator
  if (UI.drawerLivenessBadge) {
    if (job.status === "EXPIRED") {
      UI.drawerLivenessBadge.innerHTML = `<span style="color: #f87171; font-weight: 600;">🔴 Posting Confirmed Closed / Expired</span>`;
    } else {
      UI.drawerLivenessBadge.innerHTML = `<span>🌐 Status: Active Portal (Click 'Verify Link' to probe in real-time)</span>`;
    }
  }

  // Active Stage Highlight
  const currentStage = (job.application ? job.application.status : (job.status || "DISCOVERED")).toUpperCase();
  document.querySelectorAll(".stage-tag-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.stage === currentStage);
  });

  // Populate 1-Click Fast Fill (Quick Copy Profile Chips)
  if (UI.drawerQuickCopyChips) {
    const p = AppState.profile || {};
    const info = p.personal_information || {};
    const fullName = `${info.first_name || ""} ${info.last_name || ""}`.trim();
    const email = info.email || "";
    const phone = `${info.phone_country_code || ""}${info.phone_number || ""}`.trim();
    const linkedin = info.linkedin_url || "";
    const portfolio = info.portfolio_url || "";
    const github = info.github_url || "";

    const chips = [
      { label: "Name", val: fullName, icon: "👤" },
      { label: "Email", val: email, icon: "✉️" },
      { label: "Phone", val: phone, icon: "📞" },
      { label: "LinkedIn", val: linkedin, icon: "🔗" },
      { label: "Portfolio", val: portfolio, icon: "🌐" },
      { label: "GitHub", val: github, icon: "💻" }
    ].filter(c => Boolean(c.val));

    if (chips.length > 0) {
      UI.drawerQuickCopyChips.innerHTML = chips.map(c => `
        <button class="btn btn-secondary btn-sm" style="font-size: 0.72rem; padding: 0.22rem 0.5rem; border-radius: 6px; display: inline-flex; align-items: center; gap: 0.25rem; background: rgba(255,255,255,0.04);" onclick="event.stopPropagation(); copyToClipboard('${escapeHtml(c.val)}', '${escapeHtml(c.label)}', this)">
          <span>${c.icon}</span>
          <span>Copy ${escapeHtml(c.label)}</span>
        </button>
      `).join("");
    } else {
      UI.drawerQuickCopyChips.innerHTML = `<span style="font-size: 0.72rem; color: var(--text-muted);">Upload your CV in Profile tab to enable 1-Click copy</span>`;
    }
  }

  // Direct Email Application Detector
  if (UI.drawerEmailApplyBanner && UI.drawerDetectedEmail && UI.btnSendEmailApp) {
    const textToScan = `${job.title} ${job.description || ""}`;
    const emailMatch = textToScan.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
    if (emailMatch && !emailMatch[0].includes("example.com")) {
      const foundEmail = emailMatch[0];
      UI.drawerDetectedEmail.textContent = foundEmail;
      UI.drawerEmailApplyBanner.style.display = "block";

      const candInfo = (AppState.profile && AppState.profile.personal_information) || {};
      const candName = `${candInfo.first_name || ""} ${candInfo.last_name || ""}`.trim() || "Applicant";
      const subject = encodeURIComponent(`Application for ${job.title} - ${candName}`);
      
      const coverText = (job.application && job.application.cover_letter)
        ? job.application.cover_letter
        : `Dear Hiring Team at ${job.company},\n\nI am writing to express my strong interest in the ${job.title} role.\n\nPlease find my resume attached.\n\nBest regards,\n${candName}`;
      
      const body = encodeURIComponent(coverText);
      UI.btnSendEmailApp.href = `mailto:${foundEmail}?subject=${subject}&body=${body}`;

      if (UI.btnCopyDetectedEmail) {
        UI.btnCopyDetectedEmail.onclick = function(e) {
          e.stopPropagation();
          copyToClipboard(foundEmail, "Recruiter Email", this);
        };
      }
    } else {
      UI.drawerEmailApplyBanner.style.display = "none";
    }
  }

  openDrawer();
};

function openDrawer() {
  UI.inspectorDrawer.classList.add("open");
}

function closeDrawer() {
  UI.inspectorDrawer.classList.remove("open");
}

// Event Listeners
function setupEventListeners() {
  UI.btnCloseDrawer.addEventListener("click", closeDrawer);

  UI.globalSearchInput.addEventListener("input", (e) => {
    AppState.activeFilter.query = e.target.value;
    renderDataGrid();
  });

  UI.filterAtsSource.addEventListener("change", (e) => {
    AppState.activeFilter.source = e.target.value;
    renderDataGrid();
  });

  UI.filterPills.forEach(pill => {
    pill.addEventListener("click", () => {
      UI.filterPills.forEach(p => p.classList.remove("active"));
      pill.classList.add("active");
      AppState.activeFilter.scoreCategory = pill.getAttribute("data-filter-score");
      renderDataGrid();
    });
  });

  UI.btnSyncAll.addEventListener("click", () => {
    refreshAllData(true);
  });

  // Autonomous Web Job Discovery
  async function launchAutonomousDiscovery(locationsStr) {
    const locList = (locationsStr || "Bangladesh, Dhaka, Remote").split(",").map(s => s.trim()).filter(Boolean);
    appendTerminalLine("DISCOVERY", `Launching Autonomous Web Job Discovery (Targets: ${locList.join(", ")})...`, "info");
    try {
      const res = await fetch("/api/crawlers/autonomous-discover", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          locations: locList,
          limit_per_source: 12
        })
      });
      const data = await res.json();
      appendTerminalLine("DISCOVERY", data.message, "success");
      alert("Autonomous Web Discovery initiated! Scanning live network feeds for Bangladesh & Remote jobs...");
    } catch (err) {
      appendTerminalLine("DISCOVERY", `Error: ${err.message}`, "error");
      alert(`Discovery failed: ${err.message}`);
    }
  }

  // Mission Control: Save Search Preferences
  const btnMissionSave = document.getElementById("btn-mission-save-pref");
  if (btnMissionSave) {
    btnMissionSave.addEventListener("click", async () => {
      const rolesRaw = (document.getElementById("mission-input-roles")?.value || "").split(",").map(r => r.trim()).filter(Boolean);
      const locsRaw = (document.getElementById("mission-input-locations")?.value || "").split(",").map(l => l.trim()).filter(Boolean);
      const freshness = parseInt(document.getElementById("mission-select-freshness")?.value || "7", 10);
      const mobility = {
        accept_remote_worldwide: document.getElementById("mission-chk-remote")?.checked ?? true,
        accept_home_country_onsite: document.getElementById("mission-chk-bd")?.checked ?? true,
        accept_foreign_onsite_with_visa: document.getElementById("mission-chk-visa")?.checked ?? true,
        reject_foreign_onsite_without_visa: true
      };

      appendTerminalLine("PREF", "Saving autonomous search preferences & mobility rules...", "info");
      try {
        const res = await fetch("/api/profile/preferences", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            positions: rolesRaw,
            locations: locsRaw,
            max_age_days: freshness,
            mobility: mobility
          })
        });
        const data = await res.json();
        if (res.ok) {
          const feedback = document.getElementById("mission-save-feedback");
          if (feedback) {
            feedback.style.display = "inline";
            setTimeout(() => { feedback.style.display = "none"; }, 3000);
          }
          appendTerminalLine("PREF", `Preferences saved! Tracking ${rolesRaw.length} roles across ${locsRaw.length} locations.`, "success");
        }
      } catch (err) {
        appendTerminalLine("PREF", `Failed to save preferences: ${err.message}`, "error");
      }
    });
  }

  // Mission Control: ⚡ Instant Run Now
  const btnMissionInstant = document.getElementById("btn-mission-instant-run");
  if (btnMissionInstant) {
    btnMissionInstant.addEventListener("click", async () => {
      const rolesRaw = (document.getElementById("mission-input-roles")?.value || "").split(",").map(r => r.trim()).filter(Boolean);
      const locsRaw = (document.getElementById("mission-input-locations")?.value || "").split(",").map(l => l.trim()).filter(Boolean);
      const freshness = parseInt(document.getElementById("mission-select-freshness")?.value || "7", 10);

      appendTerminalLine("INSTANT", `⚡ Launching Instant Run: Crawling live web feeds for [${rolesRaw.join(", ")}] in [${locsRaw.join(", ")}] (<= ${freshness} days)...`, "info");
      btnMissionInstant.disabled = true;
      const originalHtml = btnMissionInstant.innerHTML;
      btnMissionInstant.innerHTML = `<span>⏳ Searching Live Worldwide Feeds...</span>`;

      try {
        const res = await fetch("/api/pipeline/instant-run", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            roles: rolesRaw.length ? rolesRaw : undefined,
            locations: locsRaw.length ? locsRaw : undefined,
            max_age_days: freshness
          })
        });
        const data = await res.json();
        appendTerminalLine("INSTANT", data.message, "success");
        setTimeout(async () => {
          await refreshAllData(false);
          btnMissionInstant.disabled = false;
          btnMissionInstant.innerHTML = originalHtml;
        }, 3500);
      } catch (err) {
        appendTerminalLine("INSTANT", `Instant run failed: ${err.message}`, "error");
        btnMissionInstant.disabled = false;
        btnMissionInstant.innerHTML = originalHtml;
      }
    });
  }

  // 1-Click Master Auto-Pilot Pipeline
  if (UI.btnMasterAutopilot) {
    UI.btnMasterAutopilot.addEventListener("click", async () => {
      appendTerminalLine("AUTOPILOT", "Master Auto-Pilot Pipeline triggered: Pruning expired leads, discovering fresh postings (<=7 days), and evaluating with Groq AI...", "info");
      try {
        const res = await fetch("/api/pipeline/autopilot", { method: "POST" });
        const data = await res.json();
        appendTerminalLine("AUTOPILOT", data.message, "success");
      } catch (err) {
        appendTerminalLine("AUTOPILOT", `Pipeline trigger error: ${err.message}`, "error");
      }
    });
  }

  // 1-Click Purge All Dummy & Stale Data
  const btnPurge = document.getElementById("btn-purge-dummy");
  if (btnPurge) {
    btnPurge.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to wipe all dummy and test data? This resets the database to a clean slate.")) return;
      appendTerminalLine("SYSTEM", "Purging all dummy and test data from database...", "warn");
      try {
        const res = await fetch("/api/pipeline/reset-all", { method: "POST" });
        const data = await res.json();
        appendTerminalLine("SYSTEM", data.message, "success");
        await refreshAllData(false);
      } catch (err) {
        appendTerminalLine("SYSTEM", `Failed to purge data: ${err.message}`, "error");
      }
    });
  }

  if (UI.btnAutoDiscoverTop) {
    UI.btnAutoDiscoverTop.addEventListener("click", () => {
      launchAutonomousDiscovery("Bangladesh, Dhaka, Remote");
    });
  }

  if (UI.btnRunAutoDiscover) {
    UI.btnRunAutoDiscover.addEventListener("click", () => {
      const loc = UI.inputDiscoverLocation ? UI.inputDiscoverLocation.value.trim() : "Bangladesh, Dhaka, Remote";
      launchAutonomousDiscovery(loc);
    });
  }

  UI.btnBatchEval.addEventListener("click", async () => {
    appendTerminalLine("EVAL", "Launching batch evaluation on unscored listings...", "info");
    try {
      const res = await fetch("/api/evaluate/all-pending/run", { method: "POST" });
      const data = await res.json();
      appendTerminalLine("EVAL", data.message, "success");
    } catch (err) {
      appendTerminalLine("EVAL", `Error: ${err}`, "error");
    }
  });

  UI.btnClearTerminal.addEventListener("click", () => {
    UI.terminalOutput.innerHTML = "";
  });

  // Generate Cover Letter
  UI.btnGenerateLetter.addEventListener("click", async () => {
    if (!AppState.selectedJobId) return;
    UI.drawerCoverLetter.textContent = "Synthesizing customized 3-paragraph letter...";
    try {
      const res = await fetch(`/api/evaluate/cover-letter/${AppState.selectedJobId}`, { method: "POST" });
      const data = await res.json();
      UI.drawerCoverLetter.textContent = data.cover_letter;
      appendTerminalLine("COVER", `Generated targeted letter for Job #${AppState.selectedJobId}`, "success");
      fetchJobs();
    } catch {
      UI.drawerCoverLetter.textContent = "Failed to draft letter.";
    }
  });

  // Copy Cover Letter
  if (UI.btnCopyLetter) {
    UI.btnCopyLetter.addEventListener("click", () => {
      const letter = (UI.drawerCoverLetter ? UI.drawerCoverLetter.textContent : "").trim();
      if (!letter || letter.startsWith("Click 'Draft Letter'") || letter.startsWith("Synthesizing")) {
        appendTerminalLine("CLIPBOARD", "Please draft a cover letter first before copying.", "warning");
        return;
      }
      copyToClipboard(letter, "Cover Letter", UI.btnCopyLetter);
    });
  }

  // Direct Portal Apply
  if (UI.btnDrawerOpenPortal) {
    UI.btnDrawerOpenPortal.addEventListener("click", () => {
      if (!AppState.selectedJobId) return;
      openCareerPortal(AppState.selectedJobId);
    });
  }

  // Mark as Applied
  if (UI.btnDrawerMarkApplied) {
    UI.btnDrawerMarkApplied.addEventListener("click", () => {
      if (!AppState.selectedJobId) return;
      trackJobStage(AppState.selectedJobId, "APPLIED");
    });
  }

  // Link Liveness Check
  if (UI.btnDrawerVerifyLive) {
    UI.btnDrawerVerifyLive.addEventListener("click", () => {
      if (!AppState.selectedJobId) return;
      verifyJobLiveness(AppState.selectedJobId);
    });
  }

  // Application Stage Selector Tags
  document.querySelectorAll(".stage-tag-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!AppState.selectedJobId) return;
      trackJobStage(AppState.selectedJobId, btn.dataset.stage);
    });
  });

  // Top Banner Candidate CV Upload & Re-Ranking
  async function uploadCandidateCV(file) {
    if (!file) return;
    if (UI.bannerCvStatusText) {
      UI.bannerCvStatusText.textContent = `⏳ Uploading & Analyzing ${file.name}...`;
      UI.bannerCvStatusText.style.color = "var(--accent-amber)";
    }
    appendTerminalLine("CV_MATCHER", `Uploading resume '${file.name}' to re-calculate personalized job matches...`, "info");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch("/api/profile/upload-resume", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");

      if (UI.bannerCvStatusText) {
        UI.bannerCvStatusText.textContent = `✓ Active CV: ${file.name}`;
        UI.bannerCvStatusText.style.color = "var(--accent-emerald)";
      }
      appendTerminalLine("CV_MATCHER", `✓ Successfully parsed CV! Candidate profile synchronized. Re-ranking all jobs...`, "success");

      await fetchProfile();
      await fetchJobs();
      appendTerminalLine("CV_MATCHER", `🌟 Feed updated: Top jobs sorted by best fit with ${file.name}.`, "success");
    } catch (err) {
      if (UI.bannerCvStatusText) {
        UI.bannerCvStatusText.textContent = `✕ Failed: ${err.message}`;
        UI.bannerCvStatusText.style.color = "var(--accent-rose)";
      }
      appendTerminalLine("CV_MATCHER", `Upload error: ${err.message}`, "error");
      alert(`CV Upload Error: ${err.message}`);
    }
  }

  if (UI.bannerCvFileInput) {
    UI.bannerCvFileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) uploadCandidateCV(file);
    });
  }

  if (UI.bannerCvDropzone) {
    UI.bannerCvDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      UI.bannerCvDropzone.classList.add("dragover");
    });
    UI.bannerCvDropzone.addEventListener("dragleave", () => {
      UI.bannerCvDropzone.classList.remove("dragover");
    });
    UI.bannerCvDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      UI.bannerCvDropzone.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadCandidateCV(e.dataTransfer.files[0]);
      }
    });
  }

  if (UI.btnReRankCv) {
    UI.btnReRankCv.addEventListener("click", async () => {
      appendTerminalLine("CV_MATCHER", "Re-scoring and re-ranking all job vacancies against current CV profile...", "info");
      const origHtml = UI.btnReRankCv.innerHTML;
      UI.btnReRankCv.innerHTML = `<span>⏳ Re-Scoring...</span>`;
      UI.btnReRankCv.disabled = true;
      try {
        await fetchProfile();
        await fetchJobs();
        appendTerminalLine("CV_MATCHER", `✓ Re-scoring complete. ${AppState.jobs.length} jobs evaluated against candidate profile.`, "success");
      } finally {
        UI.btnReRankCv.innerHTML = origHtml;
        UI.btnReRankCv.disabled = false;
      }
    });
  }

  // Resume File Upload & AI Generation Handlers (Profile Tab)
  const fileInput = document.getElementById("input-resume-file");
  const btnBrowse = document.getElementById("btn-browse-resume");
  const uploadCard = document.getElementById("resume-upload-card");
  const uploadStatusRow = document.getElementById("upload-status-row");
  const uploadedFilename = document.getElementById("uploaded-filename");
  const btnParseAI = document.getElementById("btn-parse-resume-ai");

  let selectedResumeFile = null;

  if (btnBrowse && fileInput) {
    btnBrowse.addEventListener("click", () => fileInput.click());
  }

  function handleFileSelected(file) {
    if (!file) return;
    selectedResumeFile = file;
    if (uploadedFilename) uploadedFilename.textContent = file.name;
    if (uploadStatusRow) uploadStatusRow.style.display = "flex";
  }

  if (fileInput) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      handleFileSelected(file);
    });
  }

  if (uploadCard) {
    uploadCard.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadCard.classList.add("dragover");
    });
    uploadCard.addEventListener("dragleave", () => {
      uploadCard.classList.remove("dragover");
    });
    uploadCard.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadCard.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        handleFileSelected(e.dataTransfer.files[0]);
      }
    });
  }

  if (btnParseAI) {
    btnParseAI.addEventListener("click", async () => {
      if (!selectedResumeFile) {
        alert("Please select or drop a resume file first.");
        return;
      }

      const originalHtml = btnParseAI.innerHTML;
      btnParseAI.disabled = true;
      btnParseAI.innerHTML = `<span>⏳ Extracting Text &amp; Generating Profile with Groq AI...</span>`;
      appendTerminalLine("RESUME", `Uploading '${selectedResumeFile.name}' for AI text extraction & schema synthesis...`, "info");

      try {
        const formData = new FormData();
        formData.append("file", selectedResumeFile);

        const res = await fetch("/api/profile/upload-resume", {
          method: "POST",
          body: formData
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to parse resume");

        const parsed = data.profile;
        AppState.profile = parsed;

        // Populate visual fields
        const info = parsed.personal_information || {};
        const elName = document.getElementById("vis-cand-name");
        const elTitle = document.getElementById("vis-cand-title");
        const elEmail = document.getElementById("vis-cand-email");
        const elLoc = document.getElementById("vis-cand-location");
        const elSkills = document.getElementById("vis-cand-skills");
        const elSum = document.getElementById("vis-cand-summary");

        if (elName) elName.value = `${info.first_name || ""} ${info.last_name || ""}`.trim();
        if (elTitle && info.headline) elTitle.value = info.headline;
        if (elEmail && info.email) elEmail.value = info.email;
        if (elLoc) elLoc.value = `${info.city || ""}, ${info.country || ""}`.replace(/^, |, $/g, "");

        if (elSkills && parsed.skills) {
          const allSkills = [
            ...(parsed.skills.languages || []),
            ...(parsed.skills.frameworks_and_backend || []),
            ...(parsed.skills.ai_and_data || [])
          ];
          if (allSkills.length) elSkills.value = allSkills.join(", ");
        }
        if (elSum && parsed.summary) elSum.value = parsed.summary.trim();

        // Populate JSON editor
        if (UI.profileEditor) {
          UI.profileEditor.value = JSON.stringify(parsed, null, 2);
        }

        // Also suggest role in Mission Control if available
        const missionRoles = document.getElementById("mission-input-roles");
        if (missionRoles && info.headline) {
          const cleanHeadline = info.headline.replace(/&amp;/g, "&");
          if (!missionRoles.value.includes(cleanHeadline)) {
            missionRoles.value = `${cleanHeadline}, ${missionRoles.value}`;
          }
        }

        appendTerminalLine("RESUME", `✓ Successfully parsed '${selectedResumeFile.name}'! Candidate schema generated and active.`, "success");
        await fetchProfile();
        await fetchJobs();
        alert(`✓ Resume '${selectedResumeFile.name}' parsed successfully!\nCandidate Profile JSON schema has been generated and saved. All job vacancies re-ranked for your CV!`);
      } catch (err) {
        appendTerminalLine("RESUME", `Error parsing resume: ${err.message}`, "error");
        alert("Failed to parse resume: " + err.message);
      } finally {
        btnParseAI.disabled = false;
        btnParseAI.innerHTML = originalHtml;
      }
    });
  }

  // Save Visual Candidate Profile
  const btnSaveVisual = document.getElementById("btn-save-visual-profile");
  if (btnSaveVisual) {
    btnSaveVisual.addEventListener("click", async () => {
      let current = AppState.profile || {};
      if (!current.personal_information) current.personal_information = {};
      if (!current.skills) current.skills = {};

      const fullName = (document.getElementById("vis-cand-name")?.value || "").trim();
      const parts = fullName.split(" ");
      current.personal_information.first_name = parts[0] || "";
      current.personal_information.last_name = parts.slice(1).join(" ") || "";
      current.personal_information.headline = document.getElementById("vis-cand-title")?.value || "";
      current.personal_information.email = document.getElementById("vis-cand-email")?.value || "";

      const loc = (document.getElementById("vis-cand-location")?.value || "").split(",");
      current.personal_information.city = loc[0]?.trim() || "Dhaka";
      current.personal_information.country = loc[1]?.trim() || "Bangladesh";

      const skillsList = (document.getElementById("vis-cand-skills")?.value || "").split(",").map(s => s.trim()).filter(Boolean);
      current.skills.languages = skillsList.slice(0, 5);
      current.skills.frameworks_and_backend = skillsList.slice(5);

      current.summary = document.getElementById("vis-cand-summary")?.value || "";

      try {
        const res = await fetch("/api/profile", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(current)
        });
        if (res.ok) {
          AppState.profile = current;
          if (UI.profileEditor) UI.profileEditor.value = JSON.stringify(current, null, 2);
          alert("Candidate Profile updated successfully!");
          appendTerminalLine("PROFILE", "Candidate profile saved & synced with AI evaluation engine.", "success");
        }
      } catch (err) {
        alert("Failed to save profile: " + err.message);
      }
    });
  }

  // Save Profile (Raw Editor)
  UI.btnSaveProfile.addEventListener("click", async () => {
    try {
      const parsed = JSON.parse(UI.profileEditor.value);
      const res = await fetch("/api/profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parsed)
      });
      if (res.ok) alert("Candidate Profile saved successfully.");
    } catch {
      alert("Invalid JSON format in editor.");
    }
  });

  // Provider Change Handler
  if (UI.settingProvider) {
    UI.settingProvider.addEventListener("change", (e) => {
      const p = e.target.value;
      if (UI.testConnectionResult) UI.testConnectionResult.style.display = "none";
      updateProviderUI(p, AppState.settingsData);
    });
  }

  // API Key Input → Auto-fetch Live Models on blur (debounced)
  if (UI.settingApiKey) {
    UI.settingApiKey.addEventListener("blur", () => {
      const key = UI.settingApiKey.value.trim();
      const provider = UI.settingProvider ? UI.settingProvider.value : "groq";
      if (key.length >= 8) {
        appendTerminalLine("ROUTER", `API key entered. Fetching live model list from ${provider.toUpperCase()}...`, "info");
        fetchModelsForProvider(provider, key);
        // Update status indicator
        if (UI.settingKeyStatus) {
          UI.settingKeyStatus.textContent = `🔑 Key entered. Testing availability...`;
          UI.settingKeyStatus.style.color = "#93c5fd";
        }
      }
    });
    // Also trigger on paste
    UI.settingApiKey.addEventListener("paste", () => {
      setTimeout(() => {
        const key = UI.settingApiKey.value.trim();
        const provider = UI.settingProvider ? UI.settingProvider.value : "groq";
        if (key.length >= 8) {
          fetchModelsForProvider(provider, key);
        }
      }, 100);
    });
  }

  // Ollama host change → refetch local models
  if (UI.settingHost) {
    UI.settingHost.addEventListener("blur", () => {
      const provider = UI.settingProvider ? UI.settingProvider.value : "groq";
      if (provider === "ollama") {
        fetchModelsForProvider("ollama", "", UI.settingHost.value.trim());
      }
    });
  }

  // Toggle API Key Visibility
  if (UI.btnToggleKeyVisibility && UI.settingApiKey) {
    UI.btnToggleKeyVisibility.addEventListener("click", () => {
      if (UI.settingApiKey.type === "password") {
        UI.settingApiKey.type = "text";
        UI.btnToggleKeyVisibility.textContent = "🔒";
      } else {
        UI.settingApiKey.type = "password";
        UI.btnToggleKeyVisibility.textContent = "👁";
      }
    });
  }

  // Live Test Connection Handler
  if (UI.btnTestConnection) {
    UI.btnTestConnection.addEventListener("click", async () => {
      const provider = UI.settingProvider ? UI.settingProvider.value : "groq";
      const model = UI.settingModel ? UI.settingModel.value : "llama-3.3-70b-versatile";
      const apiKey = UI.settingApiKey ? UI.settingApiKey.value.trim() : "";
      const host = UI.settingHost ? UI.settingHost.value.trim() : "";

      const btn = UI.btnTestConnection;
      const originalHtml = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<span style="display: inline-block; width: 12px; height: 12px; border: 2px solid #fff; border-top-color: transparent; border-radius: 50%; animation: spin 0.8s linear infinite;"></span> <span>Testing...</span>`;

      if (UI.testConnectionResult) {
        UI.testConnectionResult.style.display = "none";
      }
      appendTerminalLine("ROUTER", `Testing live connection to ${provider.toUpperCase()} (${model})...`, "info");

      try {
        const payload = {
          provider,
          model,
          api_key: apiKey || undefined,
          ollama_host: host || undefined
        };

        const res = await fetch("/api/settings/test-connection", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (UI.testConnectionResult) {
          UI.testConnectionResult.style.display = "block";
          if (data.success) {
            UI.testConnectionResult.style.background = "rgba(16, 185, 129, 0.12)";
            UI.testConnectionResult.style.border = "1px solid rgba(16, 185, 129, 0.35)";
            UI.testConnectionResult.style.color = "#34d399";
            UI.testConnectionResult.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                <span style="font-weight: 700;">✓ Live Probe Succeeded</span>
                <span style="background: rgba(16, 185, 129, 0.25); color: #6ee7b7; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 700; font-size: 0.72rem;">${data.latency_ms} ms</span>
              </div>
              <div style="font-size: 0.76rem; color: #cbd5e1;">${data.message}</div>
              <div style="font-size: 0.72rem; color: #94a3b8; margin-top: 0.25rem; font-family: monospace;">Sample reply: "${data.reply}"</div>
            `;
            appendTerminalLine("ROUTER", `✓ Test passed: ${provider.toUpperCase()} responded in ${data.latency_ms}ms!`, "success");
          } else {
            UI.testConnectionResult.style.background = "rgba(239, 68, 68, 0.12)";
            UI.testConnectionResult.style.border = "1px solid rgba(239, 68, 68, 0.35)";
            UI.testConnectionResult.style.color = "#f87171";
            UI.testConnectionResult.innerHTML = `
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                <span style="font-weight: 700;">✕ Connection Failed (${data.latency_ms || 0} ms)</span>
              </div>
              <div style="font-size: 0.76rem; color: #fca5a5;">${data.error || data.message}</div>
            `;
            appendTerminalLine("ROUTER", `✕ Test failed: ${data.error || data.message}`, "error");
          }
        }
      } catch (err) {
        if (UI.testConnectionResult) {
          UI.testConnectionResult.style.display = "block";
          UI.testConnectionResult.style.background = "rgba(239, 68, 68, 0.12)";
          UI.testConnectionResult.style.border = "1px solid rgba(239, 68, 68, 0.35)";
          UI.testConnectionResult.style.color = "#f87171";
          UI.testConnectionResult.innerHTML = `<div style="font-weight: 700;">✕ Request Error</div><div style="font-size: 0.76rem;">${err.message}</div>`;
        }
        appendTerminalLine("ROUTER", `Error testing connection: ${err.message}`, "error");
      } finally {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    });
  }

  // Save Model Settings
  if (UI.btnSaveSettings) {
    UI.btnSaveSettings.addEventListener("click", async () => {
      const provider = UI.settingProvider ? UI.settingProvider.value : "groq";
      const model = UI.settingModel ? UI.settingModel.value : "llama-3.3-70b-versatile";
      const apiKey = UI.settingApiKey ? UI.settingApiKey.value.trim() : "";
      const host = UI.settingHost ? UI.settingHost.value.trim() : "";

      const payload = {
        provider,
        model,
        api_key: apiKey || undefined,
        ollama_host: host || undefined
      };

      appendTerminalLine("ROUTER", `Saving inference provider: ${provider} (${model})...`, "info");
      try {
        const res = await fetch("/api/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok) {
          if (UI.sidebarActiveModel) {
            UI.sidebarActiveModel.textContent = `${provider}/${model}`;
          }
          appendTerminalLine("ROUTER", `✓ ${data.message}`, "success");
          alert(`✓ Configuration saved!\nInference engine set to ${provider.toUpperCase()} (${model})`);
          if (UI.settingApiKey) UI.settingApiKey.value = "";
          await fetchProfile();
        } else {
          throw new Error(data.detail || "Failed to save configuration");
        }
      } catch (err) {
        appendTerminalLine("ROUTER", `Error: ${err.message}`, "error");
        alert(`Failed to save settings: ${err.message}`);
      }
    });
  }
}

window.setModelPreset = function(modelName) {
  if (UI.settingModel) {
    UI.settingModel.value = modelName;
    appendTerminalLine("ROUTER", `Model preset set to '${modelName}'`, "info");
  }
};

// Crawler Execution Helpers
window.executeCrawl = async function(source, target) {
  appendTerminalLine("CRAWLER", `Triggering direct ingestion for ${source.toUpperCase()}: '${target}'...`, "info");
  try {
    const res = await fetch("/api/crawlers/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source, target, location: "Remote" })
    });
    const data = await res.json();
    appendTerminalLine("CRAWLER", data.message, "success");
  } catch (err) {
    appendTerminalLine("CRAWLER", `Ingestion failure: ${err}`, "error");
  }
};

window.executeCustom = function(source, inputId) {
  const el = document.getElementById(inputId);
  if (!el || !el.value.trim()) return;
  window.executeCrawl(source, el.value.trim());
};

// Direct-From-Source Career Portal & Stage Tracking
window.openCareerPortal = function(jobId) {
  const job = AppState.jobs.find(j => j.id === jobId);
  if (!job || !job.url) return;
  appendTerminalLine("PORTAL", `Navigating directly to verified career portal for ${job.company}: ${job.url}`, "info");
  window.open(job.url, "_blank");
};

window.trackJobStage = async function(jobId, stage) {
  const job = AppState.jobs.find(j => j.id === jobId);
  const company = job ? job.company : `Job #${jobId}`;
  appendTerminalLine("TRACK", `Updating application status for ${company} to [${stage}]...`, "info");
  try {
    const res = await fetch(`/api/applications/track/${jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: stage })
    });
    const data = await res.json();
    appendTerminalLine("TRACK", `✓ ${company} marked as ${stage}`, "success");
    await fetchJobs();
    if (AppState.selectedJobId === jobId) {
      selectJob(jobId);
    }
  } catch (err) {
    appendTerminalLine("TRACK", `Error updating status: ${err}`, "error");
  }
};

window.verifyJobLiveness = async function(jobId) {
  const job = AppState.jobs.find(j => j.id === jobId);
  if (!job) return;
  appendTerminalLine("LIVENESS", `Probing career portal for Job #${jobId} (${job.company})...`, "info");
  if (UI.drawerLivenessBadge) {
    UI.drawerLivenessBadge.innerHTML = `<span>⏳ Probing carrier portal in real-time...</span>`;
  }
  try {
    const res = await fetch(`/api/applications/verify-liveness/${jobId}`, { method: "POST" });
    const data = await res.json();
    const lv = data.liveness;
    const isLive = lv.is_live;
    const icon = isLive ? "🟢" : "🔴";
    const color = isLive ? "#34d399" : "#f87171";
    if (UI.drawerLivenessBadge) {
      UI.drawerLivenessBadge.innerHTML = `<span style="color: ${color}; font-weight: 600;">${icon} ${escapeHtml(lv.message)}</span>`;
    }
    appendTerminalLine("LIVENESS", `${icon} ${job.company}: ${lv.message}`, isLive ? "success" : "error");
    if (!isLive) {
      await fetchJobs();
    }
  } catch (err) {
    if (UI.drawerLivenessBadge) {
      UI.drawerLivenessBadge.innerHTML = `<span style="color: var(--accent-amber);">⚠️ Probe error: ${err}</span>`;
    }
  }
};

function getGhostBadgeHtml(ghost) {
  if (!ghost) return "";
  const cls = ghost.reality_class === "fresh" ? "badge-ghost-fresh" : (ghost.reality_class === "stale" ? "badge-ghost-stale" : "badge-ghost-warning");
  const label = ghost.reality_class === "fresh" ? "🟢 Fresh" : (ghost.reality_class === "stale" ? "🟡 Stale" : "👻 Ghost");
  return `<span class="badge-ghost ${cls}" title="${escapeHtml(ghost.summary)}">${label}</span>`;
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Cover Letter Studio Integration
let selectedStudioJobId = null;
let selectedStudioTone = "technical";

function populateStudioJobSelect() {
  const sel = document.getElementById("studio-job-select");
  if (!sel) return;
  const currVal = sel.value;
  sel.innerHTML = `<option value="">Choose a target job (${AppState.jobs.length} loaded)...</option>` +
    AppState.jobs.slice(0, 80).map(j => {
      const score = j.evaluation ? `[${j.evaluation.score}%]` : `[Unscored]`;
      return `<option value="${j.id}">${escapeHtml(score)} ${escapeHtml(j.company)} - ${escapeHtml(j.title)}</option>`;
    }).join("");
  if (currVal) sel.value = currVal;
}

window.openCoverLetterStudioForJob = function(jobId) {
  window.switchTab("tab-letters");
  const sel = document.getElementById("studio-job-select");
  if (sel) {
    sel.value = String(jobId);
    selectedStudioJobId = jobId;
    updateStudioPreview();
  }
};

function updateStudioPreview() {
  const sel = document.getElementById("studio-job-select");
  const docTitle = document.getElementById("studio-doc-title");
  const textarea = document.getElementById("studio-letter-content");
  if (!sel || !sel.value) return;
  selectedStudioJobId = parseInt(sel.value, 10);
  const job = AppState.jobs.find(j => j.id === selectedStudioJobId);
  if (job) {
    if (docTitle) docTitle.textContent = `Target: ${job.company} — ${job.title}`;
    if (job.application && job.application.cover_letter) {
      if (textarea) textarea.value = job.application.cover_letter;
      updateStudioWordCount();
    } else {
      if (textarea) textarea.value = `Click 'Synthesize Cover Letter' to generate a bespoke application for ${job.company} (${job.title}) using Groq AI...`;
      updateStudioWordCount();
    }
  }
}

function updateStudioWordCount() {
  const textarea = document.getElementById("studio-letter-content");
  const countEl = document.getElementById("studio-word-count");
  if (!textarea || !countEl) return;
  const words = textarea.value.trim().split(/\s+/).filter(Boolean).length;
  countEl.textContent = `${words} words`;
}

// Setup Studio Listeners
function setupStudioListeners() {
  const sel = document.getElementById("studio-job-select");
  const btnGen = document.getElementById("btn-studio-generate");
  const btnCopy = document.getElementById("btn-studio-copy");
  const btnDownload = document.getElementById("btn-studio-download");
  const textarea = document.getElementById("studio-letter-content");
  const toneChips = document.querySelectorAll(".tone-chip");

  if (sel) {
    sel.addEventListener("change", updateStudioPreview);
  }

  toneChips.forEach(chip => {
    chip.addEventListener("click", () => {
      toneChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      selectedStudioTone = chip.getAttribute("data-tone") || "technical";
      appendTerminalLine("STUDIO", `Cover Letter persona updated: ${chip.textContent.trim()}`, "info");
    });
  });

  if (textarea) {
    textarea.addEventListener("input", updateStudioWordCount);
  }

  if (btnGen) {
    btnGen.addEventListener("click", async () => {
      if (!selectedStudioJobId) {
        alert("Please select a target job first.");
        return;
      }
      appendTerminalLine("STUDIO", `Synthesizing tailored cover letter with Groq Cloud AI (${selectedStudioTone})...`, "info");
      if (textarea) textarea.value = "Synthesizing custom 3-paragraph letter with Groq Cloud AI...";
      try {
        const res = await fetch(`/api/evaluate/cover-letter/${selectedStudioJobId}`, { method: "POST" });
        const data = await res.json();
        if (textarea) textarea.value = data.cover_letter;
        updateStudioWordCount();
        appendTerminalLine("STUDIO", "Cover letter successfully generated!", "success");
        fetchJobs();
      } catch (err) {
        if (textarea) textarea.value = `Error generating letter: ${err.message}`;
        appendTerminalLine("STUDIO", `Failed to generate letter: ${err.message}`, "error");
      }
    });
  }

  if (btnCopy) {
    btnCopy.addEventListener("click", () => {
      if (!textarea || !textarea.value) return;
      navigator.clipboard.writeText(textarea.value);
      const originalText = btnCopy.innerHTML;
      btnCopy.innerHTML = "<span>✓ Copied!</span>";
      setTimeout(() => { btnCopy.innerHTML = originalText; }, 2000);
    });
  }

  if (btnDownload) {
    btnDownload.addEventListener("click", () => {
      if (!textarea || !textarea.value) return;
      const job = AppState.jobs.find(j => j.id === selectedStudioJobId);
      const compName = job ? job.company.replace(/[^a-zA-Z0-9]/g, "_") : "Cover_Letter";
      const blob = new Blob([textarea.value], { type: "text/plain;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${compName}_Cover_Letter.txt`;
      a.click();
    });
  }
}

setTimeout(setupStudioListeners, 400);
