interface SubmitButtonProps {
  loading: boolean;
  loadingText: string;
  children: React.ReactNode;
}

export default function SubmitButton({
  loading,
  loadingText,
  children,
}: SubmitButtonProps) {
  return (
    <button
      type="submit"
      disabled={loading}
      className={`w-full py-3 text-lg rounded-lg font-semibold text-white transition ${
        loading
          ? "bg-troy-dark cursor-not-allowed"
          : "bg-troy-red hover:bg-troy-dark"
      }`}
    >
      {loading ? loadingText : children}
    </button>
  );
}
