// src/pages/AdminUsersPage.js
import React, { useEffect, useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import "./AdminUsersPage.css";
import AdminNavbar from "../components/AdminNavbar";

function AdminUsersPage() {
  const [users, setUsers] = useState([]);
  const [query, setQuery] = useState("");
  const [sortOption, setSortOption] = useState("oldest");

  const fetchUsers = async () => {
    try {
      const params = new URLSearchParams({
        format: "json",
        q: query,
        sort: sortOption,
      });
      const res = await fetch(
        `/app/admin-panel/users/?${params.toString()}`,
        {
          credentials: "include",
          headers: {
            "x-requested-with": "XMLHttpRequest",
            Accept: "application/json",
          },
        }
      );
      const data = await res.json();
      setUsers(data.users || []);
    } catch (err) {
      console.error("Error fetching users:", err);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortOption]);

  const deleteUser = async (id) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this user?"
      )
    )
      return;

    const res = await fetch(
      `/app/admin-panel/delete-user/${id}/`,
      {
        method: "POST",
        credentials: "include",
        headers: {
          "x-requested-with": "XMLHttpRequest",
          Accept: "application/json",
        },
      }
    );
    const data = await res.json();
    alert(data.message || data.error);
    fetchUsers();
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchUsers();
  };

  return (
    <>
      <AdminNavbar />
      <div className="table-container">
        <h2 className="explore-heading">
          <a href="/app/admin-panel/users/">
            Manage Users
          </a>
        </h2>

        <form
          onSubmit={handleSearch}
          className="mb-4 text-center"
        >
          <div
            className="input-group mx-auto"
            style={{ maxWidth: "600px" }}
          >
            <input
              type="text"
              className="form-control search-input"
              placeholder="Search by username..."
              value={query}
              onChange={(e) =>
                setQuery(e.target.value)
              }
            />
            <button
              className="btn btn-outline-primary"
              type="submit"
            >
              Search
            </button>
          </div>

          <div className="d-flex justify-content-center align-items-center gap-2 mt-3">
            <label
              htmlFor="sortSelect"
              className="fw-bold mb-0 sort-label"
            >
              Sort by:
            </label>
            <select
              id="sortSelect"
              className="form-select sort-select"
              value={sortOption}
              onChange={(e) =>
                setSortOption(e.target.value)
              }
            >
              <option value="oldest">
                Registration Date (Oldest)
              </option>
              <option value="newest">
                Registration Date (Newest)
              </option>
            </select>
          </div>
        </form>

        <table className="table table-striped align-middle">
          <thead>
            <tr>
              <th>ID</th>
              <th>Username</th>
              <th>Email</th>
              <th>Registration Date</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {users.length > 0 ? (
              users.map((user) => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.username}</td>
                  <td>{user.email}</td>
                  <td>{user.date_joined}</td>
                  <td>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() =>
                        deleteUser(user.id)
                      }
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td
                  colSpan="5"
                  className="text-center text-muted py-4"
                >
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default AdminUsersPage;
