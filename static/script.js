(function () {
    // ---- point this at your Flask backend ----
    const API_BASE = "http://127.0.0.1:5000";
    document.getElementById('apiBaseLabel').textContent = API_BASE;

    const urlInput = document.getElementById('urlInput');
    const loadBtn = document.getElementById('loadBtn');
    const statusLine = document.getElementById('statusLine');
    const statusText = document.getElementById('statusText');
    const loadError = document.getElementById('loadError');

    const playerWrap = document.getElementById('playerWrap');
    const videoMeta = document.getElementById('videoMeta');
    const videoThumb = document.getElementById('videoThumb');
    const videoTitle = document.getElementById('videoTitle');
    const videoChannel = document.getElementById('videoChannel');
    const videoDuration = document.getElementById('videoDuration');
    const videoLink = document.getElementById('videoLink');
    const statChunks = document.getElementById('statChunks');

    const stageTitle = document.getElementById('stageTitle');
    const stageSubtitle = document.getElementById('stageSubtitle');
    const chatScroll = document.getElementById('chatScroll');
    const emptyState = document.getElementById('emptyState');
    const composerForm = document.getElementById('composerForm');
    const questionInput = document.getElementById('questionInput');
    const sendBtn = document.getElementById('sendBtn');
    const clearBtn = document.getElementById('clearBtn');
    const marquee = document.getElementById('marquee');
    const jumpLatestBtn = document.getElementById('jumpLatestBtn');

    let videoLoaded = false;
    let busy = false;
    let sidebarCollapsed = false;

    // ---- Jump-to-latest button ----
    chatScroll.addEventListener('scroll', () => {
        const distFromBottom = chatScroll.scrollHeight - chatScroll.scrollTop - chatScroll.clientHeight;
        if (distFromBottom > 100) {
            jumpLatestBtn.classList.add('is-visible');
        } else {
            jumpLatestBtn.classList.remove('is-visible');
        }
    });

    jumpLatestBtn.addEventListener('click', () => {
        chatScroll.scrollTo({ top: chatScroll.scrollHeight, behavior: 'smooth' });
    });

    // ---- Sidebar toggle ----
    const consoleEl = document.getElementById('console');
    const consoleToggle = document.getElementById('consoleToggle');
    const showSidebarBtn = document.getElementById('showSidebarBtn');

    function collapseSidebar() {
        sidebarCollapsed = true;
        consoleEl.classList.add('is-collapsed');
        consoleToggle.setAttribute('title', 'Show sidebar');
        consoleToggle.setAttribute('aria-label', 'Show sidebar');
        if (showSidebarBtn) showSidebarBtn.style.display = '';
    }

    function expandSidebar() {
        sidebarCollapsed = false;
        consoleEl.classList.remove('is-collapsed');
        consoleToggle.setAttribute('title', 'Hide sidebar');
        consoleToggle.setAttribute('aria-label', 'Hide sidebar');
        if (showSidebarBtn) showSidebarBtn.style.display = 'none';
    }

    consoleToggle.addEventListener('click', () => {
        if (sidebarCollapsed) expandSidebar();
        else collapseSidebar();
    });

    if (showSidebarBtn) {
        showSidebarBtn.addEventListener('click', () => expandSidebar());
    }

    // ---- Theme toggle ----
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeToggleLabel = document.getElementById('themeToggleLabel');
    const sunIcon = themeToggleBtn ? themeToggleBtn.querySelector('.sun-icon') : null;
    const moonIcon = themeToggleBtn ? themeToggleBtn.querySelector('.moon-icon') : null;

    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (theme === 'light') {
            if (themeToggleLabel) themeToggleLabel.textContent = 'Dark mode';
            if (sunIcon) sunIcon.style.display = 'none';
            if (moonIcon) moonIcon.style.display = '';
        } else {
            if (themeToggleLabel) themeToggleLabel.textContent = 'Light mode';
            if (sunIcon) sunIcon.style.display = '';
            if (moonIcon) moonIcon.style.display = 'none';
        }
    }

    const savedTheme = localStorage.getItem('theme') || (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    setTheme(savedTheme);

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
            setTheme(currentTheme === 'light' ? 'dark' : 'light');
        });
    }

    // one-time marquee chase on load
    requestAnimationFrame(() => {
        marquee.classList.add('animate');
        [...marquee.children].forEach((dot, i) => {
            dot.style.animationDelay = (i * 0.06) + 's';
        });
    });

    function extractVideoId(url) {
        const pattern = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|live\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
        const match = url.match(pattern);
        return match ? match[1] : null;
    }

    function escapeHtml(str) {
        const d = document.createElement('div');
        d.textContent = str;
        return d.innerHTML;
    }

    function formatAnswerWithTimestamps(text) {
        let safeText = escapeHtml(text);

        // Preserve basic markdown bold formatting & line breaks
        safeText = safeText.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        safeText = safeText.replace(/\n/g, '<br>');

        /*
         * Match single timestamps and time ranges such as:
         * (05:50)
         * (9:15)
         * (1:02:15)
         * (05:50 - 06:15)
         * (5:50 - 6:15)
         */
        const timestampRegex = /\((?:(?:\d{1,2}:)?\d{1,2}:\d{1,2})(?:\s*-\s*(?:(?:\d{1,2}:)?\d{1,2}:\d{1,2}))?\)/g;

        safeText = safeText.replace(timestampRegex, match => {
            const rawInside = match.slice(1, -1).trim();
            const firstTimestamp = rawInside.split('-')[0].trim();
            const seconds = timestampToSeconds(firstTimestamp);

            return `
                <button
                    type="button"
                    class="inline-timestamp"
                    data-seconds="${seconds}"
                    title="Jump to ${firstTimestamp}"
                >
                    (${rawInside})
                </button>
            `;
        });

        return safeText;
    }

    function timestampToSeconds(timestamp) {
        const parts = timestamp.split(':').map(Number);

        if (parts.length === 2) {
            const [minutes, seconds] = parts;
            return (minutes * 60) + seconds;
        }

        if (parts.length === 3) {
            const [hours, minutes, seconds] = parts;
            return (hours * 3600) + (minutes * 60) + seconds;
        }

        return 0;
    }

    document.addEventListener('click', event => {
        const timestamp = event.target.closest('.inline-timestamp');

        if (!timestamp) return;

        const seconds = Number(timestamp.dataset.seconds);

        seekYouTubeVideo(seconds);
    });

    function seekYouTubeVideo(seconds) {
        const iframe = document.querySelector('.player-wrap iframe');

        if (!iframe) {
            console.warn('YouTube player not found.');
            return;
        }

        iframe.contentWindow.postMessage(
            JSON.stringify({
                event: 'command',
                func: 'seekTo',
                args: [seconds, true]
            }),
            'https://www.youtube.com'
        );

        iframe.contentWindow.postMessage(
            JSON.stringify({
                event: 'command',
                func: 'playVideo'
            }),
            'https://www.youtube.com'
        );
    }

    const PROGRESS_STEPS = [
        "Pulling the transcript…",
        "Splitting it into chunks…",
        "Building the embedding index…"
    ];

    function startProgress() {
        statusLine.classList.add('is-visible');
        let i = 0;
        statusText.textContent = PROGRESS_STEPS[0];
        const id = setInterval(() => {
            i = (i + 1) % PROGRESS_STEPS.length;
            statusText.textContent = PROGRESS_STEPS[i];
        }, 1200);
        return () => { clearInterval(id); statusLine.classList.remove('is-visible'); };
    }

    function formatSecondsToMMSS(seconds) {
        if (!seconds || isNaN(seconds) || seconds <= 0) return '';
        const totalSec = Math.floor(seconds);
        const hrs = Math.floor(totalSec / 3600);
        const mins = Math.floor((totalSec % 3600) / 60);
        const secs = totalSec % 60;
        if (hrs > 0) {
            return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        }
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function loadYTPlayerApi() {
        if (window.YT && window.YT.Player) return;
        if (!document.getElementById('yt-iframe-api')) {
            const tag = document.createElement('script');
            tag.id = 'yt-iframe-api';
            tag.src = "https://www.youtube.com/iframe_api";
            const firstScriptTag = document.getElementsByTagName('script')[0];
            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        }
    }

    function setDurationBadge(seconds) {
        const formatted = formatSecondsToMMSS(seconds);
        if (formatted && videoDuration) {
            videoDuration.textContent = formatted;
            videoDuration.style.display = 'inline-block';
        }
    }

    function fetchVideoDuration(videoId) {
        loadYTPlayerApi();

        if (videoDuration) {
            videoDuration.style.display = 'none';
            videoDuration.textContent = '';
        }

        let attempts = 0;
        const maxAttempts = 30;

        function checkPlayer() {
            if (window.YT && window.YT.Player) {
                try {
                    const ytPlayer = new YT.Player('youtube-player', {
                        events: {
                            'onReady': (event) => {
                                const dur = event.target.getDuration();
                                if (dur > 0) setDurationBadge(dur);
                            },
                            'onStateChange': (event) => {
                                const dur = event.target.getDuration();
                                if (dur > 0) setDurationBadge(dur);
                            }
                        }
                    });

                    const pollId = setInterval(() => {
                        if (ytPlayer && typeof ytPlayer.getDuration === 'function') {
                            const dur = ytPlayer.getDuration();
                            if (dur > 0) {
                                setDurationBadge(dur);
                                clearInterval(pollId);
                            }
                        }
                    }, 300);
                    setTimeout(() => clearInterval(pollId), 8000);
                } catch (e) {
                    console.warn("Could not bind YT.Player for duration", e);
                }
            } else if (attempts < maxAttempts) {
                attempts++;
                setTimeout(checkPlayer, 200);
            }
        }

        checkPlayer();
    }

    async function fetchOEmbed(url) {
        try {
            const res = await fetch(`https://www.youtube.com/oembed?url=${encodeURIComponent(url)}&format=json`);
            if (!res.ok) return null;
            return await res.json();
        } catch (e) {
            return null;
        }
    }

    async function loadVideo() {
        if (busy) return;
        const raw = urlInput.value.trim();
        loadError.classList.remove('is-visible');

        if (!raw) {
            loadError.textContent = "Paste a YouTube link first.";
            loadError.classList.add('is-visible');
            return;
        }
        const videoId = extractVideoId(raw);
        if (!videoId) {
            loadError.textContent = "That doesn't look like a valid YouTube link.";
            loadError.classList.add('is-visible');
            return;
        }

        busy = true;
        loadBtn.disabled = true;
        const stopProgress = startProgress();

        let oembed = null;
        let apiResult = null;
        try {
            const [oembedResult, processResponse] = await Promise.all([
                fetchOEmbed(raw),
                fetch(`${API_BASE}/process-video`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: raw })
                })
            ]);
            oembed = oembedResult;
            const data = await processResponse.json().catch(() => ({}));
            if (!processResponse.ok) throw new Error(data.error || `Request failed (${processResponse.status})`);
            apiResult = data;
        } catch (err) {
            stopProgress();
            busy = false;
            loadBtn.disabled = false;
            showLoadError(err);
            return;
        }

        stopProgress();
        busy = false;
        loadBtn.disabled = false;

        // video player
        playerWrap.innerHTML = `
            <iframe
                id="youtube-player"
                src="https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${encodeURIComponent(window.location.origin)}"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowfullscreen
                title="video player">
            </iframe>
        `;

        // metadata (title, thumbnail, channel, duration)
        const thumbUrl = (oembed && oembed.thumbnail_url)
            ? oembed.thumbnail_url
            : `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;

        if (videoThumb) {
            videoThumb.src = thumbUrl;
            videoThumb.onerror = () => {
                videoThumb.src = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
            };
        }

        const titleText = (oembed && oembed.title) ? oembed.title : `YouTube Video (${videoId})`;
        const channelText = (oembed && oembed.author_name) ? oembed.author_name : 'YouTube';

        if (videoTitle) videoTitle.textContent = titleText;
        if (videoChannel) videoChannel.textContent = channelText;
        if (videoMeta) videoMeta.style.display = 'block';

        stageTitle.textContent = titleText;
        stageSubtitle.textContent = `Ask anything about what's actually said in this video.`;
        videoLink.href = `https://www.youtube.com/watch?v=${videoId}`;

        // Fetch duration via frontend YouTube Player API
        fetchVideoDuration(videoId);

        if (apiResult && typeof apiResult.chunks !== 'undefined') {
            statChunks.textContent = apiResult.chunks;
            statChunks.classList.remove('is-empty');
        }

        if (apiResult && apiResult.suggested_questions && apiResult.suggested_questions.length > 0) {
            currentSuggestedQuestions = apiResult.suggested_questions;
        } else {
            currentSuggestedQuestions = DEFAULT_SUGGESTIONS;
        }

        videoLoaded = true;
        questionInput.disabled = false;
        sendBtn.disabled = false;
        questionInput.placeholder = "Ask a question about the video…";

        renderEmptyChatWithChips(currentSuggestedQuestions);
    }

    function showLoadError(err) {
        loadError.innerHTML = `Couldn't process that video.<code>${escapeHtml(err.message || String(err))}</code>`;
        loadError.classList.add('is-visible');
    }

    loadBtn.addEventListener('click', loadVideo);
    urlInput.addEventListener('keydown', e => { if (e.key === 'Enter') loadVideo(); });

    const DEFAULT_SUGGESTIONS = [
        "Summarize this video in a few sentences",
        "What are the key takeaways of this video?",
        "What is the main argument presented in this video?",
        "What key topics and insights are covered here?"
    ];
    let currentSuggestedQuestions = DEFAULT_SUGGESTIONS;

    function renderEmptyChatWithChips(questions = currentSuggestedQuestions) {
        chatScroll.innerHTML = '';
        const wrap = document.createElement('div');
        wrap.className = 'empty-state';
        wrap.innerHTML = `
      <div class="empty-state__mark"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div>
      <h2>Ready when you are</h2>
      <p>The transcript is indexed. Ask a specific question, or try one of these suggestions:</p>
      <div class="chips">
        ${questions.map(s => `<button type="button" class="chip">${escapeHtml(s)}</button>`).join('')}
      </div>
    `;
        chatScroll.appendChild(wrap);
        wrap.querySelectorAll('.chip').forEach(chip => {
            chip.addEventListener('click', () => {
                questionInput.value = chip.textContent;
                composerForm.requestSubmit();
            });
        });
    }

    function clearEmptyState() {
        const es = chatScroll.querySelector('.empty-state');
        if (es) es.remove();
    }

    function addUserMessage(text) {
        clearEmptyState();
        const el = document.createElement('div');
        el.className = 'msg msg--user';
        el.innerHTML = `
      <div class="msg__avatar"><svg viewBox="0 0 24 24"><path d="M12 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zm0 2c-4.4 0-8 2.2-8 5v2h16v-2c0-2.8-3.6-5-8-5z"/></svg></div>
      <div class="msg__bubble"></div>
    `;
        el.querySelector('.msg__bubble').textContent = text;
        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    function addThinking() {
        clearEmptyState();
        const el = document.createElement('div');
        el.className = 'msg msg--assistant thinking';
        el.id = 'thinkingMsg';
        el.innerHTML = `
      <div class="msg__avatar"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div>
      <div class="msg__bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span></div>
    `;
        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    function removeThinking() {
        const el = document.getElementById('thinkingMsg');
        if (el) el.remove();
    }

    function addAssistantMessage(text, { sources = null, followupQuestions = null, isError = false } = {}) {
        const el = document.createElement('div');
        el.className = 'msg msg--assistant' + (isError ? ' is-error' : '');

        el.innerHTML = `
            <div class="msg__avatar">
                <svg viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z"/>
                </svg>
            </div>

            <div class="msg__body">
                <div class="msg__bubble">
                    <p class="assistant-answer"></p>
                </div>
                ${isError ? '' : `
                <div class="msg__actions">
                    <button type="button" class="copy-btn" title="Copy answer" aria-label="Copy answer">
                        <svg viewBox="0 0 24 24" class="copy-icon">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                        <svg viewBox="0 0 24 24" class="check-icon" style="display:none">
                            <polyline points="20 6 9 17 4 12"></polyline>
                        </svg>
                        <span class="copy-btn__label">Copy</span>
                    </button>
                </div>`}
            </div>
        `;

        const answerElement = el.querySelector('.assistant-answer');

        if (isError) {
            answerElement.textContent = text;
        } else {
            answerElement.innerHTML = formatAnswerWithTimestamps(text);

            // Wire up copy button
            const copyBtn = el.querySelector('.copy-btn');
            const copyIcon = el.querySelector('.copy-icon');
            const checkIcon = el.querySelector('.check-icon');
            const copyLabel = el.querySelector('.copy-btn__label');
            copyBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(text).then(() => {
                    copyIcon.style.display = 'none';
                    checkIcon.style.display = '';
                    copyLabel.textContent = 'Copied!';
                    copyBtn.classList.add('is-copied');
                    setTimeout(() => {
                        copyIcon.style.display = '';
                        checkIcon.style.display = 'none';
                        copyLabel.textContent = 'Copy';
                        copyBtn.classList.remove('is-copied');
                    }, 2000);
                });
            });

            if (followupQuestions && followupQuestions.length > 0) {
                const msgBody = el.querySelector('.msg__body');
                const followupsEl = document.createElement('div');
                followupsEl.className = 'msg__followups';
                followupsEl.innerHTML = `
                    <span class="msg__followups-label">Suggested follow-ups</span>
                    <div class="chips chips--inline">
                        ${followupQuestions.map(q => `<button type="button" class="chip chip--followup">${escapeHtml(q)}</button>`).join('')}
                    </div>
                `;
                msgBody.appendChild(followupsEl);

                followupsEl.querySelectorAll('.chip--followup').forEach(chip => {
                    chip.addEventListener('click', () => {
                        questionInput.value = chip.textContent;
                        composerForm.requestSubmit();
                    });
                });
            }
        }

        chatScroll.appendChild(el);
        chatScroll.scrollTop = chatScroll.scrollHeight;
    }

    composerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!videoLoaded || busy) return;
        const question = questionInput.value.trim();
        if (!question) return;

        addUserMessage(question);
        questionInput.value = '';
        questionInput.disabled = true;
        sendBtn.disabled = true;
        addThinking();

        try {
            const res = await fetch(`${API_BASE}/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question })
            });
            const data = await res.json().catch(() => ({}));
            removeThinking();
            if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
            addAssistantMessage(data.answer, {
                sources: data.sources,
                followupQuestions: data.followup_questions || []
            });
        } catch (err) {
            removeThinking();
            addAssistantMessage(`Sorry, something went wrong: ${err.message || err}`, { isError: true });
        } finally {
            questionInput.disabled = false;
            sendBtn.disabled = false;
            questionInput.focus();
        }
    });

    clearBtn.addEventListener('click', () => {
        if (videoLoaded) {
            renderEmptyChatWithChips();
        } else {
            chatScroll.innerHTML = '';
            chatScroll.innerHTML = `
        <div class="empty-state">
          <div class="empty-state__mark"><svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg></div>
          <h2>No video queued yet</h2>
          <p>Paste a link into the console on the left and load it — once it's indexed, ask anything about what's actually said in it.</p>
        </div>
      `;
        }
    });

// ===============================
// AI RESPONSE LOADING INDICATOR
// ===============================
let activeRequests = 0;

function showLoadingIndicator() {
    let loader = document.getElementById("ai-loading-indicator");

    if (!loader) {
        loader = document.createElement("div");
        loader.id = "ai-loading-indicator";

        loader.innerHTML = `
            <div class="ai-loader-spinner"></div>
            <span>Thinking...</span>
        `;

        document.body.appendChild(loader);

        const style = document.createElement("style");

        style.textContent = `
            #ai-loading-indicator {
                position: fixed;
                bottom: 25px;
                left: 50%;
                transform: translateX(-50%);
                display: flex;
                align-items: center;
                gap: 10px;
                padding: 10px 18px;
                background: rgba(25, 25, 25, 0.95);
                color: white;
                border-radius: 20px;
                font-size: 14px;
                z-index: 9999;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
            }

            .ai-loader-spinner {
                width: 14px;
                height: 14px;
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-top-color: white;
                border-radius: 50%;
                animation: ai-loader-spin 0.8s linear infinite;
            }

            @keyframes ai-loader-spin {
                to {
                    transform: rotate(360deg);
                }
            }
        `;

        document.head.appendChild(style);
    }

    loader.style.display = "flex";
}

function hideLoadingIndicator() {
    const loader = document.getElementById("ai-loading-indicator");

    if (loader) {
        loader.style.display = "none";
    }
}

// Intercept frontend API requests
const originalFetch = window.fetch;

window.fetch = async function (...args) {
    activeRequests++;

    showLoadingIndicator();

    try {
        return await originalFetch.apply(this, args);
    } finally {
        activeRequests--;

        if (activeRequests === 0) {
            hideLoadingIndicator();
        }
    }
};
})();