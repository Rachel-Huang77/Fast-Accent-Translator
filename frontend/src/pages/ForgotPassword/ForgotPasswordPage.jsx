// src/pages/ForgotPassword/ForgotPasswordPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./ForgotPasswordPage.module.css";
import { checkUserForReset, resetPassword } from "../../api/auth";
import MessageBox from "../../components/MessageBox";
import { validatePasswordComplexity, validateEmailFormat } from "../../utils/validators";

function EyeIcon({ open = false }) {
  return open ? (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle
        cx="12"
        cy="12"
        r="3"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
    </svg>
  ) : (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M3 3l18 18"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M10.58 10.58a3 3 0 104.24 4.24M9.88 5.09A10.7 10.7 0 0112 5c7 0 11 7 11 7a17.2 17.2 0 01-3.11 3.88M6.11 7.11A17.2 17.2 0 001 12s4 7 11 7a10.7 10.7 0 003.04-.43"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}



export default function ForgotPasswordPage() {
  const navigate = useNavigate();

  // Step 1: verify identity
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");

  // Step 2: password modal
  const [verifiedUserId, setVerifiedUserId] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [newPwd, setNewPwd] = useState("");
  const [showPwd, setShowPwd] = useState(false);

  const [loading, setLoading] = useState(false);

  // Unified message notifications
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  async function onVerify(e) {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    const u = username.trim();
    const em = email.trim();

    if (!u || !em) {
      setErrorMsg("Please enter both username and email.");
      return;
    }

    const emailErr = validateEmailFormat(em);
    if (emailErr) {
      setErrorMsg(emailErr);
      return;
    }

    setLoading(true);
    try {
      const r = await checkUserForReset({ username: u, email: em });
      if (r.ok) {
        setVerifiedUserId(r.userId);
        setNewPwd("");
        setShowPwd(false);
        setModalOpen(true);
        setSuccessMsg("");
      } else {
        const msg =
          typeof r.message === "string"
            ? r.message
            : r.message?.message || "User not found.";
        setErrorMsg(msg);
      }
    } catch (err) {
      const msg =
        typeof err?.message === "string"
          ? err.message
          : JSON.stringify(err) || "Unexpected error.";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  }

  function onCancelModal() {
    setModalOpen(false);
    setNewPwd("");
    setShowPwd(false);
  }

  async function onConfirmModal() {
    setErrorMsg("");
    setSuccessMsg("");

    if (!verifiedUserId) return;

    const pwd = newPwd;

    if (!pwd) {
      setErrorMsg("Please enter a new password.");
      return;
    }

    const pwdErr = validatePasswordComplexity(pwd);
    if (pwdErr) {
      setErrorMsg(pwdErr);
      return;
    }

    setLoading(true);
    try {
      const r = await resetPassword({ userId: verifiedUserId, newPassword: pwd });
      if (r.ok) {
        const msg =
          typeof r.message === "string"
            ? r.message
            : r.message?.message || "Password updated successfully.";
        setSuccessMsg(msg);
        setErrorMsg("");
        setModalOpen(false);
        // After successful password reset, redirect to login page
        setTimeout(() => {
          navigate("/login", { replace: true });
        }, 800);
      } else {
        const msg =
          typeof r.message === "string"
            ? r.message
            : r.message?.message || "Failed to update password.";
        setErrorMsg(msg);
      }
    } catch (err) {
      const msg =
        typeof err?.message === "string"
          ? err.message
          : JSON.stringify(err) || "Unexpected error.";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.pageWrap}>
      <h1 className={styles.title}>Reset your password</h1>

      <div className={styles.card}>
        {/* Top unified message notifications */}
        {errorMsg && (
          <MessageBox
            type="error"
            message={errorMsg}
            onClose={() => setErrorMsg("")}
          />
        )}
        {successMsg && (
          <MessageBox
            type="success"
            message={successMsg}
            onClose={() => setSuccessMsg("")}
          />
        )}

        <form className={styles.form} onSubmit={onVerify}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => navigate("/login")}
            >
              Cancel
            </button>
            <button type="submit" className={styles.submitBtn} disabled={loading}>
              {loading ? "Checking..." : "Confirm"}
            </button>
          </div>
        </form>
      </div>

      {modalOpen && (
        <div className={styles.backdrop} onClick={onCancelModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>Set a new password</div>
            <div className={styles.modalBody}>
              <div className={styles.field}>
                <input
                  className={`${styles.input} ${styles.inputWithEye}`}
                  type={showPwd ? "text" : "password"}
                  placeholder="Enter new password"
                  value={newPwd}
                  onChange={(e) => setNewPwd(e.target.value)}
                />
                <button
                  type="button"
                  className={styles.eyeBtn}
                  onClick={() => setShowPwd((v) => !v)}
                  aria-label={showPwd ? "Hide password" : "Show password"}
                  title={showPwd ? "Hide password" : "Show password"}
                >
                  <EyeIcon open={showPwd} />
                </button>
              </div>
              <p className={styles.hint}>
                Password must be at least 8 characters and contain at least two
                of: uppercase, lowercase, number, special character.
              </p >
            </div>
            <div className={styles.modalActions}>
              <button className={styles.btnGhost} onClick={onCancelModal}>
                Cancel
              </button>
              <button
                className={styles.submitBtn}
                onClick={onConfirmModal}
                disabled={loading}
              >
                {loading ? "Saving..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
