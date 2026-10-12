import React, { useState, useEffect } from "react";
import Accordion from "./Accordion";
import CodeBlock from "./CodeBlock";
import { FaRobot } from "react-icons/fa";
import { useLLM } from "@/contexts/useLLM";
import { ContentType } from "@/types/types";

type CodeAnalysisProps = {
  file: File;
  contentType: ContentType;
};

const CodeAnalysis = ({ file, contentType }: CodeAnalysisProps) => {
  const { sendMessage, setShowChat, isReady } = useLLM();
  const [code, setCode] = useState<string>("");

  const handleExplainCode = () => {
    const prompt = `Please analyze the following code:

\`\`\`
${code}
\`\`\`

- Provide a brief description of what the code does.
- Give a malicious score.`;
    sendMessage(prompt);
    setShowChat(true);
  };

  useEffect(() => {
    file.text().then((resolvedText) => {
      setCode(resolvedText);
    });
  }, [file]);

  const language = contentType.mime_type
    ? contentType.mime_type.split("/")[1].replace("x-", "")
    : "";

  return (
    <Accordion title="Code Analysis">
      <CodeBlock code={code} language={language} />
      {isReady && (
        <div className="w-full flex justify-end pt-2">
          <button
            className="bg-blue-600 rounded-full text-white flex items-center p-3"
            onClick={handleExplainCode}
          >
            Explain code
            <FaRobot size={24} className="ml-2" />
          </button>
        </div>
      )}
    </Accordion>
  );
};

export default CodeAnalysis;
