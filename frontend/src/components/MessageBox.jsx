// src/components/MessageBox.jsx
import React from "react";
import styles from "./MessageBox.module.css";


export default function MessageBox({ type = "error", message, children, onClose }) {
  const content = message || children;
  if (!content) return null;

  const className =
    type === "success" ? styles.boxSuccess :
    type === "info"    ? styles.boxInfo :
    styles.boxError;

  return (
    <div className={className}>
      <span>{content}</span>
      {onClose && (
        <button
          type="button"
          className={styles.closeBtn}
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>
      )}
    </div>
  );
}
