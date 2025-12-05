// src/pages/Navbar.jsx
import React, { useEffect, useState } from "react";
import "./Navbar.css";

function Navbar() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    async function fetchUser() {
      try {
        const res = await fetch("/app/api/user/", {
          credentials: "include",
          headers: {
            "x-requested-with": "XMLHttpRequest",
          },
        });

        if (!res.ok) return;

        const data = await res.json();
        setUser(data);
      } catch (err) {
        console.error("User fetch failed", err);
      }
    }

    fetchUser();
  }, []);

  return (
    <nav className="navbar">
  <div className="brand">
    <a href="/">
      <img src="/media/icons/Logo.png" alt="Logo" />
    </a>
  </div>

  {user && (
    <a href="/app/profile/" className="profile-chip">
      <span>{user.username}</span>
      <img src={user.profile_picture} alt="Profile" />
    </a>
  )}
</nav>

  );
}

export default Navbar;
