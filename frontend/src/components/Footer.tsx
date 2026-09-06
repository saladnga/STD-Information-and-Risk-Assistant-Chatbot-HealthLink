import { useLocation } from "react-router-dom";

const HIDDEN_PATHS = ["/chat"];

export default function Footer() {
  const location = useLocation();
  if (HIDDEN_PATHS.includes(location.pathname)) return null;

  return (
    <footer className="bg-troy-red border-t border-troy-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-5 flex flex-col sm:flex-row items-center justify-between gap-1 font-mono text-xs">
        <span>© {new Date().getFullYear()} Troy HealthLink</span>
        <span>Empowering students with intelligent health guidance</span>
      </div>
    </footer>
  );
}
