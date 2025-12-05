import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Navbar from "../components/Navbar";
import NavbarLogin from "../components/NavbarLogin";

import AdminHomePage from "./AdminHome";
import "./HomePage.css";

function HomePage() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

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
        } else {
          setUser(null);
        }
      } catch (err) {
        setUser(null);
      }

      setLoading(false);
    }

    loadUser();
  }, []);

  if (loading) return null;

  if (user && user.username.toLowerCase() === "admin") {
    return <AdminHomePage user={user} />;
  }

  if (!user) {
    return (
      <div className="home-page">
        <NavbarLogin />

        <main>
          <img src="/media/icons/Logo.png" className="main-logo" alt="GameLore" />

          <section className="tiles">
            <Link to="/app/explore/" className="tile">
              <img src="/media/icons/Explore.png" alt="Explore" />
            </Link>

            <Link className="tile disabled" to="/app/login/">
              <img src="/media/icons/Library.png" alt="Library" />
            </Link>

            <Link className="tile disabled" to="/app/login/">
              <img src="/media/icons/Chatbot.png" alt="Chatbot" />
            </Link>

            <Link to="/app/information/" className="tile">
              <img src="/media/icons/Information.png" alt="Information" />
            </Link>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="home-page">
      <Navbar user={user} />

      <main>
        <img src="/media/icons/Logo.png" className="main-logo" alt="GameLore" />

        <section className="tiles">
          <Link to="/app/explore/" className="tile">
            <img src="/media/icons/Explore.png" alt="Explore" />
          </Link>

          <Link to="/app/my_library/" className="tile">
            <img src="/media/icons/Library.png" alt="Library" />
          </Link>

          <Link to="/app/chatbot/" className="tile">
            <img src="/media/icons/Chatbot.png" alt="Chatbot" />
          </Link>

          <Link to="/app/information/" className="tile">
            <img src="/media/icons/Information.png" alt="Information" />
          </Link>
        </section>
      </main>
    </div>
  );
}

export default HomePage;
