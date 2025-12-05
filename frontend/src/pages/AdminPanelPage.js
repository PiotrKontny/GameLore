// src/pages/AdminPanelPage.js
import React from "react";
import "./AdminPanelPage.css";
import AdminNavbar from "../components/AdminNavbar";

function AdminPanelPage() {
  return (
    <>
      <AdminNavbar />

      <main>
        <img
          src="/media/icons/Logo.png"
          className="main-logo"
          alt="GameLore"
        />

        <section className="tiles">
          <a href="/app/admin-panel/users/" className="tile">
            <img src="/media/icons/Users.png" alt="Users" />
          </a>

          <a href="/app/admin-panel/games/" className="tile">
            <img src="/media/icons/Games.png" alt="Games" />
          </a>
        </section>
      </main>
    </>
  );
}

export default AdminPanelPage;
