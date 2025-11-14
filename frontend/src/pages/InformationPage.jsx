// frontend/src/pages/InformationPage.jsx
import React, { useEffect, useState } from "react";

import Navbar from "../components/Navbar";
import NavbarLogin from "../components/NavbarLogin";

import "./InformationPage.css";

function InformationPage() {
  const [user, setUser] = useState(null);
  console.log("INFORMATION PAGE RENDERED!!!");

  // sprawdzamy, czy user jest zalogowany – tylko po to,
  // żeby wybrać odpowiedni navbar
  useEffect(() => {
    async function loadUser() {
      try {
        const res = await fetch("/app/api/user/", {
          credentials: "include",
          headers: { "x-requested-with": "XMLHttpRequest" }
        });
        if (res.ok) {
          setUser(await res.json());
        } else {
          setUser(null);
        }
      } catch (e) {
        setUser(null);
      }
    }
    loadUser();
  }, []);

  return (
    <div className="info-page">
      {/* Navbar zależny od zalogowania */}
      {user ? <Navbar user={user} /> : <NavbarLogin />}

      <div className="info-container">
        {/* INTRODUCTION */}
        <h2>Introduction</h2>
        <p>
          Hello, my name is Peter and I am the creator of this web application,{" "}
          <strong>GameLore</strong>.
        </p>
        <p>
          You are currently in the <em>Information</em> section of the website,
          where I aim to provide a clear explanation of how the application
          works. This is not meant to be an exhaustive technical document but
          rather an accessible overview of the system, its main features, and
          potential future developments.
        </p>

        {/* HOW IT WORKS */}
        <h2>How it works?</h2>
        <p>
          Before discussing the internal mechanisms of the website, it is worth
          clarifying several terms: <strong>web scraping</strong>,{" "}
          <strong>NLP</strong>, and <strong>LLM</strong>.
        </p>

        <ul>
          <li>
            <strong>Web scraping</strong> – a technique used to retrieve
            information from existing websites and store it either in a database
            (as in this project) or directly in memory.
          </li>
          <li>
            <strong>NLP (Natural Language Processing)</strong> – a branch of
            artificial intelligence focused on analyzing and interpreting human
            language. In this application, NLP is used to generate summaries for
            games with sufficiently detailed plots.
          </li>
          <li>
            <strong>LLM (Large Language Models)</strong> – advanced neural
            models that apply NLP to understand and interpret text. In this
            project, an LLM powers the chatbot, allowing users to ask questions
            about any game they are exploring.
          </li>
        </ul>

        <p>
          GameLore uses two main scraping tools:{" "}
          <strong>Playwright</strong>, which retrieves webpage data using a
          headless browser, and <strong>BeautifulSoup</strong>, which extracts
          only the necessary parts of that data. Information is sourced from:
        </p>

        <ul>
          <li>
            <strong>MobyGames</strong> – for metadata such as cover art, genre,
            release date, developers, and score.
          </li>
          <li>
            <strong>Wikipedia</strong> – for gathering game plots.
          </li>
        </ul>

        <p>
          Suppose a user searches for a game not yet in the database —{" "}
          <em>Elden Ring</em>, for example. The user inputs the title via the
          search feature available on the <em>Explore</em> and{" "}
          <em>My Library</em> pages. The backend launches a headless browser via
          Playwright, opens the relevant MobyGames search page, retrieves the
          first ten results, filters out invalid entries, and displays the
          remaining games to the user.
        </p>

        <p>
          When a game is selected, the scraping process begins. The system
          checks if the game already exists in the database. If not, Playwright
          opens the game’s MobyGames page and determines whether the entry
          represents a standalone title, a compilation, or an add-on.
        </p>

        <ul>
          <li>
            <strong>Compilations</strong> – all titles included in the
            compilation are shown, and the user selects one.
          </li>
          <li>
            <strong>Add-ons</strong> – the link to the base game is stored,
            after which the system proceeds as with standalone titles.
          </li>
        </ul>

        <p>
          Six attributes are then scraped: <strong>Title</strong>,{" "}
          <strong>Released</strong>, <strong>Genre</strong>,{" "}
          <strong>Developers</strong>, <strong>Moby Score</strong>, and the{" "}
          <strong>cover image</strong>.
        </p>

        <p>
          Next, the scraper attempts to reach the corresponding Wikipedia page
          using the formatted title. It searches for plot-related section
          headings such as <em>Plot</em>, <em>Synopsis</em>, <em>Premise</em>,{" "}
          <em>Story</em>, or <em>Lore</em>. If found, the plot section is
          extracted and structured.
        </p>

        <p>If none of these headings exist:</p>
        <ul>
          <li>
            For <strong>add-ons</strong>, the system uses the previously saved
            base-game link and tries again.
          </li>
          <li>
            For <strong>standalone titles</strong>, the description from
            MobyGames is used instead, along with a remark that the chatbot can
            provide additional plot information if needed.
          </li>
        </ul>

        <p>
          Once scraping is complete, the user is redirected to the game’s detail
          page. Two additional features become available:
        </p>

        <ul>
          <li>
            <strong>Summary</strong> – generated using Hugging Face
            Transformers, with each plot subsection summarized separately.
          </li>
          <li>
            <strong>Chatbot</strong> – powered by <strong>OpenRouter.ai</strong>
            , which offers access to multiple LLMs through a unified API. The
            current model in use is <strong>Mistral 7B Instruct</strong>.
          </li>
        </ul>

        {/* FEATURES */}
        <h2>What are the website’s features?</h2>
        <p>
          Beyond scraping and chatbot support, GameLore includes a number of
          additional features. Some are only available to logged-in users, while
          others — such as <em>Explore</em> — are publicly accessible.
        </p>

        <ul>
          <li>
            <strong>Login and Register Pages</strong> – enabling account
            creation and authentication.
          </li>
          <li>
            <strong>Profile Page</strong> – allows users to update their
            username, password, and profile picture.
          </li>
          <li>
            <strong>Explore Page</strong> – displays all games in the database
            and includes search and sorting tools.
          </li>
          <li>
            <strong>Search and Results Pages</strong> – for locating games not
            yet in the database.
          </li>
          <li>
            <strong>Compilation Page</strong> – shown when a selected entry is
            part of a compilation.
          </li>
          <li>
            <strong>Game Detail Page</strong> – contains all game information,
            including plot, summary, chatbot access, and the option to rate the
            game.
          </li>
          <li>
            <strong>My Library Page</strong> – stores a user’s browsing history.
          </li>
          <li>
            <strong>Chatbot Page</strong> – a dedicated interface for
            interacting with the chatbot.
          </li>
        </ul>

        {/* FUTURE */}
        <h2>What’s the website’s future?</h2>
        <p>
          GameLore originally started with a much smaller scope — basic
          authentication, exploration, viewing scraped details, and basic
          chatbot and summary functionality. Over time, with helpful feedback
          from those around me, the project expanded significantly, gaining more
          advanced features such as sorting, improved scraping logic, and user
          profiles.
        </p>

        <p>
          However, the application is not perfect. Certain features could be
          improved, optimized, or expanded, but implementing these enhancements
          is not something I currently plan to pursue.
        </p>

        <p>
          Despite this, creating GameLore has been an enjoyable and meaningful
          experience, and one that I will look back on fondly in the future.
        </p>
      </div>
    </div>
  );
}

export default InformationPage;
