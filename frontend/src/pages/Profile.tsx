import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiFetch } from "../lib/api";
import ProfileField from "../components/ProfileField";
import OpenAIKeySection from "../components/OpenAIKeySection";
import { getToken, getUser, saveUser } from "../lib/storage";
import { useNotify } from "../lib/notify";

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

const emptyUser: User = {
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
};

interface FieldConfig {
  label: string;
  name: keyof User;
  type?: string;
  options?: { value: string; label: string }[];
  placeholder?: string;
  hint?: string;
  disabled?: boolean;
  required?: boolean;
}

// One section per card, one entry per field
const SECTIONS: { title: string; fields: FieldConfig[] }[] = [
  {
    title: "Personal Information",
    fields: [
      { label: "First Name", name: "first_name", required: true },
      { label: "Last Name", name: "last_name" },
      {
        label: "Email Address",
        name: "email",
        disabled: true,
        hint: "(Cannot be changed)",
      },
      {
        label: "Phone Number",
        name: "phone",
        type: "tel",
        placeholder: "(123) 456-7890",
      },
      { label: "Date of Birth", name: "date_of_birth", type: "date" },
      {
        label: "Gender",
        name: "gender",
        options: [
          { value: "male", label: "Male" },
          { value: "female", label: "Female" },
          { value: "non-binary", label: "Non-binary" },
          { value: "transgender", label: "Transgender" },
          { value: "other", label: "Other" },
          { value: "prefer-not-to-say", label: "Prefer not to say" },
        ],
      },
    ],
  },
  {
    title: "Academic Information",
    fields: [
      {
        label: "Year in School",
        name: "year_in_school",
        options: [
          { value: "freshman", label: "Freshman" },
          { value: "sophomore", label: "Sophomore" },
          { value: "junior", label: "Junior" },
          { value: "senior", label: "Senior" },
          { value: "graduate", label: "Graduate" },
        ],
      },
      { label: "Major", name: "major", placeholder: "e.g., Computer Science" },
    ],
  },
  {
    title: "Emergency Contact",
    fields: [
      {
        label: "Contact Name",
        name: "emergency_contact_name",
        placeholder: "Full Name",
      },
      {
        label: "Contact Phone",
        name: "emergency_contact_phone",
        type: "tel",
        placeholder: "(123) 456-7890",
      },
    ],
  },
  {
    title: "Change Password",
    fields: [
      {
        label: "New Password (optional)",
        name: "password",
        type: "password",
        placeholder: "Leave blank to keep current password",
      },
    ],
  },
];

export default function Profile() {
  const navigate = useNavigate();
  const notify = useNotify();
  const [user, setUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<User>(emptyUser);
  const [saving, setSaving] = useState(false);
  // Kept out of User/formData - OpenAIKeySection has its own save flow and never goes through the generic SECTIONS/ProfileField machinery.
  const [hasCustomOpenaiKey, setHasCustomOpenaiKey] = useState(false);
  const [openaiModel, setOpenaiModel] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    const storedUser = getUser();
    if (!token || !storedUser) {
      navigate("/login");
      return;
    }
    setUser(storedUser);
    setFormData(storedUser);
    setHasCustomOpenaiKey(!!storedUser.has_custom_openai_key);
    setOpenaiModel(storedUser.openai_model || null);
  }, [navigate]);

  const isDirty =
    user !== null && JSON.stringify(formData) !== JSON.stringify(user);

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => {
    const { name, value } = e.target;
    setFormData({ ...formData, [name]: value });
  };

  const handleDiscard = () => {
    if (user) setFormData(user);
  };

  const handleSave = () => {
    if (!formData.first_name || !formData.email) {
      notify.error("First name and email are required");
      return;
    }
    notify.confirm({
      title: "Save changes?",
      content: "Update your profile with these changes.",
      onOk: doSave,
    });
  };

  const doSave = async () => {
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

    setSaving(true);
    try {
      const response = await apiFetch(`/auth/profile`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profileFields),
      });

      if (!response.ok) {
        throw new Error("Failed to update profile");
      }

      const updatedProfile = await response.json();
      saveUser(updatedProfile);
      setUser(updatedProfile);
      setFormData(updatedProfile);
      notify.success("Profile updated");
    } catch (error) {
      console.error("Error updating profile:", error);
      notify.error("Failed to update profile. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-[calc(100vh-4rem)] bg-troy-clinic">
      <div className="px-6 sm:px-12 lg:px-16 py-8">
        <div className="max-w-xl mx-auto space-y-8">
          {SECTIONS.map((section) => (
            <div key={section.title} className="border-b border-troy-line pb-6">
              <h3 className="text-lg font-medium text-troy-ink mb-4 font-mono">
                {section.title}
              </h3>
              <div className="space-y-4">
                {section.fields.map((field) => (
                  <ProfileField
                    key={field.name}
                    {...field}
                    value={formData[field.name] || ""}
                    onChange={handleChange}
                  />
                ))}
              </div>
            </div>
          ))}

          <OpenAIKeySection
            hasCustomKey={hasCustomOpenaiKey}
            currentModel={openaiModel}
            onChange={(hasCustomKey, model) => {
              setHasCustomOpenaiKey(hasCustomKey);
              setOpenaiModel(model);
            }}
          />

          {/* Save bar */}
          <div className="pt-2 flex items-center justify-center gap-3">
            <button
              onClick={handleSave}
              disabled={!isDirty || saving}
              className="px-6 py-3 text-lg bg-troy-red text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none flex items-center justify-center gap-2"
            >
              {saving ? "Saving..." : "Save changes"}
            </button>
            {isDirty && !saving && (
              <button
                onClick={handleDiscard}
                className="text-sm text-troy-ink/60 hover:text-troy-ink transition-colors"
              >
                Discard changes
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
