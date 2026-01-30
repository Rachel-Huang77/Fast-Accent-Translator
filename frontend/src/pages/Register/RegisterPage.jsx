// src/pages/RegisterPage/RegisterPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./RegisterPage.module.css";
import { register } from "../../api/auth";
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



export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);

  // New: Unified error/success messages
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const onChange = (k) => (e) =>
    setForm((p) => ({ ...p, [k]: e.target.value }));

  const onConfirm = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setSuccessMsg("");

    const username = form.username.trim();
    const email = form.email.trim();
    const password = form.password;

    if (!username || !email || !password) {
      setErrorMsg("Please fill in all fields.");
      return;
    }

    // Email format validation
    const emailErr = validateEmailFormat(email);
    if (emailErr) {
      setErrorMsg(emailErr);
      return;
    }

    // Password complexity validation
    const pwdErr = validatePasswordComplexity(password);
    if (pwdErr) {
      setErrorMsg(pwdErr);
      return;
    }

    setLoading(true);
    try {
      const resp = await register({ username, email, password });
      if (resp.ok) {
        const msg =
          typeof resp.message === "string"
            ? resp.message
            : resp.message?.message ||
              JSON.stringify(resp.message) ||
              "Registration successful.";
        setSuccessMsg(msg);
        setErrorMsg("");

        // After success, redirect to login page
        setTimeout(() => {
          navigate("/login", { replace: true });
        }, 800);
      } else {
        const msg =
          typeof resp.message === "string"
            ? resp.message
            : resp.message?.message ||
              JSON.stringify(resp.message) ||
              "Registration failed.";
        setErrorMsg(msg);
        setSuccessMsg("");
      }
    } catch (err) {
      const msg =
        typeof err?.message === "string"
          ? err.message
          : JSON.stringify(err) || "Unexpected error.";
      setErrorMsg(msg);
      setSuccessMsg("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.pageWrap}>
      <h1 className={styles.title}>
        Create your <span className={styles.colorful}>SystemX</span> account
      </h1>

      <div className={styles.card}>
        {/* Unified message box: error or success */}
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

        <form className={styles.form} onSubmit={onConfirm}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            placeholder="Enter your username"
            value={form.username}
            onChange={onChange("username")}
          />

          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            placeholder="Enter your email"
            value={form.email}
            onChange={onChange("email")}
          />

          <label htmlFor="password">Password</label>
          <div className={styles.inputGroup}>
            <input
              id="password"
              type={showPwd ? "text" : "password"}
              placeholder="Enter your password"
              value={form.password}
              onChange={onChange("password")}
              className={styles.inputWithEye}
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

          {/* Optional: Add a static rule hint below password */}
          <p className={styles.hint}>
            Password must be at least 8 characters and contain at least two of:
            uppercase, lowercase, number, special character.
          </p >

          <div className={styles.actions}>
            <button
              type="button"
              className={styles.btnGhost}
              onClick={() => navigate("/login")}
            >
              Cancel
            </button>
            <button
              type="submit"
              className={styles.submitBtn}
              disabled={loading}
            >
              {loading ? "Submitting..." : "Confirm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}