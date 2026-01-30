// src/pages/LoginPage/LoginPage.jsx
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import styles from "./LoginPage.module.css";
import { login } from "../../api/auth";
import MessageBox from "../../components/MessageBox";

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

export default function LoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(""); // New: error message

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    const u = username.trim();
    const p = password;

    if (!u || !p) {
      setError("Please fill in both username and password.");
      return;
    }

    setLoading(true);
    try {
      const resp = await login({ username: u, password: p });
      // Defensive check: ensure resp exists and has ok property
      if (resp && resp.ok === true) {
        // store session
        localStorage.setItem("authToken", resp.token || "mock-token");
        localStorage.setItem("authUserId", resp.user?.id || u);
        localStorage.setItem("authUsername", resp.user?.username || u);
        localStorage.setItem("authUserRole", resp.user?.role || "user");

        // Navigate based on role: admin → /admin, regular user → /dashboard
        if (resp.user?.role === "admin") {
          navigate("/admin");
        } else {
          navigate("/dashboard");
        }
      } else {
        // Unified message processing, avoid [Object Object]
        const msg =
          resp && typeof resp.message === "string"
            ? resp.message
            : resp?.message?.message ||
              resp?.message?.detail ||
              "Login failed. Please check your username and password.";
        setError(msg);
      }
    } catch (err) {
      const msg =
        typeof err?.message === "string"
          ? err.message
          : "Unexpected error. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.pageWrap}>
      <h1 className={styles.title}>
        Welcome to <span className={styles.colorful}>SystemX!</span>
      </h1>

      <div className={styles.card}>
        {/* Unified error message area */}
        <MessageBox
          type="error"
          message={error}
          onClose={() => setError("")}
        />

        <form className={styles.form} onSubmit={handleSubmit}>
          <label htmlFor="username">Username</label>
          <input
            id="username"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />

          <label htmlFor="password">Password</label>
          <div className={styles.field}>
            <input
              id="password"
              className={`${styles.input} ${styles.inputWithEye}`}
              type={showPwd ? "text" : "password"}
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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

          <button type="submit" className={styles.primaryBtn} disabled={loading}>
            {loading ? "Signing In..." : "Sign In"}
          </button>

          <div className={styles.footer}>
            <span className={styles.link} onClick={() => navigate("/register")}>
              Register
            </span>
            <span
              className={styles.link}
              onClick={() => navigate("/forgot-password")}
            >
              Forget password?
            </span>
          </div>
        </form>
      </div>
    </div>
  );
}
