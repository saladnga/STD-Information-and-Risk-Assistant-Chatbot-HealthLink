import { useState } from "react";
import { useNavigate } from "react-router-dom";

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

    try {
      const response = await fetch("http://localhost:8000/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          password,
          first_name: firstName,
          last_name: lastName,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user));
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
    <div className="flex justify-center items-center min-h-screen bg-troy-gray">
    <form
      onSubmit={handleSignup}
      className="bg-white p-8 rounded-2xl shadow-lg w-96 border-t-4 border-troy-red"
    >
      <h1 className="text-3xl font-bold text-center mb-6 text-troy-red">
        Sign Up
      </h1>

      <div className="mb-4">
        <label className="block text-sm font-semibold text-gray-700 mb-1">
          First Name
        </label>
        <input
          type="text"
          value={firstName}
          onChange={(e) => setFirstName(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-troy-red"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-semibold text-gray-700 mb-1">
          Last Name
        </label>
        <input
          type="text"
          value={lastName}
          onChange={(e) => setLastName(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-troy-red"
        />
      </div>

      <div className="mb-4">
        <label className="block text-sm font-semibold text-gray-700 mb-1">
          Email
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-troy-red"
        />
      </div>

      <div className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-1">
          Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          className="w-full border border-gray-300 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-troy-red"
        />
      </div>

      {error && (
        <p className="text-red-600 text-sm text-center mb-4 bg-red-50 p-2 rounded">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className={`w-full py-2 rounded-lg font-semibold text-white transition ${
          loading
            ? "bg-troy-dark cursor-not-allowed"
            : "bg-troy-red hover:bg-troy-dark"
        }`}
      >
        {loading ? "Signing up..." : "Sign Up"}
      </button>

      <p className="text-center text-sm text-gray-600 mt-4">
        Already have an account?{" "}
        <a
          href="/login"
          className="text-troy-red font-semibold hover:underline"
        >
          Login
        </a>
      </p>
    </form>
  </div>
  );
}

export default Signup;