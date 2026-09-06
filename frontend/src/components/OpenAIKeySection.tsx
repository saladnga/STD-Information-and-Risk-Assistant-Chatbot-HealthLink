import { useState } from "react";
import { Select } from "antd";
import { setOpenaiKey, clearOpenaiKey } from "../lib/api";
import { useNotify } from "../lib/notify";

// Kept in sync with ALLOWED_CUSTOM_MODELS in backend/app/routers/auth.py.
const MODEL_OPTIONS = [
  { value: "gpt-4o", label: "GPT-4o (recommended)" },
  { value: "gpt-4o-mini", label: "GPT-4o mini (fastest, cheapest)" },
  { value: "gpt-4-turbo", label: "GPT-4 Turbo" },
];

// Saves immediately on its own action instead of riding the generic "Save changes" bar - the key is write-only, never echoed back (auth.py's _strip_openai_key).
export default function OpenAIKeySection({
  hasCustomKey,
  currentModel,
  onChange,
}: {
  hasCustomKey: boolean;
  currentModel: string | null;
  onChange: (hasCustomKey: boolean, model: string | null) => void;
}) {
  const notify = useNotify();
  const [input, setInput] = useState("");
  const [selectedModel, setSelectedModel] = useState(currentModel || "gpt-4o");
  const [saving, setSaving] = useState(false);

  // A new key always counts as a change; with a key already on file, just switching the model (without retyping the key) is also a valid save.
  const canSave =
    input.trim().length > 0 || (hasCustomKey && selectedModel !== currentModel);

  const save = async () => {
    if (!canSave) return;
    setSaving(true);
    try {
      const { ok, data } = await setOpenaiKey(
        input.trim() || undefined,
        selectedModel,
      );
      if (ok) {
        setInput("");
        onChange(true, data.openai_model);
        notify.success("Saved - chat now uses this model.");
      } else {
        notify.error(data.detail || "Could not save that key");
      }
    } catch {
      notify.error("Connection error - please try again.");
    } finally {
      setSaving(false);
    }
  };

  const remove = () => {
    notify.confirm({
      title: "Remove your API key?",
      content: "Chat will go back to the app's default model.",
      danger: true,
      onOk: async () => {
        const { ok, data } = await clearOpenaiKey();
        if (ok) {
          setSelectedModel("gpt-4o");
          onChange(false, null);
          notify.success("API key removed");
        } else {
          notify.error(data.detail || "Could not remove the key");
        }
      },
    });
  };

  return (
    <div className="border-b border-troy-line pb-6">
      <h3 className="text-lg font-medium text-troy-ink mb-1 font-mono">
        AI Model
      </h3>
      <p className="text-sm text-troy-ink/60 mb-4">
        {hasCustomKey
          ? "A personal OpenAI API key is on file - chat uses the model below, billed to your own OpenAI account."
          : "By default, chat uses the app's own key on its standard model. Add your own OpenAI API key to unlock a higher-tier model at your own cost."}
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-base font-medium text-troy-ink mb-2">
            OpenAI API Key
            {hasCustomKey && (
              <span className="text-xs text-troy-ink/60 ml-1">
                (leave blank to keep your current key)
              </span>
            )}
          </label>
          <input
            type="password"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="sk-..."
            className="w-full border-2 rounded-xl px-4 py-3 text-lg transition-all duration-200 border-troy-line focus:border-troy-red focus:ring-2 focus:ring-troy-red/20"
          />
        </div>

        <div>
          <label className="block text-base font-medium text-troy-ink mb-2">
            Model
          </label>
          <Select
            size="large"
            className="w-full"
            value={selectedModel}
            options={MODEL_OPTIONS}
            onChange={setSelectedModel}
          />
        </div>

        <div className="pt-2 flex items-center justify-center gap-3">
          <button
            onClick={save}
            disabled={!canSave || saving}
            className="px-6 py-3 text-lg bg-troy-red text-white rounded-xl font-medium hover:shadow-lg transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {saving ? "Saving..." : "Apply Model Settings"}
          </button>
          {hasCustomKey && (
            <button
              onClick={remove}
              className="text-sm text-troy-ink/60 hover:text-troy-ink transition-colors"
            >
              Remove key
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
