// Transcribe Studio - Frontend Logic
document.addEventListener("DOMContentLoaded", () => {
    // Estado da aplicação
    const state = {
        mode: "local", // "local" | "cloud"
        files: [], // Array de { id, file, status, result, error, audioUrl }
        history: [], // Transcrições salvas no disco
        activeItem: null, // Item atualmente exibido (da fila ou do histórico)
        activeTab: "queue", // "queue" | "history"
        isProcessing: false,
        providers: [],
        localEngines: [],
        localModels: [],
        languages: [],
        searchQuery: "",
        showRomanized: false
    };

    const API_BASE = "";

    // Elementos DOM
    const tabLocal = document.getElementById("tab-local");
    const tabCloud = document.getElementById("tab-cloud");
    const localSettings = document.getElementById("local-settings");
    const cloudSettings = document.getElementById("cloud-settings");
    const hardwareBadge = document.getElementById("hardware-badge");
    const hardwareText = document.getElementById("hardware-text");
    const remoteBtn = document.getElementById("remote-btn");

    // Modal de Acesso Remoto
    const remoteModal = document.getElementById("remote-modal");
    const remoteModalClose = document.getElementById("remote-modal-close");
    const tabRemoteInternet = document.getElementById("tab-remote-internet");
    const tabRemoteLan = document.getElementById("tab-remote-lan");
    const remoteContentInternet = document.getElementById("remote-content-internet");
    const remoteContentLan = document.getElementById("remote-content-lan");
    const tunnelActiveBox = document.getElementById("tunnel-active-box");
    const tunnelInactiveBox = document.getElementById("tunnel-inactive-box");
    const tunnelUrlInput = document.getElementById("tunnel-url-input");
    const lanUrlInput = document.getElementById("lan-url-input");
    const copyTunnelLinkBtn = document.getElementById("copy-tunnel-link-btn");
    const copyLanLinkBtn = document.getElementById("copy-lan-link-btn");
    const pinDisplayBox = document.getElementById("pin-display-box");
    const displayPinCode = document.getElementById("display-pin-code");
    const copyPinBtn = document.getElementById("copy-pin-btn");
    const qrContainerPublic = document.getElementById("qr-container-public");
    const qrContainerLan = document.getElementById("qr-container-lan");

    // Modal de Autenticação por PIN
    const authModal = document.getElementById("auth-modal");
    const authForm = document.getElementById("auth-form");
    const authPinInput = document.getElementById("auth-pin-input");
    const authSubmitBtn = document.getElementById("auth-submit-btn");
    const authErrorMsg = document.getElementById("auth-error-msg");

    const localEngineSelect = document.getElementById("local-engine");
    const localModelSelect = document.getElementById("local-model");
    const cloudProviderSelect = document.getElementById("cloud-provider");
    const cloudModelSelect = document.getElementById("cloud-model");
    const cloudApiKeyInput = document.getElementById("cloud-api-key");
    const apiKeyLink = document.getElementById("api-key-link");
    const audioLanguageSelect = document.getElementById("audio-language");
    const audioTaskSelect = document.getElementById("audio-task");
    const initialPromptInput = document.getElementById("initial-prompt");

    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const startTranscribeBtn = document.getElementById("start-transcribe-btn");

    // Microfone / Gravação ao Vivo
    const recordBtn = document.getElementById("record-btn");
    const recordIdle = document.getElementById("record-idle");
    const recordActive = document.getElementById("record-active");
    const recordingTimer = document.getElementById("recording-timer");
    const stopRecordBtn = document.getElementById("stop-record-btn");
    const cancelRecordBtn = document.getElementById("cancel-record-btn");
    
    // Abas de Fila vs Histórico
    const tabQueue = document.getElementById("tab-queue");
    const tabHistory = document.getElementById("tab-history");
    const fileQueueList = document.getElementById("file-queue-list");
    const historyList = document.getElementById("history-list");
    const queueCount = document.getElementById("queue-count");
    const historyCount = document.getElementById("history-count");
    const clearQueueBtn = document.getElementById("clear-queue-btn");

    const progressContainer = document.getElementById("progress-container");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressMessage = document.getElementById("progress-message");
    const progressPercentage = document.getElementById("progress-percentage");

    const transcriptFilename = document.getElementById("transcript-filename");
    const transcriptMeta = document.getElementById("transcript-meta");
    const metaDuration = document.getElementById("meta-duration");
    const metaLang = document.getElementById("meta-lang");
    const metaEngine = document.getElementById("meta-engine");
    const exportActions = document.getElementById("export-actions");
    const transcriptBody = document.getElementById("transcript-body");

    // Audio Player Elements
    const audioPlayerContainer = document.getElementById("audio-player-container");
    const nativeAudio = document.getElementById("native-audio");
    const audioPlayBtn = document.getElementById("audio-play-btn");
    const playBtnIcon = document.getElementById("play-btn-icon");
    const audioScrubber = document.getElementById("audio-scrubber");
    const audioCurrentTime = document.getElementById("audio-current-time");
    const audioTotalTime = document.getElementById("audio-total-time");

    // Stats & Search Elements
    const statsStrip = document.getElementById("stats-strip");
    const statDuration = document.getElementById("stat-duration");
    const statWords = document.getElementById("stat-words");
    const statChars = document.getElementById("stat-chars");
    const statSegments = document.getElementById("stat-segments");

    const searchWrapper = document.getElementById("search-wrapper");
    const transcriptSearch = document.getElementById("transcript-search");
    const toastContainer = document.getElementById("toast-container");

    const saveEditBtn = document.getElementById("save-edit-btn");
    const toggleRomanizeBtn = document.getElementById("toggle-romanize-btn");
    const llmActionsCard = document.getElementById("llm-actions-card");
    const copyBtn = document.getElementById("copy-btn");
    const downloadTxt = document.getElementById("download-txt");
    const downloadSrt = document.getElementById("download-srt");
    const downloadVtt = document.getElementById("download-vtt");
    const downloadJson = document.getElementById("download-json");

    // Gerenciamento de Sessão e Autenticação
    function getSessionId() {
        let sid = localStorage.getItem("transcribe_session_id");
        if (!sid || sid.length < 8) {
            sid = "sess_" + (crypto.randomUUID ? crypto.randomUUID().replace(/-/g, "") : Math.random().toString(36).substring(2) + Date.now().toString(36));
            localStorage.setItem("transcribe_session_id", sid);
        }
        try {
            document.cookie = "session_id=" + encodeURIComponent(sid) + "; path=/; max-age=2592000; SameSite=Lax";
        } catch(e) {}
        return sid;
    }

    function getAccessPin() {
        return localStorage.getItem("transcribe_access_pin") || "";
    }

    async function apiRequest(url, options = {}) {
        options.headers = options.headers || {};
        if (options.headers instanceof Headers) {
            options.headers.set("X-Session-ID", getSessionId());
            const pin = getAccessPin();
            if (pin) options.headers.set("X-Access-PIN", pin);
        } else {
            options.headers["X-Session-ID"] = getSessionId();
            const pin = getAccessPin();
            if (pin) options.headers["X-Access-PIN"] = pin;
        }

        const resp = await fetch(url, options);

        if (resp.status === 401) {
            openAuthModal();
            throw new Error("PIN de acesso obrigatório ou incorreto.");
        } else if (resp.status === 429) {
            let errData = {};
            try { errData = await resp.clone().json(); } catch(e) {}
            showToast(errData.detail || "Limite de requisições excedido. Aguarde alguns instantes.");
        }

        return resp;
    }

    async function verifyAndSavePin(pin) {
        try {
            const resp = await fetch("/api/auth/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ pin: pin })
            });
            if (resp.ok) {
                localStorage.setItem("transcribe_access_pin", pin);
                try {
                    document.cookie = "access_pin=" + encodeURIComponent(pin) + "; path=/; max-age=2592000; SameSite=Lax";
                } catch(e) {}
                showToast("Autenticado com sucesso via PIN!");
                return true;
            } else {
                const err = await resp.json();
                showToast(err.detail || "PIN incorreto.");
                return false;
            }
        } catch (e) {
            return false;
        }
    }

    // Inicialização
    init();

    async function init() {
        if (window.AppIcons) window.AppIcons.renderAll();
        setupTabs();
        setupHistoryTabs();
        setupDragAndDrop();
        setupDropzoneTabs();
        setupMicrophoneRecording();
        setupActions();
        setupAudioPlayer();
        setupSearch();
        setupInlineEditingAndRomanize();
        setupLLMActions();
        setupRemoteModal();
        setupAuthModal();

        // Checa se há PIN na URL para login automático com 1 toque
        const params = new URLSearchParams(window.location.search);
        const pinFromUrl = params.get("pin");
        if (pinFromUrl) {
            await verifyAndSavePin(pinFromUrl);
            params.delete("pin");
            const cleanUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({}, document.title, cleanUrl);
        }

        await loadSystemInfo();
        await loadHistory();
        loadSavedApiKeys();
        
        // Auto-carrega demo se solicitado via query param (para screenshots e previews)
        if (params.get("demo")) {
            const targetId = state.history.some(h => h.id === "demo_transcription") ? "demo_transcription" : (state.history.length > 0 ? state.history[0].id : null);
            if (targetId) {
                await openHistoryItem(targetId);
                if (state.activeItem) {
                    state.activeItem.audioUrl = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAAAAA=";
                    audioPlayerContainer.classList.remove("hidden");
                    audioTotalTime.textContent = "01:18";
                    audioCurrentTime.textContent = "00:00";
                    playBtnIcon.innerHTML = AppIcons.get("play", "ui-icon");

                    // Preenche exemplo visual de Resumo com IA para preview
                    const outBox = document.getElementById("llm-output-box");
                    const outTitle = document.getElementById("llm-output-title");
                    const outContent = document.getElementById("llm-output-content");
                    if (outBox && outContent) {
                        outBox.classList.remove("hidden");
                        outTitle.innerHTML = `<span data-icon="fileText" data-icon-class="ui-icon ui-icon-sm"></span> 📝 Resumo Executivo (Groq / Llama-3.3-70B)`;
                        outContent.innerHTML = `<strong>Visão Geral do Episódio:</strong>\n• <strong>Arquitetura Local:</strong> Apresentação do faster-whisper com quantização int8, alcançando processamento 4x mais rápido na CPU com consumo mínimo de RAM.\n• <strong>Privacidade & Segurança:</strong> Transcrição e arquivos persistidos 100% no disco local, sem dependência de nuvem ou vazamento de dados.\n• <strong>Novos Recursos:</strong> Demonstração de sincronização por palavra (Karaoke), edição inline e ingestão direta de links do YouTube com proteção anti-SSRF.\n\n<strong>Ações & Próximos Passos:</strong>\n1. Validar suporte para novos idiomas e romanização fonética automática.\n2. Expandir exportações para contêineres MP4 com legendas embutidas.`;
                    }
                }
            }
        }

        if (params.get("tab") === "url") {
            const tabUrl = document.getElementById("tab-dropzone-url");
            if (tabUrl) tabUrl.click();
            const urlInput = document.getElementById("web-url-input");
            if (urlInput) urlInput.value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";
        }

        if (params.get("story")) {
            document.body.classList.add("story-mode");
            // Adiciona rodapé com link do GitHub para contexto no Story
            const footer = document.createElement("div");
            footer.className = "story-footer";
            footer.innerHTML = `
                <div class="story-footer-line"></div>
                <p class="story-footer-text">🔗 github.com/realkalashnikov/transcribe</p>
                <p class="story-footer-sub">100% Open-Source • Funciona offline na sua máquina</p>
            `;
            document.querySelector(".app-container").appendChild(footer);
        }

        if (params.get("remote")) {
            await openRemoteModal();
        }

        if (window.AppIcons) window.AppIcons.renderAll();
    }

    // Carrega informações do servidor
    async function loadSystemInfo() {
        try {
            const resp = await apiRequest("/api/info");
            const data = await resp.json();

            // Atualiza Hardware Badge
            if (data.cuda_available) {
                hardwareText.textContent = "Aceleração GPU (CUDA) Ativa";
                hardwareBadge.className = "badge badge-cuda";
                hardwareBadge.querySelector("[data-icon]").innerHTML = AppIcons.get("zap", "ui-icon ui-icon-sm");
            } else {
                hardwareText.textContent = "Modo CPU (int8 otimizado)";
                hardwareBadge.className = "badge badge-cpu";
                hardwareBadge.querySelector("[data-icon]").innerHTML = AppIcons.get("cpu", "ui-icon ui-icon-sm");
            }

            // Em modo BYOK, oculta aba local e seleciona Nuvem
            const inst = data.instance || {};
            if (inst.instance_mode === "byok") {
                if (tabCloud) tabCloud.click();
                if (tabLocal) tabLocal.style.display = "none";
            } else {
                if (tabLocal) tabLocal.style.display = "";
            }

            // Popula motores locais
            state.localEngines = data.local_engines || [];
            if (localEngineSelect && state.localEngines.length > 0) {
                localEngineSelect.innerHTML = "";
                state.localEngines.forEach(eng => {
                    const opt = document.createElement("option");
                    opt.value = eng.id;
                    opt.textContent = eng.name;
                    if (eng.id === "faster-whisper") opt.selected = true;
                    localEngineSelect.appendChild(opt);
                });
            }

            // Popula modelos locais
            state.localModels = data.local_models || [];
            localModelSelect.innerHTML = "";
            state.localModels.forEach(m => {
                const opt = document.createElement("option");
                opt.value = m.id;
                opt.textContent = m.name;
                if (m.id === "base") opt.selected = true;
                localModelSelect.appendChild(opt);
            });

            // Popula provedores de nuvem
            state.providers = data.cloud_providers || [];
            cloudProviderSelect.innerHTML = "";
            state.providers.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                cloudProviderSelect.appendChild(opt);
            });
            updateCloudModels();

            // Popula idiomas
            state.languages = data.languages || [];
            audioLanguageSelect.innerHTML = "";
            state.languages.forEach(l => {
                const opt = document.createElement("option");
                opt.value = l.code;
                opt.textContent = l.name;
                audioLanguageSelect.appendChild(opt);
            });

        } catch (err) {
            console.error("Erro ao carregar informações da API:", err);
            hardwareText.textContent = "Erro de conexão com backend";
        }
    }

    // Gerenciamento de Histórico Salvo no Disco
    async function loadHistory() {
        try {
            const resp = await apiRequest("/api/history");
            if (!resp.ok) return;
            state.history = await resp.json();
            renderHistory();
        } catch (err) {
            console.error("Erro ao carregar histórico:", err);
        }
    }

    function setupHistoryTabs() {
        tabQueue.addEventListener("click", () => {
            state.activeTab = "queue";
            tabQueue.classList.add("active");
            tabHistory.classList.remove("active");
            fileQueueList.classList.remove("hidden");
            historyList.classList.add("hidden");
            clearQueueBtn.style.display = state.files.length > 0 ? "inline-flex" : "none";
        });

        tabHistory.addEventListener("click", () => {
            state.activeTab = "history";
            tabHistory.classList.add("active");
            tabQueue.classList.remove("active");
            historyList.classList.remove("hidden");
            fileQueueList.classList.add("hidden");
            clearQueueBtn.style.display = "none";
            loadHistory();
        });
    }

    function renderHistory() {
        historyCount.textContent = state.history.length;

        if (state.history.length === 0) {
            historyList.className = "queue-list empty" + (state.activeTab === "history" ? "" : " hidden");
            historyList.innerHTML = `<p class="empty-msg">Nenhuma transcrição salva no disco ainda.</p>`;
            return;
        }

        historyList.className = "queue-list" + (state.activeTab === "history" ? "" : " hidden");
        historyList.innerHTML = "";

        state.history.forEach(item => {
            const div = document.createElement("div");
            const isActive = state.activeItem && state.activeItem.id === item.id;
            div.className = `queue-item ${isActive ? "active" : ""}`;
            div.onclick = () => openHistoryItem(item.id);

            const durStr = `${(item.duration || 0).toFixed(0)}s`;
            const langStr = item.language ? item.language.toUpperCase() : "AUTO";

            div.innerHTML = `
                <div class="queue-item-left">
                    <span class="file-icon-box">${AppIcons.get("fileText", "ui-icon")}</span>
                    <div>
                        <div class="file-name" title="${item.filename}">${escapeHtml(item.filename)}</div>
                        <small style="color: var(--text-dim);">${item.saved_at} • ${durStr}</small>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="file-status-badge status-done">${langStr}</span>
                    <button type="button" class="btn-text" title="Excluir do disco" onclick="event.stopPropagation(); window.__deleteHistory('${item.id}')">
                        ${AppIcons.get("trash", "ui-icon ui-icon-sm")}
                    </button>
                </div>
            `;
            historyList.appendChild(div);
        });
    }

    async function openHistoryItem(id) {
        try {
            showProgress("Carregando transcrição do histórico...", 30);
            const resp = await apiRequest(`/api/history/${id}`);
            if (!resp.ok) throw new Error("Erro ao carregar item do histórico");
            const fullData = await resp.json();

            const sid = getSessionId();
            const pin = getAccessPin();
            let audioSrc = `/api/history/${id}/audio`;
            const q = new URLSearchParams();
            if (sid) q.set("session_id", sid);
            if (pin) q.set("pin", pin);
            if (q.toString()) audioSrc += `?${q.toString()}`;

            state.activeItem = {
                id: fullData.id,
                filename: fullData.filename,
                result: fullData,
                audioUrl: audioSrc
            };

            showTranscriptionResult(state.activeItem);
            renderHistory();
            hideProgress();
        } catch (err) {
            console.error(err);
            hideProgress();
            showToast("Erro ao abrir transcrição salva.");
        }
    }

    async function deleteHistoryItem(id) {
        if (!confirm("Deseja realmente excluir esta transcrição do histórico?")) return;
        try {
            const resp = await apiRequest(`/api/history/${id}`, { method: "DELETE" });
            if (!resp.ok) throw new Error("Erro ao excluir");
            state.history = state.history.filter(h => h.id !== id);
            if (state.activeItem && state.activeItem.id === id) {
                state.activeItem = null;
                resetTranscriptView();
            }
            renderHistory();
            showToast("Item removido do histórico com sucesso.");
        } catch (err) {
            showToast("Erro ao excluir item.");
        }
    }

    window.__deleteHistory = deleteHistoryItem;

    // Alternância de Abas (Local vs Nuvem)
    function setupTabs() {
        tabLocal.addEventListener("click", () => {
            state.mode = "local";
            tabLocal.classList.add("active");
            tabCloud.classList.remove("active");
            localSettings.classList.remove("hidden");
            cloudSettings.classList.add("hidden");
            updateStartButtonState();
        });

        tabCloud.addEventListener("click", () => {
            state.mode = "cloud";
            tabCloud.classList.add("active");
            tabLocal.classList.remove("active");
            cloudSettings.classList.remove("hidden");
            localSettings.classList.add("hidden");
            loadSavedApiKeyForCurrentProvider();
            updateStartButtonState();
        });

        cloudProviderSelect.addEventListener("change", () => {
            updateCloudModels();
            loadSavedApiKeyForCurrentProvider();
            updateStartButtonState();
        });

        cloudApiKeyInput.addEventListener("input", () => {
            const provider = cloudProviderSelect.value;
            localStorage.setItem(`transcribe_key_${provider}`, cloudApiKeyInput.value.trim());
            updateStartButtonState();
        });
    }

    function updateCloudModels() {
        const providerId = cloudProviderSelect.value;
        const provider = state.providers.find(p => p.id === providerId);
        cloudModelSelect.innerHTML = "";
        if (!provider) return;

        if (apiKeyLink && provider.doc_url) {
            apiKeyLink.href = provider.doc_url;
        }

        provider.models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            if (m === provider.default_model) opt.selected = true;
            cloudModelSelect.appendChild(opt);
        });
    }

    function loadSavedApiKeys() {
        loadSavedApiKeyForCurrentProvider();
    }

    function loadSavedApiKeyForCurrentProvider() {
        const provider = cloudProviderSelect.value;
        const saved = localStorage.getItem(`transcribe_key_${provider}`) || "";
        cloudApiKeyInput.value = saved;
    }

    // Drag and Drop de arquivos
    function setupDragAndDrop() {
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.add("dragover");
            });
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropzone.classList.remove("dragover");
            });
        });

        dropzone.addEventListener("drop", (e) => {
            const droppedFiles = Array.from(e.dataTransfer.files);
            addFiles(droppedFiles);
        });

        fileInput.addEventListener("change", (e) => {
            const selectedFiles = Array.from(e.target.files);
            addFiles(selectedFiles);
            fileInput.value = "";
        });

        clearQueueBtn.addEventListener("click", () => {
            if (state.isProcessing) return;
            state.files.forEach(f => {
                if (f.audioUrl) URL.revokeObjectURL(f.audioUrl);
            });
            state.files = [];
            state.activeItem = null;
            renderQueue();
            resetTranscriptView();
            updateStartButtonState();
        });
    }

    // Abas de Arquivo Local vs URL Web
    function setupDropzoneTabs() {
        const tabFile = document.getElementById("tab-dropzone-file");
        const tabUrl = document.getElementById("tab-dropzone-url");
        const dropzoneEl = document.getElementById("dropzone");
        const urlContainer = document.getElementById("url-ingest-container");
        const urlInput = document.getElementById("web-url-input");
        const urlBtn = document.getElementById("web-url-btn");

        if (tabFile && tabUrl) {
            tabFile.addEventListener("click", () => {
                tabFile.classList.add("active");
                tabUrl.classList.remove("active");
                if (dropzoneEl) dropzoneEl.classList.remove("hidden");
                if (urlContainer) urlContainer.classList.add("hidden");
            });

            tabUrl.addEventListener("click", () => {
                tabUrl.classList.add("active");
                tabFile.classList.remove("active");
                if (urlContainer) urlContainer.classList.remove("hidden");
                if (dropzoneEl) dropzoneEl.classList.add("hidden");
                if (urlInput) urlInput.focus();
            });
        }

        if (urlBtn && urlInput) {
            const handleUrlSubmit = async () => {
                if (state.isProcessing) return;
                const url = urlInput.value.trim();
                if (!url) {
                    showToast("Por favor, cole um link de áudio ou vídeo.");
                    return;
                }
                if (!url.startsWith("http://") && !url.startsWith("https://")) {
                    showToast("O link deve iniciar com http:// ou https://");
                    return;
                }

                urlBtn.disabled = true;
                const origHtml = urlBtn.innerHTML;
                urlBtn.innerHTML = `<span>Baixando mídia...</span>`;

                try {
                    const chosenEngine = (state.mode === "local")
                        ? (localEngineSelect ? localEngineSelect.value : "faster-whisper")
                        : cloudProviderSelect.value;
                    const chosenModel = (state.mode === "local")
                        ? localModelSelect.value
                        : cloudModelSelect.value;
                    const apiKey = (state.mode === "cloud")
                        ? cloudApiKeyInput.value.trim()
                        : null;

                    const payload = {
                        url: url,
                        provider: chosenEngine,
                        model: chosenModel,
                        language: audioLanguageSelect.value || null,
                        task: audioTaskSelect.value || "transcribe",
                        prompt: initialPromptInput && initialPromptInput.value.trim() ? initialPromptInput.value.trim() : null,
                        api_key: apiKey
                    };

                    const resp = await apiRequest("/api/ingest/url", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify(payload)
                    });

                    if (!resp.ok) {
                        const err = await resp.json();
                        throw new Error(err.detail || "Erro ao baixar áudio da URL");
                    }

                    const data = await resp.json();
                    urlInput.value = "";
                    showToast("Mídia baixada com sucesso! Transcrevendo...");

                    const queueItem = {
                        id: data.job_id,
                        filename: data.filename,
                        status: "processing",
                        result: null,
                        error: null,
                        audioUrl: `/api/history/${data.job_id}/audio`
                    };
                    state.files.push(queueItem);
                    state.activeItem = queueItem;
                    if (state.activeTab !== "queue") tabQueue.click();
                    renderQueue();
                    showProgress("Iniciando transcrição...", 10);

                    try {
                        const result = await trackJobPromise(data.job_id);
                        queueItem.status = "completed";
                        queueItem.result = result;
                        showTranscriptionResult(queueItem);
                        await loadHistory();
                    } catch (err) {
                        queueItem.status = "error";
                        queueItem.error = err.message || "Erro na transcrição";
                        showErrorInView(queueItem);
                    }
                    renderQueue();
                    hideProgress();

                } catch (e) {
                    showToast(e.message || "Falha ao processar URL");
                } finally {
                    urlBtn.disabled = false;
                    urlBtn.innerHTML = origHtml;
                    if (window.AppIcons) window.AppIcons.renderAll();
                }
            };

            urlBtn.addEventListener("click", handleUrlSubmit);
            urlInput.addEventListener("keydown", (e) => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    handleUrlSubmit();
                }
            });
        }
    }

    // Edição Inline e Romanização Fonética
    function setupInlineEditingAndRomanize() {
        if (saveEditBtn) {
            saveEditBtn.addEventListener("click", async () => {
                if (!state.activeItem || !state.activeItem.result) return;
                const res = state.activeItem.result;
                const jobId = state.activeItem.id;

                saveEditBtn.disabled = true;
                const origHtml = saveEditBtn.innerHTML;
                saveEditBtn.innerHTML = `<span>Salvando...</span>`;

                try {
                    const resp = await apiRequest(`/api/history/${jobId}`, {
                        method: "PUT",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            text: res.text,
                            segments: res.segments
                        })
                    });

                    if (resp.ok) {
                        const data = await resp.json();
                        if (data.item && data.item.exports) {
                            res.exports = data.item.exports;
                        }
                        saveEditBtn.classList.add("hidden");
                        showToast("Revisão salva com sucesso no disco!");
                        await loadHistory();
                    } else {
                        const err = await resp.json();
                        showToast(err.detail || "Erro ao salvar revisão.");
                    }
                } catch (e) {
                    showToast("Falha de rede ao salvar revisão.");
                } finally {
                    saveEditBtn.disabled = false;
                    saveEditBtn.innerHTML = origHtml;
                    if (window.AppIcons) window.AppIcons.renderAll();
                }
            });
        }

        if (toggleRomanizeBtn) {
            toggleRomanizeBtn.addEventListener("click", async () => {
                if (!state.activeItem || !state.activeItem.result) return;
                state.showRomanized = !state.showRomanized;

                if (state.showRomanized) {
                    toggleRomanizeBtn.classList.add("btn-primary");
                    toggleRomanizeBtn.classList.remove("btn-outline");

                    const res = state.activeItem.result;
                    const needsRomanize = res.segments && res.segments.some(s => !s.romanized);
                    if (needsRomanize) {
                        showToast("Calculando romanização fonética...");
                        try {
                            const resp = await apiRequest("/api/romanize", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({
                                    text: res.text,
                                    language: res.language || "ja",
                                    segments: res.segments
                                })
                            });
                            if (resp.ok) {
                                const data = await resp.json();
                                if (data.segments) {
                                    res.segments = data.segments;
                                }
                            }
                        } catch (e) {
                            console.error("Erro ao romanizar:", e);
                        }
                    }
                } else {
                    toggleRomanizeBtn.classList.remove("btn-primary");
                    toggleRomanizeBtn.classList.add("btn-outline");
                }

                renderActiveSegments();
            });
        }
    }

    // Ações Inteligentes com IA (Resumo, Ata, Tópicos, Tradução)
    function setupLLMActions() {
        const actionBtns = document.querySelectorAll(".llm-action-btn");
        const providerSel = document.getElementById("llm-provider-select");
        const targetLangSel = document.getElementById("llm-target-lang");
        const outputBox = document.getElementById("llm-output-box");
        const outputTitle = document.getElementById("llm-output-title");
        const outputContent = document.getElementById("llm-output-content");
        const copyLlmBtn = document.getElementById("copy-llm-btn");
        const closeLlmBtn = document.getElementById("close-llm-btn");

        actionBtns.forEach(btn => {
            btn.addEventListener("click", async () => {
                if (!state.activeItem || !state.activeItem.result) return;
                const action = btn.dataset.action;
                const provider = providerSel ? providerSel.value : "groq";
                const targetLang = targetLangSel ? targetLangSel.value : "pt";
                const apiKey = (cloudApiKeyInput && cloudApiKeyInput.value.trim()) || localStorage.getItem(`transcribe_key_${provider}`) || "";

                const actionTitles = {
                    summary: "📝 Resumo Executivo",
                    action_items: "📋 Ata de Reunião & Próximos Passos",
                    bullet_points: "🎯 Pontos Principais",
                    translate: `🌐 Tradução para ${targetLang.toUpperCase()}`
                };

                if (outputBox) outputBox.classList.remove("hidden");
                if (outputTitle) outputTitle.textContent = actionTitles[action] || "Processando com IA...";
                if (outputContent) outputContent.innerHTML = `<span style="color: var(--text-dim);">Aguarde... conectando ao provedor ${provider.toUpperCase()}</span>`;

                try {
                    const resp = await apiRequest("/api/summarize", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({
                            job_id: state.activeItem.id,
                            text: state.activeItem.result.text,
                            action: action,
                            target_language: targetLang,
                            provider: provider,
                            api_key: apiKey
                        })
                    });

                    if (!resp.ok) {
                        const err = await resp.json();
                        throw new Error(err.detail || "Falha ao processar solicitação de IA.");
                    }

                    const data = await resp.json();
                    if (outputContent) {
                        outputContent.textContent = data.result || "Sem resposta retornada.";
                    }
                    showToast("Ação com IA finalizada com sucesso!");
                } catch (e) {
                    if (outputContent) {
                        outputContent.innerHTML = `<span style="color: var(--danger);">${escapeHtml(e.message)}</span>`;
                    }
                }
            });
        });

        if (copyLlmBtn && outputContent) {
            copyLlmBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(outputContent.textContent);
                showToast("Resultado copiado com sucesso!");
            });
        }

        if (closeLlmBtn && outputBox) {
            closeLlmBtn.addEventListener("click", () => {
                outputBox.classList.add("hidden");
            });
        }
    }

    // Gravação ao vivo pelo Microfone
    function setupMicrophoneRecording() {
        if (!recordBtn) return;

        let mediaRecorder = null;
        let audioChunks = [];
        let recordInterval = null;
        let recordSeconds = 0;
        let stream = null;

        recordBtn.addEventListener("click", async () => {
            if (state.isProcessing) return;
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                showToast("Seu navegador não possui suporte para gravação via microfone.");
                return;
            }

            try {
                stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                audioChunks = [];
                recordSeconds = 0;
                recordingTimer.textContent = "00:00";

                const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") 
                    ? "audio/webm;codecs=opus" 
                    : (MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "");

                mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

                mediaRecorder.ondataavailable = (e) => {
                    if (e.data && e.data.size > 0) {
                        audioChunks.push(e.data);
                    }
                };

                mediaRecorder.onstop = () => {
                    clearInterval(recordInterval);
                    if (stream) {
                        stream.getTracks().forEach(t => t.stop());
                    }

                    if (audioChunks.length === 0) {
                        resetRecordUI();
                        return;
                    }

                    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType || "audio/webm" });
                    const date = new Date();
                    const timeStr = `${date.getHours().toString().padStart(2, '0')}h${date.getMinutes().toString().padStart(2, '0')}m${date.getSeconds().toString().padStart(2, '0')}s`;
                    const ext = (mediaRecorder.mimeType && mediaRecorder.mimeType.includes("ogg")) ? "ogg" : "webm";
                    const filename = `gravacao_mic_${timeStr}.${ext}`;

                    const recordedFile = new File([blob], filename, { type: blob.type });
                    addFiles([recordedFile]);
                    showToast(`Áudio gravado (${formatTime(recordSeconds)}) pronto na fila!`);
                    resetRecordUI();
                };

                mediaRecorder.start(250);
                recordIdle.classList.add("hidden");
                recordActive.classList.remove("hidden");
                if (window.AppIcons) window.AppIcons.renderAll();

                recordInterval = setInterval(() => {
                    recordSeconds++;
                    recordingTimer.textContent = formatTime(recordSeconds);
                }, 1000);

            } catch (err) {
                console.error("Erro ao acessar microfone:", err);
                showToast("Não foi possível acessar o microfone. Verifique as permissões.");
                resetRecordUI();
            }
        });

        stopRecordBtn.addEventListener("click", () => {
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
        });

        cancelRecordBtn.addEventListener("click", () => {
            audioChunks = [];
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
            if (stream) {
                stream.getTracks().forEach(t => t.stop());
            }
            resetRecordUI();
            showToast("Gravação cancelada.");
        });

        function resetRecordUI() {
            clearInterval(recordInterval);
            recordSeconds = 0;
            if (recordingTimer) recordingTimer.textContent = "00:00";
            if (recordActive) recordActive.classList.add("hidden");
            if (recordIdle) recordIdle.classList.remove("hidden");
            if (window.AppIcons) window.AppIcons.renderAll();
        }
    }

    function addFiles(newFiles) {
        newFiles.forEach(file => {
            const audioUrl = URL.createObjectURL(file);
            state.files.push({
                id: "f_" + Math.random().toString(36).substring(2, 9),
                file: file,
                audioUrl: audioUrl,
                status: "pending",
                result: null,
                error: null
            });
        });
        
        // Alterna para a aba da fila caso estivesse no histórico
        if (state.activeTab !== "queue") {
            tabQueue.click();
        }

        renderQueue();
        updateStartButtonState();
    }

    function removeFile(fileId) {
        if (state.isProcessing) return;
        const target = state.files.find(f => f.id === fileId);
        if (target && target.audioUrl) {
            URL.revokeObjectURL(target.audioUrl);
        }
        state.files = state.files.filter(f => f.id !== fileId);
        if (state.activeItem && state.activeItem.id === fileId) {
            state.activeItem = null;
            resetTranscriptView();
        }
        renderQueue();
        updateStartButtonState();
    }

    function renderQueue() {
        queueCount.textContent = state.files.length;
        if (state.activeTab === "queue") {
            clearQueueBtn.style.display = state.files.length > 0 ? "inline-flex" : "none";
        }

        if (state.files.length === 0) {
            fileQueueList.className = "queue-list empty" + (state.activeTab === "queue" ? "" : " hidden");
            fileQueueList.innerHTML = `<p class="empty-msg">Nenhum arquivo adicionado ainda.</p>`;
            return;
        }

        fileQueueList.className = "queue-list" + (state.activeTab === "queue" ? "" : " hidden");
        fileQueueList.innerHTML = "";

        state.files.forEach(item => {
            const div = document.createElement("div");
            const isActive = state.activeItem && state.activeItem.id === item.id;
            div.className = `queue-item ${isActive ? "active" : ""}`;
            div.onclick = () => {
                if (item.result) {
                    state.activeItem = item;
                    showTranscriptionResult(item);
                    renderQueue();
                }
            };

            const sizeFormatted = (item.file.size / (1024 * 1024)).toFixed(1) + " MB";
            const statusMap = {
                pending: { label: "Pendente", class: "status-pending" },
                processing: { label: "Processando...", class: "status-running" },
                completed: { label: "Concluído", class: "status-done" },
                error: { label: "Erro", class: "status-error" }
            };
            const currentStatus = statusMap[item.status] || statusMap.pending;

            div.innerHTML = `
                <div class="queue-item-left">
                    <span class="file-icon-box">${AppIcons.get("fileAudio", "ui-icon")}</span>
                    <div>
                        <div class="file-name" title="${item.file.name}">${escapeHtml(item.file.name)}</div>
                        <small style="color: var(--text-dim);">${sizeFormatted}</small>
                    </div>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="file-status-badge ${currentStatus.class}">${currentStatus.label}</span>
                    ${!state.isProcessing ? `<button type="button" class="btn-text" title="Remover" onclick="event.stopPropagation(); window.__removeFile('${item.id}')">${AppIcons.get("x", "ui-icon ui-icon-sm")}</button>` : ''}
                </div>
            `;
            fileQueueList.appendChild(div);
        });
    }

    window.__removeFile = removeFile;

    function updateStartButtonState() {
        const hasPendingFiles = state.files.some(f => f.status === "pending" || f.status === "error");
        let valid = hasPendingFiles && !state.isProcessing;

        if (state.mode === "cloud") {
            const key = cloudApiKeyInput.value.trim();
            if (!key) valid = false;
        }

        startTranscribeBtn.disabled = !valid;
    }

    // Player de Áudio Integrado
    function setupAudioPlayer() {
        audioPlayBtn.addEventListener("click", () => {
            if (nativeAudio.paused) {
                nativeAudio.play();
                playBtnIcon.innerHTML = AppIcons.get("pause", "ui-icon");
            } else {
                nativeAudio.pause();
                playBtnIcon.innerHTML = AppIcons.get("play", "ui-icon");
            }
        });

        nativeAudio.addEventListener("timeupdate", () => {
            if (!nativeAudio.duration) return;
            const cur = nativeAudio.currentTime;
            const dur = nativeAudio.duration;
            audioScrubber.value = (cur / dur) * 100;
            audioCurrentTime.textContent = formatTime(cur);
            highlightActiveSegment(cur);
        });

        nativeAudio.addEventListener("loadedmetadata", () => {
            audioTotalTime.textContent = formatTime(nativeAudio.duration);
        });

        nativeAudio.addEventListener("ended", () => {
            playBtnIcon.innerHTML = AppIcons.get("play", "ui-icon");
        });

        audioScrubber.addEventListener("input", () => {
            if (!nativeAudio.duration) return;
            const targetSec = (audioScrubber.value / 100) * nativeAudio.duration;
            nativeAudio.currentTime = targetSec;
            audioCurrentTime.textContent = formatTime(targetSec);
        });
    }

    function highlightActiveSegment(currentTime) {
        document.querySelectorAll(".segment-item").forEach(item => {
            const start = parseFloat(item.dataset.start);
            const end = parseFloat(item.dataset.end);
            if (currentTime >= start && currentTime <= end) {
                item.classList.add("playing-segment");
                item.querySelectorAll(".karaoke-word").forEach(wEl => {
                    const wStart = parseFloat(wEl.dataset.start);
                    const wEnd = parseFloat(wEl.dataset.end);
                    if (currentTime >= wStart && currentTime <= wEnd) {
                        wEl.classList.add("active");
                    } else {
                        wEl.classList.remove("active");
                    }
                });
            } else {
                item.classList.remove("playing-segment");
                item.querySelectorAll(".karaoke-word").forEach(wEl => wEl.classList.remove("active"));
            }
        });
    }

    // Busca no Texto
    function setupSearch() {
        transcriptSearch.addEventListener("input", (e) => {
            state.searchQuery = e.target.value.trim().toLowerCase();
            renderActiveSegments();
        });
    }

    // Modal de Acesso Remoto & Celular
    function setupRemoteModal() {
        if (!remoteBtn) return;
        remoteBtn.addEventListener("click", () => {
            openRemoteModal();
        });

        if (remoteModalClose) {
            remoteModalClose.addEventListener("click", () => {
                closeRemoteModal();
            });
        }

        if (remoteModal) {
            remoteModal.addEventListener("click", (e) => {
                if (e.target === remoteModal) closeRemoteModal();
            });
        }

        if (tabRemoteInternet && tabRemoteLan) {
            tabRemoteInternet.addEventListener("click", () => {
                tabRemoteInternet.classList.add("active");
                tabRemoteLan.classList.remove("active");
                remoteContentInternet.classList.remove("hidden");
                remoteContentLan.classList.add("hidden");
            });

            tabRemoteLan.addEventListener("click", () => {
                tabRemoteLan.classList.add("active");
                tabRemoteInternet.classList.remove("active");
                remoteContentLan.classList.remove("hidden");
                remoteContentInternet.classList.add("hidden");
            });
        }

        if (copyTunnelLinkBtn && tunnelUrlInput) {
            copyTunnelLinkBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(tunnelUrlInput.value);
                showToast("Link público copiado!");
            });
        }

        if (copyLanLinkBtn && lanUrlInput) {
            copyLanLinkBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(lanUrlInput.value);
                showToast("Link Wi-Fi copiado!");
            });
        }

        if (copyPinBtn && displayPinCode) {
            copyPinBtn.addEventListener("click", () => {
                navigator.clipboard.writeText(displayPinCode.textContent);
                showToast("PIN copiado!");
            });
        }
    }

    async function openRemoteModal() {
        if (!remoteModal) return;
        remoteModal.classList.remove("hidden");
        await loadTunnelInfo();
        if (window.AppIcons) window.AppIcons.renderAll();
    }

    function closeRemoteModal() {
        if (!remoteModal) return;
        remoteModal.classList.add("hidden");
    }

    async function loadTunnelInfo() {
        try {
            const resp = await apiRequest("/api/tunnel/info");
            if (!resp.ok) return;
            const data = await resp.json();

            // Simula dados do túnel para captura em demo/screenshot
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.get("demo")) {
                data.tunnel_active = true;
                data.public_url = "https://swift-echo-demo.trycloudflare.com";
                data.requires_pin = true;
                data.access_pin = "482 109";
            }

            // Link do Túnel Cloudflare
            if (data.tunnel_active && data.public_url) {
                tunnelActiveBox.classList.remove("hidden");
                tunnelInactiveBox.classList.add("hidden");

                let publicLink = data.public_url;
                if (data.requires_pin && data.access_pin) {
                    publicLink += `?pin=${data.access_pin}`;
                }
                tunnelUrlInput.value = publicLink;

                if (window.QRCodeSVG && qrContainerPublic) {
                    qrContainerPublic.innerHTML = window.QRCodeSVG.generate(publicLink, 180);
                }

                if (data.requires_pin && data.access_pin) {
                    pinDisplayBox.classList.remove("hidden");
                    displayPinCode.textContent = data.access_pin;
                } else {
                    pinDisplayBox.classList.add("hidden");
                }
            } else {
                tunnelActiveBox.classList.add("hidden");
                tunnelInactiveBox.classList.remove("hidden");
            }

            // Link Wi-Fi Local
            let lanLink = data.lan_url;
            if (data.requires_pin && data.access_pin) {
                lanLink += `?pin=${data.access_pin}`;
            }
            if (lanUrlInput) lanUrlInput.value = lanLink;
            if (window.QRCodeSVG && qrContainerLan) {
                qrContainerLan.innerHTML = window.QRCodeSVG.generate(lanLink, 180);
            }
        } catch (e) {
            console.error("Erro ao carregar informações de túnel:", e);
        }
    }

    // Modal de Autenticação por PIN
    function setupAuthModal() {
        if (!authForm) return;
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const pinVal = authPinInput.value.trim();
            if (!pinVal) return;

            authSubmitBtn.disabled = true;
            authErrorMsg.classList.add("hidden");

            try {
                const ok = await verifyAndSavePin(pinVal);
                if (ok) {
                    closeAuthModal();
                    authPinInput.value = "";
                    await loadSystemInfo();
                    await loadHistory();
                } else {
                    authErrorMsg.textContent = "PIN incorreto. Tente novamente.";
                    authErrorMsg.classList.remove("hidden");
                }
            } catch (err) {
                authErrorMsg.textContent = err.message || "Erro de conexão.";
                authErrorMsg.classList.remove("hidden");
            } finally {
                authSubmitBtn.disabled = false;
            }
        });
    }

    function openAuthModal() {
        if (!authModal) return;
        authModal.classList.remove("hidden");
        if (authPinInput) authPinInput.focus();
        if (window.AppIcons) window.AppIcons.renderAll();
    }

    function closeAuthModal() {
        if (!authModal) return;
        authModal.classList.add("hidden");
    }

    // Ações de Botões e Exportações
    function setupActions() {
        startTranscribeBtn.addEventListener("click", () => {
            startTranscriptionQueue();
        });

        copyBtn.addEventListener("click", () => {
            if (!state.activeItem || !state.activeItem.result) return;
            navigator.clipboard.writeText(state.activeItem.result.text);
            showToast("Texto copiado para a área de transferência!");
        });

        downloadTxt.addEventListener("click", () => triggerDownload("txt"));
        downloadSrt.addEventListener("click", () => triggerDownload("srt"));
        downloadVtt.addEventListener("click", () => triggerDownload("vtt"));
        downloadJson.addEventListener("click", () => triggerDownload("json"));
    }

    function triggerDownload(format) {
        if (!state.activeItem || !state.activeItem.result) return;
        const res = state.activeItem.result;
        const content = res.exports ? res.exports[format] : res.text;
        
        const originalName = state.activeItem.file ? state.activeItem.file.name : (state.activeItem.filename || "transcricao");
        const baseName = originalName.substring(0, originalName.lastIndexOf('.')) || originalName;
        const filename = `${baseName}.${format}`;

        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        showToast(`Arquivo .${format.toUpperCase()} baixado!`);
    }

    function showToast(message) {
        const toast = document.createElement("div");
        toast.className = "toast toast-success";
        toast.innerHTML = `
            <span class="toast-icon">${AppIcons.get("check", "ui-icon")}</span>
            <span>${escapeHtml(message)}</span>
        `;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateY(10px)";
            toast.style.transition = "all 0.3s";
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    // Execução da fila de transcrição
    async function startTranscriptionQueue() {
        if (state.isProcessing) return;
        state.isProcessing = true;
        updateStartButtonState();

        const pendingItems = state.files.filter(f => f.status === "pending" || f.status === "error");

        for (const item of pendingItems) {
            item.status = "processing";
            state.activeItem = item;
            renderQueue();
            showProgress("Enviando arquivo...", 0);

            try {
                const result = await processFile(item);
                item.status = "completed";
                item.result = result;
                showTranscriptionResult(item);
                // Atualiza lista de histórico em disco em background
                loadHistory();
            } catch (err) {
                console.error("Erro no processamento:", err);
                item.status = "error";
                item.error = err.message || "Erro durante a transcrição";
                showErrorInView(item);
            }

            renderQueue();
        }

        state.isProcessing = false;
        hideProgress();
        updateStartButtonState();
    }

    async function processFile(item) {
        const formData = new FormData();
        formData.append("file", item.file);

        if (state.mode === "local") {
            const chosenEngine = localEngineSelect ? localEngineSelect.value : "faster-whisper";
            formData.append("provider", chosenEngine);
            formData.append("model", localModelSelect.value);
        } else {
            formData.append("provider", cloudProviderSelect.value);
            formData.append("model", cloudModelSelect.value);
            formData.append("api_key", cloudApiKeyInput.value.trim());
        }

        formData.append("language", audioLanguageSelect.value);
        formData.append("task", audioTaskSelect.value);
        if (initialPromptInput && initialPromptInput.value.trim()) {
            formData.append("prompt", initialPromptInput.value.trim());
        }

        const jobResp = await apiRequest("/api/jobs", {
            method: "POST",
            body: formData
        });

        if (!jobResp.ok) {
            const err = await jobResp.json();
            throw new Error(err.detail || "Falha ao iniciar trabalho de transcrição.");
        }

        const { job_id } = await jobResp.json();
        return trackJobPromise(job_id);
    }

    function trackJobPromise(job_id) {
        // 1. Tenta SSE (Server-Sent Events) para conexão única sem spam de requisições
        return new Promise((resolve, reject) => {
            let finished = false;
            let eventSource = null;

            const cleanup = () => {
                finished = true;
                if (eventSource) {
                    eventSource.close();
                    eventSource = null;
                }
            };

            const fallbackPolling = () => {
                cleanup();
                const interval = setInterval(async () => {
                    try {
                        const statusResp = await apiRequest(`/api/jobs/${job_id}`);
                        if (!statusResp.ok) {
                            clearInterval(interval);
                            return reject(new Error("Erro ao obter status do trabalho."));
                        }
                        const data = await statusResp.json();
                        showProgress(data.message || "Processando...", data.progress || 0);

                        if (data.status === "completed") {
                            clearInterval(interval);
                            resolve(data.result);
                        } else if (data.status === "error") {
                            clearInterval(interval);
                            reject(new Error(data.error || "Erro durante a transcrição"));
                        }
                    } catch (e) {
                        clearInterval(interval);
                        reject(e);
                    }
                }, 1500);
            };

            if (typeof EventSource !== "undefined") {
                const sseUrl = `${API_BASE}/api/jobs/${job_id}/stream`;
                eventSource = new EventSource(sseUrl);

                eventSource.onmessage = (event) => {
                    if (finished) return;
                    try {
                        const data = JSON.parse(event.data);
                        showProgress(data.message || "Processando...", data.progress || 0);

                        if (data.status === "completed") {
                            cleanup();
                            resolve(data.result);
                        } else if (data.status === "error") {
                            cleanup();
                            reject(new Error(data.error || "Erro durante a transcrição"));
                        }
                    } catch (err) {
                        console.error("Erro ao processar evento SSE:", err);
                    }
                };

                eventSource.onerror = () => {
                    if (finished) return;
                    fallbackPolling();
                };
            } else {
                fallbackPolling();
            }
        });
    }

    // Atualizações Visuais
    function showProgress(message, percentage) {
        progressContainer.classList.remove("hidden");
        progressBarFill.style.width = `${percentage}%`;
        progressPercentage.textContent = `${Math.round(percentage)}%`;
        progressMessage.textContent = message;
    }

    function hideProgress() {
        progressContainer.classList.add("hidden");
    }

    function showTranscriptionResult(item) {
        state.activeItem = item;
        const res = item.result;
        const displayName = item.file ? item.file.name : (item.filename || "Transcrição");

        transcriptFilename.innerHTML = `
            <span class="card-title-icon">${AppIcons.get("fileText", "ui-icon")}</span>
            <span>${escapeHtml(displayName)}</span>
        `;
        transcriptMeta.style.display = "flex";
        exportActions.style.display = "flex";
        statsStrip.classList.remove("hidden");
        searchWrapper.classList.remove("hidden");

        // Metatags
        metaDuration.innerHTML = `${AppIcons.get("clock", "ui-icon ui-icon-sm")} ${(res.duration || 0).toFixed(1)}s`;
        metaLang.innerHTML = `${AppIcons.get("globe", "ui-icon ui-icon-sm")} ${res.language ? res.language.toUpperCase() : 'AUTO'}`;
        metaEngine.innerHTML = `${AppIcons.get("zap", "ui-icon ui-icon-sm")} ${res.provider || 'local'}`;

        // Estatísticas
        statDuration.textContent = `${(res.duration || 0).toFixed(1)}s`;
        const words = res.text ? res.text.trim().split(/\s+/).filter(Boolean).length : 0;
        statWords.textContent = words.toLocaleString();
        statChars.textContent = (res.text ? res.text.length : 0).toLocaleString();
        statSegments.textContent = (res.segments ? res.segments.length : 0).toString();

        // Configura Audio Player se o arquivo de áudio estiver disponível
        if (item.audioUrl) {
            audioPlayerContainer.classList.remove("hidden");
            nativeAudio.src = item.audioUrl;
            playBtnIcon.innerHTML = AppIcons.get("play", "ui-icon");
            audioScrubber.value = 0;
            audioCurrentTime.textContent = "00:00";
            if (res.duration) {
                audioTotalTime.textContent = formatTime(res.duration);
            }
            nativeAudio.onerror = () => {
                audioPlayerContainer.classList.add("hidden");
            };
        } else {
            audioPlayerContainer.classList.add("hidden");
            if (nativeAudio) {
                nativeAudio.pause();
                nativeAudio.src = "";
            }
        }

        if (llmActionsCard) llmActionsCard.classList.remove("hidden");
        if (toggleRomanizeBtn) toggleRomanizeBtn.classList.remove("hidden");
        if (saveEditBtn) saveEditBtn.classList.add("hidden");

        renderActiveSegments();
    }

    function renderActiveSegments() {
        if (!state.activeItem || !state.activeItem.result) return;
        const res = state.activeItem.result;

        transcriptBody.className = "transcript-body";
        transcriptBody.innerHTML = "";

        if (!res.segments || res.segments.length === 0) {
            transcriptBody.innerHTML = `<p style="padding: 10px; line-height: 1.6;">${escapeHtml(res.text || 'Nenhum texto detectado.')}</p>`;
            return;
        }

        const query = state.searchQuery;
        let matchCount = 0;

        res.segments.forEach(seg => {
            const hasMatch = !query || seg.text.toLowerCase().includes(query);
            if (!hasMatch) return;
            matchCount++;

            const div = document.createElement("div");
            div.className = "segment-item";
            div.dataset.start = seg.start;
            div.dataset.end = seg.end;

            const startFmt = formatTime(seg.start);
            const endFmt = formatTime(seg.end);

            let displayText = escapeHtml(seg.text);
            if (query) {
                const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                displayText = displayText.replace(regex, '<mark class="search-highlight">$1</mark>');
            }

            // Word-level karaoke se disponível
            let wordsHtml = '';
            if (seg.words && Array.isArray(seg.words) && seg.words.length > 0 && !query) {
                wordsHtml = seg.words.map(w => {
                    return `<span class="karaoke-word" data-start="${w.start}" data-end="${w.end}">${escapeHtml(w.word)}</span>`;
                }).join(" ");
            } else {
                wordsHtml = displayText;
            }

            let romanizedHtml = '';
            if (state.showRomanized && seg.romanized) {
                romanizedHtml = `<div class="romanized-text">${escapeHtml(seg.romanized)}</div>`;
            }

            div.innerHTML = `
                <div class="timestamp" title="Clique para ouvir este trecho">${startFmt} - ${endFmt}</div>
                <div class="segment-text" contenteditable="true" spellcheck="false" data-id="${seg.id}">${wordsHtml}</div>
                ${romanizedHtml}
            `;

            // Clique no timestamp pula o áudio direto para o ponto inicial se houver áudio
            const timeEl = div.querySelector(".timestamp");
            timeEl.onclick = () => {
                if (nativeAudio && nativeAudio.src) {
                    nativeAudio.currentTime = seg.start;
                    nativeAudio.play();
                    playBtnIcon.innerHTML = AppIcons.get("pause", "ui-icon");
                }
            };

            // Clique na palavra pula para o ponto exato da palavra
            div.querySelectorAll(".karaoke-word").forEach(wEl => {
                wEl.addEventListener("click", (e) => {
                    e.stopPropagation();
                    const wStart = parseFloat(wEl.dataset.start);
                    if (nativeAudio && nativeAudio.src && !isNaN(wStart)) {
                        nativeAudio.currentTime = wStart;
                        nativeAudio.play();
                        playBtnIcon.innerHTML = AppIcons.get("pause", "ui-icon");
                    }
                });
            });

            // Edição inline da transcrição
            const textEl = div.querySelector(".segment-text");
            textEl.addEventListener("input", () => {
                const newText = textEl.innerText.trim();
                seg.text = newText;
                res.text = res.segments.map(s => s.text).join(" ");
                if (saveEditBtn) saveEditBtn.classList.remove("hidden");
            });

            transcriptBody.appendChild(div);
        });

        if (matchCount === 0 && query) {
            transcriptBody.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 30px;">Nenhum trecho encontrado para "${escapeHtml(query)}"</div>`;
        }
    }

    function showErrorInView(item) {
        const displayName = item.file ? item.file.name : (item.filename || "Arquivo");
        transcriptFilename.innerHTML = `
            <span class="card-title-icon">${AppIcons.get("fileText", "ui-icon")}</span>
            <span>${escapeHtml(displayName)}</span>
        `;
        transcriptMeta.style.display = "none";
        exportActions.style.display = "none";
        audioPlayerContainer.classList.add("hidden");
        statsStrip.classList.add("hidden");
        searchWrapper.classList.add("hidden");
        if (llmActionsCard) llmActionsCard.classList.add("hidden");
        if (toggleRomanizeBtn) toggleRomanizeBtn.classList.add("hidden");
        if (saveEditBtn) saveEditBtn.classList.add("hidden");

        transcriptBody.className = "transcript-body";
        transcriptBody.innerHTML = `
            <div style="color: var(--danger); padding: 30px; text-align: center;">
                <div style="width: 48px; height: 48px; margin: 0 auto 12px; color: var(--danger); display: flex; align-items: center; justify-content: center;">
                    ${AppIcons.get("x", "ui-icon ui-icon-xl")}
                </div>
                <h4>Falha na transcrição</h4>
                <p style="margin-top: 8px; font-size: 0.85rem; color: var(--text-muted);">${escapeHtml(item.error || 'Erro desconhecido')}</p>
            </div>
        `;
    }

    function resetTranscriptView() {
        transcriptFilename.innerHTML = `
            <span class="card-title-icon">${AppIcons.get("fileText", "ui-icon")}</span>
            <span>Resultado da Transcrição</span>
        `;
        transcriptMeta.style.display = "none";
        exportActions.style.display = "none";
        audioPlayerContainer.classList.add("hidden");
        statsStrip.classList.add("hidden");
        searchWrapper.classList.add("hidden");
        if (llmActionsCard) llmActionsCard.classList.add("hidden");
        if (toggleRomanizeBtn) toggleRomanizeBtn.classList.add("hidden");
        if (saveEditBtn) saveEditBtn.classList.add("hidden");

        if (nativeAudio) {
            nativeAudio.pause();
            nativeAudio.src = "";
        }

        transcriptBody.className = "transcript-body empty";
        transcriptBody.innerHTML = `
            <div class="placeholder-state">
                <div class="placeholder-icon">${AppIcons.get("fileText", "ui-icon ui-icon-xl")}</div>
                <p>Selecione um arquivo de áudio ou vídeo e clique em "Iniciar Transcrição" para ver o texto com minutagem interativa aqui.</p>
            </div>
        `;
    }

    function formatTime(seconds) {
        if (isNaN(seconds) || seconds < 0) return "00:00";
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function escapeHtml(text) {
        if (!text) return "";
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
