import React, { useState, useEffect, useRef } from 'react';
import { Bot, X, Loader2, Send } from 'lucide-react';
import useAuth from '../hooks/useAuth';
import chatbotService from '../services/chatbotService';

const ChatBot = ({ onClose }) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([
    { 
      text: 'Hello! I\'m your AI support assistant. How can I help you today?', 
      sender: 'bot', 
      timestamp: new Date() 
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Helper function to add messages
  const addMessage = (text, sender) => {
    setMessages(prev => [...prev, {
      text,
      sender,
      timestamp: new Date()
    }]);
  };

  // Handle predefined button clicks
  const handleQuickAction = async (action) => {
    setIsLoading(true);
    
    try {
      let response;
      
      switch (action) {
        case 'getMyTickets':
          addMessage('📋 Get my recent tickets', 'user');
          response = await handleGetMyTickets();
          break;
        case 'aiResolution':
          addMessage('🤖 AI Resolution', 'user');
          response = await handleAIResolution();
          break;
        case 'getSimilarTickets':
          addMessage('🧾 Similar tickets', 'user');
          response = await handleSimilarTickets();
          break;
        case 'getFAQ':
          addMessage('❓ Get FAQ', 'user');
          response = await handleGetFAQ();
          break;
        default:
          response = 'Unknown action requested.';
      }
      
      addMessage(response, 'bot');
    } catch (error) {
      console.error('Quick action error:', error);
      addMessage('Sorry, I encountered an error processing your request. Please try again.', 'bot');
    } finally {
      setIsLoading(false);
    }
  };

  // Get my tickets
  const handleGetMyTickets = async () => {
    try {
      const tickets = await chatbotService.getMyTickets();
      
      if (tickets && tickets.length > 0) {
        const ticketList = tickets.map(ticket => 
          `• **${ticket.ticket_id}**: ${ticket.title} (${ticket.status})`
        ).join('\n');
        
        return `Here are your recent tickets:\n\n${ticketList}\n\n💡 Would you like details about any specific ticket? Just ask!`;
      } else {
        return `You don't have any assigned tickets at the moment.\n\n📝 **You can:**\n• Create a new ticket for an issue\n• Ask me about common problems\n• Browse our FAQ for solutions\n\n💬 **What technical issue are you experiencing?**`;
      }
    } catch (error) {
      console.error('Get my tickets error:', error);
      return `I couldn't fetch your tickets right now.\n\n🔧 **Alternative options:**\n• Describe your issue and I'll help directly\n• Ask me about common solutions\n• Use the AI Resolution feature\n\n💬 **What problem can I help you solve?**`;
    }
  };

  // AI Resolution assistance
  const handleAIResolution = async () => {
    try {
      // Use the enhanced AI resolution endpoint
      const response = await chatbotService.sendChatMessage(
        'AI resolution: I need help with technical troubleshooting',
        { type: 'ai_resolution' }
      );

      return response.response || response.message || `🤖 **AI Resolution Ready!**\n\nI'm here to help solve your technical issues.\n\n📝 **Please tell me:**\n• What problem are you experiencing?\n• Any error messages you see?\n• When did it start?\n• What have you tried so far?\n\nThe more details you provide, the better I can assist you!`;
    } catch (error) {
      console.error('AI Resolution error:', error);
      return `🤖 **AI Troubleshooting Available**\n\nI can help with technical issues!\n\n🔧 **Hardware Issues:**\n• Computer won't start\n• Slow performance\n• Connectivity problems\n\n💻 **Software Issues:**\n• Application crashes\n• Login problems\n• File access issues\n\n🌐 **Network Issues:**\n• Internet connectivity\n• Email problems\n• VPN issues\n\n💬 **What technical issue can I help you resolve?**`;
    }
  };

  // Find similar tickets
  const handleSimilarTickets = async () => {
    try {
      // Use the enhanced similar tickets functionality
      const response = await chatbotService.sendChatMessage(
        'Similar tickets: Find tickets similar to my latest ticket',
        { type: 'similar_tickets' }
      );

      if (response.response || response.message) {
        return response.response || response.message;
      }

      // Fallback to the old method if the enhanced one doesn't work
      const myTickets = await chatbotService.getMyTickets();
      
      if (myTickets && myTickets.length > 0) {
        const latestTicket = myTickets[0];
        const ticketNumber = latestTicket.ticket_id;
        
        if (ticketNumber) {
          const similarTickets = await chatbotService.getSimilarTickets(ticketNumber);
          
          if (similarTickets && similarTickets.length > 0) {
            const similarList = similarTickets.map(ticket => 
              `• **${ticket.ticket_id}**: ${ticket.title} (${ticket.status})`
            ).join('\n');
            
            return `Here are tickets similar to your latest ticket (**${ticketNumber}**):\n\n${similarList}\n\n💡 These might help you find solutions or see how similar issues were resolved!`;
          } else {
            return `No similar tickets found for your latest ticket (**${ticketNumber}**).\n\n✨ **This could mean:**\n• Your issue is unique\n• It's a new type of problem\n• You're the first to report it\n\n💬 Feel free to describe your issue and I'll help you directly!`;
          }
        }
      }
      
      return `To find similar tickets, I need you to have at least one ticket.\n\n📝 **You can:**\n• Create a new ticket for your issue\n• Ask me about common problems\n• Browse our FAQ for solutions\n\n💬 **What technical issue are you experiencing?**`;
    } catch (error) {
      console.error('Similar tickets error:', error);
      return `I couldn't find similar tickets right now.\n\n🔧 **Alternative options:**\n• Describe your issue and I'll help directly\n• Check the main dashboard for ticket history\n• Ask me about common solutions\n\n💬 **What problem can I help you solve?**`;
    }
  };

  // Get FAQ information
  const handleGetFAQ = async () => {
    try {
      const response = await chatbotService.getFAQ();
      if (response.response || response.message) {
        return response.response || response.message;
      }
      
      return `❓ **Frequently Asked Questions**\n\n🔧 **Technical Issues:**\n• How do I reset my password?\n• Why is my application running slowly?\n• How do I report a bug or error?\n• What should I do if I can't log in?\n\n📋 **Ticket Management:**\n• How do I create a new support ticket?\n• How can I check my ticket status?\n• How do I escalate an urgent issue?\n• Can I update my ticket information?\n\n💬 **Support Information:**\n• What are your support hours?\n• How do I contact a technician directly?\n• How long does ticket resolution take?\n• What information should I include in tickets?\n\n🤖 **AI Assistant:**\n• How does AI troubleshooting work?\n• Can you help with hardware issues?\n• Do you provide step-by-step solutions?\n\n💡 **Type any question for specific help, or describe your technical issue for personalized assistance!**`;
    } catch (error) {
      console.error('FAQ error:', error);
      return `❓ **Help Topics Available**\n\nI can assist you with:\n\n• **Technical troubleshooting**\n• **Account and login issues**\n• **Software problems**\n• **Hardware diagnostics**\n• **Network connectivity**\n• **Performance optimization**\n\n💬 **What would you like help with today?**`;
    }
  };

  // Handle regular chat messages
  const handleChatMessage = async (message) => {
    try {
      // Check if the message contains AI resolution keywords
      const aiKeywords = ['ai resolution', 'ai help', 'ai support', 'troubleshoot', 'fix', 'problem', 'issue', 'error'];
      const hasAIKeywords = aiKeywords.some(keyword => message.toLowerCase().includes(keyword));
      
      // Check if the message contains similar tickets keywords
      const similarKeywords = ['similar tickets', 'find similar', 'like this', 'same issue'];
      const hasSimilarKeywords = similarKeywords.some(keyword => message.toLowerCase().includes(keyword));

      let enhancedMessage = message;
      
      // Add appropriate prefix for better intent detection
      if (hasAIKeywords && !message.toLowerCase().startsWith('ai resolution')) {
        enhancedMessage = `AI resolution: ${message}`;
      } else if (hasSimilarKeywords && !message.toLowerCase().startsWith('similar tickets')) {
        enhancedMessage = `Similar tickets: ${message}`;
      }

      const response = await chatbotService.sendChatMessage(enhancedMessage);
      return response.response || response.message || `I understand you're asking about "${message}". Let me help you with that. Could you provide more details about what specific assistance you need?`;
    } catch (error) {
      console.error('Chat message error:', error);
      return `I'm here to help! I had trouble processing that request, but I can still assist you.\n\n💬 **Try:**\n• Using the quick action buttons above\n• Rephrasing your question\n• Being more specific about your issue\n\n🔧 **I'm great at helping with technical problems, ticket management, and troubleshooting!**`;
    }
  };

  // Handle sending messages
  const handleSendMessage = async (text) => {
    if (!text.trim()) return;
    
    addMessage(text, 'user');
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await handleChatMessage(text);
      addMessage(response, 'bot');
    } catch (error) {
      console.error('Send message error:', error);
      addMessage('I apologize, but I encountered an error. Please try again or use the quick action buttons.', 'bot');
    } finally {
      setIsLoading(false);
    }
  };

  const handleInputSubmit = () => {
    if (!isLoading && inputValue.trim()) {
      handleSendMessage(inputValue);
    }
  };

  return (
    <div className="fixed bottom-4 right-4 w-96 h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 flex flex-col z-50">
      {/* Header */}
      <div className="bg-[#00ABE4] text-white p-4 rounded-t-lg flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6" />
          <div>
            <h3 className="font-semibold">Support Bot</h3>
            <p className="text-xs opacity-90">
              🟢 Connected
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-white hover:bg-[#88defb] hover:bg-opacity-20 p-1 rounded"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Quick Action Buttons */}
      <div className="p-3 border-b border-gray-200 bg-gray-50">
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => !isLoading && handleQuickAction('getMyTickets')}
            disabled={isLoading}
            className="bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-700 text-xs font-medium px-3 py-2 rounded-lg text-left disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <span>📋</span>
            <span>Get my recent tickets</span>
          </button>
          
          <button
            onClick={() => !isLoading && handleQuickAction('aiResolution')}
            disabled={isLoading}
            className="bg-green-50 hover:bg-green-100 border border-green-200 text-green-700 text-xs font-medium px-3 py-2 rounded-lg text-left disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <span>🤖</span>
            <span>AI Resolution</span>
          </button>
          
          <button
            onClick={() => !isLoading && handleQuickAction('getSimilarTickets')}
            disabled={isLoading}
            className="bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-700 text-xs font-medium px-3 py-2 rounded-lg text-left disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <span>🧾</span>
            <span>Similar tickets</span>
          </button>
          
          <button
            onClick={() => !isLoading && handleQuickAction('getFAQ')}
            disabled={isLoading}
            className="bg-orange-50 hover:bg-orange-100 border border-orange-200 text-orange-700 text-xs font-medium px-3 py-2 rounded-lg text-left disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
          >
            <span>❓</span>
            <span>Get FAQ</span>
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`rounded-lg px-4 py-2 text-sm max-w-[85%] ${
                msg.sender === 'user'
                  ? 'bg-[#00ABE4] text-white'
                  : 'bg-gray-100 text-gray-800'
              }`}
            >
              <pre className="whitespace-pre-wrap font-sans">{msg.text}</pre>
              <div className="text-xs opacity-70 mt-1">
                {msg.timestamp?.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 rounded-lg px-4 py-2 text-sm max-w-[85%] flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-3">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Type your message..."
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !isLoading && handleInputSubmit()}
            disabled={isLoading}
            className="flex-1 border border-gray-300 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#00ABE4] focus:border-transparent text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
          <button
            onClick={handleInputSubmit}
            disabled={isLoading || !inputValue.trim()}
            className="bg-[#00ABE4] text-white p-2 rounded-full hover:bg-[#008CC4] transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatBot;
