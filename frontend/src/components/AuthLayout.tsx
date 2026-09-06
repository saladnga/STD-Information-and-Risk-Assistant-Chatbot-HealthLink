import type { ReactNode } from "react";

// Shared shell for Login/Signup/ForgotPassword/ResetPassword
export default function AuthLayout({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen flex justify-center items-center">
      <div className="flex flex-col justify-center bg-troy-clinic px-6 sm:px-12 lg:px-16 py-10 w-full">
        <div className="max-w-xl mx-auto w-full">
          <h1 className="font-thin text-3xl text-troy-white mb-6 text-center font-mono">
            {title}
          </h1>
          {children}
        </div>
      </div>
    </div>
  );
}
