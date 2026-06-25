import React, { useState } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function SettingsDialog({ settings, onClose, onSaved }) {
  const [url, setUrl] = useState(settings.nextcloud_url || "");
  const [username, setUsername] = useState(settings.nextcloud_username || "");
  const [password, setPassword] = useState(settings.nextcloud_password || "");
  const [verifySsl, setVerifySsl] = useState(settings.verify_ssl ?? true);
  const [saving, setSaving] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const s = {
        nextcloud_url: url || null,
        nextcloud_username: username || null,
        nextcloud_password: password || null,
        verify_ssl: verifySsl,
      };
      await invoke("save_settings", { s });
      onSaved(s);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog">
        <h2>Settings</h2>

        <div>
          <label>Nextcloud server URL</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://cloud.example.com"
          />
        </div>
        <div>
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="your-username"
          />
        </div>
        <div>
          <label>Password / App password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <span className="dialog-path" style={{ marginTop: 4, display: "block" }}>
            Use an app password from Nextcloud → Settings → Security for best practice.
            Profiles sync to/from a <code>konsave/</code> folder in your Nextcloud.
          </span>
        </div>
        <div>
          <label style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={verifySsl}
              onChange={(e) => setVerifySsl(e.target.checked)}
            />
            Verify SSL certificate
          </label>
          {!verifySsl && (
            <span className="dialog-path" style={{ marginTop: 4, display: "block", color: "#fbbf24" }}>
              Disabled — accepts self-signed certificates.
            </span>
          )}
        </div>

        <div className="dialog-row">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={save} disabled={saving}>Save</button>
        </div>
      </div>
    </div>
  );
}
