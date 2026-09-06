export default function FormError({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p className="text-red-400 text-sm text-center mb-4 bg-red-950/40 p-2 rounded">
      {message}
    </p>
  );
}
