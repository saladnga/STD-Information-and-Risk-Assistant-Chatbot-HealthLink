import type React from "react";
import { Select } from "antd";

interface Option {
  value: string;
  label: string;
}

interface ProfileFieldProps {
  label: string;
  name: string;
  value: string;
  onChange: (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>,
  ) => void;
  type?: string;
  options?: Option[];
  disabled?: boolean;
  hint?: string;
  placeholder?: string;
  required?: boolean;
}

const fieldClass = (active: boolean) =>
  `w-full border-2 rounded-xl px-4 py-3 text-lg transition-all duration-200 ${
    active
      ? "border-troy-line focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
      : "bg-troy-clinic border-troy-line cursor-not-allowed"
  }`;

export default function ProfileField({
  label,
  name,
  value,
  onChange,
  type = "text",
  options,
  disabled,
  hint,
  placeholder,
  required,
}: ProfileFieldProps) {
  const active = !disabled;

  return (
    <div>
      <label className="block text-base font-medium text-troy-ink mb-2">
        {label}
        {required && " *"}
        {hint && <span className="text-xs text-troy-ink/60 ml-1">{hint}</span>}
      </label>
      {options ? (
        <Select
          size="large"
          className="w-full"
          value={value || undefined}
          placeholder={`Select ${label}`}
          disabled={!active}
          options={options}
          onChange={(val: string) =>
            onChange({
              target: { name, value: val },
            } as React.ChangeEvent<HTMLSelectElement>)
          }
        />
      ) : (
        <input
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          disabled={!active}
          placeholder={placeholder}
          className={fieldClass(active)}
        />
      )}
    </div>
  );
}
