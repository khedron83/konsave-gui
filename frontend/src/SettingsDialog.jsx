import React, { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";

export default function SettingsDialog({ settings, onClose, onSaved }) {
  const [path, setPath] = useState(settings.nextcloud_path || "");
  const [saving, setSaving] = useState(false);

  const pick = async () => {
    const dir = await open({ directory: true, title: "Select Nextcloud folder" });
    if (dir) setPath(dir);
  };

  const save = async () => {
    setSaving(true);
    try {
      await invoke("save_settings", { s: { nextcloud_path: path || null } });
      onSaved({ nextcloud_path: path || null });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog">
        <h2>Settings</h2>
        <div>
          <label>Nextcloud sync folder</label>
          <div className="dialog-field">
            <input
              type="text"
              value={path}
              onChange={(e) => setPath(e.target.value)}
              placeholder="/home/you/Nextcloud"
            />
            <button className="btn-ghost" onClick={pick}>Browse</button>
          </div>
          <span className="dialog-path" style={{ marginTop: 4, display: "block" }}>
            Profiles will be synced to/from a <code>konsave/</code> subfolder here.
          </span>
        </div>
        <div className="dialog-row">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={save} disabled={saving}>Save</button>
        </div>
      </div>
    </div>
  );
}
