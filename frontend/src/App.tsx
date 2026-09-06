import { Suspense, lazy } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { ConfigProvider, App as AntApp, theme, Spin } from "antd";
import Header from "./components/Header";
import Footer from "./components/Footer";

// Route-level code splitting - each page ships as its own chunk, fetched only when visited, instead of one bundle with every page up front.
const Login = lazy(() => import("./pages/Login"));
const Signup = lazy(() => import("./pages/Signup"));
const HomePage = lazy(() => import("./pages/HomePage"));
const Profile = lazy(() => import("./pages/Profile"));
const ChatLayout = lazy(() => import("./pages/ChatLayout"));
const ResetPassword = lazy(() => import("./pages/ResetPassword"));
const ForgotPassword = lazy(() => import("./pages/ForgotPassword"));
const NotFound = lazy(() => import("./pages/NotFound"));

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: "#9b2428",
          colorBgContainer: "#1F221C",
          colorBgElevated: "#1F221C",
          colorBorder: "#35392F",
          colorText: "#F1EFEA",
          colorLink: "#9b2428",
          colorLinkHover: "#9b2428",
          colorLinkActive: "#7a1d20",
          borderRadius: 10,
          fontFamily: "'Source Sans 3', sans-serif",
        },
      }}
    >
      <AntApp>
        <Router>
          <Header />
          <Suspense
            fallback={
              <div
                style={{
                  display: "flex",
                  justifyContent: "center",
                  padding: "4rem",
                }}
              >
                <Spin size="large" />
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/login" element={<Login />} />
              <Route path="/signup" element={<Signup />} />
              <Route path="/forgot-password" element={<ForgotPassword />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/chat" element={<ChatLayout />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Suspense>
          <Footer />
        </Router>
      </AntApp>
    </ConfigProvider>
  );
}

export default App;
