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
          return `<button type="button" class="lang-script-btn ${active}" data-lang="${escapeAttr(
            l.id
          )}" role="radio" aria-checked="${l.id === sel}">
            <span class="lang-script-flag">${escapeHtml(l.flag || "")}</span>
            <span class="lang-script-name">${escapeHtml(l.label)}</span>
            <span class="lang-script-code">${escapeHtml(l.short || l.id.toUpperCase())}</span>
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
      <select id="langSel" class="chip" style="appearance:auto;background:var(--surface);border:1px solid var(--border);color:var(--ink);padding:0.35rem 0.5rem;border-radius:999px">
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

  function nav(extra = "") {
    const u = state.user;
    const left = u.daily_left ?? u.videos_left;
    const lim = u.daily_limit ?? u.video_limit;
    return `
      <nav class="nav">
        <div class="brand" data-go="dashboard" title="GhostWave">
          <img class="brand-logo" src="/assets/logo.png" alt="GhostWave" width="44" height="44" />
          <div class="brand-text">GhostWave</div>
        </div>
        <div class="nav-right">
          ${langSelect()}
          <button class="btn btn-ghost btn-sm" data-go="tutorials">Tutoriais</button>
          <button class="btn btn-ghost btn-sm" data-go="pricing">Planos</button>
          <span class="chip cyan">${(u.plan_name || u.plan || "free").toString()}</span>
          <span class="chip">${left}/${lim} hoje</span>
          ${u.role === "admin" ? `<span class="chip admin">ADMIN</span>` : ""}
          <button class="btn btn-ghost btn-sm" id="btnLogout">${t("logout")}</button>
        </div>
      </nav>
      ${extra}`;
  }

  function bindNav() {
    bindLang();
    $$("[data-go]").forEach((el) => {
      el.onclick = () => {
        state.view = el.getAttribute("data-go");
        if (state.view === "protect") {
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
        }
        render();
      };
    });
    const lo = $("#btnLogout");
    if (lo) {
      lo.onclick = async () => {
        try {
          await msApi.logout();
        } catch (_) {}
        state.user = null;
        state.view = "auth";
        render();
      };
    }
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
          <img class="auth-logo" src="/assets/logo.png" alt="GhostWave" width="112" height="112" />
          <h1>GhostWave</h1>
          <p class="sub">Duas camadas. Duas realidades. O humano ouve o original; a IA lê a copy white.</p>
          <div style="text-align:center;margin-bottom:1rem">
            ${langSelect()}
          </div>
          <div class="tabs">
            <button class="tab ${tab === "login" ? "active" : ""}" data-tab="login">${t("login")}</button>
            <button class="tab ${tab === "register" ? "active" : ""}" data-tab="register">${t("register")}</button>
          </div>
          <form id="authForm">
            ${
              tab === "register"
                ? `<div class="field"><label>${t("name")}</label><input name="name" required autocomplete="name" /></div>`
                : ""
            }
            <div class="field"><label>${t("email")}</label><input name="email" type="email" required autocomplete="email" /></div>
            <div class="field"><label>${t("password")}</label><input name="password" type="password" required minlength="6" autocomplete="${tab === "login" ? "current-password" : "new-password"}" /></div>
            <button class="btn btn-primary btn-block" type="submit">${tab === "login" ? t("login") : t("register")}</button>
          </form>
          <p class="auth-foot">2 grátis/dia · Mensal R$ 59,90 · Trimestral R$ 129,90 · Anual R$ 299</p>
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
    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
        <p class="kicker">PAINEL</p>
        <h1 class="h1">${t("welcome")}, ${escapeHtml(u.name)}</h1>
        <p class="lead">Duas camadas. Duas realidades. Seu público ouve o criativo original; a IA de moderação tende a ler a copy white.</p>

        <div class="dual-demo">
          <div class="dual-box human">
            <div class="who">CAMADA HUMANA</div>
            <blockquote>“Compre agora com 50% off!”</blockquote>
            <p style="margin:0.5rem 0 0;color:var(--muted);font-size:0.85rem">O que a pessoa ouve — áudio original, intacto.</p>
          </div>
          <div class="dual-box ai">
            <div class="who">CAMADA IA (STT)</div>
            <blockquote>“Dicas de jardinagem e flores sustentáveis.”</blockquote>
            <p style="margin:0.5rem 0 0;color:var(--muted);font-size:0.85rem">O que a legenda/moderação tende a transcrever (copy white).</p>
          </div>
        </div>

        <div class="stats">
          <div class="stat"><div class="lbl">${t("plan")}</div><div class="val" style="font-size:1.05rem">${escapeHtml(u.plan_name || u.plan || "free")}</div></div>
          <div class="stat"><div class="lbl">Hoje</div><div class="val">${usedToday}/${lim}</div></div>
          <div class="stat"><div class="lbl">Restam hoje</div><div class="val">${left}</div></div>
        </div>

        <div class="actions">
          <button class="action featured" data-go="protect" type="button">
            <span class="arrow">→</span>
            <div class="cta-media">
              <img src="/assets/cta-protect.jpg" alt="GhostWave — proteger criativo" />
            </div>
            <div class="cta-body">
              <span class="cta-pill">★ Principal</span>
              <h3>Proteger criativo</h3>
              <p>Plataforma → funções dual-layer → upload → download. Como o líder do mercado, só que com fluxo GhostWave.</p>
            </div>
          </button>
          <div style="display:flex;flex-direction:column;gap:1rem">
            <button class="action" data-go="tutorials" style="min-height:100px">
              <div class="num">02</div>
              <h3>Tutoriais (modo leigo)</h3>
              <p>Entenda dual-layer sem jargão técnico.</p>
            </button>
            <button class="action" data-go="account" style="min-height:100px">
              <div class="num">03</div>
              <h3>${t("account")}</h3>
              <p>Plano, créditos diários e assinatura.</p>
            </button>
            ${
              u.role === "admin"
                ? `<button class="action" data-go="admin" style="min-height:100px">
                    <div class="num">04</div>
                    <h3>${t("admin")}</h3>
                    <p>Usuários, planos e cotas diárias.</p>
                  </button>`
                : `<button class="action" data-go="pricing" style="min-height:100px">
                    <div class="num">04</div>
                    <h3>Planos</h3>
                    <p>Mensal, trimestral e anual ilimitado.</p>
                  </button>`
            }
          </div>
        </div>

        <div class="section">
          <h2 class="h2">Funções (iguais ao top do mercado — e além)</h2>
          <div class="layers">
            <div class="layer"><span class="tag">01</span><strong>Dual-layer black → white</strong><span>Humano ouve black; white baixa para STT/moderação.</span></div>
            <div class="layer"><span class="tag">02</span><strong>Limpar metadados</strong><span>Remove rastros digitais do arquivo.</span></div>
            <div class="layer"><span class="tag">03</span><strong>Phase-stereo</strong><span>Proteção L/R invisível no downmix mono.</span></div>
            <div class="layer"><span class="tag">04</span><strong>Compressão inteligente</strong><span>Vídeo menor sem perda visual perceptível.</span></div>
          </div>
        </div>
      </div>`;
    bindNav();
  }

  function viewAccount() {
    const u = state.user;
    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
        <button class="btn btn-ghost btn-sm" data-go="dashboard">← ${t("back")}</button>
        <h1 class="h1" style="margin-top:1rem">${t("account")}</h1>
        <div class="panel panel-pad" style="margin-top:1rem">
          <p><strong>${t("email")}:</strong> ${escapeHtml(u.email)}</p>
          <p><strong>${t("plan")}:</strong> ${escapeHtml(u.plan_name || u.plan)}</p>
          <p><strong>Hoje:</strong> ${u.daily_used ?? 0}/${u.daily_limit ?? u.video_limit} · restam <span class="chip cyan">${u.daily_left ?? u.videos_left}</span></p>
          <p style="color:var(--muted);font-size:0.85rem">Contador zera todo dia (UTC). Total histórico: ${u.videos_used}</p>
        </div>
        <div class="panel panel-pad" style="margin-top:1rem">
          <h2 class="h2">Assinar / mudar plano</h2>
          <p class="lead">Pagamento manual por enquanto — peça no botão e o admin libera o plano.</p>
          <button class="btn btn-primary" id="btnPro" data-go="pricing">Ver planos</button>
        </div>
        <div id="usageList" class="panel panel-pad" style="margin-top:1rem"></div>
      </div>`;
    bindNav();
    msApi.usage().then((r) => {
      const box = $("#usageList");
      if (!box) return;
      const rows = r.usage || [];
      if (!rows.length) {
        box.innerHTML = `<p class="lead" style="margin:0">Sem processamentos ainda.</p>`;
        return;
      }
      box.innerHTML =
        `<h2 class="h2">Histórico</h2>` +
        rows
          .slice(0, 15)
          .map(
            (x) =>
              `<div style="font-family:var(--mono);font-size:0.78rem;color:var(--muted);padding:0.35rem 0;border-bottom:1px solid var(--border)">${(x.created_at || "").slice(0, 19)} · ${x.kind} · ${x.platform || "—"} · ${escapeHtml(x.filename || "")}</div>`
          )
          .join("");
    });
  }

  function viewPricing() {
    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
        <button class="btn btn-ghost btn-sm" data-go="dashboard">← ${t("back")}</button>
        <h1 class="h1" style="margin-top:1rem">Planos GhostWave</h1>
        <p class="lead">Comece grátis. Escalone quando a operação crescer.</p>
        <div class="price-grid">
          <div class="price-card">
            <div class="chip">FREE</div>
            <div class="price">R$ 0</div>
            <ul>
              <li>2 uploads por dia</li>
              <li>Dual-layer black → white</li>
              <li>Arquivos até 50 MB</li>
            </ul>
          </div>
          <div class="price-card">
            <div class="chip">MENSAL</div>
            <div class="price">R$ 59,90<span style="font-size:0.8rem;color:var(--muted)">/mês</span></div>
            <ul>
              <li><strong>10 vídeos por dia</strong></li>
              <li>Todas as 4 funções</li>
              <li>Phase-stereo + metadados</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="mensal">Quero Mensal</button>
          </div>
          <div class="price-card popular">
            <div class="chip cyan">TRIMESTRAL · POPULAR</div>
            <div class="price">R$ 129,90<span style="font-size:0.8rem;color:var(--muted)">/3 meses</span></div>
            <ul>
              <li><strong>20 vídeos por dia</strong></li>
              <li>Todas as funções</li>
              <li>Melhor custo/benefício</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="trimestral">Quero Trimestral</button>
          </div>
          <div class="price-card">
            <div class="chip">ANUAL</div>
            <div class="price">R$ 299<span style="font-size:0.8rem;color:var(--muted)">/ano</span></div>
            <ul>
              <li><strong>Ilimitado</strong></li>
              <li>Agências e times</li>
              <li>Prioridade total</li>
            </ul>
            <button class="btn btn-primary btn-block btn-sm" data-req="anual">Quero Anual</button>
          </div>
        </div>
        <p style="color:var(--muted);font-size:0.85rem">O botão registra o pedido na sua conta. O admin ativa o plano após o pagamento (PIX/cartão pode ser ligado depois).</p>
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
    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
        <button class="btn btn-ghost btn-sm" data-go="dashboard">← ${t("back")}</button>
        <h1 class="h1" style="margin-top:1rem">Como funciona (modo leigo)</h1>
        <p class="lead">Sem jargão. Pense no GhostWave como um <strong>envelope com duas cartas</strong> no mesmo pacote.</p>

        <div class="tutorial-grid">
          <div class="tutorial-card">
            <h3>1. O problema</h3>
            <p>Redes e editores (Meta, TikTok, CapCut) usam “ouvidos de robô” (IA) para legendar e moderar. Às vezes a copy do anúncio é agressiva demais para o robô — e o anúncio cai.</p>
          </div>
          <div class="tutorial-card">
            <h3>2. A ideia dual-layer</h3>
            <p><strong>Carta de cima (black):</strong> o que o ser humano ouve — seu criativo original, claro e natural.</p>
            <p><strong>Carta de baixo (white):</strong> uma copy “limpa”, bem baixinha, moldada para o robô de legenda preferir ler ela.</p>
          </div>
          <div class="tutorial-card">
            <h3>3. Analogia do apito e da festa</h3>
            <p>Na festa (seu áudio alto), o sussurro white fica mascarado. O ouvido humano foca na festa. O software de transcrição, porém, “caça” trechos limpos de voz — e a white é fabricada para ser fácil de transcrever.</p>
          </div>
          <div class="tutorial-card">
            <h3>4. Passo a passo no GhostWave</h3>
            <ul>
              <li>Escolha a <strong>plataforma</strong> (CapCut, TikTok, Meta…)</li>
              <li>Marque as <strong>4 funções</strong> (cloaker, metadados, phase-stereo, compressão)</li>
              <li>Cole a <strong>copy white</strong> (ou envie áudio white)</li>
              <li>Envie o vídeo/áudio black e baixe o resultado</li>
            </ul>
          </div>
          <div class="tutorial-card">
            <h3>5. O que cada função faz</h3>
            <ul>
              <li><strong>Proteger áudio IA:</strong> dual-layer black + white</li>
              <li><strong>Limpar metadados:</strong> apaga rastros do arquivo (software, GPS, tags)</li>
              <li><strong>Phase-stereo:</strong> proteção extra L/R quase imperceptível</li>
              <li><strong>Compressão:</strong> deixa o vídeo mais leve sem “pixelar” de propósito</li>
            </ul>
          </div>
          <div class="tutorial-card">
            <h3>6. Expectativa realista</h3>
            <p>Nenhuma ferramenta no mundo garante 100% de aprovação para sempre — as IAs mudam. O GhostWave maximiza a chance: <strong>humano ouve black; máquina tende a white</strong>. Sempre teste a legenda na plataforma antes de escalar spend.</p>
          </div>
        </div>

        <div class="row-actions">
          <button class="btn btn-primary" data-go="protect">Proteger um criativo agora</button>
        </div>
      </div>`;
    bindNav();
  }

  async function viewAdmin() {
    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
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
          <div class="field"><label>Modo dual-layer</label>
            <select id="cloakMode">
              <option value="anti_analise" ${(o.cloakMode||'')==='anti_analise'?'selected':''}>Anti-análise (recomendado p/ ads) — black normal + white mascarada + micro-scramble</option>
              <option value="auto" ${(o.cloakMode||'auto')==='auto'?'selected':''}>Auto — loop Whisper até white vencer no score</option>
              <option value="natural" ${(o.cloakMode||'')==='natural'?'selected':''}>Natural — black 100% limpa + watermark (STT ainda lê black)</option>
              <option value="white_only" ${(o.cloakMode||'')==='white_only'?'selected':''}>White only — legenda white (humano também ouve white)</option>
              <option value="redirect" ${(o.cloakMode||'')==='redirect'?'selected':''}>Redirect fixo (sem loop)</option>
            </select>
          </div>
          <label class="field" style="display:flex;gap:0.75rem;align-items:flex-start;cursor:pointer">
            <input type="checkbox" id="opt_proteger" ${o.proteger ? "checked" : ""} style="margin-top:0.35rem;width:auto" />
            <span><strong>1 · Dual-layer / cloaker</strong><br/>
            <span style="color:var(--muted);font-size:0.88rem">Aplica o modo escolhido (anti-análise, natural, white_only, auto ou redirect).</span></span>
          </label>
          <label class="field" style="display:flex;gap:0.75rem;align-items:flex-start;cursor:pointer">
            <input type="checkbox" id="opt_metadados" ${o.metadados ? "checked" : ""} style="margin-top:0.35rem;width:auto" />
            <span><strong>2 · Limpar metadados digitais</strong><br/>
            <span style="color:var(--muted);font-size:0.88rem">Remove tags, software, GPS e rastros do arquivo de mídia.</span></span>
          </label>
          <label class="field" style="display:flex;gap:0.75rem;align-items:flex-start;cursor:pointer">
            <input type="checkbox" id="opt_phase" ${o.phase ? "checked" : ""} style="margin-top:0.35rem;width:auto" />
            <span><strong>3 · Encriptamento phase-stereo invisível</strong><br/>
            <span style="color:var(--muted);font-size:0.88rem">Codifica proteção no canal L/R (diferença de fase), quase imperceptível.</span></span>
          </label>
          <label class="field" style="display:flex;gap:0.75rem;align-items:flex-start;cursor:pointer;margin-bottom:0">
            <input type="checkbox" id="opt_compress" ${o.compress ? "checked" : ""} style="margin-top:0.35rem;width:auto" />
            <span><strong>4 · Compressão de vídeo sem perda perceptível</strong><br/>
            <span style="color:var(--muted);font-size:0.88rem">H.264 CRF ~20 — arquivo menor, visual praticamente igual.</span></span>
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
      body = `
        <h1 class="h1">${t("uploadTitle")}</h1>
        <p class="lead">${t("uploadSub")}</p>
        <div class="hint"><strong>${escapeHtml(plat.name)}</strong> — black audível + white baixa para ASR. Compare o resultado antes de subir na plataforma.</div>
        <div class="drop" id="drop">
          <strong>${t("drop")}</strong>
          <span>${t("dropHint")}</span>
          <div id="fileName" style="margin-top:0.75rem;font-family:var(--mono);font-size:0.8rem;color:var(--cyan)"></div>
          <input type="file" id="fileInput" accept="audio/*,video/*,.mp4,.mov,.wav,.mp3,.mkv,.webm" />
        </div>
        <div class="row-actions">
          <button class="btn btn-ghost" id="backOpts">← ${t("back")}</button>
          <button class="btn btn-primary" id="runBtn" disabled>
            <span id="runLabel">${w.file ? "Pronto para processar" : "Selecione um arquivo"}</span>
          </button>
        </div>
        <p id="runHint" style="color:var(--muted);font-size:0.85rem;margin-top:0.75rem">
          ${w.file ? "Arquivo carregado. Clique em processar — o botão muda para “Processando…” e depois “Concluído”." : "Envie o vídeo ou áudio para habilitar o botão."}
        </p>`;
    } else {
      const r = w.result;
      body = `
        <h1 class="h1">${t("result")}</h1>
        <div class="hint" style="border-color:rgba(61,214,140,0.4);background:rgba(61,214,140,0.08)">
          <strong>✓ Processamento concluído</strong>
        </div>
        ${renderSttPreview(r)}
        <div class="compare">
          <div class="box">
            <h4>${t("original")} (black)</h4>
            <audio controls src="${r.files.original_wav}"></audio>
          </div>
          <div class="box">
            <h4>${t("protected")} (dual-layer)</h4>
            <audio controls src="${r.files.protected_wav}"></audio>
          </div>
        </div>
        ${
          r.files.protected_mp4
            ? `<div class="panel panel-pad" style="margin-bottom:1rem"><video controls src="${r.files.protected_mp4}" style="width:100%;border-radius:10px;max-height:360px"></video></div>`
            : ""
        }
        <div class="row-actions">
          <a class="btn btn-primary" href="${r.files.protected_wav}" download>${t("downloadWav")}</a>
          ${
            r.files.protected_mp4
              ? `<a class="btn" href="${r.files.protected_mp4}" download>${t("downloadMp4")}</a>`
              : ""
          }
          <button class="btn btn-ghost" id="again">${t("again")}</button>
          <button class="btn btn-ghost" data-go="dashboard">${t("home")}</button>
        </div>
        <pre class="panel panel-pad" style="margin-top:1.25rem;font-family:var(--mono);font-size:0.75rem;color:var(--muted);overflow:auto">${escapeHtml(
          JSON.stringify(r.report, null, 2)
        )}</pre>`;
    }

    app.innerHTML = `
      <div class="shell fade-in">
        ${nav()}
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
      $("#toUpload").onclick = () => {
        state.wizard.opts = {
          proteger: $("#opt_proteger").checked,
          metadados: $("#opt_metadados").checked,
          phase: $("#opt_phase").checked,
          compress: $("#opt_compress").checked,
          decoyDb: parseFloat($("#decoyDb").value || "-22"),
          cloakMode: $("#cloakMode").value || "anti_analise",
          blackText: $("#blackText").value || "",
        };
        state.wizard.whiteLang =
          ($("#whiteLang") && $("#whiteLang").value) || state.wizard.whiteLang || "pt";
        state.wizard.whiteText =
          ($("#whiteText") && $("#whiteText").value) ||
          defaultWhiteText(state.wizard.whiteLang);
        state.wizard.whiteNiche = ($("#whiteNiche") && $("#whiteNiche").value) || "mmo";
        state.wizard.whiteCopyId = ($("#whiteCopySel") && $("#whiteCopySel").value) || "mmo_1";
        const wf = $("#whiteFile").files[0];
        state.wizard.whiteFile = wf || null;
        state.wizard.step = 3;
        render();
      };
    }
    if (w.step === 3) {
      const drop = $("#drop");
      const input = $("#fileInput");
      const run = $("#runBtn");
      const nameEl = $("#fileName");
      const label = $("#runLabel");
      const hint = $("#runHint");
      const setFile = (f) => {
        state.wizard.file = f;
        nameEl.textContent = f ? "✓ " + f.name : "";
        run.disabled = !f;
        run.classList.remove("is-loading", "is-success");
        if (label) label.textContent = f ? "Proteger agora" : "Selecione um arquivo";
        if (hint) {
          hint.textContent = f
            ? "Arquivo pronto. Ao clicar, o botão mostra Processando… e depois Concluído."
            : "Envie o vídeo ou áudio para habilitar o botão.";
        }
      };
      if (state.wizard.file) setFile(state.wizard.file);
      drop.onclick = () => {
        if (!run.classList.contains("is-loading")) input.click();
      };
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
      $("#backOpts").onclick = () => {
        if (run.classList.contains("is-loading")) return;
        state.wizard.step = 2;
        render();
      };
      run.onclick = async () => {
        if (!state.wizard.file || !state.wizard.platform) return;
        if (run.classList.contains("is-loading")) return;
        if ((state.user.daily_left ?? state.user.videos_left) <= 0) {
          toast(t("noCredits"));
          return;
        }
        run.disabled = true;
        run.classList.add("is-loading");
        run.classList.remove("is-success");
        run.innerHTML = `<span class="spinner"></span> Processando…`;
        if (hint) hint.textContent = "Aguarde — não feche a página.";
        try {
          const res = await msApi.process(
            state.wizard.file,
            state.wizard.platform,
            {
              ...state.wizard.opts,
              whiteText: state.wizard.whiteText,
              whiteFile: state.wizard.whiteFile,
              blackText: (state.wizard.opts && state.wizard.opts.blackText) || "",
            }
          );
          run.classList.remove("is-loading");
          run.classList.add("is-success");
          run.innerHTML = "✓ Concluído";
          if (hint) hint.textContent = "Pronto! Abrindo resultado…";
          state.wizard.result = res;
          if (res.user) state.user = res.user;
          toast("Processamento concluído");
          setTimeout(() => {
            state.wizard.step = 4;
            render();
          }, 450);
        } catch (e) {
          run.classList.remove("is-loading");
          run.disabled = false;
          run.innerHTML = "Tentar de novo";
          if (hint) hint.textContent = "Falhou. Ajuste o arquivo e tente outra vez.";
          toast(e.message);
        }
      };
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

  function renderSttPreview(r) {
    const p = (r && (r.stt_preview || (r.report && r.report.stt_preview))) || null;
    if (!p) {
      return `<p class="lead">Compare os áudios. Instale <code>openai-whisper</code> no servidor para o preview “IA leu”.</p>`;
    }
    const passed = p.passed;
    const badge = passed
      ? `<span class="chip" style="color:var(--ok);border-color:rgba(61,214,140,0.4)">✓ Score: white venceu no Whisper</span>`
      : `<span class="chip" style="color:var(--warn);border-color:rgba(240,180,41,0.4)">⚠ Score: black ainda forte no Whisper</span>`;
    const avail = p.stt_available
      ? ""
      : `<p style="color:var(--warn);font-size:0.9rem">Whisper não está no servidor — otimizador rodou sem feedback STT real.</p>`;
    return `
      <div class="dual-demo">
        <div class="dual-box human">
          <div class="who">HUMANO OUVE (black)</div>
          <blockquote>Seu criativo original permanece a camada principal para o ouvido.</blockquote>
        </div>
        <div class="dual-box ai">
          <div class="who">IA LEU (Whisper local)</div>
          <blockquote>${escapeHtml(p.ai_heard || "(sem transcrição)")}</blockquote>
          <p style="margin:0.5rem 0 0;font-size:0.8rem;color:var(--muted)">Vencedor no score: <strong>${escapeHtml(p.winner || "?")}</strong> · tentativas: ${p.attempts ?? "—"}</p>
        </div>
      </div>
      <div style="margin:0.75rem 0 1rem">${badge}</div>
      ${avail}
      <p class="lead" style="font-size:0.9rem">${escapeHtml(p.honest_note || p.note || "")}</p>`;
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
