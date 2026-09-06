import { Link } from "react-router-dom";
import {
  LockOutlined,
  ThunderboltOutlined,
  HourglassOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import hero from "../assets/hero.webp";

const FEATURES = [
  {
    icon: <ThunderboltOutlined />,
    title: "AI-powered",
    description: "Trained on clinical symptom patterns.",
  },
  {
    icon: <LockOutlined />,
    title: "Confidential",
    description: "Your conversations stay private, always.",
  },
  {
    icon: <HourglassOutlined />,
    title: "24/7 available",
    description: "No appointment needed.",
  },
];

export default function Homepage() {
  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem)] bg-troy-clinic">
      {/* Hero */}
      <section className="flex-1 grid lg:grid-cols-2">
        <div className="bg-troy-surface text-white px-6 sm:px-12 lg:px-16 flex flex-col justify-center">
          <h1 className="font-display font-bold text-5xl sm:text-7xl leading-[1.05] mb-4 [text-wrap:balance] text-troy-red">
            Ask what you'd never say out loud.
          </h1>
          <p className="text-white text-2xl mb-4">
            Private, AI-guided health answers for Troy University students - no
            waiting room, no judgment.
          </p>

          <section className="py-6">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 max-w-5xl">
              {FEATURES.map((feature) => (
                <div key={feature.title} className="flex items-start gap-3">
                  <span className="text-troy-red text-2xl mt-0.5">
                    {feature.icon}
                  </span>
                  <div>
                    <h3 className="font-semibold text-troy-ink text-xl">
                      {feature.title}
                    </h3>
                    <p className="text-md text-troy-ink/70">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <div className="flex flex-wrap gap-10 mt-6">
            <Link
              to="/login"
              className="bg-white text-troy-red font-semibold px-6 py-3 hover:bg-troy-white/90 transition-colors font-mono"
            >
              Start a conversation
            </Link>
            <Link
              to="/signup"
              className="bg-white text-troy-red font-semibold px-6 py-3 hover:bg-troy-white/90 transition-colors font-mono"
            >
              Create account
            </Link>
          </div>

          <div className="max-w-5xl mt-10 p-3 rounded-xl">
            <p className="text-md text-yellow-200">
              <span className="font-semibold">
                <WarningOutlined /> Note:
              </span>{" "}
              This AI assistant provides general guidance only. Always consult a
              healthcare professional for medical advice.
            </p>
          </div>
        </div>

        {/* Hero image - fills the column height, cropped rather than stretched */}
        <div className="hidden lg:block h-full">
          <img
            src={hero}
            alt="Student using Troy HealthLink on a laptop"
            className="w-full h-full object-cover grayscale"
          />
        </div>
      </section>
    </div>
  );
}
