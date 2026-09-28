// Transcribe Studio - Frontend Logic
document.addEventListener("DOMContentLoaded", () => {
    // Estado da aplicação
    const state = {
        mode: "local", // "local" | "cloud"
        files: [], // Array de objetos { id, file, status, result, error }
        activeFileId: null,
        isProcessing: false,
        providers: [],
        localModels: [],
        languages: []
    };

    // Elementos DOM
    const tabLocal = document.getElementById("tab-local");
    const tabCloud = document.getElementById("tab-cloud");
    const localSettings = document.getElementById("local-settings");
    const cloudSettings = document.getElementById("cloud-settings");
    const hardwareBadge = document.getElementById("hardware-badge");

    const localEngineSelect = document.getElementById("local-engine");
    const localModelSelect = document.getElementById("local-model");
    const cloudProviderSelect = document.getElementById("cloud-provider");
    const cloudModelSelect = document.getElementById("cloud-model");
    const cloudApiKeyInput = document.getElementById("cloud-api-key");
    const apiKeyLink = document.getElementById("api-key-link");
    const audioLanguageSelect = document.getElementById("audio-language");
    const audioTaskSelect = document.getElementById("audio-task");

    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("file-input");
    const startTranscribeBtn = document.getElementById("start-transcribe-btn");
    const fileQueueList = document.getElementById("file-queue-list");
    const queueCount = document.getElementById("queue-count");
    const clearQueueBtn = document.getElementById("clear-queue-btn");

    const progressContainer = document.getElementById("progress-container");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const progressMessage = document.getElementById("progress-message");
    const progressPercentage = document.getElementById("progress-percentage");

    const transcriptCard = document.querySelector(".transcript-card");
    const transcriptFilename = document.getElementById("transcript-filename");
    const transcriptMeta = document.getElementById("transcript-meta");
    const metaDuration = document.getElementById("meta-duration");
    const metaLang = document.getElementById("meta-lang");
    const metaEngine = document.getElementById("meta-engine");
    const exportActions = document.getElementById("export-actions");
    const transcriptBody = document.getElementById("transcript-body");

    const copyBtn = document.getElementById("copy-btn");
    const downloadTxt = document.getElementById("download-txt");
    const downloadSrt = document.getElementById("download-srt");
    const downloadVtt = document.getElementById("download-vtt");
    const downloadJson = document.getElementById("download-json");

    // Inicialização
    init();

    async function init() {
        setupTabs();
        setupDragAndDrop();
        setupActions();
        await loadSystemInfo();
        loadSavedApiKeys();
    }

    // Carrega informações do servidor
    async function loadSystemInfo() {
        try {
            const resp = await fetch("/api/info");
            const data = await resp.json();

            // Atualiza Hardware Badge
            if (data.cuda_available) {
                hardwareBadge.textContent = "⚡ Aceleração GPU (CUDA) Ativa";
                hardwareBadge.className = "badge badge-cuda";
            } else {
                hardwareBadge.textContent = "💻 Modo CPU (int8 otimizado)";
                hardwareBadge.className = "badge badge-cpu";
            }

            // Popula motores locais
            if (data.local_engines && localEngineSelect) {
                localEngineSelect.innerHTML = "";
                data.local_engines.forEach(eng => {
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
            hardwareBadge.textContent = "⚠️ Erro de conexão com backend";
        }
    }

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
            fileInput.value = ""; // Reseta para permitir escolher o mesmo arquivo de novo
        });

        clearQueueBtn.addEventListener("click", () => {
            if (state.isProcessing) return;
            state.files = [];
            state.activeFileId = null;
            renderQueue();
            resetTranscriptView();
            updateStartButtonState();
        });
    }

    function addFiles(newFiles) {
        newFiles.forEach(file => {
            state.files.push({
                id: "f_" + Math.random().toString(36).substring(2, 9),
                file: file,
                status: "pending", // pending, processing, completed, error
                result: null,
                error: null
            });
        });
        renderQueue();
        updateStartButtonState();
    }

    function removeFile(fileId) {
        if (state.isProcessing) return;
        state.files = state.files.filter(f => f.id !== fileId);
        if (state.activeFileId === fileId) {
            state.activeFileId = null;
            resetTranscriptView();
        }
        renderQueue();
        updateStartButtonState();
    }

    function renderQueue() {
        queueCount.textContent = state.files.length;
        clearQueueBtn.style.display = state.files.length > 0 ? "block" : "none";

        if (state.files.length === 0) {
            fileQueueList.className = "queue-list empty";
            fileQueueList.innerHTML = `<p class="empty-msg">Nenhum arquivo adicionado ainda.</p>`;
            return;
        }

        fileQueueList.className = "queue-list";
        fileQueueList.innerHTML = "";

        state.files.forEach(item => {
            const div = document.createElement("div");
            div.className = `queue-item ${item.id === state.activeFileId ? "active" : ""}`;
            div.onclick = () => {
                if (item.result) {
                    showTranscriptionResult(item);
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
                <div>
                    <div class="file-name" title="${item.file.name}">${item.file.name}</div>
                    <small style="color: var(--text-muted);">${sizeFormatted}</small>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <span class="file-status-badge ${currentStatus.class}">${currentStatus.label}</span>
                    ${!state.isProcessing ? `<button type="button" class="btn-text" title="Remover" onclick="event.stopPropagation(); window.__removeFile('${item.id}')">✕</button>` : ''}
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

    // Ações de Botões e Exportações
    function setupActions() {
        startTranscribeBtn.addEventListener("click", () => {
            startTranscriptionQueue();
        });

        copyBtn.addEventListener("click", () => {
            const activeItem = state.files.find(f => f.id === state.activeFileId);
            if (!activeItem || !activeItem.result) return;
            navigator.clipboard.writeText(activeItem.result.text);
            const orig = copyBtn.textContent;
            copyBtn.textContent = "✓ Copiado!";
            setTimeout(() => copyBtn.textContent = orig, 1800);
        });

        downloadTxt.addEventListener("click", () => triggerDownload("txt"));
        downloadSrt.addEventListener("click", () => triggerDownload("srt"));
        downloadVtt.addEventListener("click", () => triggerDownload("vtt"));
        downloadJson.addEventListener("click", () => triggerDownload("json"));
    }

    function triggerDownload(format) {
        const activeItem = state.files.find(f => f.id === state.activeFileId);
        if (!activeItem || !activeItem.result) return;

        const content = activeItem.result.exports ? activeItem.result.exports[format] : activeItem.result.text;
        const baseName = activeItem.file.name.substring(0, activeItem.file.name.lastIndexOf('.')) || activeItem.file.name;
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
    }

    // Execução da fila de transcrição
    async function startTranscriptionQueue() {
        if (state.isProcessing) return;
        state.isProcessing = true;
        updateStartButtonState();

        const pendingItems = state.files.filter(f => f.status === "pending" || f.status === "error");

        for (const item of pendingItems) {
            item.status = "processing";
            state.activeFileId = item.id;
            renderQueue();
            showProgress("Enviando arquivo...", 0);

            try {
                const result = await processFile(item);
                item.status = "completed";
                item.result = result;
                showTranscriptionResult(item);
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

        // Dispara o Job em segundo plano para termos progresso real
        const jobResp = await fetch("/api/jobs", {
            method: "POST",
            body: formData
        });

        if (!jobResp.ok) {
            const err = await jobResp.json();
            throw new Error(err.detail || "Falha ao iniciar trabalho de transcrição.");
        }

        const { job_id } = await jobResp.json();

        // Polling do progresso
        return new Promise((resolve, reject) => {
            const interval = setInterval(async () => {
                try {
                    const statusResp = await fetch(`/api/jobs/${job_id}`);
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
            }, 700);
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
        state.activeFileId = item.id;
        renderQueue();

        const res = item.result;
        transcriptFilename.textContent = item.file.name;
        transcriptMeta.style.display = "flex";
        exportActions.style.display = "flex";

        metaDuration.textContent = `⏱️ ${(res.duration || 0).toFixed(1)}s`;
        metaLang.textContent = `🌐 ${res.language ? res.language.toUpperCase() : 'AUTO'}`;
        metaEngine.textContent = `⚡ ${res.provider || 'local'}`;

        transcriptBody.className = "transcript-body";
        transcriptBody.innerHTML = "";

        if (!res.segments || res.segments.length === 0) {
            transcriptBody.innerHTML = `<p style="padding: 10px; line-height: 1.6;">${res.text || 'Nenhum texto detectado.'}</p>`;
            return;
        }

        res.segments.forEach(seg => {
            const div = document.createElement("div");
            div.className = "segment-item";
            const startFmt = formatTime(seg.start);
            const endFmt = formatTime(seg.end);

            div.innerHTML = `
                <div class="timestamp">${startFmt} - ${endFmt}</div>
                <div class="segment-text">${escapeHtml(seg.text)}</div>
            `;
            transcriptBody.appendChild(div);
        });
    }

    function showErrorInView(item) {
        transcriptFilename.textContent = item.file.name;
        transcriptMeta.style.display = "none";
        exportActions.style.display = "none";
        transcriptBody.className = "transcript-body";
        transcriptBody.innerHTML = `
            <div style="color: var(--danger); padding: 20px; text-align: center;">
                <h4>Falha na transcrição</h4>
                <p style="margin-top: 8px; font-size: 0.85rem;">${escapeHtml(item.error || 'Erro desconhecido')}</p>
            </div>
        `;
    }

    function resetTranscriptView() {
        transcriptFilename.textContent = "Resultado da Transcrição";
        transcriptMeta.style.display = "none";
        exportActions.style.display = "none";
        transcriptBody.className = "transcript-body empty";
        transcriptBody.innerHTML = `
            <div class="placeholder-state">
                <span class="placeholder-icon">📄</span>
                <p>Selecione um arquivo de áudio ou vídeo e clique em "Iniciar Transcrição" para ver o texto com minutagem aqui.</p>
            </div>
        `;
    }

    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text;
        return div.innerHTML;
    }
});
