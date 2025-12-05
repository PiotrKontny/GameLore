// src/pages/AdminNavbar.jsx
import React, { useEffect, useState } from "react";
import "./AdminNavbar.css";

function AdminNavbar() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const res = await fetch("/app/api/user/", {
          credentials: "include",
          headers: { "x-requested-with": "XMLHttpRequest" },
        });

        if (res.ok) {
          const data = await res.json();
          setUser(data);
        }
      } catch (err) {
        console.error("User fetch failed", err);
      }
    }

    loadUser();
  }, []);

  return (
    <nav className="admin-navbar">
      <div className="brand">
        <a href="/">
          <img src="/media/icons/Logo.png" alt="Logo" />
        </a>
      </div>

      <a href="/app/admin-panel/" className="navbar-center">
        Admin Panel
      </a>

      {user && (
        <a href="/app/profile/" className="profile-chip">
          <span>{user.username}</span>
          <img src={user.profile_picture} alt="Profile" />
        </a>
      )}
    </nav>
  );
}

export default AdminNavbar;
