import React, { useState } from 'react';
import { Bot } from 'lucide-react';
import ChatBot from '../chat/ChatBot';

const ChatButton = () => {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setIsChatOpen(!isChatOpen)}
        className="fixed bottom-15 right-12 bg-white p-3 rounded-full shadow-lg border border-gray-200 hover:bg-gray-50 transition-colors z-50"
      >
        <Bot className="w-16 h-16 text-[#00ABE4]" />
      </button>
      
      {isChatOpen && (
        <div className="fixed bottom-15 right-6 w-90 h-110 bg-white rounded-lg shadow-xl border border-gray-200 z-50 overflow-hidden">
          <ChatBot onClose={() => setIsChatOpen(false)} />
        </div>
      )}
    </>
  );
};

export default ChatButton;