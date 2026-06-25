import React, { useState, useEffect, useCallback } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open, save } from "@tauri-apps/plugin-dialog";
import ConfigEditorDialog from "./ConfigEditorDialog.jsx";
import SettingsDialog from "./SettingsDialog.jsx";

export default function App() {
  const [profiles, setProfiles] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [settings, setSettings] = useState(null);
  const [showConfig, setShowConfig] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const loadProfiles = useCallback(async () => {
    try {
      const list = await invoke("list_profiles");
      setProfiles(list);
      if (list.length > 0) {
        setSelected((prev) => list.find((p) => p.name === prev?.name) ?? list[0]);
      } else {
        setSelected(null);
      }
    } catch (e) {
      setStatus("Error: " + e);
    }
  }, []);

  useEffect(() => {
    invoke("get_settings").then(setSettings).catch(() => {});
    loadProfiles();
  }, [loadProfiles]);

  const run = async (fn, msg) => {
    setBusy(true);
    setStatus(msg ?? "Working…");
    try {
      const result = await fn();
      return result;
    } catch (e) {
      setStatus("Error: " + e);
      throw e;
    } finally {
      setBusy(false);
    }
  };

  // ── Actions ──────────────────────────────────────────────────────────────

  const onSave = async () => {
    const name = prompt("Profile name:");
    if (!name?.trim()) return;
    const trimmed = name.trim();
    const exists = profiles.some((p) => p.name === trimmed);
    if (exists && !confirm(`Profile "${trimmed}" already exists. Overwrite?`)) return;
    await run(() => invoke("save_profile", { name: trimmed, force: exists }), "Saving…");
    await loadProfiles();
    setStatus(`Profile "${trimmed}" saved.`);
  };

  const onApply = async () => {
    if (!selected) return;
    if (!confirm(`Apply "${selected.name}"?\n\nConfig files will be overwritten. You may need to log out to see all changes.`)) return;
    await run(() => invoke("apply_profile", { name: selected.name }), "Applying…");
    setStatus(`"${selected.name}" applied. Log out and back in to see all changes.`);
  };

  const onDelete = async () => {
    if (!selected) return;
    if (!confirm(`Delete "${selected.name}"?\n\nThis cannot be undone.`)) return;
    await run(() => invoke("delete_profile", { name: selected.name }), "Deleting…");
    await loadProfiles();
    setStatus(`Profile "${selected.name}" deleted.`);
  };

  const onWipe = async () => {
    if (!confirm("Wipe ALL profiles?\n\nThis cannot be undone.")) return;
    await run(() => invoke("wipe_profiles"), "Wiping…");
    await loadProfiles();
    setStatus("All profiles wiped.");
  };

  const onExport = async () => {
    if (!selected) return;
    const dir = await open({ directory: true, title: "Export to directory" });
    if (!dir) return;
    const out = await run(
      () => invoke("export_profile", { name: selected.name, destDir: dir }),
      "Exporting…"
    );
    setStatus(`Exported to ${out}`);
  };

  const onImport = async () => {
    const path = await open({
      filters: [{ name: "Konsave archive", extensions: ["knsv"] }],
      title: "Import .knsv file",
    });
    if (!path) return;
    const name = await run(() => invoke("import_profile", { path }), "Importing…");
    await loadProfiles();
    setStatus(`Imported "${name}".`);
  };

  const onSyncPush = async () => {
    if (!settings?.nextcloud_path) {
      setStatus("Set a Nextcloud folder in Settings first.");
      return;
    }
    const count = await run(
      () => invoke("sync_push", { nextcloudPath: settings.nextcloud_path }),
      "Pushing to Nextcloud…"
    );
    setStatus(`Pushed ${count} profile${count !== 1 ? "s" : ""} to Nextcloud.`);
  };

  const onSyncPull = async () => {
    if (!settings?.nextcloud_path) {
      setStatus("Set a Nextcloud folder in Settings first.");
      return;
    }
    const count = await run(
      () => invoke("sync_pull", { nextcloudPath: settings.nextcloud_path }),
      "Pulling from Nextcloud…"
    );
    await loadProfiles();
    setStatus(
      count > 0
        ? `Pulled ${count} new profile${count !== 1 ? "s" : ""} from Nextcloud.`
        : "No new profiles in Nextcloud."
    );
  };

  // ── Detail panel ──────────────────────────────────────────────────────────

  const detail = selected ? (
    <>
      <div className="detail-name">{selected.name}</div>
      <div className="detail-date">Saved {selected.modified}</div>
      <hr className="divider" />
      <div className="sections-scroll">
        {selected.sections_save.length > 0 && (
          <>
            <div className="group-heading">Saved sections</div>
            {selected.sections_save.map((s) => (
              <SectionCard key={s.name} section={s} />
            ))}
          </>
        )}
        {selected.sections_export.length > 0 && (
          <>
            <div className="group-heading">Export-only sections</div>
            {selected.sections_export.map((s) => (
              <SectionCard key={s.name} section={s} />
            ))}
          </>
        )}
        {selected.sections_save.length === 0 && selected.sections_export.length === 0 && (
          <div style={{ color: "#475569" }}>No sections in this profile's config.</div>
        )}
      </div>
      <div className="detail-actions">
        <button className="btn-ghost" onClick={onExport} disabled={busy}>Export .knsv</button>
        <button className="btn-ghost" onClick={onImport} disabled={busy}>Import .knsv</button>
      </div>
    </>
  ) : (
    <>
      <div className="detail-name" style={{ color: "#475569" }}>
        {profiles.length === 0 ? "No profiles yet" : "Select a profile"}
      </div>
      <div className="detail-date">
        {profiles.length === 0
          ? 'Use "Save Current" to snapshot your desktop config.'
          : ""}
      </div>
      <div style={{ flex: 1 }} />
      <div className="detail-actions">
        <button className="btn-ghost" onClick={onImport} disabled={busy}>Import .knsv</button>
      </div>
    </>
  );

  return (
    <div className="app">
      {/* Toolbar */}
      <div className="toolbar">
        <span className="toolbar-title">Konsave</span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          <button
            className="btn-ghost"
            onClick={onSyncPush}
            disabled={busy || !settings?.nextcloud_path}
            title={settings?.nextcloud_path ? `Push to ${settings.nextcloud_path}/konsave/` : "Set Nextcloud path in Settings"}
          >
            ↑ Nextcloud
          </button>
          <button
            className="btn-ghost"
            onClick={onSyncPull}
            disabled={busy || !settings?.nextcloud_path}
            title={settings?.nextcloud_path ? `Pull from ${settings.nextcloud_path}/konsave/` : "Set Nextcloud path in Settings"}
          >
            ↓ Nextcloud
          </button>
          <button className="btn-ghost" onClick={() => setShowConfig(true)} title="Edit config file">
            Edit Config
          </button>
          <button className="btn-ghost" onClick={() => setShowSettings(true)} title="Settings">⚙</button>
        </div>
      </div>

      {/* Body */}
      <div className="app-body">
        <aside className="sidebar">
          <div className="sidebar-heading">Profiles</div>
          <ul className="profile-list">
            {profiles.map((p) => (
              <li
                key={p.name}
                className={`profile-item${selected?.name === p.name ? " selected" : ""}`}
                onClick={() => setSelected(p)}
              >
                {p.name}
              </li>
            ))}
          </ul>
          <div className="sidebar-actions">
            <button className="btn-success" onClick={onSave} disabled={busy}>
              Save Current
            </button>
            <button className="btn" onClick={onApply} disabled={busy || !selected}>
              Apply
            </button>
            <button className="btn-danger" onClick={onDelete} disabled={busy || !selected}>
              Delete
            </button>
            <button
              className="btn-ghost"
              style={{ marginTop: 4 }}
              onClick={onWipe}
              disabled={busy || profiles.length === 0}
            >
              Wipe All…
            </button>
          </div>
        </aside>

        <main className="detail">{detail}</main>
      </div>

      <div className="statusbar">{status}</div>

      {showConfig && <ConfigEditorDialog onClose={() => setShowConfig(false)} />}
      {showSettings && settings && (
        <SettingsDialog
          settings={settings}
          onClose={() => setShowSettings(false)}
          onSaved={(s) => { setSettings(s); setShowSettings(false); }}
        />
      )}
    </div>
  );
}

function SectionCard({ section }) {
  const shown = section.entries.slice(0, 10);
  const extra = section.entries.length - 10;
  return (
    <div className="section-card">
      <div className="section-name">{section.name}</div>
      {section.location && (
        <div className="section-location">{section.location}</div>
      )}
      {section.entries.length > 0 && (
        <div className="section-entries">
          {shown.join(", ")}
          {extra > 0 && ` +${extra} more`}
        </div>
      )}
    </div>
  );
}
