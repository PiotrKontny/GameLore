import React, { Component } from "react";
import { createRoot } from "react-dom/client";
import HomePage from "./HomePage";
import ExplorePage from "./ExplorePage";
import LibraryPage from "./LibraryPage";

export default class App extends Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (<div>
                <HomePage />
            </div>
        );
    }
}

const appDiv = document.getElementById("app");
const root = createRoot(appDiv);
root.render(<App />);