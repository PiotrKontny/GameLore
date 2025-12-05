// src/pages/RegisterPage.jsx
import React, { useState } from "react";
import "./RegisterPage.css";

function RegisterPage() {
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: ""
  });

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

    const handleRegister = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    const trimmedUsername = form.username.trim();

    if (trimmedUsername.length < 4) {
      setError("Username must be at least 4 characters long.");
      return;
    }

    if (!/^[A-Za-z0-9]+$/.test(trimmedUsername)) {
      setError("Username can only contain letters and digits (no spaces or special characters).");
      return;
    }

    if (form.password.length < 5) {
      setError("Password must be at least 5 characters long.");
      return;
    }

    try {
      const res = await fetch("/app/register/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-requested-with": "XMLHttpRequest",
        },
        body: JSON.stringify({
          ...form,
          username: trimmedUsername,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.error || "Registration failed.");
        return;
      }

      setSuccess("Account created successfully!");

      setTimeout(() => {
        window.location.href = "/app/login/";
      }, 1000);

    } catch (err) {
      console.error(err);
      setError("Unexpected error occurred.");
    }
  };

  return (
    <div className="register-container">
      <h2>Create an Account</h2>

      {error && <div className="error-box">{error}</div>}
      {success && <div className="success-box">{success}</div>}

      <form onSubmit={handleRegister}>
        <div className="form-group">
          <label>Username</label>
          <input name="username" type="text" value={form.username} onChange={handleChange} required />
        </div>

        <div className="form-group">
          <label>Email</label>
          <input name="email" type="email" value={form.email} onChange={handleChange} required />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input name="password" type="password" value={form.password} onChange={handleChange} required />
        </div>

        <button type="submit" className="btn-register">Register</button>
      </form>

      <div className="login-redirect">
        Already have an account? <a href="/app/login/">Login</a>
      </div>
    </div>
  );
}

export default RegisterPage;
