import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

type ErrorBoundaryState = { error: Error | null };

class ProductionErrorBoundary extends React.Component<React.PropsWithChildren, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("EDGEiQ production render failure", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <main style={{ minHeight: "100vh", background: "#f5f8fc", color: "#10213f", padding: 32, fontFamily: "Inter, system-ui, sans-serif" }}>
          <h1 style={{ margin: 0, fontSize: 24 }}>EDGEiQ Racing</h1>
          <p style={{ marginTop: 12 }}>The application hit a runtime render error.</p>
          <pre style={{ whiteSpace: "pre-wrap", marginTop: 16, padding: 16, background: "#fff", border: "1px solid #dce5f0" }}>
            {this.state.error.message}
          </pre>
        </main>
      );
    }
    return this.props.children;
  }
}

const root = document.getElementById("root");
if (!root) throw new Error("Missing #root mount point");

ReactDOM.createRoot(root).render(
  <ProductionErrorBoundary>
    <App />
  </ProductionErrorBoundary>,
);
