// LogoutButton.tsx
import React from "react";
import { auth } from "./firebase";
import { signOut } from "firebase/auth";

const LogoutButton: React.FC = () => {
  const handleLogout = async () => {
    if (!auth) return;

    try {
      await signOut(auth);
    } catch (error) {
      console.error("Error signing out:", error);
    }
  };

  return (
    <button onClick={handleLogout} disabled={!auth}>
      Logout
    </button>
  );
};

export default LogoutButton;
