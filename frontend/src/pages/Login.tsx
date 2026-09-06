import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authRequest } from "../lib/api";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import FormError from "../components/FormError";
import SubmitButton from "../components/SubmitButton";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { ok, data } = await authRequest("/auth/login", {
        email,
        password,
      });

      if (ok) {
        navigate("/chat");
      } else {
        setError(data.detail || "Login failed");
      }
    } catch (err) {
      setError("Connection error");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Login">
      <form onSubmit={handleLogin} className="space-y-4">
        <FormField
          label="Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />

        <FormField
          label="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />

        <FormError message={error} />

        <SubmitButton loading={loading} loadingText="Logging in...">
          Login
        </SubmitButton>

        <p className="text-center text-base text-troy-ink/70">
          Don't have an account?{" "}
          <Link to="/signup" className="text-troy-red font-semibold hover:underline">
            Sign up
          </Link>
        </p>
        <p className="text-center text-base text-troy-ink/70">
          <Link to="/forgot-password" className="text-troy-red font-semibold hover:underline">
            Forgot your password?
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

export default Login;
