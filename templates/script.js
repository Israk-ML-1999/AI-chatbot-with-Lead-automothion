document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatMessages = document.getElementById('chat-messages');
    const refreshBtn = document.getElementById('refresh-db-btn');
    const toast = document.getElementById('toast');

    const addMessage = (text, sender) => {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);
        msgDiv.innerHTML = `<div class="content">${text}</div>`;
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const showTypingIndicator = () => {
        const indicator = document.createElement('div');
        indicator.id = 'typing-indicator';
        indicator.classList.add('message', 'ai');
        indicator.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    const removeTypingIndicator = () => {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) indicator.remove();
    };

    const showToast = (message) => {
        toast.textContent = message;
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    };

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = userInput.value.trim();
        if (!query) return;

        addMessage(query, 'user');
        userInput.value = '';
        userInput.disabled = true;

        showTypingIndicator();

        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const data = await response.json();
            removeTypingIndicator();

            if (data.response) {
                addMessage(data.response, 'ai');
            } else {
                addMessage("Sorry, I encountered an error. Please try again.", 'ai');
            }
        } catch (error) {
            removeTypingIndicator();
            addMessage("Unable to connect to the server.", 'ai');
            console.error(error);
        } finally {
            userInput.disabled = false;
            userInput.focus();
        }
    });

    refreshBtn.addEventListener('click', async () => {
        refreshBtn.disabled = true;
        refreshBtn.classList.add('fa-spin');
        
        try {
            const response = await fetch('/api/refresh-data', { method: 'POST' });
            const data = await response.json();
            showToast(data.message || "Data refreshed!");
        } catch (error) {
            showToast("Failed to refresh data.");
        } finally {
            refreshBtn.disabled = false;
            refreshBtn.classList.remove('fa-spin');
        }
    });
});
