// src/pages/LoginPage.jsx
import React, { useState } from "react";
import "./LoginPage.css";

function LoginPage() {
  const [error, setError] = useState("");

  async function handleSubmit(e) {
    e.preventDefault();

    const form = new FormData(e.target);
    const body = new URLSearchParams(form);

    const res = await fetch("/app/login/", {
      method: "POST",
      body,
      credentials: "include",
    });

    if (res.redirected) {
      window.location.href = res.url;
      return;
    }

    setError("Invalid username or password.");
  }

  return (
    <div className="login-container">
      <h2 className="login-title">Login to GameLore</h2>

      {error && <div className="error-text">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label>Username or Email</label>
          <input type="text" className="form-control" name="username" required />
        </div>

        <div className="mb-3">
          <label>Password</label>
          <input type="password" className="form-control" name="password" required />
        </div>

        <button type="submit" className="btn-login">Login</button>
      </form>

      <div className="register-link">
        Don’t have an account? <a href="/app/register/">Register</a>
      </div>
    </div>
  );
}

export default LoginPage;
