import React from "react";
import Logo from "../components/Logo";
import Accordion from "@/components/Accordion";
import { NavLink } from "react-router";
import { FaArrowLeft, FaGithub } from "react-icons/fa";

const faqs = [
  {
    question: "What is this application about?",
    answer:
      "This application provides advanced file analysis using techniques like entropy calculations, metadata extraction, and heuristic evaluations to help identify potential threats in files.",
    open: false,
  },
  {
    question: "How does file analysis work?",
    answer:
      "The application processes the file in chunks and uses worker threads to extract features such as strings, IPs, URLs, and metadata, while calculating entropy to detect anomalies.",
    open: false,
  },
  {
    question: "What file formats are supported?",
    answer:
      "Currently, the application supports analysis of DOC, DOCX, RTF, XLS, XLSX, PPT, PPTX, and PDF files.",
    open: false,
  },
  {
    question: "Is my data secure?",
    answer:
      "Yes, your files are processed locally, ensuring that no sensitive data leaves your device.",
    open: false,
  },
  {
    question: "Where can I find the source code?",
    answer:
      "The project is open source and available on GitHub. You can find the source code, contribute, and report issues at: https://github.com/filippofinke/infectio",
    open: false,
  },
];

const LearnMorePage = () => {
  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-6">
      <div className="flex items-center mb-8 justify-between">
        <Logo />
        <div className="flex items-center space-x-4">
          <a
            href="https://github.com/filippofinke/infectio"
            target="_blank"
            rel="noopener noreferrer"
            className="text-gray-700 hover:text-blue-500 transition-colors"
            title="View on GitHub"
          >
            <FaGithub size={24} />
          </a>
          <NavLink
            to="/"
            className="text-blue-500 hover:underline flex items-center"
          >
            <FaArrowLeft className="inline-block mr-1" />
            Go back
          </NavLink>
        </div>
      </div>

      <p className="mb-6">
        This application empowers users with advanced tools for file analysis,
        focusing on identifying potential threats through static malware
        analysis. Learn how it works and discover its key features below.
      </p>

      <section className="flex flex-col flex-grow overflow-hidden">
        <h2 className="text-2xl font-semibold mb-4">FAQs</h2>
        <div className="overflow-y-auto flex-grow">
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <Accordion key={index} title={faq.question} defaultOpen={false}>
                <p className="mt-2 text-gray-600">{faq.answer}</p>
              </Accordion>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default LearnMorePage;
