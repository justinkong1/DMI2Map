const logEl = document.getElementById("log");
const busyBadge = document.getElementById("busyBadge");
const tilesetStatus = document.getElementById("tilesetStatus");
const tilesetSelect = document.getElementById("tilesetSelect");
const fileSelect = document.getElementById("fileSelect");
const btnConvert = document.getElementById("btnConvert");

let logCursor = 0;
let pollTimer = null;

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatDetail(data.detail) || data.message || res.statusText);
  }
  return data;
}

function formatDetail(detail) {
  if (detail == null || detail === "") return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const loc = Array.isArray(item.loc) ? item.loc.join(".") : "";
          const msg = item.msg || item.message || JSON.stringify(item);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      })
      .join("\n");
  }
  if (typeof detail === "object") {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return String(detail);
}

function appendLogs(lines) {
  if (!lines.length) return;
  logEl.textContent += (logEl.textContent ? "\n" : "") + lines.join("\n");
  logEl.scrollTop = logEl.scrollHeight;
}

async function refreshLogs() {
  const data = await api(`/api/logs?after=${logCursor}`);
  appendLogs(data.lines);
  logCursor = data.next;
}

async function refreshStatus() {
  const s = await api("/api/status");
  document.getElementById("rootPath").textContent = s.root;

  tilesetSelect.innerHTML = s.tilesets
    .map((t) => `<option value="${t}">${t}</option>`)
    .join("");
  if (!s.tilesets.length) {
    tilesetSelect.innerHTML = `<option value="">(no tilesets yet)</option>`;
  }

  const source = document.querySelector('input[name="source"]:checked').value;
  const list = source === "png" ? s.png : s.dmi;
  const prev = fileSelect.value;
  fileSelect.innerHTML = list.map((t) => `<option value="${t}">${t}</option>`).join("");
  if (!list.length) {
    fileSelect.innerHTML = `<option value="">(empty)</option>`;
  } else if ([...fileSelect.options].some((o) => o.value === prev)) {
    fileSelect.value = prev;
  }

  if (s.tileset_ready) {
    tilesetStatus.textContent = `Tileset: ${s.tileset_name} (${s.tileset_count} states)`;
    tilesetStatus.classList.add("ready");
  } else {
    tilesetStatus.textContent = "No tileset set";
    tilesetStatus.classList.remove("ready");
  }

  busyBadge.classList.toggle("hidden", !s.busy);
  btnConvert.disabled = s.busy || !s.tileset_ready;
  return s;
}

async function pollWhileBusy() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      await refreshLogs();
      const s = await refreshStatus();
      if (!s.busy) {
        clearInterval(pollTimer);
        await refreshLogs();
      }
    } catch (e) {
      console.error(e);
    }
  }, 400);
}

document.getElementById("btnLoadTileset").addEventListener("click", async () => {
  const name = tilesetSelect.value;
  if (!name) return alert("No tileset selected");
  try {
    await api("/api/tileset", {
      method: "POST",
      body: JSON.stringify({ action: "load", name }),
    });
    logCursor = 0;
    logEl.textContent = "";
    await refreshLogs();
    await refreshStatus();
  } catch (e) {
    alert(e.message);
  }
});

document.getElementById("btnNewTileset").addEventListener("click", async () => {
  const name = document.getElementById("newTilesetName").value.trim();
  if (!name) return alert("Enter a tileset name");
  try {
    await api("/api/tileset", {
      method: "POST",
      body: JSON.stringify({ action: "new", name }),
    });
    logCursor = 0;
    logEl.textContent = "";
    await refreshLogs();
    await refreshStatus();
  } catch (e) {
    alert(e.message);
  }
});

document.querySelectorAll('input[name="source"]').forEach((el) => {
  el.addEventListener("change", () => refreshStatus());
});

btnConvert.addEventListener("click", async () => {
  const selection = fileSelect.value;
  if (!selection) return alert("Nothing to convert");
  const source = document.querySelector('input[name="source"]:checked').value;
  const duplicates = document.getElementById("duplicates").checked;
  try {
    logCursor = 0;
    logEl.textContent = "";
    await api("/api/convert", {
      method: "POST",
      body: JSON.stringify({ source, selection, duplicates }),
    });
    await pollWhileBusy();
  } catch (e) {
    alert(e.message);
  }
});

document.querySelectorAll("[data-folder]").forEach((btn) => {
  btn.addEventListener("click", async () => {
    try {
      await api("/api/open-folder", {
        method: "POST",
        body: JSON.stringify({ folder: btn.dataset.folder }),
      });
    } catch (e) {
      alert(e.message);
    }
  });
});

refreshStatus().catch((e) => {
  logEl.textContent = "Failed to reach API: " + e.message;
});
