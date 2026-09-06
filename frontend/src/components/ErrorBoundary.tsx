import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

// Error boundaries must be class components - no hook equivalent exists.
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Unhandled UI error:", error, info);
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-screen bg-troy-clinic flex flex-col items-center justify-center text-center px-6">
        <h1 className="font-display font-bold text-3xl text-troy-ink mb-2">
          Something went wrong.
        </h1>
        <p className="text-troy-ink/60 max-w-sm mb-6">
          Troy HealthLink hit an unexpected error. Reloading the page usually
          fixes it.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-troy-red text-white font-semibold px-6 py-3 rounded-xl hover:bg-troy-dark transition-colors"
        >
          Reload
        </button>
      </div>
    );
  }
}
