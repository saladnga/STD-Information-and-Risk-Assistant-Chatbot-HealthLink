export function validatePasswordStrength(password: string): string {
  if (password.length < 8) return "Password must be at least 8 characters";

  if (!/[A-Z]/.test(password))
    return "Password must contain at least one uppercase letter";

  if (!/[^A-Za-z0-9]/.test(password))
    return "Password must contain at least one symbol";

  return "";
}
