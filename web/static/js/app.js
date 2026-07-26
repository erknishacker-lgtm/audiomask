/* MASK.SOUND SPA */
(() => {
  const $ = (sel, el = document) => el.querySelector(sel);
  const app = $("#app");
  const state = {
    user: null,
    view: "boot",
    platforms: [],
    wizard: {
      step: 1,
      platform: null,
      file: null,
      whiteFile: null,
      whiteText: "",
      whiteNiche: "mmo",
      whiteCopyId: "mmo_1",
      whiteLang: "pt",
      result: null,
      opts: {
        proteger: true,
        metadados: true,
        phase: true,
        compress: true,
        // espelho de mercado: secundário ~−20…−22 dB sob a principal
        decoyDb: -22,
        cloakMode: "anti_analise",
      },
    },
    authTab: "login",
  };

  function toast(msg) {
    const el = $("#toast");
    el.hidden = false;
    el.textContent = msg;
    clearTimeout(toast._t);
    toast._t = setTimeout(() => {
      el.hidden = true;
    }, 3200);
  }

  function t(k) {
    return window.msT(k);
  }

  function whitePresets() {
    return (
      window.GW_WHITE_PRESETS || {
        niches: [],
        langs: [
          { id: "pt", label: "Português", short: "PT-BR" },
          { id: "en", label: "English", short: "EN" },
          { id: "es", label: "Español", short: "ES" },
        ],
        findNiche: () => ({ copies: [] }),
        findCopy: () => null,
        getText: () => "",
        getTitle: () => "",
        pick: (o) => (typeof o === "string" ? o : ""),
        defaultText: () => "",
        normLang: (l) => l || "pt",
      }
    );
  }

  function currentWhiteLang() {
    const lib = whitePresets();
    const fromState = state.wizard.whiteLang;
    const fromUi = $("#whiteLang") && $("#whiteLang").value;
    return lib.normLang ? lib.normLang(fromUi || fromState || "pt") : "pt";
  }

  function defaultWhiteText(lang) {
    try {
      return whitePresets().defaultText(lang || currentWhiteLang()) || "";
    } catch (_) {
      return "";
    }
  }

  function whiteNicheOptions(selectedId) {
    const niches = whitePresets().niches || [];
    return niches
      .map(
        (n) =>
          `<option value="${escapeAttr(n.id)}" ${n.id === selectedId ? "selected" : ""}>${escapeHtml(
            (n.icon ? n.icon + " " : "") + n.label
          )}</option>`
      )
      .join("");
  }

  function whiteCopyOptions(nicheId, selectedCopyId, lang) {
    const lib = whitePresets();
    const niche = lib.findNiche ? lib.findNiche(nicheId) : (lib.niches || [])[0];
    if (!niche || !niche.copies) return "";
    const L = lang || currentWhiteLang();
    return niche.copies
      .map((c) => {
        const title = lib.getTitle
          ? lib.getTitle(nicheId, c.id, L)
          : lib.pick
            ? lib.pick(c.title, L)
            : c.title;
        return `<option value="${escapeAttr(c.id)}" ${c.id === selectedCopyId ? "selected" : ""}>${escapeHtml(
          title
        )}</option>`;
      })
      .join("");
  }

  function whiteLangButtons(selectedLang) {
    const langs = whitePresets().langs || [];
    const sel = whitePresets().normLang
      ? whitePresets().normLang(selectedLang || "pt")
      : selectedLang || "pt";
    return (
      `<div class="lang-script-grid" id="whiteLangGrid" role="radiogroup" aria-label="Idioma do script">` +
      langs
        .map((l) => {
          const active = l.id === sel ? "active" : "";
          const code = l.short || l.id.toUpperCase();
          return `<button type="button" class="lang-script-btn ${active}" data-lang="${escapeAttr(
            l.id
          )}" role="radio" aria-checked="${l.id === sel}">
            <span class="lang-script-flag">${escapeHtml(code)}</span>
            <span class="lang-script-name">${escapeHtml(l.label)}</span>
          </button>`;
        })
        .join("") +
      `<input type="hidden" id="whiteLang" value="${escapeAttr(sel)}" />` +
      `</div>`
    );
  }

  function applyWhiteCopyToForm(nicheId, copyId, { silent, lang } = {}) {
    const lib = whitePresets();
    const L = lang || currentWhiteLang();
    const copy = lib.findCopy ? lib.findCopy(nicheId, copyId) : null;
    const ta = $("#whiteText");
    const sel = $("#whiteCopySel");
    if (copy && ta) {
      const text = lib.getText
        ? lib.getText(nicheId, copy.id, L)
        : lib.pick
          ? lib.pick(copy.text, L)
          : copy.text;
      const title = lib.getTitle
        ? lib.getTitle(nicheId, copy.id, L)
        : lib.pick
          ? lib.pick(copy.title, L)
          : copy.title;
      ta.value = text;
      state.wizard.whiteText = text;
      state.wizard.whiteNiche = nicheId;
      state.wizard.whiteCopyId = copy.id;
      state.wizard.whiteLang = L;
      if (sel) sel.value = copy.id;
      const langInput = $("#whiteLang");
      if (langInput) langInput.value = L;
      if (!silent) toast("White script: " + title + " (" + L.toUpperCase() + ")");
    }
    renderWhiteChips(nicheId, copy ? copy.id : copyId, L);
  }

  function renderWhiteChips(nicheId, activeCopyId, lang) {
    const host = $("#whiteCopyChips");
    if (!host) return;
    const lib = whitePresets();
    const niche = lib.findNiche ? lib.findNiche(nicheId) : null;
    const L = lang || currentWhiteLang();
    if (!niche) {
      host.innerHTML = "";
      return;
    }
    host.innerHTML = niche.copies
      .map((c) => {
        const title = lib.getTitle
          ? lib.getTitle(nicheId, c.id, L)
          : lib.pick
            ? lib.pick(c.title, L)
            : c.title;
        return `<button type="button" class="chip-copy ${
          c.id === activeCopyId ? "active" : ""
        }" data-copy="${escapeAttr(c.id)}">${escapeHtml(title)}</button>`;
      })
      .join("");
    host.querySelectorAll("[data-copy]").forEach((btn) => {
      btn.onclick = () => {
        const nid = ($("#whiteNiche") && $("#whiteNiche").value) || nicheId;
        applyWhiteCopyToForm(nid, btn.dataset.copy);
        const sel = $("#whiteCopySel");
        if (sel) sel.value = btn.dataset.copy;
      };
    });
  }

  function bindWhitePresetControls() {
    const nicheSel = $("#whiteNiche");
    const copySel = $("#whiteCopySel");
    if (!nicheSel || !copySel) return;

    const refreshCopyList = (applyText) => {
      const nid = nicheSel.value;
      const lib = whitePresets();
      const niche = lib.findNiche(nid);
      const first = niche && niche.copies[0];
      const keepId =
        copySel.value && niche.copies.some((c) => c.id === copySel.value)
          ? copySel.value
          : first
            ? first.id
            : "";
      copySel.innerHTML = whiteCopyOptions(nid, keepId, currentWhiteLang());
      if (applyText && keepId) applyWhiteCopyToForm(nid, keepId, { silent: true });
      else renderWhiteChips(nid, keepId, currentWhiteLang());
    };

    nicheSel.onchange = () => {
      const niche = whitePresets().findNiche(nicheSel.value);
      const first = niche && niche.copies[0];
      if (first) {
        copySel.innerHTML = whiteCopyOptions(nicheSel.value, first.id, currentWhiteLang());
        applyWhiteCopyToForm(nicheSel.value, first.id, { silent: true });
      }
    };

    copySel.onchange = () =>
      applyWhiteCopyToForm(nicheSel.value, copySel.value, { silent: false });

    // idioma do script (PT / EN / ES)
    $$("[data-lang]").forEach((btn) => {
      btn.onclick = () => {
        const L = whitePresets().normLang(btn.dataset.lang);
        state.wizard.whiteLang = L;
        const hidden = $("#whiteLang");
        if (hidden) hidden.value = L;
        $$("[data-lang]").forEach((b) => {
          const on = b.dataset.lang === L;
          b.classList.toggle("active", on);
          b.setAttribute("aria-checked", on ? "true" : "false");
        });
        // reaplica copy atual no novo idioma
        const nid = nicheSel.value;
        const cid = copySel.value;
        copySel.innerHTML = whiteCopyOptions(nid, cid, L);
        applyWhiteCopyToForm(nid, cid, { silent: true, lang: L });
      };
    });

    const ta = $("#whiteText");
    const L = currentWhiteLang();
    if (ta && !String(ta.value || "").trim()) {
      applyWhiteCopyToForm(
        nicheSel.value || "mmo",
        copySel.value || "mmo_1",
        { silent: true, lang: L }
      );
    } else if (ta && state.wizard.whiteText) {
      // mantém texto já escolhido; só atualiza chips
      renderWhiteChips(nicheSel.value, copySel.value, L);
    } else {
      refreshCopyList(true);
    }
  }


  function langSelect() {
    const cur = localStorage.getItem("ms_lang") || "pt";
    return `
      <select id="langSel" class="chip" aria-label="Idioma">
        <option value="pt" ${cur === "pt" ? "selected" : ""}>PT</option>
        <option value="en" ${cur === "en" ? "selected" : ""}>EN</option>
      </select>`;
  }

  function bindLang() {
    const s = $("#langSel");
    if (!s) return;
    s.onchange = () => {
      window.msSetLang(s.value);
      render();
    };
  }

  /* kept for legacy template strings that still call nav() */
  function nav() { return ""; }

  function _navIcon(name) {
    const icons = {
      dashboard: `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="2" width="7" height="7" rx="1.5"/><rect x="11" y="2" width="7" height="7" rx="1.5"/><rect x="2" y="11" width="7" height="7" rx="1.5"/><rect x="11" y="11" width="7" height="7" rx="1.5"/></svg>`,
      protect:   `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M10 2L3 5v5c0 4.4 3 7.9 7 9 4-1.1 7-4.6 7-9V5l-7-3z"/></svg>`,
      tutorials: `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M4 4h12v12H4z" rx="1"/><path d="M4 8h12M8 4v12"/></svg>`,
      pricing:   `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="2" y="5" width="16" height="11" rx="2"/><path d="M6 5V4a2 2 0 0 1 8 0v1"/><path d="M10 10v2M8 11h4"/></svg>`,
      account:   `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="7" r="3"/><path d="M4 17c0-3 2.7-5 6-5s6 2 6 5"/></svg>`,
      admin:     `<svg class="sidebar-nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="2"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.2 4.2l1.4 1.4M14.4 14.4l1.4 1.4M4.2 15.8l1.4-1.4M14.4 5.6l1.4-1.4"/></svg>`,
    };
    return icons[name] || "";
  }

  function renderShell() {
    if ($("#sidebar")) {
      updateSidebarActive();
      return;
    }
    const u = state.user;
    const left = u.daily_left ?? u.videos_left ?? 0;
    const lim  = u.daily_limit ?? u.video_limit ?? 1;
    const pct  = Math.round(Math.min(100, (left / Math.max(lim, 1)) * 100));
    const planLabel = escapeHtml((u.plan_name || u.plan || "free").toString());
    const initials = escapeHtml((u.name || u.email || "U")[0].toUpperCase());
    const adminItem = u.role === "admin"
      ? `<button class="sidebar-nav-item" data-go="admin">${_navIcon("admin")} Admin</button>` : "";

    app.innerHTML = `
      <div class="layout">
        <aside class="sidebar" id="sidebar">
          <div class="sidebar-brand" data-go="dashboard">
            <img class="sidebar-brand-logo" src="/assets/logo.png" alt="Ghost Wave" />
            <span class="sidebar-brand-name">Ghost Wave</span>
          </div>
          <nav class="sidebar-nav">
            <button class="sidebar-nav-item" data-go="dashboard">${_navIcon("dashboard")} Dashboard</button>
            <button class="sidebar-nav-item" data-go="protect">${_navIcon("protect")} Processar</button>
            <button class="sidebar-nav-item" data-go="tutorials">${_navIcon("tutorials")} Tutoriais</button>
            <button class="sidebar-nav-item" data-go="pricing">${_navIcon("pricing")} Planos</button>
            <button class="sidebar-nav-item" data-go="account">${_navIcon("account")} Conta</button>
            ${adminItem}
          </nav>
          <div class="sidebar-footer">
            <div class="sidebar-plan-badge">
              <span class="sidebar-plan-name">${planLabel}</span>
              <span class="sidebar-plan-quota">${left}/${lim}</span>
            </div>
            <div class="sidebar-plan-bar">
              <div class="sidebar-plan-bar-fill" style="width:${pct}%"></div>
            </div>
            <div class="sidebar-user">
              <div class="sidebar-avatar">${initials}</div>
              <div class="sidebar-user-info">
                <div class="sidebar-user-name">${escapeHtml(u.name || "")}</div>
                <div class="sidebar-user-email">${escapeHtml(u.email || "")}</div>
              </div>
              <button class="sidebar-logout" id="btnLogout" title="${t("logout")}">
                <svg width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M13 7l3 3-3 3M16 10H8M8 3H5a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h3"/></svg>
              </button>
            </div>
          </div>
        </aside>
        <div class="content-area">
          <div id="content"></div>
        </div>
      </div>`;

    updateSidebarActive();
    bindLang();
    $$("[data-go]").forEach((el) => {
      el.onclick = () => {
        const target = el.getAttribute("data-go");
        if (target === "protect") {
          state.wizard = {
            step: 1, platform: null, file: null, whiteFile: null,
            whiteText: "", whiteNiche: "mmo", whiteCopyId: "mmo_1",
            whiteLang: "pt", result: null,
            opts: { proteger: true, metadados: true, phase: true, compress: true, decoyDb: -22, cloakMode: "anti_analise" },
          };
        }
        state.view = target;
        render();
      };
    });
    const lo = $("#btnLogout");
    if (lo) {
      lo.onclick = async () => {
        try { await msApi.logout(); } catch (_) {}
        state.user = null;
        state.view = "auth";
        app.innerHTML = "";
        render();
      };
    }
  }

  function updateSidebarActive() {
    $$(".sidebar-nav-item[data-go]").forEach((el) => {
      el.classList.toggle("active", el.getAttribute("data-go") === state.view);
    });
  }

  function getContent() {
    return $("#content") || app;
  }

  function bindNav() {
    /* legacy: sidebar already handles nav */
    bindLang();
    $$("[data-go]").forEach((el) => {
      if (el.closest("#sidebar")) return; // sidebar handles its own
      el.onclick = () => {
        state.view = el.getAttribute("data-go");
        render();
      };
    });
  }

  function $$(sel) {
    return [...document.querySelectorAll(sel)];
  }

  /* ── views ── */

  /* ── Auth ambient décor (fantasminhas + som bloqueado) ── */
  let authDecorCleanup = null;

  function stopAuthDecor() {
    if (typeof authDecorCleanup === "function") {
      try {
        authDecorCleanup();
      } catch (_) {}
    }
    authDecorCleanup = null;
  }

  function svgGhost() {
    return `<svg viewBox="0 0 64 72" fill="none" aria-hidden="true">
      <path d="M32 6c-14 0-24 10-24 26v28c0 3 2.2 4 4.2 2.4L20 56l6 6.5c1.4 1.5 3.6 1.5 5 0L32 56l1-1 6 6.5c1.4 1.5 3.6 1.5 5 0L50 56l7.8 6.4C59.8 64 62 63 62 60V32C62 16 52 6 32 6z" fill="currentColor" opacity="0.92"/>
      <circle cx="24" cy="30" r="3.2" fill="#0a0a0a"/>
      <circle cx="40" cy="30" r="3.2" fill="#0a0a0a"/>
      <path d="M22 42h4v8h-4zm8-2h4v12h-4zm8 2h4v8h-4z" fill="#0a0a0a"/>
    </svg>`;
  }

  function svgMute() {
    return `<svg viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <path d="M10 18h8l10-8v28l-10-8h-8a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2z" fill="currentColor" opacity="0.85"/>
      <path d="M34 16l10 16M44 16L34 32" stroke="#ff5c5c" stroke-width="2.6" stroke-linecap="round"/>
    </svg>`;
  }

  function svgWaves() {
    return `<svg viewBox="0 0 72 36" fill="none" aria-hidden="true">
      <path d="M6 18c4-8 8-8 12 0s8 8 12 0 8-8 12 0 8 8 12 0 8-8 12 0" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" opacity="0.7"/>
      <path d="M10 18c3-5 6-5 9 0s6 5 9 0 6-5 9 0 6 5 9 0 6-5 9 0" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" opacity="0.35"/>
      <line x1="8" y1="30" x2="64" y2="6" stroke="#ff5c5c" stroke-width="2" stroke-linecap="round" opacity="0.8"/>
    </svg>`;
  }

  function svgLock() {
    return `<svg viewBox="0 0 40 40" fill="none" aria-hidden="true">
      <rect x="10" y="18" width="20" height="16" rx="3" stroke="currentColor" stroke-width="2" fill="currentColor" fill-opacity="0.12"/>
      <path d="M14 18v-4a6 6 0 0 1 12 0v4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>`;
  }

  function mountAuthDecor(root) {
    stopAuthDecor();
    const host = root.querySelector(".auth-decor");
    if (!host) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      // still show static light décor
    }

    const items = [];
    const mk = (cls, html, style) => {
      const el = document.createElement("div");
      el.className = `ad-item ${cls}`;
      el.innerHTML = html;
      Object.assign(el.style, style);
      host.appendChild(el);
      return el;
    };

    // fantasminhas andando em faixas
    const ghostLanes = [
      { y: 12, dir: 1, speed: 28, scale: 1, delay: 0 },
      { y: 38, dir: -1, speed: 36, scale: 0.75, delay: 1.2 },
      { y: 68, dir: 1, speed: 22, scale: 1.15, delay: 2.4 },
      { y: 82, dir: -1, speed: 40, scale: 0.65, delay: 0.6 },
      { y: 52, dir: 1, speed: 18, scale: 0.9, delay: 3.1 },
    ];
    ghostLanes.forEach((g, i) => {
      const el = mk(
        `ad-ghost${g.dir < 0 ? " flip" : ""}`,
        svgGhost(),
        {
          top: `${g.y}%`,
          left: g.dir > 0 ? "-8%" : "108%",
          width: `${42 * g.scale}px`,
          height: `${48 * g.scale}px`,
          animationDelay: `${g.delay}s`,
          opacity: String(0.35 + (i % 3) * 0.08),
        }
      );
      items.push({
        el,
        kind: "ghost",
        y: g.y,
        dir: g.dir,
        speed: g.speed,
        x: g.dir > 0 ? -10 : 110,
        bob: g.delay,
      });
    });

    // ícones de som bloqueado flutuando
    const mutes = [
      { x: 8, y: 18 },
      { x: 88, y: 28 },
      { x: 14, y: 72 },
      { x: 78, y: 78 },
      { x: 50, y: 8 },
    ];
    mutes.forEach((m, i) => {
      const wrap = mk(
        "ad-mute",
        `<div style="position:relative">${svgMute()}</div>`,
        {
          left: `${m.x}%`,
          top: `${m.y}%`,
          animationDelay: `${i * 0.7}s`,
          animationDuration: `${5.5 + i * 0.4}s`,
        }
      );
      items.push({ el: wrap, kind: "static" });
    });

    // ondas riscadas
    [
      { x: 6, y: 48 },
      { x: 84, y: 58 },
      { x: 70, y: 12 },
    ].forEach((w, i) => {
      mk("ad-wave", svgWaves(), {
        left: `${w.x}%`,
        top: `${w.y}%`,
        animationDelay: `${i * 0.5}s`,
      });
    });

    // equalizers “bloqueados”
    [
      { x: 22, y: 88 },
      { x: 62, y: 90 },
      { x: 42, y: 6 },
    ].forEach((e, i) => {
      const el = mk(
        "ad-eq blocked",
        `<span></span><span></span><span></span><span></span><span></span><div class="ad-slash"></div>`,
        {
          left: `${e.x}%`,
          top: `${e.y}%`,
          position: "absolute",
          animationDelay: `${i * 0.2}s`,
        }
      );
      el.style.position = "absolute";
    });

    // cadeados + sparks
    [
      { x: 30, y: 30 },
      { x: 72, y: 42 },
    ].forEach((l, i) => {
      mk("ad-lock", svgLock(), {
        left: `${l.x}%`,
        top: `${l.y}%`,
        animationDelay: `${i * 1.4}s`,
      });
    });
    for (let i = 0; i < 10; i++) {
      mk("ad-spark", "", {
        left: `${8 + Math.random() * 84}%`,
        top: `${8 + Math.random() * 84}%`,
        animationDelay: `${Math.random() * 3}s`,
        animationDuration: `${3 + Math.random() * 3}s`,
      });
    }

    let raf = 0;
    let last = performance.now();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const tick = (now) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!reduced) {
        items.forEach((it) => {
          if (it.kind !== "ghost") return;
          it.x += it.dir * it.speed * dt;
          if (it.dir > 0 && it.x > 112) it.x = -12;
          if (it.dir < 0 && it.x < -12) it.x = 112;
          const bob = Math.sin(now / 500 + it.bob) * 6;
          const flip = it.dir < 0 ? " scaleX(-1)" : "";
          it.el.style.left = `${it.x}%`;
          it.el.style.transform = `translateY(${bob}px)${flip}`;
        });
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    authDecorCleanup = () => {
      cancelAnimationFrame(raf);
      host.innerHTML = "";
    };
  }

  function viewAuth() {
    const tab = state.authTab;
    app.innerHTML = `
      <div class="auth-wrap fade-in">
        <div class="auth-decor" aria-hidden="true"></div>
        <div class="auth-card">
          <img class="auth-logo" src="/assets/logo.png" alt="GhostWave" width="96" height="96" />
          <h1>GhostWave</h1>
          <p class="sub">Humano ouve o original. A IA tende a ler a copy white.</p>
          <div class="auth-lang">${langSelect()}</div>
          <div class="tabs" role="tablist">
            <button type="button" class="tab ${tab === "login" ? "active" : ""}" data-tab="login" role="tab" aria-selected="${tab === "login"}">${t("login")}</button>
            <button type="button" class="tab ${tab === "register" ? "active" : ""}" data-tab="register" role="tab" aria-selected="${tab === "register"}">${t("register")}</button>
          </div>
          <form id="authForm">
            ${
              tab === "register"
                ? `<div class="field"><label for="auth-name">${t("name")}</label><input id="auth-name" name="name" required autocomplete="name" /></div>`
                : ""
            }
            <div class="field"><label for="auth-email">${t("email")}</label><input id="auth-email" name="email" type="email" required autocomplete="email" /></div>
            <div class="field"><label for="auth-pass">${t("password")}</label><input id="auth-pass" name="password" type="password" required minlength="6" autocomplete="${tab === "login" ? "current-password" : "new-password"}" /></div>
            <button class="btn btn-primary btn-block" type="submit">${tab === "login" ? t("login") : t("register")}</button>
          </form>
          <p class="auth-foot">Free 2/dia · Mensal R$ 59,90 · Trimestral R$ 129,90 · Anual R$ 299</p>
        </div>
      </div>`;
    mountAuthDecor(app);
    bindLang();
    $$(".tab").forEach((b) => {
      b.onclick = () => {
        state.authTab = b.dataset.tab;
        render();
      };
    });
    $("#authForm").onsubmit = async (e) => {
      e.preventDefault();
      const fd = new FormData(e.target);
      const email = fd.get("email");
      const password = fd.get("password");
      const name = fd.get("name");
      try {
        if (state.authTab === "register") {
          await msApi.register(name, email, password);
          toast("Conta criada. Entre agora.");
          state.authTab = "login";
          render();
          return;
        }
        const data = await msApi.login(email, password);
        state.user = data.user;
        state.view = "dashboard";
        stopAuthDecor();
        render();
      } catch (err) {
        toast(err.message || "Erro");
      }
    };
  }

  function viewDashboard() {
    const u = state.user;
    const left = u.daily_left ?? u.videos_left;
    const lim = u.daily_limit ?? u.video_limit;
    const usedToday = u.daily_used ?? 0;
    const planLabel = escapeHtml(u.plan_name || u.plan || "free");
    getContent().innerHTML = `
      <div class="shell fade-in">
        <header class="page-head">
          <h1 class="h1">${t("welcome")}, ${escapeHtml(u.name)}</h1>
          <p class="lead">Seu público ouve o criativo original. A IA de legenda e moderação tende a ler a copy white.</p>
        </header>

        <div class="dual-demo" aria-label="Demonstração dual-layer">
          <div class="dual-box human">
            <div class="who">Camada humana</div>
            <blockquote>"Compre agora com 50% off!"</blockquote>
            <p class="note">O que a pessoa ouve: audio original, intacto.</p>
          </div>
          <div class="dual-box ai">
            <div class="who">Camada IA</div>
            <blockquote>"Dicas de jardinagem e flores sustentáveis."</blockquote>
            <p class="note">O que a legenda tende a transcrever: copy white.</p>
          </div>
        </div>

        <div class="stats" role="group" aria-label="Uso de hoje">
          <div class="stat"><div class="lbl">${t("plan")}</div><div class="val" style="font-size:1rem">${planLabel}</div></div>
          <div class="stat"><div class="lbl">Usados hoje</div><div class="val">${usedToday}/${lim}</div></div>
          <div class="stat"><div class="lbl">Restam</div><div class="val">${left}</div></div>
        </div>

        <div class="actions">
          <button class="action featured" data-go="protect" type="button">
            <span class="arrow" aria-hidden="true">→</span>
            <div class="cta-media">
              <img src="/assets/cta-protect.jpg" alt="" width="640" height="360" />
            </div>
            <div class="cta-body">
              <span class="cta-pill">Fluxo principal</span>
              <h3>Proteger criativo</h3>
              <p>Plataforma, funções dual-layer, upload e download em um fluxo único.</p>
            </div>
          </button>
          <div class="actions-side">
            <button class="action" data-go="tutorials" type="button">
              <span class="arrow" aria-hidden="true">→</span>
              <h3>Tutoriais</h3>
              <p>Dual-layer explicado sem jargão, com analogias simples.</p>
            </button>
            <button class="action" data-go="account" type="button">
              <span class="arrow" aria-hidden="true">→</span>
              <h3>${t("account")}</h3>
              <p>Plano, créditos diários e histórico de uso.</p>
            </button>
            ${
              u.role === "admin"
                ? `<button class="action" data-go="admin" type="button">
                    <span class="arrow" aria-hidden="true">→</span>
                    <h3>${t("admin")}</h3>
                    <p>Usuários, planos e cotas diárias.</p>
                  </button>`
                : `<button class="action" data-go="pricing" type="button">
                    <span class="arrow" aria-hidden="true">→</span>
                    <h3>Planos</h3>
                    <p>Mensal, trimestral e anual ilimitado.</p>
                  </button>`
            }
          </div>
        </div>

        <div class="section">
          <h2 class="h2">O que entra em cada processamento</h2>
          <div class="layers">
            <div class="layer"><strong>Dual-layer black e white</strong><span>Humano ouve black; white fica baixa para STT e moderação.</span></div>
            <div class="layer"><strong>Limpar metadados</strong><span>Remove rastros digitais do arquivo de mídia.</span></div>
            <div class="layer"><strong>Phase-stereo</strong><span>Proteção L/R discreta no downmix mono.</span></div>
            <div class="layer"><strong>Compressão inteligente</strong><span>Vídeo menor sem perda visual perceptível.</span></div>
          </div>
        </div>
      </div>`;
    bindNav();
  }

  function viewAccount() {
    const u = state.user;
    getContent().innerHTML = `
      <div class="shell fade-in">
        <div class="page-head">
          <div class="back-row"><button class="btn btn-ghost btn-sm" data-go="dashboard" type="button">← ${t("back")}</button></div>
          <h1 class="h1">${t("account")}</h1>
          <p class="lead">Plano, cota diária e histórico de processamentos.</p>
        </div>
        <div class="panel panel-pad account-meta">
          <p><strong>${t("email")}:</strong> ${escapeHtml(u.email)}</p>
          <p><strong>${t("plan")}:</strong> ${escapeHtml(u.plan_name || u.plan)}</p>
          <p><strong>Hoje:</strong> ${u.daily_used ?? 0}/${u.daily_limit ?? u.video_limit} · restam <span class="chip accent">${u.daily_left ?? u.videos_left}</span></p>
          <p class="muted">Contador zera todo dia (UTC). Total histórico: ${u.videos_used}</p>
        </div>
        <div class="panel panel-pad">
          <h2 class="h2">Mudar plano</h2>
          <p class="lead" style="margin-bottom:1rem">Escolha o plano. O admin libera após confirmação de pagamento.</p>
          <button class="btn btn-primary" id="btnPro" data-go="pricing" type="button">Ver planos</button>
        </div>
        <div id="usageList" class="panel panel-pad"></div>
      </div>`;
    bindNav();
    msApi.usage().then((r) => {
      const box = $("#usageList");
      if (!box) return;
      const rows = r.usage || [];
      if (!rows.length) {
        box.innerHTML = `<h2 class="h2">Histórico</h2><p class="lead" style="margin:0">Nenhum processamento ainda. Proteja o primeiro criativo para começar.</p>`;
        return;
      }
      box.innerHTML =
        `<h2 class="h2">Histórico</h2>` +
        rows
          .slice(0, 15)
          .map(
            (x) =>
              `<div class="usage-row">${(x.created_at || "").slice(0, 19)} · ${x.kind} · ${x.platform || "-"} · ${escapeHtml(x.filename || "")}</div>`
          )
          .join("");
    });
  }

  function viewPricing() {
    getContent().innerHTML = `
      <div class="shell fade-in">
        <div class="page-head">
          <div class="back-row"><button class="btn btn-ghost btn-sm" data-go="dashboard" type="button">← ${t("back")}</button></div>
          <h1 class="h1">Planos</h1>
          <p class="lead">Comece grátis. Escalone quando a operação de mídia crescer.</p>
        </div>
        <div class="price-grid">
          <div class="price-card">
            <div class="plan-label">Free</div>
            <div class="price">R$ 0</div>
            <div class="price-period">para sempre</div>
            <ul>
              <li>2 uploads por dia</li>
              <li>Dual-layer black e white</li>
              <li>Arquivos até 50 MB</li>
            </ul>
          </div>
          <div class="price-card">
            <div class="plan-label">Mensal</div>
            <div class="price">R$ 59,90</div>
            <div class="price-period">por mês</div>
            <ul>
              <li><strong>10 vídeos por dia</strong></li>
              <li>Todas as funções</li>
              <li>Phase-stereo e metadados</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="mensal" type="button">Assinar Mensal</button>
          </div>
          <div class="price-card popular">
            <div class="plan-label">Trimestral · mais escolhido</div>
            <div class="price">R$ 129,90</div>
            <div class="price-period">a cada 3 meses</div>
            <ul>
              <li><strong>20 vídeos por dia</strong></li>
              <li>Todas as funções</li>
              <li>Melhor custo por vídeo</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="trimestral" type="button">Assinar Trimestral</button>
          </div>
          <div class="price-card">
            <div class="plan-label">Anual</div>
            <div class="price">R$ 299</div>
            <div class="price-period">por ano</div>
            <ul>
              <li><strong>Ilimitado</strong></li>
              <li>Agências e times</li>
              <li>Prioridade de suporte</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="anual" type="button">Assinar Anual</button>
          </div>
        </div>
        <p class="price-note">O botão registra o pedido na sua conta. O admin ativa o plano após o pagamento. PIX e cartão podem ser ligados depois no backend.</p>
      </div>`;
    bindNav();
    $$("[data-req]").forEach((b) => {
      b.onclick = async () => {
        try {
          await msApi.requestPro();
          toast("Pedido de plano " + b.dataset.req + " registrado. Admin libera em breve.");
        } catch (e) {
          toast(e.message);
        }
      };
    });
  }

  function viewTutorials() {
    getContent().innerHTML = `
      <div class="shell fade-in">
        <div class="page-head">
          <div class="back-row"><button class="btn btn-ghost btn-sm" data-go="dashboard" type="button">← ${t("back")}</button></div>
          <h1 class="h1">Como funciona</h1>
          <p class="lead">Sem jargão. Pense no GhostWave como um <strong>envelope com duas cartas</strong> no mesmo pacote.</p>
        </div>

        <div class="tutorial-grid">
          <div class="tutorial-card">
            <h3>O problema</h3>
            <p>Redes e editores (Meta, TikTok, CapCut) usam "ouvidos de robô" para legendar e moderar. Copy agressiva demais pode derrubar o anúncio.</p>
          </div>
          <div class="tutorial-card">
            <h3>A ideia dual-layer</h3>
            <p><strong>Carta de cima (black):</strong> o que o humano ouve. Seu criativo original, claro e natural.</p>
            <p><strong>Carta de baixo (white):</strong> copy limpa, bem baixa, moldada para o robô de legenda preferir ler ela.</p>
          </div>
          <div class="tutorial-card">
            <h3>Festa e sussurro</h3>
            <p>Na festa (áudio alto), o sussurro white fica mascarado. O ouvido foca na festa. O software de transcrição caça trechos limpos de voz, e a white é feita para ser fácil de ler.</p>
          </div>
          <div class="tutorial-card">
            <h3>Passo a passo</h3>
            <ul>
              <li>Escolha a <strong>plataforma</strong> (CapCut, TikTok, Meta)</li>
              <li>Marque as <strong>funções</strong> (cloaker, metadados, phase-stereo, compressão)</li>
              <li>Cole a <strong>copy white</strong> ou envie áudio white</li>
              <li>Envie o vídeo/áudio black e baixe o resultado</li>
            </ul>
          </div>
          <div class="tutorial-card">
            <h3>O que cada função faz</h3>
            <ul>
              <li><strong>Proteger áudio IA:</strong> dual-layer black + white</li>
              <li><strong>Limpar metadados:</strong> apaga rastros do arquivo</li>
              <li><strong>Phase-stereo:</strong> proteção L/R discreta</li>
              <li><strong>Compressão:</strong> vídeo mais leve sem pixelar de propósito</li>
            </ul>
          </div>
          <div class="tutorial-card">
            <h3>Expectativa realista</h3>
            <p>Nenhuma ferramenta garante 100% para sempre. As IAs mudam. O GhostWave maximiza a chance: <strong>humano ouve black; máquina tende a white</strong>. Sempre teste a legenda na plataforma antes de escalar spend.</p>
          </div>
        </div>

        <div class="row-actions">
          <button class="btn btn-primary" data-go="protect" type="button">Proteger um criativo agora</button>
        </div>
      </div>`;
    bindNav();
  }

  async function viewAdmin() {
    getContent().innerHTML = `
      <div class="shell fade-in">
        <button class="btn btn-ghost btn-sm" data-go="dashboard">← ${t("back")}</button>
        <h1 class="h1" style="margin-top:1rem">${t("admin")}</h1>
        <div class="stats" id="adminStats"></div>
        <h2 class="h2">${t("users")}</h2>
        <div class="table-wrap panel">
          <table>
            <thead><tr>
              <th>ID</th><th>Email</th><th>Nome</th><th>Role</th><th>Plano</th><th>Uso</th><th>Ativo</th><th></th>
            </tr></thead>
            <tbody id="userRows"></tbody>
          </table>
        </div>
      </div>
      <div id="modalRoot"></div>`;
    bindNav();
    try {
      const [stats, users] = await Promise.all([
        msApi.adminStats(),
        msApi.adminUsers(),
      ]);
      $("#adminStats").innerHTML = `
        <div class="stat"><div class="lbl">Users</div><div class="val">${stats.total_users}</div></div>
        <div class="stat"><div class="lbl">Pro</div><div class="val">${stats.pro_users}</div></div>
        <div class="stat"><div class="lbl">Videos</div><div class="val">${stats.videos_processed}</div></div>`;
      const tb = $("#userRows");
      tb.innerHTML = users.users
        .map(
          (u) => `
        <tr>
          <td>${u.id}</td>
          <td>${escapeHtml(u.email)}</td>
          <td>${escapeHtml(u.name)}</td>
          <td><span class="badge ${u.role === "admin" ? "admin" : ""}">${u.role}</span></td>
          <td><span class="badge ${u.plan === "pro" ? "pro" : "free"}">${u.plan}</span></td>
          <td style="font-family:var(--mono)">${u.videos_used}/${u.video_limit}</td>
          <td>${u.active ? "✓" : "—"}</td>
          <td><button class="btn btn-sm" data-edit="${u.id}">Edit</button></td>
        </tr>`
        )
        .join("");
      $$("[data-edit]").forEach((b) => {
        b.onclick = () => openEdit(users.users.find((x) => x.id === +b.dataset.edit));
      });
    } catch (e) {
      toast(e.message);
    }
  }

  function openEdit(u) {
    if (!u) return;
    const root = $("#modalRoot");
    root.innerHTML = `
      <div class="modal-back">
        <div class="modal">
          <h3>${escapeHtml(u.email)}</h3>
          <div class="field"><label>Nome</label><input id="e_name" value="${escapeAttr(u.name)}" /></div>
          <div class="field"><label>Role</label>
            <select id="e_role"><option value="user" ${u.role === "user" ? "selected" : ""}>user</option><option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option></select>
          </div>
          <div class="field"><label>Plano</label>
            <select id="e_plan">
                      <option value="free" ${u.plan === "free" ? "selected" : ""}>free (2/dia)</option>
                      <option value="mensal" ${u.plan === "mensal" ? "selected" : ""}>mensal (10/dia)</option>
                      <option value="trimestral" ${u.plan === "trimestral" ? "selected" : ""}>trimestral (20/dia)</option>
                      <option value="anual" ${u.plan === "anual" ? "selected" : ""}>anual (ilimitado)</option>
                      <option value="pro" ${u.plan === "pro" ? "selected" : ""}>pro legado</option>
                    </select>
          </div>
          <div class="field"><label>Limite</label><input id="e_limit" type="number" value="${u.video_limit}" /></div>
          <div class="field"><label>Usados</label><input id="e_used" type="number" value="${u.videos_used}" /></div>
          <div class="field"><label><input id="e_active" type="checkbox" ${u.active ? "checked" : ""} /> Ativo</label></div>
          <div class="field"><label>Notas</label><textarea id="e_notes">${escapeHtml(u.notes || "")}</textarea></div>
          <div class="field"><label>Nova senha</label><input id="e_pw" type="password" /></div>
          <div class="row-actions">
            <button class="btn btn-primary" id="e_save">${t("save")}</button>
            <button class="btn btn-ghost" id="e_close">Fechar</button>
          </div>
        </div>
      </div>`;
    $("#e_close").onclick = () => {
      root.innerHTML = "";
    };
    $(".modal-back").onclick = (ev) => {
      if (ev.target.classList.contains("modal-back")) root.innerHTML = "";
    };
    $("#e_save").onclick = async () => {
      try {
        await msApi.adminUpdate(u.id, {
          name: $("#e_name").value,
          role: $("#e_role").value,
          plan: $("#e_plan").value,
          video_limit: +$("#e_limit").value,
          videos_used: +$("#e_used").value,
          active: $("#e_active").checked,
          notes: $("#e_notes").value,
          new_password: $("#e_pw").value || null,
        });
        toast("Salvo");
        root.innerHTML = "";
        viewAdmin();
      } catch (e) {
        toast(e.message);
      }
    };
  }

  async function viewProtect() {
    if (!state.platforms.length) {
      try {
        const r = await msApi.platforms();
        state.platforms = r.platforms || [];
      } catch (e) {
        toast(e.message);
      }
    }
    const w = state.wizard;
    const steps = `
      <div class="steps">
        <span class="step-dot ${w.step === 1 ? "on" : w.step > 1 ? "done" : ""}">1 · Plataforma</span>
        <span class="step-dot ${w.step === 2 ? "on" : w.step > 2 ? "done" : ""}">2 · Funções</span>
        <span class="step-dot ${w.step === 3 ? "on" : w.step > 3 ? "done" : ""}">3 · Arquivo</span>
        <span class="step-dot ${w.step === 4 ? "on" : ""}">4 · Resultado</span>
      </div>`;

    let body = "";
    if (w.step === 1) {
      body = `
        <h1 class="h1">${t("platformTitle")}</h1>
        <p class="lead">${t("platformSub")}</p>
        <div class="plat-grid">
          ${state.platforms
            .map(
              (p) => `
            <button class="plat ${w.platform === p.id ? "selected" : ""}" data-plat="${p.id}">
              <img src="${p.icon_url}" alt="" onerror="this.style.display='none'" />
              <span class="name">${escapeHtml(p.name)}</span>
            </button>`
            )
            .join("")}
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost" data-go="dashboard">← ${t("back")}</button>
        </div>`;
    } else if (w.step === 2) {
      /* POPUP / painel das 4 funções principais */
      const o = w.opts;
      body = `
        <h1 class="h1">Funções do criativo</h1>
        <p class="lead"><strong>Verdade:</strong> black clara → legenda/extrator ainda leem black. Não há mágica 100%. Para <em>robô de anúncios</em>, use Anti-análise (som ainda da black). Para legenda white, use White only.</p>
        <div class="panel panel-pad" style="margin-bottom:1rem">
          <div class="field"><label for="cloakMode">Modo dual-layer</label>
            <select id="cloakMode">
              <option value="anti_analise" ${(o.cloakMode||'')==='anti_analise'?'selected':''}>Anti-análise (recomendado p/ ads) - black normal + white mascarada + micro-scramble</option>
              <option value="auto" ${(o.cloakMode||'auto')==='auto'?'selected':''}>Auto - loop Whisper até white vencer no score</option>
              <option value="natural" ${(o.cloakMode||'')==='natural'?'selected':''}>Natural - black 100% limpa + watermark (STT ainda lê black)</option>
              <option value="white_only" ${(o.cloakMode||'')==='white_only'?'selected':''}>White only - legenda white (humano também ouve white)</option>
              <option value="redirect" ${(o.cloakMode||'')==='redirect'?'selected':''}>Redirect fixo (sem loop)</option>
            </select>
          </div>
          <label class="check-row" for="opt_proteger">
            <input type="checkbox" id="opt_proteger" ${o.proteger ? "checked" : ""} />
            <span><strong>Dual-layer / cloaker</strong><span class="desc">Aplica o modo escolhido (anti-análise, natural, white_only, auto ou redirect).</span></span>
          </label>
          <label class="check-row" for="opt_metadados">
            <input type="checkbox" id="opt_metadados" ${o.metadados ? "checked" : ""} />
            <span><strong>Limpar metadados digitais</strong><span class="desc">Remove tags, software, GPS e rastros do arquivo de mídia.</span></span>
          </label>
          <label class="check-row" for="opt_phase">
            <input type="checkbox" id="opt_phase" ${o.phase ? "checked" : ""} />
            <span><strong>Phase-stereo invisível</strong><span class="desc">Codifica proteção no canal L/R (diferença de fase), quase imperceptível.</span></span>
          </label>
          <label class="check-row" for="opt_compress">
            <input type="checkbox" id="opt_compress" ${o.compress ? "checked" : ""} />
            <span><strong>Compressão de vídeo</strong><span class="desc">H.264 CRF ~20 - arquivo menor, visual praticamente igual.</span></span>
          </label>
        </div>
        <div class="panel panel-pad">
          <h2 class="h2">White Script</h2>
          <p class="lead" style="margin-bottom:0.75rem">Escolha o nicho e o idioma do script (como no mercado) — o texto preenche e você ainda pode editar. Volume secondary padrão ~−22 dB.</p>
          <div class="field"><label>White Script Template (nicho)</label>
            <select id="whiteNiche">${whiteNicheOptions(w.whiteNiche || "mmo")}</select>
          </div>
          <div class="field"><label>Idioma do Script</label>
            ${whiteLangButtons(w.whiteLang || "pt")}
            <p class="hint" style="margin-top:0.45rem;margin-bottom:0">Aplicado ao white script selecionado · PT-BR / EN / ES</p>
          </div>
          <div class="field"><label>Variação do script</label>
            <select id="whiteCopySel">${whiteCopyOptions(w.whiteNiche || "mmo", w.whiteCopyId || "mmo_1", w.whiteLang || "pt")}</select>
          </div>
          <div id="whiteCopyChips" class="white-copy-chips" aria-label="Atalhos de copy"></div>
          <div class="field"><label>Texto white (editável — injetado na camada secondary)</label>
            <textarea id="whiteText" rows="5" placeholder="Script white...">${escapeHtml(w.whiteText || defaultWhiteText(w.whiteLang || "pt"))}</textarea>
          </div>
          <div class="field"><label>Texto black (opcional — copy real, só para o score)</label>
            <textarea id="blackText" placeholder="Ex.: Compre agora com 50% off...">${escapeHtml(o.blackText || "")}</textarea>
          </div>
          <div class="field"><label>Áudio white (opcional — se enviar, prefere o arquivo ao texto sintético)</label>
            <input type="file" id="whiteFile" accept="audio/*,.wav,.mp3,.m4a" />
          </div>
          <div class="field"><label>Volume white (dB relativo à black) — mercado ~−22 · natural ~−40</label>
            <input type="number" id="decoyDb" value="${o.decoyDb}" min="-50" max="-18" step="1" />
          </div>
          <div class="hint">
            <strong>Nichos:</strong> MMO, Riqueza, Perda de Peso, Diabetes, DE, Memória, Anti-idade (+ Geral).<br/>
            <strong>Idioma:</strong> o TTS sintético e o score usam o texto no idioma escolhido.<br/>
            <strong>Nível:</strong> secondary ~−22 dB no anti-análise (referência de mercado).
          </div>
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost" id="backPlat">← ${t("back")}</button>
          <button class="btn btn-primary" id="toUpload">${t("continue")}</button>
        </div>`;
    } else if (w.step === 3) {
      const plat = state.platforms.find((p) => p.id === w.platform) || {
        name: w.platform,
      };
      if (w.processing) {
        const pct = Math.max(0, Math.min(100, Number(w.progressPct) || 0));
        const stage = w.progressStage || "Preparando…";
        body = `
        <h1 class="h1">Processando criativo</h1>
        <p class="lead">Um clique já iniciou. Não precisa clicar de novo — aguarde chegar a 100%.</p>
        <div class="panel panel-pad process-panel">
          <div class="process-pct" id="processPct">${pct}%</div>
          <div class="process-bar" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
            <div class="process-bar-fill" id="processBarFill" style="width:${pct}%"></div>
          </div>
          <p class="process-stage" id="processStage">${escapeHtml(stage)}</p>
          <p class="process-file">${escapeHtml((w.file && w.file.name) || "arquivo")}</p>
          <div class="process-steps">
            <span class="${pct >= 5 ? "on" : ""}">Upload</span>
            <span class="${pct >= 25 ? "on" : ""}">TTS white</span>
            <span class="${pct >= 55 ? "on" : ""}">Cloaker</span>
            <span class="${pct >= 85 ? "on" : ""}">Vídeo</span>
            <span class="${pct >= 100 ? "on" : ""}">Pronto</span>
          </div>
        </div>
        <p id="runHint" class="process-wait-hint">
          Não feche a página. Vídeos longos ou modo anti-análise podem levar vários minutos (TTS + Whisper + encode).
        </p>`;
      } else {
        const errBox = w.processError
          ? `<div class="hint process-error" role="alert"><strong>Processamento falhou</strong><br/>${escapeHtml(
              w.processError
            )}<div class="row-actions" style="margin-top:0.85rem;margin-bottom:0">
              <button type="button" class="btn btn-primary btn-sm" id="retryProcess">Tentar de novo</button>
            </div></div>`
          : "";
        body = `
        <h1 class="h1">${t("uploadTitle")}</h1>
        <p class="lead">${t("uploadSub")}</p>
        ${errBox}
        <div class="hint"><strong>${escapeHtml(plat.name)}</strong> — black audível + white em fala (TTS) baixa. Compare o resultado antes de subir na plataforma.</div>
        <div class="drop" id="drop">
          <strong>${t("drop")}</strong>
          <span>${t("dropHint")}</span>
          <div id="fileName" style="margin-top:0.75rem;font-family:var(--mono);font-size:0.8rem;color:var(--muted)"></div>
          <input type="file" id="fileInput" accept="audio/*,video/*,.mp4,.mov,.wav,.mp3,.mkv,.webm" />
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost" id="backOpts" type="button">← ${t("back")}</button>
          <button class="btn btn-primary" id="runBtn" type="button" ${w.file ? "" : "disabled"}>
            <span id="runLabel">${w.file ? "Proteger agora" : "Selecione um arquivo"}</span>
          </button>
        </div>
        <p id="runHint" style="color:var(--muted);font-size:0.85rem;margin-top:0.75rem">
          ${w.file ? "Clique uma vez em Proteger agora. A barra de progresso vai de 0% a 100% e o vídeo é entregue ao terminar." : "Envie o vídeo ou áudio para habilitar o botão."}
        </p>`;
      }
    } else {
      const r = w.result || {};
      const files = r.files || {};
      const baseName =
        (w.file && w.file.name && w.file.name.replace(/\.[^.]+$/, "")) ||
        "ghostwave";
      const hasMp4 = !!files.protected_mp4;
      const hasWav = !!files.protected_wav;
      body = `
        <h1 class="h1">Pronto</h1>
        <div class="hint result-ok">
          <strong>Processamento concluído</strong>
          ${
            hasMp4
              ? " Seu vídeo protegido está abaixo para baixar e pré-visualizar."
              : hasWav
                ? " Áudio protegido pronto (este upload não gerou MP4 — use WAV ou envie um vídeo)."
                : " Resposta sem arquivos — rode de novo ou veja o relatório técnico."
          }
        </div>

        <div class="result-dl panel panel-pad">
          <h2 class="h2" style="margin-bottom:0.75rem">Baixar arquivos</h2>
          <div class="row-actions" style="margin-top:0">
            ${
              hasMp4
                ? `<a class="btn btn-primary" href="${escapeAttr(
                    files.protected_mp4
                  )}" download="${escapeAttr(baseName)}_protegido.mp4">Baixar vídeo MP4</a>`
                : `<span class="chip">MP4 não gerado</span>`
            }
            ${
              hasWav
                ? `<a class="btn" href="${escapeAttr(
                    files.protected_wav
                  )}" download="${escapeAttr(baseName)}_protegido_stereo.wav">Baixar WAV estéreo</a>`
                : ""
            }
            ${
              files.tiktok_mono_wav
                ? `<a class="btn btn-ghost" href="${escapeAttr(
                    files.tiktok_mono_wav
                  )}" download="${escapeAttr(baseName)}_tiktok_mono.wav">Baixar mono TikTok</a>`
                : ""
            }
            ${
              files.white_preview_wav
                ? `<a class="btn btn-ghost" href="${escapeAttr(
                    files.white_preview_wav
                  )}" download="${escapeAttr(baseName)}_white.wav">Baixar white (voz)</a>`
                : ""
            }
            ${
              files.original_wav
                ? `<a class="btn btn-ghost" href="${escapeAttr(
                    files.original_wav
                  )}" download="${escapeAttr(baseName)}_original.wav">Baixar original</a>`
                : ""
            }
          </div>
          ${
            !hasMp4
              ? `<p class="lead" style="margin:0.85rem 0 0;font-size:0.9rem">Se você enviou MP4 e o botão não aparece, o remux falhou no servidor (ffmpeg). Veja o relatório técnico no fim da página.</p>`
              : ""
          }
        </div>

        ${
          hasMp4
            ? `<div class="panel panel-pad result-video">
                <h2 class="h2" style="margin-bottom:0.75rem">Prévia do vídeo</h2>
                <video controls playsinline preload="metadata" src="${escapeAttr(
                  files.protected_mp4
                )}"></video>
              </div>`
            : ""
        }

        <div class="hint" style="margin:1rem 0 0.75rem">
          <strong>Como ouvir (importante)</strong><br/>
          Use <strong>fone estéreo</strong> no áudio/vídeo protegido: você deve ouvir o anúncio (black).
          O arquivo <strong>TikTok mono</strong> é o que a plataforma tende a ouvir: copy white limpa.
          Alto-falante do celular = mono = soa como white (é o truque, não um bug).
        </div>
        <div class="compare">
          <div class="box">
            <h4>Original (black)</h4>
            ${
              files.original_wav
                ? `<audio controls src="${escapeAttr(files.original_wav)}"></audio>`
                : `<p class="lead" style="margin:0">Indisponível</p>`
            }
          </div>
          <div class="box">
            <h4>Protegido estéreo (humano)</h4>
            ${
              files.protected_wav
                ? `<audio controls src="${escapeAttr(files.protected_wav)}"></audio>`
                : `<p class="lead" style="margin:0">Indisponível</p>`
            }
            <p class="note">Fone estéreo: anúncio principal. Não use só o alto-falante do celular.</p>
          </div>
          ${
            files.tiktok_mono_wav
              ? `<div class="box">
            <h4>TikTok mono (plataforma)</h4>
            <audio controls src="${escapeAttr(files.tiktok_mono_wav)}"></audio>
            <p class="note">Downmix (L+R)/2 — deve ser a copy white falada, limpa.</p>
          </div>`
              : ""
          }
          ${
            files.white_preview_wav
              ? `<div class="box">
            <h4>White isolada (TTS)</h4>
            <audio controls src="${escapeAttr(files.white_preview_wav)}"></audio>
            <p class="note">Só a voz da copy — tem que ser fala, não chiado.</p>
          </div>`
              : ""
          }
        </div>

        ${
          r.tts_meta
            ? r.tts_meta.tts
              ? `<div class="hint result-ok" style="margin:1rem 0">
                   Voz white (copy falada): <strong>${escapeHtml(r.tts_meta.engine || "ok")}</strong>
                   · ouça o arquivo <strong>white isolada</strong> para validar a fala.
                 </div>`
              : `<div class="hint process-error" style="margin:1rem 0" role="alert">
                   <strong>White NÃO é voz real</strong> (caiu em formantes/barulho).
                   Na VPS: <code>pip install edge-tts gTTS</code> e
                   <code>apt-get install -y espeak-ng ffmpeg</code>, depois rebuild.
                   ${
                     r.tts_meta.warning
                       ? `<br/><span style="font-size:0.85rem">${escapeHtml(
                           r.tts_meta.warning
                         )}</span>`
                       : ""
                   }
                 </div>`
            : ""
        }

        ${renderSttPreview(r)}

        <div class="row-actions">
          <button class="btn btn-primary" id="again" type="button">${t("again") || "Novo arquivo"}</button>
          <button class="btn btn-ghost" data-go="dashboard" type="button">${t("home") || "Início"}</button>
        </div>

        <details class="result-tech">
          <summary>Relatório técnico (JSON)</summary>
          <pre class="panel panel-pad">${escapeHtml(JSON.stringify(r.report || {}, null, 2))}</pre>
        </details>`;
    }

    getContent().innerHTML = `
      <div class="shell fade-in">
        ${steps}
        ${body}
      </div>`;
    bindNav();

    if (w.step === 1) {
      $$("[data-plat]").forEach((b) => {
        b.onclick = () => {
          state.wizard.platform = b.dataset.plat;
          state.wizard.step = 2;
          render();
        };
      });
    }
    if (w.step === 2) {
      bindWhitePresetControls();
      $("#backPlat").onclick = () => {
        state.wizard.step = 1;
        render();
      };
      const toUp = $("#toUpload");
      if (toUp) {
        toUp.onclick = () => {
          try {
            const chk = (id, fallback = true) => {
              const el = $("#" + id);
              return el ? !!el.checked : fallback;
            };
            state.wizard.opts = {
              proteger: chk("opt_proteger", true),
              metadados: chk("opt_metadados", true),
              phase: chk("opt_phase", true),
              compress: chk("opt_compress", true),
              decoyDb: parseFloat(($("#decoyDb") && $("#decoyDb").value) || "-22"),
              cloakMode: ($("#cloakMode") && $("#cloakMode").value) || "anti_analise",
              blackText: ($("#blackText") && $("#blackText").value) || "",
            };
            state.wizard.whiteLang =
              ($("#whiteLang") && $("#whiteLang").value) || state.wizard.whiteLang || "pt";
            state.wizard.whiteText =
              ($("#whiteText") && $("#whiteText").value) ||
              defaultWhiteText(state.wizard.whiteLang);
            state.wizard.whiteNiche = ($("#whiteNiche") && $("#whiteNiche").value) || "mmo";
            state.wizard.whiteCopyId = ($("#whiteCopySel") && $("#whiteCopySel").value) || "mmo_1";
            const wfEl = $("#whiteFile");
            state.wizard.whiteFile =
              wfEl && wfEl.files && wfEl.files[0] ? wfEl.files[0] : null;
            state.wizard.processError = "";
            state.wizard.step = 3;
            render();
          } catch (err) {
            console.error(err);
            toast(err.message || "Não foi possível avançar. Tente de novo.");
          }
        };
      }
    }
    if (w.step === 3) {
      // se já está processando, só sincroniza a barra (sem re-bind de upload)
      if (w.processing) {
        const fill = $("#processBarFill");
        const pctEl = $("#processPct");
        const stageEl = $("#processStage");
        const pct = Math.max(0, Math.min(100, Number(w.progressPct) || 0));
        if (fill) fill.style.width = pct + "%";
        if (pctEl) pctEl.textContent = Math.floor(pct) + "%";
        if (stageEl) stageEl.textContent = w.progressStage || "Processando…";
        return;
      }

      const retry = $("#retryProcess");
      if (retry) {
        retry.onclick = () => {
          state.wizard.processError = "";
          startProtectProcess();
        };
      }

      const drop = $("#drop");
      const input = $("#fileInput");
      const run = $("#runBtn");
      const nameEl = $("#fileName");
      const label = $("#runLabel");
      const hint = $("#runHint");
      const setFile = (f) => {
        state.wizard.file = f;
        state.wizard.processError = "";
        if (nameEl) nameEl.textContent = f ? "✓ " + f.name : "";
        if (run) run.disabled = !f;
        if (label) label.textContent = f ? "Proteger agora" : "Selecione um arquivo";
        if (hint) {
          hint.textContent = f
            ? "Clique uma vez em Proteger agora. Progresso 0%→100% e entrega automática."
            : "Envie o vídeo ou áudio para habilitar o botão.";
        }
      };
      if (state.wizard.file) setFile(state.wizard.file);
      if (drop && input) {
        drop.onclick = () => input.click();
        input.onchange = () => setFile(input.files[0]);
        drop.ondragover = (e) => {
          e.preventDefault();
          drop.classList.add("drag");
        };
        drop.ondragleave = () => drop.classList.remove("drag");
        drop.ondrop = (e) => {
          e.preventDefault();
          drop.classList.remove("drag");
          if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
        };
      }
      const back = $("#backOpts");
      if (back) {
        back.onclick = () => {
          state.wizard.step = 2;
          state.wizard.processError = "";
          render();
        };
      }
      if (run) {
        run.onclick = () => startProtectProcess();
      }
    }
    if (w.step === 4) {
      const ag = $("#again");
      if (ag) {
        ag.onclick = () => {
          state.wizard = {
            step: 1,
            platform: null,
            file: null,
            whiteFile: null,
            whiteText: "",
            whiteNiche: "mmo",
            whiteCopyId: "mmo_1",
            whiteLang: "pt",
            result: null,
            opts: {
              proteger: true,
              metadados: true,
              phase: true,
              compress: true,
              decoyDb: -22,
              cloakMode: "anti_analise",
            },
          };
          render();
        };
      }
    }
  }

  function truncateText(s, max = 220) {
    const t = String(s || "").replace(/\s+/g, " ").trim();
    if (!t) return "";
    if (t.length <= max) return t;
    return t.slice(0, max - 1) + "…";
  }

  function renderSttPreview(r) {
    const p = (r && (r.stt_preview || (r.report && r.report.stt_preview))) || null;
    if (!p) {
      return `<p class="lead">Compare os áudios acima. Whisper local opcional no servidor para o preview “IA leu”.</p>`;
    }
    const goal = String(p.goal || "").toLowerCase();
    const isAnti = goal.includes("anti") || goal.includes("ads");
    const heard = truncateText(p.ai_heard || p.final_transcript || "", 220);
    let badge;
    if (isAnti) {
      badge = p.passed
        ? `<span class="chip ok">Anti-análise: confusão OK (proxy Whisper)</span>`
        : `<span class="chip" style="color:var(--warn);border-color:rgba(251,191,36,0.35)">Anti-análise: confusão fraca neste teste</span>`;
    } else {
      badge = p.passed
        ? `<span class="chip ok">Score: white venceu no Whisper</span>`
        : `<span class="chip" style="color:var(--warn);border-color:rgba(251,191,36,0.35)">Score: black ainda forte no Whisper</span>`;
    }
    const avail = p.stt_available
      ? ""
      : `<p class="lead" style="font-size:0.9rem;margin:0.5rem 0 0">Whisper não está no servidor — preview STT não rodou de verdade.</p>`;
    return `
      <div class="section">
        <h2 class="h2">Preview STT (Whisper local)</h2>
        <p class="lead" style="margin-bottom:0.85rem;font-size:0.9rem">
          Isso é um <strong>proxy local</strong>, não o classificador real do TikTok/Meta.
          Texto longo e “louco” costuma ser alucinação do Whisper em áudio dual-layer — não significa que o MP4 quebrou.
        </p>
        <div class="dual-demo">
          <div class="dual-box human">
            <div class="who">Humano (fone estéreo)</div>
            <blockquote>Deve ouvir principalmente a black (criativo original).</blockquote>
          </div>
          <div class="dual-box ai">
            <div class="who">Whisper local (trecho)</div>
            <blockquote>${escapeHtml(heard || "(sem transcrição)")}</blockquote>
            <p class="note">Score winner: <strong>${escapeHtml(
              p.winner || "?"
            )}</strong> · tentativas: ${p.attempts ?? "—"} · modo: ${escapeHtml(
      p.goal || "?"
    )}</p>
          </div>
        </div>
        <div style="margin:0.75rem 0">${badge}</div>
        ${avail}
        <p class="lead" style="font-size:0.88rem;margin:0">${escapeHtml(
          p.honest_note || p.note || ""
        )}</p>
      </div>`;
  }

  function escapeHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  /** Atualiza barra 0–100 sem re-render completo (evita perder o job). */
  function setProcessProgress(pct, stage) {
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    state.wizard.progressPct = p;
    if (stage) state.wizard.progressStage = stage;
    const fill = document.getElementById("processBarFill");
    const pctEl = document.getElementById("processPct");
    const stageEl = document.getElementById("processStage");
    if (fill) fill.style.width = p + "%";
    if (pctEl) pctEl.textContent = Math.floor(p) + "%";
    if (stageEl && stage) stageEl.textContent = stage;
    // acende chips de etapa se existirem
    document.querySelectorAll(".process-steps span").forEach((el, i) => {
      const thr = [5, 25, 55, 85, 100][i] || 100;
      el.classList.toggle("on", p >= thr);
    });
  }

  /**
   * Um clique em "Proteger agora":
   * mostra progresso 0→100 e só entrega o resultado quando a API terminar.
   * Não precisa clicar de novo.
   */
  async function startProtectProcess() {
    const w = state.wizard;
    if (w.processing) return;
    if (!w.file || !w.platform) {
      toast("Selecione o arquivo e a plataforma.");
      return;
    }
    if ((state.user.daily_left ?? state.user.videos_left) <= 0) {
      toast(t("noCredits"));
      return;
    }

    w.processing = true;
    w.processError = "";
    w.progressPct = 0;
    w.progressStage = "Enviando arquivo…";
    render(); // entra na tela de progresso

    let fake = 0;
    let waitedMs = 0;
    const stages = [
      [8, "Enviando arquivo…"],
      [22, "Gerando voz white (TTS)…"],
      [48, "Aplicando dual-layer…"],
      [68, "Otimizando camadas (Whisper)…"],
      [82, "Montando vídeo…"],
      [92, "Finalizando no servidor…"],
    ];
    const tick = setInterval(() => {
      waitedMs += 280;
      // sobe sozinho até 92%; os 100% só quando a API responder
      if (fake < 92) {
        const step = fake < 30 ? 1.8 : fake < 60 ? 1.1 : 0.45;
        fake = Math.min(92, fake + step);
        let stage = w.progressStage;
        for (const [th, label] of stages) {
          if (fake >= th) stage = label;
        }
        // após 90s parado no teto fake, deixa claro que o servidor ainda trabalha
        if (fake >= 90 && waitedMs > 90000) {
          stage = "Servidor ainda processando (TTS/Whisper/ffmpeg). Aguarde…";
        }
        setProcessProgress(fake, stage);
      } else if (waitedMs > 90000) {
        setProcessProgress(
          92,
          "Servidor ainda processando (TTS/Whisper/ffmpeg). Aguarde…"
        );
      }
    }, 280);

    try {
      const res = await msApi.process(w.file, w.platform, {
        proteger: w.opts?.proteger !== false,
        metadados: w.opts?.metadados !== false,
        phase: w.opts?.phase !== false,
        compress: w.opts?.compress !== false,
        decoyDb: w.opts?.decoyDb ?? -22,
        cloakMode: w.opts?.cloakMode || "anti_analise",
        whiteText: w.whiteText || defaultWhiteText(w.whiteLang || "pt"),
        whiteLang: w.whiteLang || "pt",
        whiteFile: w.whiteFile || null,
        blackText: (w.opts && w.opts.blackText) || "",
      });
      if (!res || res.ok === false) {
        throw new Error(
          (res && (res.detail || res.error || res.message)) ||
            "Resposta inválida do servidor"
        );
      }
      const files = (res && res.files) || {};
      if (!files.protected_wav && !files.protected_mp4) {
        throw new Error(
          "O servidor respondeu sem arquivos. Veja o log da API (ffmpeg/TTS)."
        );
      }
      setProcessProgress(100, "Concluído — abrindo resultado…");
      await new Promise((r) => setTimeout(r, 350));
      w.processing = false;
      w.progressPct = 100;
      w.processError = "";
      w.result = res;
      if (res.user) state.user = res.user;
      w.step = 4;
      toast("Processamento concluído");
      // Se a tela de resultado falhar por bug de UI, NÃO tratar como falha do processar
      try {
        render();
      } catch (renderErr) {
        console.error("result render error", renderErr);
        showEmergencyResult(res);
      }
    } catch (e) {
      console.error("process error", e);
      w.processing = false;
      w.progressPct = 0;
      w.progressStage = "";
      let msg = e && e.message ? String(e.message) : "Falha no processamento";
      if (e && e.name === "AbortError") {
        msg =
          "Tempo esgotado (15 min). O vídeo é muito longo ou o servidor travou no Whisper/ffmpeg.";
      }
      if (msg.startsWith("[") || msg.startsWith("{")) {
        try {
          const parsed = JSON.parse(msg);
          if (Array.isArray(parsed) && parsed[0] && parsed[0].msg) {
            msg = parsed.map((x) => x.msg).join("; ");
          } else if (parsed && parsed.detail) {
            msg = String(parsed.detail);
          }
        } catch (_) {}
      }
      w.processError = msg;
      try {
        render();
      } catch (re) {
        console.error(re);
        toast(msg);
        getContent().innerHTML = `<div class="shell"><div class="hint process-error"><strong>Erro</strong><br/>${escapeHtml(
          msg
        )}</div><button class="btn" data-go="dashboard">Início</button></div>`;
        bindNav();
      }
      toast(msg);
    } finally {
      clearInterval(tick);
    }
  }

  /** Fallback mínimo se a tela de resultado normal quebrar */
  function showEmergencyResult(res) {
    const files = (res && res.files) || {};
    const links = [];
    if (files.protected_mp4) {
      links.push(
        `<a class="btn btn-primary" href="${escapeAttr(
          files.protected_mp4
        )}" download>Baixar vídeo MP4</a>`
      );
    }
    if (files.protected_wav) {
      links.push(
        `<a class="btn" href="${escapeAttr(
          files.protected_wav
        )}" download>Baixar áudio WAV</a>`
      );
    }
    if (files.white_preview_wav) {
      links.push(
        `<a class="btn btn-ghost" href="${escapeAttr(
          files.white_preview_wav
        )}" download>Baixar white</a>`
      );
    }
    getContent().innerHTML = `
      <div class="shell fade-in">
        <h1 class="h1">Pronto</h1>
        <div class="hint result-ok"><strong>Processamento concluído</strong> (tela simplificada)</div>
        <div class="result-dl panel panel-pad">
          <div class="row-actions" style="margin-top:0">${
            links.join(" ") || "<p>Sem links de arquivo.</p>"
          }</div>
          ${
            files.protected_mp4
              ? `<video controls playsinline style="width:100%;margin-top:1rem;border-radius:10px" src="${escapeAttr(
                  files.protected_mp4
                )}"></video>`
              : ""
          }
        </div>
        <div class="row-actions">
          <button class="btn btn-primary" data-go="protect" type="button">Novo arquivo</button>
          <button class="btn btn-ghost" data-go="dashboard" type="button">Início</button>
        </div>
      </div>`;
    bindNav();
  }

  async function render() {
    if (state.view !== "auth") stopAuthDecor();

    if (state.view === "boot") {
      app.innerHTML = `<div class="auth-wrap"><div class="spinner"></div></div>`;
      try {
        const me = await msApi.me();
        state.user = me.user;
        state.view = "dashboard";
      } catch {
        state.view = "auth";
      }
    }

    if (state.view === "auth") return viewAuth();
    if (!state.user) {
      state.view = "auth";
      return viewAuth();
    }

    // Mounts sidebar once; subsequent calls only update #content
    renderShell();

    if (state.view === "dashboard") return viewDashboard();
    if (state.view === "account") return viewAccount();
    if (state.view === "admin") return viewAdmin();
    if (state.view === "protect") return viewProtect();
    if (state.view === "tutorials") return viewTutorials();
    if (state.view === "pricing") return viewPricing();
    return viewDashboard();
  }

  // start
  render();
})();
