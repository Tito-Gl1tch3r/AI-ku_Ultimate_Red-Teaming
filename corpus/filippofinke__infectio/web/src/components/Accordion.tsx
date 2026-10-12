import React, { useState, ReactNode } from "react";

type AccordionProps = {
  title: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

const Accordion = ({ title, children, defaultOpen }: AccordionProps) => {
  const [isOpen, setIsOpen] = useState(defaultOpen || false);

  const toggleAccordion = () => {
    setIsOpen(!isOpen);
  };

  return (
    <div className="w-full border border-gray-300 bg-gray-200 rounded-lg">
      <button
        onClick={toggleAccordion}
        className={`w-full text-left p-4 bg-white hover:bg-gray-200 focus:outline-none rounded-t-lg ${
          isOpen ? "rounded-b-none" : "rounded-b-lg"
        }`}
      >
        <div className="flex justify-between items-center">
          <span className="font-semibold text-lg">{title}</span>
          <span>{isOpen ? "-" : "+"}</span>
        </div>
      </button>
      {isOpen && (
        <div className="p-4 bg-white transition-all ease-in-out duration-200 rounded-b-lg">
          {children}
        </div>
      )}
    </div>
  );
};

export default Accordion;
