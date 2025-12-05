import React, { useEffect, useState } from "react";
import "./ProfilePage.css";

function ProfilePage() {
  const [user, setUser] = useState(null);

  const [msgUsername, setMsgUsername] = useState(null);
  const [msgPassword, setMsgPassword] = useState(null);
  const [msgPfp, setMsgPfp] = useState(null);

  useEffect(() => {
    async function loadUser() {
      const res = await fetch("/app/api/profile/", {
        credentials: "include",
        headers: {
          "x-requested-with": "XMLHttpRequest",
          Accept: "application/json",
        },
      });
      if (res.ok) setUser(await res.json());
    }
    loadUser();
  }, []);

  if (!user) return null;

  const changeUsername = async (e) => {
    e.preventDefault();
    setMsgUsername(null);

    const newUsername = e.target.new_username.value.trim();
    if (newUsername.length < 4) {
      setMsgUsername({
        text: "Username must be at least 4 characters long.",
        error: true,
      });
      return;
    }
    if (!/^[A-Za-z0-9]+$/.test(newUsername)) {
      setMsgUsername({
        text: "Username can only contain letters and digits (no spaces or special characters).",
        error: true,
      });
      return;
    }

    const form = new FormData(e.target);
    form.set("new_username", newUsername);

    const res = await fetch("/app/api/profile/", {
      method: "POST",
      credentials: "include",
      body: form,
      headers: {
        "x-requested-with": "XMLHttpRequest",
      },
    });

    const data = await res.json();
    if (!res.ok) {
      setMsgUsername({ text: data.error, error: true });
      return;
    }

    setMsgUsername({ text: data.message, error: false });
    setUser({ ...user, username: newUsername });
  };

  const changePfp = async (e) => {
    e.preventDefault();
    setMsgPfp(null);

    const form = new FormData(e.target);
    const res = await fetch("/app/api/profile/", {
      method: "POST",
      credentials: "include",
      body: form,
      headers: {
        "x-requested-with": "XMLHttpRequest",
      },
    });

    const data = await res.json();
    if (!res.ok) {
      setMsgPfp({ text: data.error, error: true });
      return;
    }
    setMsgPfp({ text: data.message, error: false });

    const reload = await fetch("/app/api/profile/", {
      credentials: "include",
      headers: {
        "x-requested-with": "XMLHttpRequest",
        Accept: "application/json",
      },
    });
    setUser(await reload.json());
  };

  const changePassword = async (e) => {
    e.preventDefault();
    setMsgPassword(null);

    const newPassword = e.target.new_password.value;
    if (newPassword.length < 5) {
      setMsgPassword({
        text: "New password must be at least 5 characters long.",
        error: true,
      });
      return;
    }

    const form = new FormData(e.target);
    const res = await fetch("/app/api/profile/", {
      method: "POST",
      credentials: "include",
      body: form,
      headers: {
        "x-requested-with": "XMLHttpRequest",
      },
    });

    const data = await res.json();
    if (!res.ok) {
      setMsgPassword({ text: data.error, error: true });
      return;
    }

    setMsgPassword({ text: data.message, error: false });
  };

  const logout = async () => {
    const form = new FormData();
    form.append("action", "logout");

    const res = await fetch("/app/api/profile/", {
      method: "POST",
      credentials: "include",
      body: form,
      headers: {
        "x-requested-with": "XMLHttpRequest",
        Accept: "application/json",
      },
    });

    if (res.ok) {
      window.location.href = "/app/login/";
    }
  };

  return (
    <div className="profile-container">
      <h2>Your Profile</h2>

      <div className="form-section text-center">
        <h5>Profile Picture</h5>
        {msgPfp && (
          <p
            className={`msg-box ${
              msgPfp.error ? "error" : "success"
            }`}
          >
            {msgPfp.text}
          </p>
        )}
        <img
          src={user.profile_picture}
          alt="Profile"
          className="profile-picture"
        />
        <form
          onSubmit={changePfp}
          encType="multipart/form-data"
        >
          <input
            type="hidden"
            name="action"
            value="change_profile_picture"
          />
          <input
            type="file"
            name="profile_picture"
            className="form-control mt-3"
            required
          />
          <div className="button-center">
            <button className="btn btn-primary mt-2">
              Change Picture
            </button>
          </div>
        </form>
      </div>

      <div className="form-section">
        <h5>Change Username</h5>
        {msgUsername && (
          <p
            className={`msg-box ${
              msgUsername.error ? "error" : "success"
            }`}
          >
            {msgUsername.text}
          </p>
        )}
        <form onSubmit={changeUsername}>
          <input
            type="hidden"
            name="action"
            value="change_username"
          />
          <label className="form-label">New Username</label>
          <input
            className="form-control"
            name="new_username"
            defaultValue={user.username}
          />
          <div className="button-center">
            <button className="btn btn-primary mt-3">
              Save Username
            </button>
          </div>
        </form>
      </div>

      <div className="form-section">
        <h5>Change Password</h5>
        {msgPassword && (
          <p
            className={`msg-box ${
              msgPassword.error ? "error" : "success"
            }`}
          >
            {msgPassword.text}
          </p>
        )}
        <form onSubmit={changePassword}>
          <input
            type="hidden"
            name="action"
            value="change_password"
          />
          <label className="form-label">Current Password</label>
          <input
            className="form-control"
            name="old_password"
            type="password"
            required
          />
          <label className="form-label mt-3">
            New Password
          </label>
          <input
            className="form-control"
            name="new_password"
            type="password"
            required
          />
          <div className="button-center">
            <button className="btn btn-primary mt-3">
              Save Password
            </button>
          </div>
        </form>
      </div>

      <div className="form-section logout-section text-center">
        <button className="btn btn-danger" onClick={logout}>
          Log Out
        </button>
      </div>
    </div>
  );
}

export default ProfilePage;
