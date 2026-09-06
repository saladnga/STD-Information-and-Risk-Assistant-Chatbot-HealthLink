import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { resetPassword } from "../lib/api";
import { validatePasswordStrength } from "../lib/validation";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import FormError from "../components/FormError";
import SubmitButton from "../components/SubmitButton";

function getRecoveryToken(): string {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  return hash.get("access_token") || "";
}

function ResetPassword() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const token = getRecoveryToken();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!token) {
      setError(
        "This reset link is invalid or has expired. Please request a new one.",
      );
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    const passwordError = validatePasswordStrength(password);
    if (passwordError) {
      setError(passwordError);
      return;
    }

    setLoading(true);
    try {
      const { ok, data } = await resetPassword(token, password);
      if (ok) {
        navigate("/login");
      } else {
        setError(data.detail || "Failed to reset password");
      }
    } catch (err) {
      setError("Connection error: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Reset Password">
      <form onSubmit={handleSubmit} className="space-y-4">
        <FormField
          label="New Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <FormField
          label="Confirm New Password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          required
        />

        <FormError message={error} />

        <SubmitButton loading={loading} loadingText="Updating...">
          Update password
        </SubmitButton>
      </form>

      <p className="text-center text-base text-troy-ink/70 mt-4">
        <Link to="/login" className="text-troy-red font-semibold hover:underline">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  );
}

export default ResetPassword;
