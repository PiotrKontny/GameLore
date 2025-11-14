import React from "react";
import Navbar from "../components/Navbar";
import "./AdminHome.css";

function AdminHomePage({ user }) {
  return (
    <div className="admin-home">
      <Navbar user={user} />

      <main>
        <img src="/media/icons/Logo.png" className="main-logo" alt="GameLore" />

        <section className="tiles tiles--upper">
          <a href="/app/explore/" className="tile">
            <img src="/media/icons/Explore.png" alt="Explore" />
          </a>

          <a href="/app/my_library/" className="tile">
            <img src="/media/icons/Library.png" alt="Library" />
          </a>

          <a href="/app/chatbot/" className="tile">
            <img src="/media/icons/Chatbot.png" alt="Chatbot" />
          </a>

          <a href="/app/information/" className="tile">
            <img src="/media/icons/Information.png" alt="Information" />
          </a>
        </section>

        <section className="tiles tiles--admin">
          <a href="/app/admin-panel/" className="tile">
            <img src="/media/icons/Admin.png" alt="Admin Panel" />
          </a>
        </section>
      </main>
    </div>
  );
}

export default AdminHomePage;
