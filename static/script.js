const processButton = document.getElementById("process-btn");
const askButton = document.getElementById("ask-btn");

const urlInput = document.getElementById("youtube-url");
const questionInput = document.getElementById("question");

const status = document.getElementById("status");
const videoContainer = document.getElementById("video-container");
const chatMessages = document.getElementById("chat-messages");


processButton.addEventListener("click", async () => {

    const url = urlInput.value.trim();

    if (!url) {
        status.textContent = "Please enter a YouTube URL.";
        return;
    }

    status.textContent = "Processing video...";

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/process-video",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    url: url
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        status.textContent = data.message;

        // Display YouTube video
        videoContainer.innerHTML = `
            <iframe
                width="100%"
                height="400"
                src="https://www.youtube.com/embed/${data.video_id}"
                frameborder="0"
                allowfullscreen>
            </iframe>
        `;

    } catch (error) {

        status.textContent = "Error: " + error.message;
    }
});


askButton.addEventListener("click", askQuestion);


questionInput.addEventListener("keydown", (event) => {

    if (event.key === "Enter") {
        askQuestion();
    }

});


async function askQuestion() {

    const question = questionInput.value.trim();

    if (!question) {
        return;
    }

    addMessage("user", question);

    questionInput.value = "";

    addMessage("assistant", "Thinking...");

    try {

        const response = await fetch(
            "http://127.0.0.1:5000/ask",
            {
                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    question: question
                })
            }
        );

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error);
        }

        // Replace "Thinking..."
        chatMessages.lastElementChild.remove();

        addMessage("assistant", data.answer);

    } catch (error) {

        chatMessages.lastElementChild.remove();

        addMessage(
            "assistant",
            "Error: " + error.message
        );
    }
}


function addMessage(role, message) {

    const div = document.createElement("div");

    div.className = `message ${role}`;

    div.textContent = message;

    chatMessages.appendChild(div);

    chatMessages.scrollTop = chatMessages.scrollHeight;
}