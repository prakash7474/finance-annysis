// ErrorBoundary.tsx - Recoverable crash guard for the whole app.
//
// Without this, any unhandled render exception unmounts the entire React tree,
// leaving a blank white screen. This boundary catches such errors and shows a
// recoverable panel instead, so a single bad SSE payload or value can never
// take down the whole UI.

import React from "react";

interface State {
  error: Error | null;
}

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Keep a structured log for diagnostics (no stack traces leak to users).
    console.error("[ErrorBoundary] caught render error:", error?.message, info?.componentStack);
  }

  private reset = () => this.setState({ error: null });

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-[#0B0E14] p-6">
          <div className="max-w-md w-full rounded-2xl border border-red/30 bg-[#1a0f12] p-6 text-center shadow-card">
            <div className="text-2xl font-extrabold text-red">Something went wrong</div>
            <p className="mt-2 text-sm text-text2">
              The interface hit an unexpected error and was paused to avoid a blank screen.
              Your session is still alive — you can resume.
            </p>
            <pre className="mt-3 max-h-32 overflow-auto rounded-lg bg-black/40 p-3 text-left text-[11px] text-red/90">
              {this.state.error.message}
            </pre>
            <div className="mt-4 flex justify-center gap-3">
              <button
                onClick={this.reset}
                className="px-4 py-2 rounded-xl bg-blue text-white text-sm font-bold"
              >
                Try again
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 rounded-xl bg-panel-raised text-text2 text-sm font-semibold"
              >
                Reload
              </button>
            </div>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
