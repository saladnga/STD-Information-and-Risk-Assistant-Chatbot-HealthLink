import background from "../assets/troycampus.png";
import { Link } from "react-router-dom";
import {
  LockOutlined,
  ThunderboltOutlined,
  HourglassOutlined,
} from "@ant-design/icons";

export default function Homepage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-troy-gray to-troy-white">
      {/* Hero Section */}
      <section
        className="relative flex flex-col items-center justify-center min-h-screen bg-cover bg-center text-center text-white px-4 sm:px-6 lg:px-8"
        style={{
          backgroundImage: `url(${background})`,
        }}
      >
        {/* Improved Overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-black/60 via-black/50 to-black/40"></div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-4xl mx-auto">
          <div className="space-y-8">
            {/* Main Heading */}
            <div className="space-y-4">
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
                <span className="block">Welcome to</span>
                <span className="block text-transparent bg-clip-text bg-gradient-to-r from-white to-troy-gray">
                  Troy HealthBot
                </span>
              </h1>
              <div className="w-24 h-1 bg-troy-red mx-auto rounded-full"></div>
            </div>

            {/* Subtitle */}
            <p className="max-w-2xl mx-auto text-lg sm:text-xl lg:text-2xl leading-relaxed text-gray-200">
              Your AI-powered health assistant providing trusted medical
              insights and personalized guidance for Troy University students.
            </p>

            {/* Features */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 max-w-3xl mx-auto text-sm sm:text-base">
              <div className="flex flex-col items-center space-y-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg">
                <div className="w-12 h-12 bg-troy-red rounded-full flex items-center justify-center">
                  <span className="text-xl">
                    <HourglassOutlined />
                  </span>
                </div>
                <h3 className="font-semibold">AI-Powered</h3>
                <p className="text-gray-300 text-center">
                  Advanced machine learning for accurate health insights
                </p>
              </div>
              <div className="flex flex-col items-center space-y-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg">
                <div className="w-12 h-12 bg-troy-red rounded-full flex items-center justify-center">
                  <span className="text-xl">
                    <LockOutlined />
                  </span>
                </div>
                <h3 className="font-semibold">Secure & Private</h3>
                <p className="text-gray-300 text-center">
                  Your health information stays confidential
                </p>
              </div>
              <div className="flex flex-col items-center space-y-2 p-4 bg-white/10 backdrop-blur-sm rounded-lg">
                <div className="w-12 h-12 bg-troy-red rounded-full flex items-center justify-center">
                  <span className="text-xl">
                    <ThunderboltOutlined />
                  </span>
                </div>
                <h3 className="font-semibold">24/7 Available</h3>
                <p className="text-gray-300 text-center">
                  Get health guidance anytime, anywhere
                </p>
              </div>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/login"
                className="w-full sm:w-auto bg-troy-red hover:bg-troy-dark text-white font-semibold px-8 py-4 rounded-xl transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl text-lg"
              >
                Get Started Now
              </Link>
              <Link
                to="/signup"
                className="w-full sm:w-auto bg-white/20 backdrop-blur-sm hover:bg-white/30 text-white font-semibold px-8 py-4 rounded-xl transition-all duration-300 border border-white/20 hover:border-white/40 text-lg"
              >
                Create Account
              </Link>
            </div>

            {/* Disclaimer */}
            <div className="mt-8 p-4 bg-yellow-500/20 backdrop-blur-sm rounded-lg border border-yellow-300/30">
              <p className="text-sm text-yellow-100 flex items-center justify-center gap-2">
                <span className="text-lg">⚠️</span>
                This AI assistant provides general guidance only. Always consult
                a healthcare professional for medical advice.
              </p>
            </div>
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-8 left-1/2 transform -translate-x-1/2 animate-bounce">
          <div className="w-6 h-10 border-2 border-white/50 rounded-full flex justify-center">
            <div className="w-1 h-3 bg-white/50 rounded-full mt-2 animate-pulse"></div>
          </div>
        </div>
      </section>
    </div>
  );
}
