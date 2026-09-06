import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authRequest } from "../lib/api";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import FormError from "../components/FormError";
import SubmitButton from "../components/SubmitButton";
import { validatePasswordStrength } from "../lib/validation";

function Signup() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    const passwordError = validatePasswordStrength(password);

    if (passwordError) {
      setError(passwordError);
      setLoading(false);
      return;
    }

    try {
      const { ok, data } = await authRequest("/auth/signup", {
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      });
      if (ok) {
        navigate("/chat");
      } else {
        setError(data.detail || "Signup failed");
      }
    } catch (err) {
      setError("Connection error: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Sign Up">
      <form onSubmit={handleSignup} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <FormField
            label="First Name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            required
          />
          <FormField
            label="Last Name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            required
          />
        </div>

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

        <SubmitButton loading={loading} loadingText="Signing up...">
          Sign Up
        </SubmitButton>

        <p className="text-center text-base text-troy-ink/70">
          Already have an account?{" "}
          <Link to="/login" className="text-troy-red font-semibold hover:underline">
            Login
          </Link>
        </p>
      </form>
    </AuthLayout>
  );
}

export default Signup;
