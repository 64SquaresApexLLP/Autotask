import React, { useState } from 'react';
import { Bot, X } from 'lucide-react';

const predefinedMessages = [
  { text: '📋 Get my recent tickets', key: 'recent' },
  { text: '🤖 AI Resolution', key: 'ai' },
  { text: '🧾 Similar tickets', key: 'similar' },
  { text: '❓ Get FAQ', key: 'faq' }
];

const ChatBot = ({ onClose }) => {
  const [messages, setMessages] = useState([
    { text: 'Hello! How can I help you today?', sender: 'bot' }
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = (text) => {
    if (!text.trim()) return;
    const newMessage = { text, sender: 'user' };
    setMessages((prev) => [...prev, newMessage]);

    // Simulated bot response (replace with API later)
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { text: `You clicked "${text}"`, sender: 'bot' }
      ]);
    }, 500);
  };

  const handleInputSubmit = () => {
    handleSendMessage(inputValue);
    setInputValue('');
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="bg-[#00ABE4] text-white p-3 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5" />
          <span className="font-medium">Support Bot</span>
        </div>
        <button onClick={onClose} className="hover:bg-white/20 p-1 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {/* Predefined Buttons */}
        <div className="grid grid-cols-2 gap-2">
          {predefinedMessages.map((msg) => (
            <button
              key={msg.key}
              onClick={() => handleSendMessage(msg.text)}
              className="bg-[#E9F1FA] hover:bg-[#D6EBF8] border border-[#00ABE4] text-sm text-[#00ABE4] font-medium px-3 py-2 rounded-lg text-left"
            >
              {msg.text}
            </button>
          ))}
        </div>

        {/* Chat history */}
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`rounded-lg px-4 py-2 text-sm max-w-[80%] ${
                msg.sender === 'user'
                  ? 'bg-[#00ABE4] text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleInputSubmit()}
            className="flex-1 border border-gray-300 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent text-sm"
          />
          <button
            onClick={handleInputSubmit}
            className="bg-[#00ABE4] text-white p-2 rounded-full hover:bg-[#008CC4] transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;
