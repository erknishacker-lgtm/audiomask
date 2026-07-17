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
      result: null,
      opts: {
        proteger: true,
        metadados: true,
        phase: true,
        compress: true,
        decoyDb: -24,
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
            result: null,
            opts: {
              proteger: true,
              metadados: true,
              phase: true,
              compress: true,
              decoyDb: -24,
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

  function viewAuth() {
    const tab = state.authTab;
    app.innerHTML = `
      <div class="auth-wrap fade-in">
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
          <button class="action featured" data-go="protect">
            <span class="arrow">→</span>
            <div class="num">01</div>
            <h3>Proteger criativo</h3>
            <p>Plataforma → funções dual-layer → upload → download. Como o líder do mercado, só que com fluxo GhostWave.</p>
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
        <p class="lead">Escolha o que aplicar. O áudio principal (black) permanece <strong>100% audível</strong>. A copy white entra baixa para as IAs de legenda.</p>
        <div class="panel panel-pad" style="margin-bottom:1rem">
          <label class="field" style="display:flex;gap:0.75rem;align-items:flex-start;cursor:pointer">
            <input type="checkbox" id="opt_proteger" ${o.proteger ? "checked" : ""} style="margin-top:0.35rem;width:auto" />
            <span><strong>1 · Proteger áudio contra IA (cloaker black → white)</strong><br/>
            <span style="color:var(--muted);font-size:0.88rem">Mantém a voz do anúncio clara. Injeta copy “white” em volume baixo (mascarada) para a transcrição das plataformas.</span></span>
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
          <h2 class="h2">Copy white (o que a IA deve “ouvir”)</h2>
          <p class="lead" style="margin-bottom:0.75rem">Cole o texto da copy branca ou envie um áudio white gravado. Se vazio, geramos fala sintética limpa.</p>
          <div class="field"><label>Texto white</label>
            <textarea id="whiteText" placeholder="Ex.: Oferta especial. Confira as condições oficiais no site...">${escapeHtml(w.whiteText || "")}</textarea>
          </div>
          <div class="field"><label>Áudio white (opcional)</label>
            <input type="file" id="whiteFile" accept="audio/*,.wav,.mp3,.m4a" />
          </div>
          <div class="field"><label>Volume da white (dB, mais negativo = mais baixa) · padrão −24</label>
            <input type="number" id="decoyDb" value="${o.decoyDb}" min="-40" max="-12" step="1" />
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
          <button class="btn btn-primary" id="runBtn" disabled>${t("run")}</button>
        </div>`;
    } else {
      const r = w.result;
      body = `
        <h1 class="h1">${t("result")}</h1>
        <p class="lead">Principal deve soar normal. A white está embutida baixa. Baixe e teste a legenda na plataforma.</p>
        <div class="compare">
          <div class="box">
            <h4>${t("original")}</h4>
            <audio controls src="${r.files.original_wav}"></audio>
          </div>
          <div class="box">
            <h4>${t("protected")}</h4>
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
          decoyDb: parseFloat($("#decoyDb").value || "-24"),
        };
        state.wizard.whiteText = $("#whiteText").value || "";
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
      const setFile = (f) => {
        state.wizard.file = f;
        nameEl.textContent = f ? f.name : "";
        run.disabled = !f;
      };
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
      $("#backOpts").onclick = () => {
        state.wizard.step = 2;
        render();
      };
      run.onclick = async () => {
        if (!state.wizard.file || !state.wizard.platform) return;
        if (state.user.videos_left <= 0) {
          toast(t("noCredits"));
          return;
        }
        run.disabled = true;
        run.innerHTML = `<span class="spinner"></span> ${t("processing")}`;
        try {
          const res = await msApi.process(
            state.wizard.file,
            state.wizard.platform,
            {
              ...state.wizard.opts,
              whiteText: state.wizard.whiteText,
              whiteFile: state.wizard.whiteFile,
            }
          );
          state.wizard.result = res;
          if (res.user) state.user = res.user;
          state.wizard.step = 4;
          toast("Processamento concluído");
          render();
        } catch (e) {
          toast(e.message);
          run.disabled = false;
          run.textContent = t("run");
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
            result: null,
            opts: {
              proteger: true,
              metadados: true,
              phase: true,
              compress: true,
              decoyDb: -24,
            },
          };
          render();
        };
      }
    }
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
