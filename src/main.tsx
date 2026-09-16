import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

// EDGEiQ Pages is a private/operator deployment. Do not allow an asynchronous
// auth provider to replace a successfully mounted application with an empty
// auth surface after first paint. Access control for a truly private deployment
// must live at the hosting/repository boundary, not as a client-side blanking
// transition.
const root = document.getElementById("root");
if (!root) throw new Error("Missing #root mount point");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
