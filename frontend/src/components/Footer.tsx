export default function Footer() {
  return (
    <footer className="bg-gradient-to-r from-troy-red to-troy-dark text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold">AI Health Assistant</span>
          </div>
          <div className="text-sm text-center sm:text-right">
            <p>
              © {new Date().getFullYear()} Troy HealthBot
            </p>
            <p className="text-xs text-troy-gray/80 mt-1">
              Empowering students with intelligent health guidance
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
