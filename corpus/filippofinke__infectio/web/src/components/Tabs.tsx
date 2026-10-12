import React, { ReactNode, useState, KeyboardEvent } from "react";

interface Tab {
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  initialActiveIndex?: number;
}

const Tabs: React.FC<TabsProps> = ({ tabs, initialActiveIndex = 0 }) => {
  const [activeIndex, setActiveIndex] = useState<number>(initialActiveIndex);

  const handleKeyDown = (
    event: KeyboardEvent<HTMLButtonElement>,
    index: number
  ) => {
    let newIndex = activeIndex;

    switch (event.key) {
      case "ArrowRight":
        newIndex = (activeIndex + 1) % tabs.length;
        setActiveIndex(newIndex);
        break;
      case "ArrowLeft":
        newIndex = (activeIndex - 1 + tabs.length) % tabs.length;
        setActiveIndex(newIndex);
        break;
      case "Home":
        newIndex = 0;
        setActiveIndex(newIndex);
        break;
      case "End":
        newIndex = tabs.length - 1;
        setActiveIndex(newIndex);
        break;
      default:
        break;
    }
  };

  return (
    <div className="w-full">
      <div role="tablist" className="flex mb-1">
        {tabs.length > 1 &&
          tabs.map((tab, index) => (
            <button
              key={index}
              role="tab"
              aria-selected={activeIndex === index}
              aria-controls={`tab-panel-${index}`}
              id={`tab-${index}`}
              tabIndex={activeIndex === index ? 0 : -1}
              className={`py-2 px-4 -mb-px border-b-2 font-medium text-sm focus:outline-none transition-colors duration-200 ${
                activeIndex === index
                  ? "border-blue-500 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
              }`}
              onClick={() => setActiveIndex(index)}
              onKeyDown={(e) => handleKeyDown(e, index)}
            >
              {tab.label}
            </button>
          ))}
      </div>
      {tabs.map((tab, index) => (
        <div
          key={index}
          role="tabpanel"
          id={`tab-panel-${index}`}
          aria-labelledby={`tab-${index}`}
          hidden={activeIndex !== index}
        >
          {activeIndex === index && tab.content}
        </div>
      ))}
    </div>
  );
};

export default Tabs;
