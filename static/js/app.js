// ═══════════════════════════════════════════════════════════════════════════
// FarmAI — Main Application Logic
// ═══════════════════════════════════════════════════════════════════════════

const API = "";  // same origin

// ── State ─────────────────────────────────────────────────────────────────
let currentLang = localStorage.getItem("farmai_lang") || "en";
let histSkip = 0;
const HIST_LIMIT = 50;

// ── Boot ──────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  applyLang(currentLang);
  loadOptions();
  setupListeners();
  setupScrollAnimations();
  loadModelInfo();
});

// ═══════════════════════════════════════════════════════════════════════════
// LANGUAGE TOGGLE
// ═══════════════════════════════════════════════════════════════════════════

function applyLang(lang) {
  currentLang = lang;
  localStorage.setItem("farmai_lang", lang);
  document.documentElement.lang = lang === "hi" ? "hi" : "en";

  document.querySelectorAll("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (T[lang] && T[lang][key]) {
      if (el.tagName === "INPUT" && el.type !== "number") {
        el.placeholder = T[lang][key];
      } else {
        el.textContent = T[lang][key];
      }
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// LOAD DROPDOWN OPTIONS FROM API
// ═══════════════════════════════════════════════════════════════════════════

async function loadOptions() {
  try {
    const [states, crops, seasons] = await Promise.all([
      fetch(`${API}/options/states`).then((r) => r.json()),
      fetch(`${API}/options/crops`).then((r) => r.json()),
      fetch(`${API}/options/seasons`).then((r) => r.json()),
    ]);

    populateSelect("stateSelect", states);
    populateSelect("cropSelect", crops);
    populateSelect("seasonSelect", seasons);

    // Historical filters too
    populateSelect("histState", states);
    populateSelect("histCrop", crops);
    populateSelect("histSeason", seasons);
  } catch (e) {
    console.error("Failed to load options:", e);
  }
}

function populateSelect(id, items) {
  const sel = document.getElementById(id);
  // Keep first option (placeholder)
  const placeholder = sel.options[0];
  sel.innerHTML = "";
  sel.appendChild(placeholder);
  items.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item;
    opt.textContent = item;
    sel.appendChild(opt);
  });
}

// ── Load districts when state changes ────────────────────────────────────
async function loadDistricts(state) {
  const sel = document.getElementById("districtSelect");
  sel.innerHTML = `<option value="">${T[currentLang].select}</option>`;
  if (!state) return;

  try {
    const districts = await fetch(
      `${API}/options/districts?state=${encodeURIComponent(state)}`
    ).then((r) => r.json());
    districts.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d;
      opt.textContent = d;
      sel.appendChild(opt);
    });
  } catch (e) {
    console.error("Failed to load districts:", e);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// MODEL INFO
// ═══════════════════════════════════════════════════════════════════════════

async function loadModelInfo() {
  try {
    const info = await fetch(`${API}/model/info`).then((r) => r.json());
    const r2 = info.r2;
    const pct = Math.round(r2 * 100);
    document.getElementById("r2Fill").style.width = pct + "%";
    document.getElementById("r2Value").textContent = r2.toFixed(4);
  } catch (e) {
    console.error("Failed to load model info:", e);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// PREDICTION
// ═══════════════════════════════════════════════════════════════════════════

async function makePrediction() {
  const state = document.getElementById("stateSelect").value;
  const district = document.getElementById("districtSelect").value;
  const crop = document.getElementById("cropSelect").value;
  const season = document.getElementById("seasonSelect").value;
  const year = parseInt(document.getElementById("yearInput").value);
  const area = parseFloat(document.getElementById("areaInput").value);

  if (!state || !district || !crop || !season || !year || !area) {
    alert(currentLang === "hi" ? "कृपया सभी फ़ील्ड भरें।" : "Please fill all fields.");
    return;
  }

  const btn = document.getElementById("predictBtn");
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner"></span> ${T[currentLang].pred_loading}`;

  try {
    const resp = await fetch(`${API}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        state_name: state,
        district_name: district,
        crop: crop,
        season: season,
        crop_year: year,
        area: area,
      }),
    });

    if (!resp.ok) throw new Error("Prediction failed");
    const data = await resp.json();
    showResult(data);
  } catch (e) {
    alert(T[currentLang].error);
    console.error(e);
  } finally {
    btn.disabled = false;
    btn.innerHTML = T[currentLang].pred_btn;
  }
}

function showResult(data) {
  document.getElementById("predictForm").style.display = "none";

  const container = document.getElementById("resultContainer");
  container.classList.add("visible");

  // Animate value counting up
  const valEl = document.getElementById("resultValue");
  animateNumber(valEl, 0, Math.round(data.predicted_production), 1200);

  // Match badge
  const badgeEl = document.getElementById("matchBadge");
  const descEl = document.getElementById("matchDesc");
  if (data.has_historical_match) {
    badgeEl.innerHTML = `<span class="match-badge success">✅ ${T[currentLang].res_match}</span>`;
    descEl.textContent = T[currentLang].res_match_desc;
  } else {
    badgeEl.innerHTML = `<span class="match-badge warning">⚠️ ${T[currentLang].res_no_match}</span>`;
    descEl.textContent = T[currentLang].res_no_match_desc;
  }

  // Historical matches table
  const histSection = document.getElementById("histMatchesSection");
  const tbody = document.getElementById("histMatchesBody");
  tbody.innerHTML = "";

  if (data.historical_matches && data.historical_matches.length > 0) {
    histSection.style.display = "block";
    data.historical_matches.forEach((m) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${m.crop_year}</td>
        <td>${numberFormat(m.area)}</td>
        <td>${numberFormat(m.production)}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    histSection.style.display = "none";
  }

  // Scroll to result
  container.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetPrediction() {
  document.getElementById("predictForm").style.display = "block";
  document.getElementById("resultContainer").classList.remove("visible");
  document.getElementById("predictForm").scrollIntoView({ behavior: "smooth" });
}

// ═══════════════════════════════════════════════════════════════════════════
// HISTORICAL DATA
// ═══════════════════════════════════════════════════════════════════════════

async function searchHistorical(append = false) {
  if (!append) histSkip = 0;

  const state = document.getElementById("histState").value;
  const crop = document.getElementById("histCrop").value;
  const season = document.getElementById("histSeason").value;

  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (crop) params.set("crop", crop);
  if (season) params.set("season", season);
  params.set("skip", histSkip);
  params.set("limit", HIST_LIMIT);

  const tbody = document.getElementById("histTableBody");
  if (!append) {
    tbody.innerHTML = `<tr><td colspan="8" class="hist-empty">${T[currentLang].hist_loading}</td></tr>`;
  }

  try {
    const data = await fetch(`${API}/historical?${params}`).then((r) => r.json());

    if (!append) tbody.innerHTML = "";

    if (data.length === 0 && !append) {
      tbody.innerHTML = `<tr><td colspan="8" class="hist-empty">${T[currentLang].hist_no_data}</td></tr>`;
      document.getElementById("loadMoreBtn").style.display = "none";
      return;
    }

    data.forEach((row, i) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${histSkip + i + 1}</td>
        <td>${row.state_name}</td>
        <td>${row.district_name}</td>
        <td>${row.crop}</td>
        <td>${row.season}</td>
        <td>${row.crop_year}</td>
        <td>${numberFormat(row.area)}</td>
        <td>${numberFormat(row.production)}</td>
      `;
      tbody.appendChild(tr);
    });

    histSkip += data.length;
    document.getElementById("loadMoreBtn").style.display =
      data.length >= HIST_LIMIT ? "block" : "none";
  } catch (e) {
    console.error(e);
    if (!append) {
      tbody.innerHTML = `<tr><td colspan="8" class="hist-empty">${T[currentLang].error}</td></tr>`;
    }
  }
}

function resetHistorical() {
  document.getElementById("histState").value = "";
  document.getElementById("histCrop").value = "";
  document.getElementById("histSeason").value = "";
  histSkip = 0;
  document.getElementById("histTableBody").innerHTML = `<tr><td colspan="8" class="hist-empty">${T[currentLang].hist_no_data}</td></tr>`;
  document.getElementById("loadMoreBtn").style.display = "none";
}

// ═══════════════════════════════════════════════════════════════════════════
// EVENT LISTENERS
// ═══════════════════════════════════════════════════════════════════════════

function setupListeners() {
  // Language toggle
  document.getElementById("langToggle").addEventListener("click", () => {
    const newLang = currentLang === "en" ? "hi" : "en";
    applyLang(newLang);
  });

  // Mobile hamburger
  document.getElementById("hamburger").addEventListener("click", () => {
    document.getElementById("navLinks").classList.toggle("open");
  });

  // Close menu on link click
  document.querySelectorAll(".nav-links a").forEach((a) => {
    a.addEventListener("click", () => {
      document.getElementById("navLinks").classList.remove("open");
    });
  });

  // State -> Districts cascade
  document.getElementById("stateSelect").addEventListener("change", (e) => {
    loadDistricts(e.target.value);
  });

  // Predict button
  document.getElementById("predictBtn").addEventListener("click", makePrediction);

  // New prediction
  document.getElementById("newPredBtn").addEventListener("click", resetPrediction);

  // Historical
  document.getElementById("histSearchBtn").addEventListener("click", () => searchHistorical(false));
  document.getElementById("histResetBtn").addEventListener("click", resetHistorical);
  document.getElementById("loadMoreBtn").addEventListener("click", () => searchHistorical(true));
}

// ═══════════════════════════════════════════════════════════════════════════
// SCROLL ANIMATIONS
// ═══════════════════════════════════════════════════════════════════════════

function setupScrollAnimations() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
        }
      });
    },
    { threshold: 0.1 }
  );

  document.querySelectorAll(".fade-up").forEach((el) => observer.observe(el));
}

// ═══════════════════════════════════════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════════════════════════════════════

function numberFormat(num) {
  if (num == null) return "—";
  return parseFloat(num).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });
}

function animateNumber(el, start, end, duration) {
  const range = end - start;
  const startTime = performance.now();
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out
    const eased = 1 - Math.pow(1 - progress, 3);
    const current = Math.round(start + range * eased);
    el.textContent = current.toLocaleString("en-IN");
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}
