import { useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../lib/api";
import AuthLayout from "../components/AuthLayout";
import FormField from "../components/FormField";
import FormError from "../components/FormError";
import SubmitButton from "../components/SubmitButton";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const { ok, data } = await forgotPassword(email);
      if (ok) {
        setSubmitted(true);
      } else {
        setError(data.detail || "Something went wrong");
      }
    } catch (err) {
      setError("Connection error: " + err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthLayout title="Forgot Password">
      {submitted ? (
        <p className="text-troy-ink/80 text-center">
          If an account exists for that email, a reset link has been sent.
          Check your inbox.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <FormField
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <FormError message={error} />

          <SubmitButton loading={loading} loadingText="Sending...">
            Send reset link
          </SubmitButton>
        </form>
      )}

      <p className="text-center text-base text-troy-ink/70 mt-4">
        <Link to="/login" className="text-troy-red font-semibold hover:underline">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  );
}

export default ForgotPassword;
