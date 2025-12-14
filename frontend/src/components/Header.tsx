import { Link, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import logo from "../assets/logo.png";

export default function Header() {
  const navigate = useNavigate();
  const [user, setUser] = useState<{ first_name?: string } | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("access_token");
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    } else {
      setUser(null);
    }
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    localStorage.removeItem("access_token");
    localStorage.removeItem("current_session_id");
    setUser(null);
    setIsMobileMenuOpen(false);
    navigate("/");
  };

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const handleLogoClick = () => {
    if (user) {
      navigate("/chat");
    } else {
      navigate("/");
    }
  };

  // Determine which buttons to show
  const renderButtons = () => {
    // Hide all buttons on homepage, login, and signup pages
    if (
      location.pathname === "/" ||
      location.pathname === "/login" ||
      location.pathname === "/signup"
    ) {
      return null;
    }

    // If user is logged in
    if (user) {
      // Show different buttons based on current page
      if (location.pathname === "/profile") {
        return (
          <>
            <Link
              to="/chat"
              className="text-troy-red bg-white hover:bg-troy-red hover:text-white px-4 py-1 rounded-lg transition duration-200 text-sm font-medium"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Back to Chat
            </Link>
            <button
              onClick={handleLogout}
              className="bg-white text-troy-red font-medium px-4 py-1 rounded-lg hover:bg-gray-100 transition duration-200 text-sm"
            >
              Logout
            </button>
          </>
        );
      } else if (location.pathname === "/chat") {
        // In chat window - only show Profile and Logout, no Chat button
        return (
          <>
            <Link
              to="/profile"
              className="text-troy-red bg-white hover:opacity-85 px-4 py-1 rounded-lg transition duration-200 text-sm font-bold"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="bg-troy-red text-white border border-white font-bold px-4 py-1 rounded-lg hover:opacity-85 transition duration-200 text-sm"
            >
              Logout
            </button>
          </>
        );
      } else {
        // Other logged in pages (login, signup, etc.) - show Chat, Profile, Logout
        return (
          <>
            <Link
              to="/chat"
              className="text-troy-red bg-white hover:opacity-85 px-4 py-1 rounded-lg transition duration-200 text-sm font-bold"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Chat
            </Link>
            <Link
              to="/profile"
              className="text-troy-red bg-white hover:opacity-85 px-4 py-1 rounded-lg transition duration-200 text-sm font-bold" 
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Profile
            </Link>
            <button
              onClick={handleLogout}
              className="bg-troy-red text-white border border-white font-bold px-4 py-1 rounded-lg hover:opacity-85 transition duration-200 text-sm"
            >
              Logout
            </button>
          </>
        );
      }
    } else {
      // User not logged in - show login/signup
      return (
        <>
          <Link
            to="/login"
            className="text-troy-red bg-white hover:bg-troy-red hover:text-white px-4 py-1 rounded-lg transition duration-200 text-sm font-medium"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            Login
          </Link>
          <Link
            to="/signup"
            className="text-white bg-troy-red hover:bg-troy-dark px-4 py-1 rounded-lg transition duration-200 text-sm font-medium border border-white"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            Sign Up
          </Link>
        </>
      );
    }
  };

  return (
    <header className="bg-troy-red text-white shadow-lg relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div
            onClick={handleLogoClick}
            className="flex items-center gap-3 cursor-pointer hover:opacity-90 transition-opacity"
          >
            <img
              src={logo}
              alt="Troy HealthBot logo"
              className="h-8 w-auto sm:h-10"
            />
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-3">
            {user &&
              location.pathname !== "/" &&
              location.pathname !== "/login" &&
              location.pathname !== "/signup" && (
                <span className="text-base mr-2">
                  Welcome, {user.first_name || "User"}
                </span>
              )}
            {renderButtons()}
          </nav>

          {/* Mobile menu button - hide on homepage, login, and signup */}
          {location.pathname !== "/" &&
            location.pathname !== "/login" &&
            location.pathname !== "/signup" && (
              <button
                onClick={toggleMobileMenu}
                className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-white hover:bg-troy-dark focus:outline-none focus:ring-2 focus:ring-white transition-colors"
              >
                <svg
                  className={`${isMobileMenuOpen ? "hidden" : "block"} h-6 w-6`}
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
                <svg
                  className={`${isMobileMenuOpen ? "block" : "hidden"} h-6 w-6`}
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            )}
        </div>
      </div>

      {/* Mobile Navigation Menu - hide on homepage, login, and signup */}
      {location.pathname !== "/" &&
        location.pathname !== "/login" &&
        location.pathname !== "/signup" && (
          <div className={`md:hidden ${isMobileMenuOpen ? "block" : "hidden"}`}>
            <div className="px-2 pt-2 pb-3 space-y-1 bg-troy-dark border-t border-troy-red">
              {user && (
                <div className="px-3 py-2 text-sm text-troy-gray border-b border-troy-red/20 mb-2">
                  Welcome, {user.first_name || "User"}
                </div>
              )}
              <div className="flex flex-col space-y-2 px-3">
                {renderButtons()}
              </div>
            </div>
          </div>
        )}
    </header>
  );
}
