import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { UserOutlined } from "@ant-design/icons";
import { API_URL } from "../lib/api";

interface User {
  first_name: string;
  last_name?: string;
  email: string;
  phone?: string;
  date_of_birth?: string;
  gender?: string;
  year_in_school?: string;
  major?: string;
  emergency_contact_name?: string;
  emergency_contact_phone?: string;
  password?: string;
}

export default function Profile() {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<User>({
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    date_of_birth: "",
    gender: "",
    year_in_school: "",
    major: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    password: "",
  });

  // Load user from localStorage
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("access_token");
    if (!storedUser || !token) {
      navigate("/login");
      return;
    }

    // Try to use real user data first
    let parsedUser;
    try {
      parsedUser = JSON.parse(storedUser);
    } catch {
      parsedUser = null;
    }

    // If no real user data, use enhanced fake data for demo
    const userData = parsedUser || {
      first_name: "John",
      last_name: "Doe",
      email: "john.doe@troy.edu",
      phone: "(334) 670-3000",
      date_of_birth: "2002-03-15",
      gender: "male",
      year_in_school: "junior",
      major: "Computer Science",
      emergency_contact_name: "Jane Doe",
      emergency_contact_phone: "(334) 670-3001",
    };

    setUser(userData);
    setFormData(userData);
  }, [navigate]);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleSave = async () => {
    if (!formData.first_name || !formData.email) {
      alert("First name and email are required");
      return;
    }

    const token = localStorage.getItem("access_token");

    const {
      first_name,
      last_name,
      email,
      phone,
      date_of_birth,
      gender,
      year_in_school,
      major,
      emergency_contact_name,
      emergency_contact_phone,
    } = formData;

    const profileFields = {
      first_name,
      last_name,
      email,
      phone,
      date_of_birth,
      gender,
      year_in_school,
      major,
      emergency_contact_name,
      emergency_contact_phone,
    };

    try {
      const response = await fetch(`${API_URL}/auth/profile`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(profileFields),
      });

      if (!response.ok) {
        throw new Error("Failed to update profile");
      }

      const updatedProfile = await response.json();
      localStorage.setItem("user", JSON.stringify(updatedProfile));
      setUser(updatedProfile);
      setIsEditing(false);
      alert("Profile updated successfully!");
    } catch (error) {
      console.error("Error updating profile:", error);
      alert("Failed to update profile. Please try again.");
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-gray-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-troy-red to-troy-dark rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-white text-3xl">
              {" "}
              <UserOutlined />
            </span>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">My Profile</h1>
          <p className="text-gray-600 mt-2">
            Manage your account settings and preferences
          </p>
        </div>

        {/* Profile Summary Card */}
        <div className="bg-white shadow-lg rounded-2xl overflow-hidden border border-gray-100 mb-6">
          <div className="bg-gradient-to-r from-troy-red to-troy-dark px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="text-white">
                <h2 className="text-xl font-semibold">
                  {user.first_name} {user.last_name || ""}
                </h2>
                <p className="text-troy-red-100 opacity-90">{user.email}</p>
              </div>
              <div className="text-white text-right">
                <p className="text-sm opacity-90">{user.major || "Student"}</p>
                <p className="text-xs opacity-75 capitalize">
                  {user.year_in_school || ""}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white shadow-xl rounded-3xl overflow-hidden border border-gray-100">
          <div className="bg-gradient-to-r from-troy-red to-troy-dark px-6 py-4">
            <h2 className="text-xl font-semibold text-white">
              Profile Information
            </h2>
          </div>
          <div className="p-6 sm:p-8">
            <div className="space-y-6">
              {/* Personal Information Section */}
              <div className="border-b border-gray-200 pb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Personal Information
                </h3>

                {/* First Name and Last Name */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      First Name *
                    </label>
                    <input
                      type="text"
                      name="first_name"
                      value={formData.first_name}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      name="last_name"
                      value={formData.last_name || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                </div>

                {/* Email (Always disabled) */}
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Email Address
                    <span className="text-xs text-gray-500 ml-1">
                      (Cannot be changed)
                    </span>
                  </label>
                  <input
                    type="email"
                    name="email"
                    value={formData.email}
                    disabled={true}
                    className="w-full border-2 bg-gray-50 border-gray-200 cursor-not-allowed rounded-xl px-4 py-3 transition-all duration-200"
                  />
                </div>

                {/* Phone and Date of Birth */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Phone Number
                    </label>
                    <input
                      type="tel"
                      name="phone"
                      value={formData.phone || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      placeholder="(123) 456-7890"
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Date of Birth
                    </label>
                    <input
                      type="date"
                      name="date_of_birth"
                      value={formData.date_of_birth || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                </div>

                {/* Gender */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Gender
                  </label>
                  <select
                    name="gender"
                    value={formData.gender || ""}
                    onChange={handleChange}
                    disabled={!isEditing}
                    className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                      isEditing
                        ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                        : "bg-gray-50 border-gray-200 cursor-not-allowed"
                    }`}
                  >
                    <option value="">Select Gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="non-binary">Non-binary</option>
                    <option value="transgender">Transgender</option>
                    <option value="other">Other</option>
                    <option value="prefer-not-to-say">Prefer not to say</option>
                  </select>
                </div>
              </div>

              {/* Academic Information Section */}
              <div className="border-b border-gray-200 pb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Academic Information
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Year in School
                    </label>
                    <select
                      name="year_in_school"
                      value={formData.year_in_school || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    >
                      <option value="">Select Year</option>
                      <option value="freshman">Freshman</option>
                      <option value="sophomore">Sophomore</option>
                      <option value="junior">Junior</option>
                      <option value="senior">Senior</option>
                      <option value="graduate">Graduate</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Major
                    </label>
                    <input
                      type="text"
                      name="major"
                      value={formData.major || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      placeholder="e.g., Computer Science"
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Emergency Contact Section */}
              <div className="pb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">
                  Emergency Contact
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Contact Name
                    </label>
                    <input
                      type="text"
                      name="emergency_contact_name"
                      value={formData.emergency_contact_name || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      placeholder="Full Name"
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Contact Phone
                    </label>
                    <input
                      type="tel"
                      name="emergency_contact_phone"
                      value={formData.emergency_contact_phone || ""}
                      onChange={handleChange}
                      disabled={!isEditing}
                      placeholder="(123) 456-7890"
                      className={`w-full border-2 rounded-xl px-4 py-3 transition-all duration-200 ${
                        isEditing
                          ? "border-gray-300 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
                          : "bg-gray-50 border-gray-200 cursor-not-allowed"
                      }`}
                    />
                  </div>
                </div>
              </div>

              {/* Password Section - Only show when editing */}
              {isEditing && (
                <div>
                  <h3 className="text-lg font-medium text-gray-900 mb-4">
                    Change Password
                  </h3>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      New Password (optional)
                    </label>
                    <input
                      type="password"
                      name="password"
                      value={formData.password || ""}
                      onChange={handleChange}
                      className="w-full border-2 border-gray-300 rounded-xl px-4 py-3 focus:border-troy-red focus:ring-2 focus:ring-troy-red/20 transition-all duration-200"
                      placeholder="Leave blank to keep current password"
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-8 pt-6 border-t border-gray-200">
              {isEditing && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 mb-6">
                  <div className="flex items-start">
                    <div className="flex-shrink-0">
                      <svg
                        className="h-5 w-5 text-blue-400"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                          clipRule="evenodd"
                        />
                      </svg>
                    </div>
                    <div className="ml-3">
                      <h4 className="text-sm font-medium text-blue-800">
                        Editing Mode
                      </h4>
                      <div className="mt-1 text-sm text-blue-700">
                        <p>
                          Fields marked with * are required. Your email address
                          cannot be changed for security reasons.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3">
                {isEditing ? (
                  <>
                    <button
                      onClick={handleSave}
                      className="flex-1 sm:flex-none px-6 py-3 bg-gradient-to-r from-troy-red to-troy-dark text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      Save Changes
                    </button>
                    <button
                      onClick={() => {
                        setFormData(user);
                        setIsEditing(false);
                      }}
                      className="flex-1 sm:flex-none px-6 py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-all duration-200 flex items-center justify-center gap-2"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2"
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setIsEditing(true)}
                    className="w-full sm:w-auto px-6 py-3 bg-gradient-to-r from-troy-red to-troy-dark text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 transform hover:scale-105 flex items-center justify-center gap-2"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
                      />
                    </svg>
                    Edit Profile
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
