// Store chat or messages
let messageHistory = [];

// Select elements
const inputField = document.getElementById("userInput");
const outputDiv = document.getElementById("output");
const sendBtn = document.getElementById("sendBtn");

// Function to update UI
function updateOutput() {
    outputDiv.innerHTML = messageHistory.map(msg => `<p><strong>${msg.sender}:</strong> ${msg.text}</p>`).join("");
    outputDiv.scrollTop = outputDiv.scrollHeight; // scroll to bottom
}

// Function to send message to backend
async function sendMessage() {
    const userMessage = inputField.value.trim();
    if (!userMessage) return;

    // Add user message to history
    messageHistory.push({ sender: "User", text: userMessage });
    updateOutput();

    // Clear input field
    inputField.value = "";

    try {
        // Send message to backend (replace /api/ask with your endpoint)
        const response = await fetch("/api/ask", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: userMessage })
        });

        const data = await response.json();
        const aiMessage = data.answer || "No response";

        // Add AI response to history and update UI
        messageHistory.push({ sender: "AI", text: aiMessage });
        updateOutput();

    } catch (error) {
        console.error("Error:", error);
        messageHistory.push({ sender: "AI", text: "Error communicating with server." });
        updateOutput();
    }
}

// Event listeners
sendBtn.addEventListener("click", sendMessage);
inputField.addEventListener("keypress", function(e) {
    if (e.key === "Enter") sendMessage(); // Send on Enter key
});
