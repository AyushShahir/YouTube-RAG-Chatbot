# 🎥 YouTube RAG Chatbot

An AI-powered YouTube video assistant that allows users to interact with YouTube videos using **Retrieval-Augmented Generation (RAG)**.

Simply paste a YouTube video URL, process the video, and ask questions about its content. The chatbot retrieves relevant information from the video's transcript and uses **Google Gemini** to generate grounded answers.

The application also maintains conversation memory and provides **timestamp references** alongside relevant information so users can jump back to the corresponding part of the video.

---

## ✨ Features

### 🎥 YouTube Video Processing

- Paste a YouTube video URL
- Automatically extract the video ID
- Retrieve the video's transcript
- Preserve transcript timing information
- Process and index the transcript for question answering

### 🧠 Retrieval-Augmented Generation

The application follows a RAG pipeline:

1. Transcript extraction
2. Text chunking
3. Embedding generation
4. Vector storage
5. Semantic retrieval
6. Context injection
7. Gemini-powered answer generation

This allows the chatbot to answer questions based on the actual content of the video rather than relying only on the LLM's general knowledge.

### 💬 Conversational Memory

The chatbot supports multi-turn conversations.

For example:

> User: What does the speaker say about AI safety?

> Assistant: The speaker discusses...

> User: Why is that important?

The second question can use the previous conversation to understand what "that" refers to while still grounding the factual answer in the video transcript.

**Memory type:** In-memory conversation history.

The conversation memory is automatically cleared when a new video is processed.

### ⏱️ Timestamp-Aware Answers

Relevant answers can contain timestamps connected to the corresponding part of the video.

For example:

> AI systems can perform extremely well on complex tasks but still make basic mistakes. **[05:50]**

Clicking the timestamp can take the user to the relevant point in the YouTube video.

This makes the answers easier to verify against the original video.

### 🔎 Semantic Retrieval

The project uses vector embeddings to find transcript chunks that are semantically related to the user's question.

This means the user does not have to use the exact words spoken in the video.

For example:

> "What are the problems with current AI systems?"

can retrieve transcript content discussing limitations or inconsistencies of AI systems.

### 🤖 Google Gemini

Google Gemini is used as the language model for generating the final answer.

<img width="959" height="431" alt="Screenshot 2026-09-06 215612" src="https://github.com/user-attachments/assets/120c730c-5576-4362-a18e-effb24cca6a8" />


Current model:

```text
gemini-2.5-flash

## ✨ Recent Updates

- Added a **Copy Answer** button for AI responses.
- Added a **Jump to Latest** button for easier chat navigation.
- Added clickable **video timestamps** beside relevant answers.
- Added **conversation memory** for better contextual responses.

