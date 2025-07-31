import React from 'react';
import { Bot, X } from 'lucide-react';

const ChatBot = ({ onClose }) => {
  return (
    <div className="h-full flex flex-col">
      {/* Chat Header */}
      <div className="bg-[#00ABE4] text-white p-3 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5" />
          <span className="font-medium">Support Bot</span>
        </div>
        <button onClick={onClose} className="hover:bg-white/20 p-1 rounded">
          <X className="w-4 h-4" />
        </button>
      </div>
      
      {/* Chat Messages */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="mb-4">
          <div className="bg-gray-100 rounded-lg p-3 max-w-[80%]">
            <p className="text-sm">Hello! How can I help you today?</p>
          </div>
          <span className="text-xs text-gray-500 block mt-1">Just now</span>
        </div>
      </div>
      
      {/* Chat Input */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Type your message..."
            className="flex-1 border border-gray-300 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent text-sm"
          />
          <button className="bg-[#00ABE4] text-white p-2 rounded-full hover:bg-[#008CC4] transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.707l-3-3a1 1 0 00-1.414 1.414L10.586 9H7a1 1 0 100 2h3.586l-1.293 1.293a1 1 0 101.414 1.414l3-3a1 1 0 000-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;