import React, { Component } from "react";
import ExplorePage from "./ExplorePage";
import LibraryPage from "./LibraryPage";
import { BrowserRouter as Router, Routes, Route, Link, Navigate } from "react-router-dom";

export default class HomePage extends Component {
    render() {
        return (
            <Router>
                <Routes>
                    <Route exact path="/" element={<p>This is the Home page</p>} />
                    <Route path="/explore" element={<ExplorePage />} />
                    <Route path="/library" element={<LibraryPage />} />
                    <Route path="*" element={<Navigate to="/" />} />
                </Routes>
            </Router>
        );
    }
}
