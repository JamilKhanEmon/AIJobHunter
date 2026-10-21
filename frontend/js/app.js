/**
 * JobHunter Pro - Enterprise Application Controller.
 */

// Application State
const AppState = {
  jobs: [],
  stats: {},
  profile: null,
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
  btnDrawerDryRun: document.getElementById("btn-drawer-dry-run"),
  btnDrawerLiveApply: document.getElementById("btn-drawer-live-apply")
};

// Bootstrap
document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupKeyboardShortcuts();
  setupWebSocket();
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
      }
    }

    if (resSettings.ok) {
      const s = await resSettings.json();
      AppState.settingsData = s;
      if (UI.sidebarActiveModel) {
        UI.sidebarActiveModel.textContent = `${s.provider}/${s.model}`;
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

function updateProviderUI(provider, settingsData) {
  const p = (provider || "groq").toLowerCase();
  const meta = PROVIDERS_CATALOG[p] || PROVIDERS_CATALOG.groq;
  const s = settingsData || AppState.settingsData || {};
  const provInfo = (s.providers && s.providers[p]) ? s.providers[p] : null;

  if (UI.settingProviderBadge) {
    UI.settingProviderBadge.textContent = meta.badge;
    UI.settingProviderBadge.style.color = meta.badgeColor;
    UI.settingProviderBadge.style.borderColor = meta.badgeColor;
  }

  if (p === "ollama") {
    if (UI.providerKeyGroup) UI.providerKeyGroup.style.display = "none";
    if (UI.ollamaHostGroup) UI.ollamaHostGroup.style.display = "flex";
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
      } else {
        UI.settingKeyStatus.textContent = `✕ No key configured. Enter your ${meta.name} key above.`;
        UI.settingKeyStatus.style.color = "#fbbf24";
      }
    }
  }

  // Populate dynamic clickable preset badges
  if (UI.settingModelPresets) {
    UI.settingModelPresets.innerHTML = "";
    const label = document.createElement("span");
    label.style.fontSize = "0.72rem";
    label.style.color = "var(--text-muted)";
    label.style.marginRight = "0.3rem";
    label.textContent = "Recommended Models:";
    UI.settingModelPresets.appendChild(label);

    meta.presets.forEach(preset => {
      const chip = document.createElement("button");
      chip.type = "button";
      chip.className = "chip-btn";
      chip.style.padding = "0.2rem 0.55rem";
      chip.style.fontSize = "0.72rem";
      chip.textContent = preset;
      chip.onclick = () => {
        if (UI.settingModel) {
          UI.settingModel.value = preset;
          appendTerminalLine("ROUTER", `Model preset set to '${preset}' for ${p.toUpperCase()}`, "info");
        }
      };
      UI.settingModelPresets.appendChild(chip);
    });
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

// Render Master Data Grid
function renderDataGrid() {
  const query = AppState.activeFilter.query.toLowerCase();
  const source = AppState.activeFilter.source.toLowerCase();
  const scoreCat = AppState.activeFilter.scoreCategory;

  const filtered = AppState.jobs.filter(job => {
    // Query
    const matchesQuery = !query ||
      job.title.toLowerCase().includes(query) ||
      job.company.toLowerCase().includes(query) ||
      (job.location && job.location.toLowerCase().includes(query));

    // Source
    const matchesSource = !source || (job.source && job.source.toLowerCase() === source);

    // Score Filter
    let matchesScore = true;
    const score = job.evaluation ? job.evaluation.score : null;
    if (scoreCat === "high") matchesScore = score !== null && score >= 80;
    else if (scoreCat === "mid") matchesScore = score !== null && score >= 60 && score < 80;
    else if (scoreCat === "unscored") matchesScore = score === null;

    return matchesQuery && matchesSource && matchesScore;
  });

  // Always update Kanban and Studio Select
  renderKanbanBoard();
  populateStudioJobSelect();

  if (filtered.length === 0) {
    UI.jobsTbody.innerHTML = `
      <tr>
        <td colspan="6" style="text-align: center; color: var(--text-muted); padding: 4rem;">
          No matching listings found. Try adjusting filters or launch an ingestion crawl.
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

    // Score Gauge Pill
    let scorePill = `<span class="score-pill score-none">Unscored</span>`;
    if (job.evaluation) {
      const sc = job.evaluation.score;
      const cls = sc >= 80 ? "score-high" : (sc >= 60 ? "score-mid" : "score-low");
      scorePill = `<span class="score-pill ${cls}">${sc}% ${job.evaluation.verdict}</span>`;
    }

    // Stage
    const stage = job.application ? job.application.status : (job.status || "DISCOVERED");

    return `
      <tr class="clickable-row ${isSelected ? 'selected' : ''}" onclick="selectJob(${job.id})">
        <td>
          <div class="company-cell">
            <div class="company-avatar" style="background: ${getCompanyGradient(job.company)}; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">${initial}</div>
            <div class="job-identity">
              <div style="display: flex; align-items: center; gap: 0.45rem;">
                <span class="job-role">${escapeHtml(job.title)}</span>
                <span class="freshness-pill"><span class="autopilot-pulse-dot" style="width: 5px; height: 5px;"></span> Fresh</span>
              </div>
              <span class="job-company">${escapeHtml(job.company)}</span>
            </div>
          </div>
        </td>
        <td>
          <span class="badge ${sourceClass}">${escapeHtml(job.source || "ATS")}</span>
        </td>
        <td>
          <span style="font-size: 0.82rem; color: var(--text-secondary); display: flex; align-items: center; gap: 0.35rem;">
            ${job.remote ? '<span style="color: #34d399; font-weight: 700;">🌐 Remote</span>' : escapeHtml(job.location || "On-site")}
          </span>
        </td>
        <td>${scorePill}</td>
        <td>
          <span style="font-size: 0.74rem; font-family: 'JetBrains Mono', monospace; color: var(--text-muted); background: rgba(255,255,255,0.03); padding: 0.15rem 0.45rem; border-radius: 4px; border: 1px solid var(--border-subtle);">
            ${escapeHtml(stage)}
          </span>
        </td>
        <td style="text-align: right;">
          <div class="row-actions-group">
            <button class="row-action-btn btn-apply-fast" title="1-Click Dry-Run Auto-Apply" onclick="event.stopPropagation(); triggerQuickApply(${job.id});">
              ⚡ Apply
            </button>
            <button class="row-action-btn" title="AI Cover Letter Studio" onclick="event.stopPropagation(); openCoverLetterStudioForJob(${job.id});">
              📄 Letter
            </button>
            <button class="row-action-btn" title="Inspect Job Details" onclick="event.stopPropagation(); selectJob(${job.id});">
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
          <button class="row-action-btn btn-apply-fast" style="padding: 0.2rem 0.45rem; font-size: 0.68rem;" onclick="event.stopPropagation(); triggerQuickApply(${job.id});">
            ⚡ Quick Apply
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

  // Score
  if (job.evaluation) {
    const sc = job.evaluation.score;
    UI.drawerGauge.textContent = sc;
    UI.drawerGauge.style.borderColor = sc >= 80 ? "var(--accent-emerald)" : (sc >= 60 ? "var(--accent-amber)" : "var(--accent-rose)");
    UI.drawerGauge.style.color = sc >= 80 ? "var(--accent-emerald)" : (sc >= 60 ? "var(--accent-amber)" : "var(--accent-rose)");
    UI.drawerVerdict.textContent = `${job.evaluation.verdict} (${sc}% Match)`;
    UI.drawerRationale.textContent = job.evaluation.full_rationale || "Fit evaluated against candidate background.";

    // Strengths
    UI.drawerStrengths.innerHTML = (job.evaluation.pros || ["Candidate background demonstrates solid baseline."])
      .map(p => `<li>${escapeHtml(p)}</li>`).join("");

    // Gaps
    UI.drawerGaps.innerHTML = (job.evaluation.cons && job.evaluation.cons.length > 0)
      ? job.evaluation.cons.map(c => `<li>${escapeHtml(c)}</li>`).join("")
      : `<li>No critical qualification gaps identified.</li>`;
  } else {
    UI.drawerGauge.textContent = "--";
    UI.drawerGauge.style.borderColor = "var(--border-medium)";
    UI.drawerGauge.style.color = "var(--text-muted)";
    UI.drawerVerdict.textContent = "PENDING EVALUATION";
    UI.drawerRationale.textContent = "Run evaluation to assess technical alignment and dealbreakers.";
    UI.drawerStrengths.innerHTML = `<li>Click 'Run Batch Evaluation' to calculate fit.</li>`;
    UI.drawerGaps.innerHTML = `<li>Awaiting evaluation data.</li>`;
  }

  // Cover Letter
  if (job.application && job.application.cover_letter) {
    UI.drawerCoverLetter.textContent = job.application.cover_letter;
  } else {
    UI.drawerCoverLetter.textContent = "Click 'Draft Letter' to generate a targeted letter aligned with this job.";
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

  // Dry Run Apply
  UI.btnDrawerDryRun.addEventListener("click", () => {
    if (!AppState.selectedJobId) return;
    launchApplication(AppState.selectedJobId, true);
  });

  // Live Apply
  UI.btnDrawerLiveApply.addEventListener("click", () => {
    if (!AppState.selectedJobId) return;
    if (confirm("Execute live submission on this job?")) {
      launchApplication(AppState.selectedJobId, false);
    }
  });

  // Resume File Upload & AI Generation Handlers
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
        alert(`✓ Resume '${selectedResumeFile.name}' parsed successfully!\nCandidate Profile JSON schema has been generated and saved.`);
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
      const meta = PROVIDERS_CATALOG[p] || PROVIDERS_CATALOG.groq;
      if (UI.settingModel) {
        UI.settingModel.value = meta.defaultModel;
      }
      if (UI.testConnectionResult) UI.testConnectionResult.style.display = "none";
      updateProviderUI(p, AppState.settingsData);
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

async function launchApplication(jobId, dryRun = true) {
  appendTerminalLine("APPLY", `Dispatching browser automation bot (Job #${jobId}, DryRun: ${dryRun})...`, "info");
  try {
    const res = await fetch(`/api/automation/apply/${jobId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: dryRun, headless: false })
    });
    const data = await res.json();
    appendTerminalLine("APPLY", data.message, "success");
  } catch (err) {
    appendTerminalLine("APPLY", `Application error: ${err}`, "error");
  }
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

// Quick 1-Click Fast Apply from table row or kanban card
window.triggerQuickApply = function(jobId) {
  const job = AppState.jobs.find(j => j.id === jobId);
  const company = job ? job.company : `Job #${jobId}`;
  appendTerminalLine("AUTOPILOT", `Triggering fast dry-run apply for ${company}...`, "info");
  launchApplication(jobId, true);
};

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
