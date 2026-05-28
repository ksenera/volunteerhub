import { Home } from "lucide-react";
import { Link, NavLink } from "react-router-dom";
import LoginButton from "../auth/LoginButton";
import LogoutButton from "../auth/LogoutButton";
import { auth } from "../auth/firebase";
import { onAuthStateChanged, User } from "firebase/auth";
import { useEffect, useState } from "react";

function NavBar() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
    });
    return () => unsubscribe();
  }, []);

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-200 bg-white/90 px-4 py-3 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl items-center justify-between" aria-label="Main navigation">
        <Link to="/" className="flex items-center gap-2 font-bold text-slate-950">
          <Home className="h-6 w-6 text-orange-600" aria-hidden="true" />
          <span>VolunteerHub</span>
        </Link>

        <div className="flex items-center gap-3">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `rounded px-3 py-2 font-medium ${
                isActive ? "bg-orange-100 text-orange-800" : "text-slate-700 hover:bg-slate-100"
              }`
            }
          >
            Listings
          </NavLink>
          <NavLink
            to="/redeem"
            className={({ isActive }) =>
              `rounded px-3 py-2 font-medium ${
                isActive ? "bg-orange-100 text-orange-800" : "text-slate-700 hover:bg-slate-100"
              }`
            }
          >
            Redeem
          </NavLink>
          <div className="rounded border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800">
            {user ? <LogoutButton /> : <LoginButton />}
          </div>
        </div>
      </nav>
    </header>
  );
}

export default NavBar;
