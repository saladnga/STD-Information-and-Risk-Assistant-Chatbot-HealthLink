import { Link, useNavigate, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { MenuOutlined, CloseOutlined } from "@ant-design/icons";
import logo from "../assets/logo.png";
import { clearAuth, getToken, getUser } from "../lib/storage";
import { useNotify } from "../lib/notify";

const HIDDEN_NAV_PATHS = ["/", "/login", "/signup"];

// Desktop: small pill-style links sitting inside the red header bar.
const navLinkClass =
  "text-troy-red text-lg px-1 font-mono border bg-troy-ink hover:opacity-90";
const ctaLinkClass =
  "bg-troy-red text-white hover:bg-troy-dark transition-colors text-sm font-semibold px-4 py-2 rounded-lg";

// Mobile: full-width rows, own sizing/coloring - the desktop pill classes above read as tiny cramped chips at this size.
const mobileLinkClass =
  "block w-full text-center py-4 text-xl font-mono text-troy-ink hover:bg-troy-line rounded-lg transition-colors";
const mobileCtaLinkClass =
  "block w-full text-center py-4 text-xl font-mono font-semibold bg-troy-red text-white hover:bg-troy-dark rounded-lg transition-colors";

export default function Header() {
  const navigate = useNavigate();
  const notify = useNotify();
  const [user, setUser] = useState<{ first_name?: string } | null>(null);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();
  const isHiddenNavPage = HIDDEN_NAV_PATHS.includes(location.pathname);

  useEffect(() => {
    setUser(getToken() ? getUser() : null);
  }, [location.pathname]);

  const handleLogout = () => {
    notify.confirm({
      title: "Log out?",
      content: "Are you sure you want to log out?",
      danger: true,
      onOk: () => {
        clearAuth();
        setUser(null);
        setIsMobileMenuOpen(false);
        navigate("/");
        notify.success("Logged out");
      },
    });
  };

  const toggleMobileMenu = () => setIsMobileMenuOpen((prev) => !prev);
  const closeMenu = () => setIsMobileMenuOpen(false);

  const handleLogoClick = () => navigate(user ? "/chat" : "/");

  const renderButtons = (variant: "desktop" | "mobile" = "desktop") => {
    if (isHiddenNavPage) return null;

    const linkClass = variant === "mobile" ? mobileLinkClass : navLinkClass;
    const ctaClass = variant === "mobile" ? mobileCtaLinkClass : ctaLinkClass;

    if (!user) {
      return (
        <>
          <Link to="/login" className={linkClass} onClick={closeMenu}>
            Login
          </Link>
          <Link to="/signup" className={ctaClass} onClick={closeMenu}>
            Sign Up
          </Link>
        </>
      );
    }

    return (
      <>
        {location.pathname !== "/chat" && (
          <Link to="/chat" className={linkClass} onClick={closeMenu}>
            Chat
          </Link>
        )}
        {location.pathname !== "/profile" && (
          <Link to="/profile" className={linkClass} onClick={closeMenu}>
            Profile
          </Link>
        )}
        <button onClick={handleLogout} className={linkClass}>
          Logout
        </button>
      </>
    );
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-troy-red backdrop-blur border-b border-troy-line px-4">
        <div className="max-w-full mx-auto">
          <div className="flex justify-between items-center h-16">
            <div
              onClick={handleLogoClick}
              className="flex items-center gap-3 cursor-pointer hover:opacity-90 transition-opacity"
            >
              <img
                src={logo}
                alt="Troy HealthBot logo"
                className="h-8 w-auto sm:h-12"
              />
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center gap-5">
              {renderButtons()}
            </nav>

            {/* Mobile menu button */}
            {!isHiddenNavPage && (
              <button
                onClick={toggleMobileMenu}
                aria-label={isMobileMenuOpen ? "Close menu" : "Open menu"}
                className="md:hidden inline-flex items-center justify-center p-2 rounded-md text-troy-ink hover:bg-troy-line focus:outline-none focus:ring-2 focus:ring-troy-red transition-colors text-xl"
              >
                {isMobileMenuOpen ? <CloseOutlined /> : <MenuOutlined />}
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Mobile Navigation Menu*/}
      {!isHiddenNavPage && (
        <div
          className={`md:hidden fixed inset-x-0 top-16 bottom-0 bg-troy-surface z-30 ${
            isMobileMenuOpen ? "block" : "hidden"
          }`}
        >
          <nav className="flex flex-col gap-2 p-4">
            {renderButtons("mobile")}
          </nav>
        </div>
      )}
    </>
  );
}
