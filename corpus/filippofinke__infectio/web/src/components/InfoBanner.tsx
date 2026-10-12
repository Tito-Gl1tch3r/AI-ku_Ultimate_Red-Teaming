import React from "react";
import { FaArrowRight, FaGithub } from "react-icons/fa";
import { NavLink } from "react-router";

interface InfoBannerProps {
  text: string;
  linkText: string;
  linkHref: string;
  backgroundColor?: string;
  textColor?: string;
  linkColor?: string;
}

function InfoBanner({
  text,
  linkText,
  linkHref,
  backgroundColor = "bg-gray-200",
  textColor = "text-gray-700",
  linkColor = "text-blue-600",
}: InfoBannerProps) {
  return (
    <div
      className={`flex items-center justify-between px-6 py-4 rounded-lg ${backgroundColor} border border-gray-300`}
    >
      <a
        href="https://github.com/filippofinke/infectio"
        target="_blank"
        rel="noopener noreferrer"
        className={`flex items-center ${linkColor} hover:opacity-80 transition-opacity`}
        aria-label="View on GitHub"
      >
        <FaGithub className="h-5 w-5" />
      </a>
      <p className={`ml-2 text-sm ${textColor}`}>{text}</p>
      <div className="flex items-center space-x-4">
        <NavLink
          to={linkHref}
          className={`flex items-center text-sm font-medium ${linkColor} hover:underline ml-1`}
        >
          {linkText}
          <FaArrowRight className="ml-1 h-4 w-4" />
        </NavLink>
      </div>
    </div>
  );
}

export default InfoBanner;
