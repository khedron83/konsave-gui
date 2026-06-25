import React, { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";

export default function ConfigEditorDialog({ onClose }) {
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    invoke("read_config")
      .then(setText)
      .catch((e) => setError(String(e)));
  }, []);

  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await invoke("write_config", { text });
      onClose();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dialog-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="dialog" style={{ maxWidth: 760, height: "70vh" }}>
        <h2>Edit Config File</h2>
        <span className="dialog-path">~/.config/konsave/conf.yaml</span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          spellCheck={false}
          style={{ flex: 1 }}
        />
        {error && <span className="error-text">{error}</span>}
        <div className="dialog-row">
          <button className="btn-ghost" onClick={onClose}>Cancel</button>
          <button className="btn" onClick={save} disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
