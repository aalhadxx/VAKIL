// chat.js
export class ChatUI {
    constructor() {
        this.messagesContainer = document.getElementById('messages');
        this.userInput = document.getElementById('user-input');
        this.sendButton = document.getElementById('send-button');
        this.statusIndicator = document.getElementById('status-indicator');
        this.suggestionsContainer = document.createElement('div');
        this.suggestionsContainer.className = 'suggestions-container mt-2 space-x-2';
        
        // Add suggestions container after messages
        this.messagesContainer.parentNode.insertBefore(
            this.suggestionsContainer,
            this.messagesContainer.nextSibling
        );
        
        this.initializeEventListeners();
        this.userInput.focus();
    }

    initializeEventListeners() {
        this.sendButton.addEventListener('click', () => this.sendMessage());
        this.userInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.sendMessage();
        });

        // Add input event listener for typing assistance
        this.userInput.addEventListener('input', () => this.handleInputChange());
    }

    handleInputChange() {
        // Clear previous timeout
        if (this.typingTimeout) {
            clearTimeout(this.typingTimeout);
        }

        // Set new timeout for typing assistance
        this.typingTimeout = setTimeout(() => {
            const input = this.userInput.value.trim();
            if (input.length >= 3) {
                // Could implement real-time suggestions here
                this.showTypingAssistance(input);
            }
        }, 500);
    }

    showTypingAssistance(input) {
        // Example of simple typing assistance
        if (input.toLowerCase().includes('section')) {
            this.showSuggestions(['Which section?', 'Would you like to know about a specific IPC section?']);
        }
    }

    appendMessage(content, isUser, options = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'flex items-start space-x-3 message-animate opacity-0';
        
        const iconDiv = document.createElement('div');
        iconDiv.className = 'flex-shrink-0';
        
        const avatarDiv = document.createElement('div');
        avatarDiv.className = `h-10 w-10 rounded-full ${isUser ? 'bg-gray-100' : 'bg-blue-100'} flex items-center justify-center`;
        
        const icon = `
            <svg class="w-6 h-6 ${isUser ? 'text-gray-600' : 'text-blue-600'}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                ${isUser ? 
                    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>' :
                    '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"/>'
                }
            </svg>`;
        
        avatarDiv.innerHTML = icon;
        iconDiv.appendChild(avatarDiv);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = `rounded-lg p-4 max-w-3xl ${isUser ? 'bg-gray-50' : 'bg-blue-50'}`;
        
        if (!isUser && options.typing) {
            // Show typing indicator
            contentDiv.innerHTML = this.createTypingIndicator();
            messageDiv.classList.add('typing-message');
        } else {
            contentDiv.innerHTML = this.formatMessage(content);
        }
        
        messageDiv.appendChild(iconDiv);
        messageDiv.appendChild(contentDiv);
        this.messagesContainer.appendChild(messageDiv);
        
        // Animate message appearance
        requestAnimationFrame(() => {
            messageDiv.classList.add('opacity-100', 'transition-opacity', 'duration-300');
        });
        
        this.scrollToBottom();
        return messageDiv;
    }

    createTypingIndicator() {
        return `
            <div class="flex items-center space-x-2">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
    }

    showSuggestions(suggestions) {
    this.suggestionsContainer.innerHTML = '';
    
    // Create a flex container for suggestions
    const flexContainer = document.createElement('div');
    flexContainer.className = 'flex flex-wrap gap-2 mt-3 mb-4 px-4';
    
    suggestions.forEach(suggestion => {
        const button = document.createElement('button');
        button.className = 'suggestion-pill px-4 py-2 bg-blue-50 text-blue-600 rounded-full text-sm ' +
                          'hover:bg-blue-100 transition-colors duration-200 border border-blue-200 ' +
                          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 ' +
                          'whitespace-nowrap';
        button.textContent = suggestion;
        
        // Add click handler
        button.addEventListener('click', () => {
            this.userInput.value = suggestion;
            this.sendMessage();
        });
        
        // Add hover effect
        button.addEventListener('mouseenter', () => {
            button.classList.add('transform', 'scale-105');
        });
        
        button.addEventListener('mouseleave', () => {
            button.classList.remove('transform', 'scale-105');
        });
        
        flexContainer.appendChild(button);
    });
    
    this.suggestionsContainer.appendChild(flexContainer);
}

    formatMessage(content) {
        if (!content.includes('\n')) return content;
        
        return content.split('\n').map(line => {
            const trimmedLine = line.trim();
            if (/^\d+\./.test(trimmedLine)) {
                return `<p class="mt-2">${trimmedLine}</p>`;
            }
            if (trimmedLine.startsWith('•') || trimmedLine.startsWith('-')) {
                return `<p class="mt-2 ml-4">${trimmedLine}</p>`;
            }
            return `<p class="mt-2">${trimmedLine}</p>`;
        }).join('');
    }

    updateStatus(isOnline) {
        const indicator = this.statusIndicator.querySelector('span:first-child');
        const text = this.statusIndicator.querySelector('span:last-child');
        indicator.className = `h-3 w-3 ${isOnline ? 'bg-green-500' : 'bg-red-500'} rounded-full`;
        text.textContent = isOnline ? 'Ready' : 'Thinking...';
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message) return;

        this.userInput.disabled = true;
        this.sendButton.disabled = true;
        this.updateStatus(false);

        // Clear suggestions when sending a message
        this.suggestionsContainer.innerHTML = '';

        this.appendMessage(message, true);
        this.userInput.value = '';

        // Show typing indicator
        const typingMessage = this.appendMessage('', false, { typing: true });

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_input: message })
            });

            const data = await response.json();
            
            // Remove typing indicator
            typingMessage.remove();

            // Add response with natural delay
            const typingDuration = data.typing_duration || 1000;
            await new Promise(resolve => setTimeout(resolve, typingDuration));
            
            this.appendMessage(data.response, false);

            // Show suggestions if available
            if (data.suggestions && data.suggestions.length > 0) {
                this.showSuggestions(data.suggestions);
            }

        } catch (error) {
            typingMessage.remove();
            this.appendMessage('Sorry, I encountered an error. Please try again.', false);
        } finally {
            this.userInput.disabled = false;
            this.sendButton.disabled = false;
            this.updateStatus(true);
            this.userInput.focus();
        }
    }
}

