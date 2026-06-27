/* =========================================================================
   CineMatch frontend
   Vanilla JS, organised into small reusable functions.
   Sections: utilities → DOM refs → autocomplete → recommendations →
             card rendering → modal → events/init
   ========================================================================= */

"use strict";

/* ----------------------------- Utilities ----------------------------- */

// Debounce: limit how often a function runs (used for typing/autocomplete).
function debounce(fn, delay = 220) {
    let t;
    return (...args) => {
        clearTimeout(t);
        t = setTimeout(() => fn(...args), delay);
    };
}

// Small wrapper around fetch that always returns parsed JSON (or throws).
async function getJSON(url) {
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.error || `Request failed (${res.status})`);
    }
    return data;
}

const LANG = {
    en: "English", fr: "French", es: "Spanish", ja: "Japanese", ko: "Korean",
    de: "German", it: "Italian", zh: "Chinese", hi: "Hindi", ru: "Russian",
    pt: "Portuguese", sv: "Swedish", da: "Danish", nl: "Dutch", cn: "Chinese",
};
const langName = (code) => LANG[code] || (code ? code.toUpperCase() : "—");

const fmtMoney = (n) => (n ? "$" + Number(n).toLocaleString("en-US") : "—");
const fmtRuntime = (m) => (m ? `${Math.floor(m / 60)}h ${m % 60}m` : null);
const escapeHTML = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* ------------------------------ DOM refs ------------------------------ */
const els = {
    input:        document.getElementById("movieInput"),
    recommendBtn: document.getElementById("recommendBtn"),
    suggestions:  document.getElementById("suggestions"),
    chips:        document.getElementById("chips"),
    grid:         document.getElementById("grid"),
    empty:        document.getElementById("emptyState"),
    message:      document.getElementById("message"),
    resultsTitle: document.getElementById("resultsTitle"),
    resultsSub:   document.getElementById("resultsSub"),
    resultsSec:   document.getElementById("resultsSection"),
    cardTemplate: document.getElementById("cardTemplate"),
    modal:        document.getElementById("modal"),
    modalBody:    document.getElementById("modalBody"),
};

const TRENDING = ["RRR", "Baahubali: The Beginning", "Pushpa: The Rise", "Inception", "Interstellar", "The Dark Knight"];

/* ---------------------------- Autocomplete ---------------------------- */
let activeSuggestion = -1;

const fetchSuggestions = debounce(async (query) => {
    if (query.length < 2) return closeSuggestions();
    try {
        const { suggestions } = await getJSON(`/api/autocomplete?q=${encodeURIComponent(query)}`);
        renderSuggestions(suggestions);
    } catch {
        closeSuggestions();
    }
}, 180);

function renderSuggestions(list) {
    if (!list || !list.length) return closeSuggestions();
    activeSuggestion = -1;
    els.suggestions.innerHTML = list
        .map((t) => `<li role="option" data-title="${escapeHTML(t)}">${escapeHTML(t)}</li>`)
        .join("");
    els.suggestions.classList.add("is-open");
}

function closeSuggestions() {
    els.suggestions.classList.remove("is-open");
    els.suggestions.innerHTML = "";
    activeSuggestion = -1;
}

// Keyboard navigation for the suggestion list.
function moveSuggestion(dir) {
    const items = [...els.suggestions.querySelectorAll("li")];
    if (!items.length) return;
    activeSuggestion = (activeSuggestion + dir + items.length) % items.length;
    items.forEach((li, i) => li.classList.toggle("is-active", i === activeSuggestion));
    items[activeSuggestion].scrollIntoView({ block: "nearest" });
}

/* --------------------------- Recommendations -------------------------- */
async function getRecommendations(query) {
    const movie = (query ?? els.input.value).trim();

    // Empty-search validation.
    if (!movie) {
        showMessage("Please type a movie name first. ✍️");
        els.input.focus();
        return;
    }

    closeSuggestions();
    hideMessage();
    els.empty.hidden = true;
    showSkeletons(5);
    els.resultsTitle.textContent = "Finding similar films…";
    els.resultsSub.textContent = `Searching for “${movie}”`;
    els.resultsSec.scrollIntoView({ behavior: "smooth", block: "start" });

    try {
        const data = await getJSON(`/api/recommend?movie=${encodeURIComponent(movie)}`);
        renderCards(data.recommendations);
        els.resultsTitle.textContent = "Recommended for you";
        els.resultsSub.textContent = `Because you searched “${data.matched_title}” — ${data.recommendations.length} similar films.`;
    } catch (err) {
        els.grid.innerHTML = "";
        showMessage(err.message || "Something went wrong. Please try again.");
        els.resultsTitle.textContent = "No results";
        els.resultsSub.textContent = "Try a different movie title.";
        els.empty.hidden = false;
    }
}

/* ---------------------------- Card rendering -------------------------- */

// Skeleton placeholders shown while the API responds.
function showSkeletons(count) {
    const sk = Array.from({ length: count }).map(() => `
        <article class="card skeleton" aria-hidden="true">
            <div class="card__poster"></div>
            <div class="card__body">
                <div class="sk-line w-80"></div>
                <div class="sk-line w-40"></div>
                <div class="sk-line w-60"></div>
            </div>
        </article>`).join("");
    els.grid.innerHTML = sk;
}

// Build a poster <img>, falling back to a gradient placeholder on error / no key.
function setPoster(img, src, title) {
    if (src) {
        img.src = src;
        img.alt = `${title} poster`;
        img.onerror = () => applyPlaceholder(img, title);
    } else {
        applyPlaceholder(img, title);
    }
}
function applyPlaceholder(img, title) {
    img.removeAttribute("src");
    img.onerror = null;
    img.outerHTML = `<div class="card__img is-placeholder">${escapeHTML(title)}</div>`;
}

// Render cards by cloning the <template> (efficient, minimal innerHTML churn).
function renderCards(movies) {
    const frag = document.createDocumentFragment();

    movies.forEach((m, i) => {
        const node = els.cardTemplate.content.firstElementChild.cloneNode(true);
        node.style.animationDelay = `${i * 70}ms`;
        node.dataset.id = m.movie_id;

        setPoster(node.querySelector(".card__img"), m.poster, m.title);

        // Rating badge (hidden if unknown).
        const ratingWrap = node.querySelector(".card__rating");
        if (m.rating) node.querySelector("[data-rating]").textContent = m.rating.toFixed(1);
        else ratingWrap.remove();

        node.querySelector("[data-title]").textContent = m.title;

        // Meta line: year · runtime · language
        setText(node, "[data-year]", m.year);
        setText(node, "[data-runtime]", fmtRuntime(m.runtime));
        setText(node, "[data-lang]", langName(m.language));

        // Genres (max 3 tags).
        const genres = (m.genres || []).slice(0, 3)
            .map((g) => `<span class="tag">${escapeHTML(g)}</span>`).join("");
        node.querySelector("[data-genres]").innerHTML = genres;

        node.querySelector("[data-overview]").textContent =
            m.overview || "No overview available for this title.";

        // Streaming providers — logo when available, otherwise a name pill.
        node.querySelector("[data-providers]").innerHTML = (m.providers || [])
            .slice(0, 4)
            .map((p) => p.logo
                ? `<img src="${p.logo}" alt="${escapeHTML(p.name)}" title="Stream on ${escapeHTML(p.name)}" loading="lazy" />`
                : `<span class="provider-pill" title="Stream on ${escapeHTML(p.name)}">${escapeHTML(p.name)}</span>`)
            .join("");

        setText(node, "[data-votes]", m.vote_count ? `${Number(m.vote_count).toLocaleString()} votes` : "");
        setText(node, "[data-pop]", m.popularity ? `🔥 ${Math.round(m.popularity)}` : "");

        // Trailer button (only if a trailer URL exists).
        const trailer = node.querySelector('[data-action="trailer"]');
        if (m.trailer) { trailer.hidden = false; trailer.href = m.trailer; }

        frag.appendChild(node);
    });

    els.grid.innerHTML = "";
    els.grid.appendChild(frag);
}

function setText(scope, selector, value) {
    const el = scope.querySelector(selector);
    if (!el) return;
    if (value) el.textContent = value;
    else el.remove();
}

/* -------------------------------- Modal ------------------------------- */
async function openModal(movieId) {
    els.modal.hidden = false;
    document.body.style.overflow = "hidden";
    els.modalBody.innerHTML = `<div style="padding:80px;text-align:center;color:var(--text-dim)">
        <div class="sk-line w-60" style="margin:0 auto 14px"></div>Loading details…</div>`;

    try {
        const m = await getJSON(`/api/movie/${movieId}`);
        els.modalBody.innerHTML = buildModalHTML(m);
    } catch (err) {
        els.modalBody.innerHTML = `<div style="padding:60px;text-align:center">
            <p style="color:#fda4af">${escapeHTML(err.message || "Could not load details.")}</p></div>`;
    }
}

function closeModal() {
    els.modal.hidden = true;
    document.body.style.overflow = "";
    els.modalBody.innerHTML = "";
}

function buildModalHTML(m) {
    const poster = m.poster
        ? `<img class="modal__poster" src="${m.poster}" alt="${escapeHTML(m.title)} poster" />`
        : `<div class="modal__poster is-placeholder">${escapeHTML(m.title)}</div>`;

    const backdrop = m.backdrop ? `<img class="modal__backdrop" src="${m.backdrop}" alt="" />` : "";

    const facts = [
        m.rating ? `<span><b>★ ${m.rating.toFixed(1)}</b> / 10</span>` : "",
        m.vote_count ? `<span>${Number(m.vote_count).toLocaleString()} votes</span>` : "",
        m.year ? `<span>${escapeHTML(m.year)}</span>` : "",
        fmtRuntime(m.runtime) ? `<span>${fmtRuntime(m.runtime)}</span>` : "",
        m.language ? `<span>${escapeHTML(langName(m.language))}</span>` : "",
        m.popularity ? `<span>🔥 ${Math.round(m.popularity)} popularity</span>` : "",
    ].filter(Boolean).join("");

    const genres = (m.genres || []).map((g) => `<span class="pill">${escapeHTML(g)}</span>`).join("");

    const actions = [
        m.trailer ? `<a class="btn btn--primary" href="${m.trailer}" target="_blank" rel="noopener">▶ Watch Trailer</a>` : "",
        m.imdb_id ? `<a class="btn btn--ghost" href="https://www.imdb.com/title/${m.imdb_id}" target="_blank" rel="noopener">IMDb ↗</a>` : "",
        m.homepage ? `<a class="btn btn--ghost" href="${escapeHTML(m.homepage)}" target="_blank" rel="noopener">Website ↗</a>` : "",
    ].filter(Boolean).join("");

    const providers = (m.providers || []).length
        ? `<div><h3 class="section-title">Where to stream</h3><div class="providers-row">${
            m.providers.map((p) => `<span class="provider">${
                p.logo ? `<img src="${p.logo}" alt="" />` : ""}${escapeHTML(p.name)}</span>`).join("")
          }</div></div>`
        : "";

    const cast = (m.cast || []).length
        ? `<div><h3 class="section-title">Top cast</h3><div class="pill-row">${
            m.cast.map((c) => `<span class="pill">${escapeHTML(c)}</span>`).join("")}</div></div>`
        : "";

    const companies = (m.production_companies || []).length
        ? `<div><h3 class="section-title">Production</h3><div class="pill-row">${
            m.production_companies.map((c) => `<span class="pill">${escapeHTML(c)}</span>`).join("")}</div></div>`
        : "";

    const infoCards = [
        m.director ? infoCard("Director", m.director) : "",
        m.release_date ? infoCard("Release date", m.release_date) : "",
        m.budget ? infoCard("Budget", fmtMoney(m.budget)) : "",
        m.revenue ? infoCard("Revenue", fmtMoney(m.revenue)) : "",
    ].filter(Boolean).join("");

    return `
        <div class="modal__hero">${backdrop}
            <div class="modal__top">
                ${poster}
                <div class="modal__head">
                    <h2 class="modal__title" id="modalTitle">${escapeHTML(m.title)}</h2>
                    ${m.tagline ? `<p class="modal__tagline">“${escapeHTML(m.tagline)}”</p>` : ""}
                    <div class="modal__facts">${facts}</div>
                    ${actions ? `<div class="modal__actions">${actions}</div>` : ""}
                </div>
            </div>
        </div>
        <div class="modal__content">
            ${genres ? `<div class="pill-row">${genres}</div>` : ""}
            <p class="modal__overview">${escapeHTML(m.overview) || "No overview available."}</p>
            ${infoCards ? `<div class="modal__grid">${infoCards}</div>` : ""}
            ${cast}
            ${providers}
            ${companies}
        </div>`;
}

const infoCard = (label, value) =>
    `<div class="info"><h4>${escapeHTML(label)}</h4><p>${escapeHTML(value)}</p></div>`;

/* ---------------------------- Messages -------------------------------- */
function showMessage(text) { els.message.textContent = text; els.message.hidden = false; }
function hideMessage() { els.message.hidden = true; }

/* ----------------------------- Trending chips ------------------------- */
function renderChips() {
    TRENDING.forEach((title) => {
        const chip = document.createElement("button");
        chip.className = "chip";
        chip.type = "button";
        chip.textContent = title;
        chip.addEventListener("click", () => {
            els.input.value = title;
            getRecommendations(title);
        });
        els.chips.appendChild(chip);
    });
}

/* ------------------------------- Events ------------------------------- */
function bindEvents() {
    // Search trigger
    els.recommendBtn.addEventListener("click", () => getRecommendations());

    els.input.addEventListener("input", (e) => fetchSuggestions(e.target.value.trim()));

    els.input.addEventListener("keydown", (e) => {
        const open = els.suggestions.classList.contains("is-open");
        if (e.key === "ArrowDown" && open) { e.preventDefault(); moveSuggestion(1); }
        else if (e.key === "ArrowUp" && open) { e.preventDefault(); moveSuggestion(-1); }
        else if (e.key === "Enter") {
            const active = els.suggestions.querySelector("li.is-active");
            if (active) { els.input.value = active.dataset.title; closeSuggestions(); }
            getRecommendations();
        } else if (e.key === "Escape") closeSuggestions();
    });

    // Suggestion click (event delegation)
    els.suggestions.addEventListener("click", (e) => {
        const li = e.target.closest("li");
        if (!li) return;
        els.input.value = li.dataset.title;
        closeSuggestions();
        getRecommendations(li.dataset.title);
    });

    // Close suggestions when clicking outside the search bar
    document.addEventListener("click", (e) => {
        if (!e.target.closest("#search")) closeSuggestions();
    });

    // Card interactions (event delegation on the grid — one listener for all cards)
    els.grid.addEventListener("click", (e) => {
        if (e.target.closest('[data-action="trailer"]')) return; // let the link work
        const card = e.target.closest(".card");
        if (card && !card.classList.contains("skeleton")) openModal(card.dataset.id);
    });
    els.grid.addEventListener("keydown", (e) => {
        if (e.key !== "Enter") return;
        const card = e.target.closest(".card");
        if (card && !card.classList.contains("skeleton")) openModal(card.dataset.id);
    });

    // Modal close (overlay, close button, Esc)
    els.modal.addEventListener("click", (e) => { if (e.target.closest("[data-close]")) closeModal(); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !els.modal.hidden) closeModal(); });
}

/* -------------------------------- Init -------------------------------- */
function init() {
    renderChips();
    bindEvents();
}

document.addEventListener("DOMContentLoaded", init);
