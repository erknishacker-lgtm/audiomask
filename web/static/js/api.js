/* API client */
window.msApi = {
  async req(path, opts = {}) {
    const res = await fetch(path, {
      credentials: "include",
      ...opts,
      headers: {
        ...(opts.body && !(opts.body instanceof FormData)
          ? { "Content-Type": "application/json" }
          : {}),
        ...(opts.headers || {}),
      },
    });
    let data = null;
    const ct = res.headers.get("content-type") || "";
    if (ct.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }
    if (!res.ok) {
      const msg =
        (data && data.detail) ||
        (typeof data === "string" ? data : null) ||
        res.statusText;
      throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    }
    return data;
  },
  login(email, password) {
    return this.req("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },
  register(name, email, password) {
    return this.req("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
  },
  logout() {
    return this.req("/api/auth/logout", { method: "POST" });
  },
  me() {
    return this.req("/api/auth/me");
  },
  platforms() {
    return this.req("/api/platforms");
  },
  requestPro() {
    return this.req("/api/account/request-pro", { method: "POST" });
  },
  usage() {
    return this.req("/api/account/usage");
  },
  adminStats() {
    return this.req("/api/admin/stats");
  },
  adminUsers() {
    return this.req("/api/admin/users");
  },
  adminUpdate(id, body) {
    return this.req(`/api/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  },
  process(file, platform, opts = {}) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("platform", platform);
    fd.append("opt_proteger", opts.proteger ? "1" : "0");
    fd.append("opt_metadados", opts.metadados ? "1" : "0");
    fd.append("opt_phase", opts.phase ? "1" : "0");
    fd.append("opt_compress", opts.compress ? "1" : "0");
    fd.append("decoy_db", String(opts.decoyDb ?? -40));
    fd.append("cloak_mode", opts.cloakMode || "auto");
    fd.append("white_text", opts.whiteText || "");
    fd.append("black_text", opts.blackText || "");
    if (opts.whiteFile) fd.append("white_file", opts.whiteFile);
    return this.req("/api/process", { method: "POST", body: fd });
  },
};
