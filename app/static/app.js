// Metricool Personal - Frontend Application Logic (Vanilla JS)

let currentVideo = null;
let allAccounts = [];
let selectedAccountIds = new Set();
let allPosts = [];
let isCustomMatrixOpen = false;
let statusFilter = '';
let platformFilter = '';
let activeErrorPost = null;

// ==================== INICIALIZACIÓN ====================
document.addEventListener('DOMContentLoaded', () => {
    initDropzone();
    initDateTimeInput();
    loadDashboardStats();
    loadAccounts();
    loadScheduledPosts();

    // Polling en tiempo real cada 12 segundos para actualizar estados sin refrescar
    setInterval(() => {
        loadDashboardStats();
        if (!document.getElementById('tab-monitor').classList.contains('hidden')) {
            loadScheduledPosts(true);
        }
    }, 12000);

    // Revisar si viene de un callback OAuth (parámetro en URL)
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('account_connected')) {
        const platform = urlParams.get('account_connected');
        showToast(`¡Cuenta de ${platform.toUpperCase()} conectada exitosamente!`, 'success');
        window.history.replaceState({}, document.title, window.location.pathname);
        switchTab('tab-accounts');
    }
});

// ==================== TABS ====================
function switchTab(tabId) {
    ['tab-schedule', 'tab-monitor', 'tab-accounts'].forEach(id => {
        document.getElementById(id).classList.add('hidden');
    });
    document.getElementById(tabId).classList.remove('hidden');

    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('border-indigo-500', 'text-indigo-400');
        btn.classList.add('border-transparent', 'text-slate-400');
    });

    const activeBtnMap = {
        'tab-schedule': 'btnTabSchedule',
        'tab-monitor': 'btnTabMonitor',
        'tab-accounts': 'btnTabAccounts'
    };
    const activeBtn = document.getElementById(activeBtnMap[tabId]);
    if (activeBtn) {
        activeBtn.classList.add('border-indigo-500', 'text-indigo-400');
        activeBtn.classList.remove('border-transparent', 'text-slate-400');
    }

    if (tabId === 'tab-monitor') loadScheduledPosts();
    if (tabId === 'tab-accounts') loadAccounts();
}

// ==================== GESTIÓN DE VIDEO MAESTRO ====================
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('videoFileInput');

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('border-indigo-500', 'bg-indigo-500/5');
    });

    dropzone.addEventListener('dragleave', () => {
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-500/5');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('border-indigo-500', 'bg-indigo-500/5');
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length) {
            handleFileUpload(fileInput.files[0]);
        }
    });
}

function handleFileUpload(file) {
    const validExtensions = ['.mp4', '.mov', '.webm', '.m4v'];
    const extension = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExtensions.includes(extension)) {
        showToast('Formato no permitido. Usa MP4, MOV o WebM', 'error');
        return;
    }

    const dropzoneEmpty = document.getElementById('dropzoneEmpty');
    const progressContainer = document.getElementById('uploadProgressContainer');
    const progressBar = document.getElementById('uploadProgressBar');
    const percentText = document.getElementById('uploadPercentText');

    dropzoneEmpty.classList.add('hidden');
    progressContainer.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/videos/upload', true);

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
            const percent = Math.round((e.loaded / e.total) * 100);
            progressBar.style.width = percent + '%';
            percentText.textContent = percent + '%';
        }
    };

    xhr.onload = () => {
        progressContainer.classList.add('hidden');
        dropzoneEmpty.classList.remove('hidden');

        if (xhr.status === 201) {
            const videoData = JSON.parse(xhr.responseText);
            setLoadedVideo(videoData);
            showToast('Video maestro cargado con éxito', 'success');
        } else {
            showToast('Error al subir video: ' + xhr.responseText, 'error');
        }
    };

    xhr.onerror = () => {
        progressContainer.classList.add('hidden');
        dropzoneEmpty.classList.remove('hidden');
        showToast('Error de red al subir el video', 'error');
    };

    xhr.send(formData);
}

function setLoadedVideo(video) {
    currentVideo = video;
    document.getElementById('dropzone').classList.add('hidden');
    const previewWrapper = document.getElementById('videoPreviewWrapper');
    const player = document.getElementById('previewPlayer');

    player.src = video.preview_url;
    document.getElementById('previewVideoName').textContent = video.filename;
    document.getElementById('previewVideoSize').textContent = (video.filesize / (1024 * 1024)).toFixed(1) + ' MB';
    previewWrapper.classList.remove('hidden');

    // Si el título global está vacío, autocompletar con el nombre del video
    const globalTitle = document.getElementById('globalTitle');
    if (!globalTitle.value.trim()) {
        globalTitle.value = video.filename.replace(/\.[^/.]+$/, "");
    }
}

function removeSelectedVideo() {
    currentVideo = null;
    const player = document.getElementById('previewPlayer');
    player.pause();
    player.src = '';
    document.getElementById('videoPreviewWrapper').classList.add('hidden');
    document.getElementById('dropzone').classList.remove('hidden');
    document.getElementById('videoFileInput').value = '';
}

// ==================== GESTIÓN DE CUENTAS EN FORMULARIO ====================
async function loadAccounts() {
    try {
        const res = await fetch('/api/accounts');
        allAccounts = await res.json();
        renderAccountsCheckboxes();
        renderAccountsGrid();
        updateAccountsStat();
    } catch (e) {
        console.error('Error cargando cuentas:', e);
    }
}

function renderAccountsCheckboxes() {
    const container = document.getElementById('accountsCheckboxList');
    if (!allAccounts.length) {
        container.innerHTML = `
            <div class="text-center py-6 text-slate-500 text-xs">
                <i class="fa-solid fa-user-plus text-2xl text-slate-600 mb-2"></i>
                <p>No tienes cuentas registradas aún.</p>
                <button onclick="switchTab('tab-accounts')" class="mt-2 text-indigo-400 underline font-medium">Conectar cuentas</button>
            </div>
        `;
        return;
    }

    container.innerHTML = allAccounts.map(acc => {
        const isChecked = selectedAccountIds.has(acc.id);
        const iconConfig = getPlatformIcon(acc.platform);

        return `
            <label class="flex items-center justify-between p-3 rounded-xl border ${isChecked ? 'border-indigo-500 bg-indigo-500/10' : 'border-slate-800 bg-slate-950/40'} hover:border-slate-700 cursor-pointer transition">
                <div class="flex items-center gap-3">
                    <input type="checkbox" value="${acc.id}" ${isChecked ? 'checked' : ''} onchange="toggleAccountSelection(${acc.id})" class="w-4 h-4 rounded text-indigo-600 bg-slate-800 border-slate-700 focus:ring-0">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm ${iconConfig.bg} ${iconConfig.color}">
                        <i class="${iconConfig.icon}"></i>
                    </div>
                    <div>
                        <div class="text-xs font-semibold text-slate-200">${escapeHtml(acc.account_name)}</div>
                        <div class="text-[10px] text-slate-400 capitalize">${acc.platform}</div>
                    </div>
                </div>
                <div>
                    <span class="text-[10px] px-2 py-0.5 rounded-full ${acc.has_valid_token ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}">
                        ${acc.has_valid_token ? 'Token Activo' : 'Sin Token'}
                    </span>
                </div>
            </label>
        `;
    }).join('');

    document.getElementById('selectedCountBadge').textContent = `${selectedAccountIds.size} seleccionadas`;
    if (isCustomMatrixOpen) renderCustomMatrixCards();
}

function toggleAccountSelection(accId) {
    if (selectedAccountIds.has(accId)) {
        selectedAccountIds.delete(accId);
    } else {
        selectedAccountIds.add(accId);
    }
    renderAccountsCheckboxes();
}

function selectAllAccounts(selectAll) {
    if (selectAll) {
        allAccounts.forEach(a => selectedAccountIds.add(a.id));
    } else {
        selectedAccountIds.clear();
    }
    renderAccountsCheckboxes();
}

function selectPlatformAccounts(platform) {
    selectedAccountIds.clear();
    allAccounts.filter(a => a.platform.toLowerCase() === platform.toLowerCase()).forEach(a => selectedAccountIds.add(a.id));
    renderAccountsCheckboxes();
}

// ==================== MATRIZ DE COPYS ====================
function initDateTimeInput() {
    const input = document.getElementById('globalScheduledTime');
    const now = new Date();
    now.setMinutes(now.getMinutes() + 10); // Por defecto 10 min en el futuro
    input.value = now.toISOString().slice(0, 16);
}

function setScheduledTimeNow() {
    const input = document.getElementById('globalScheduledTime');
    const now = new Date();
    input.value = now.toISOString().slice(0, 16);
    showToast('Horario ajustado a ejecución inmediata', 'info');
}

function toggleCustomMatrix() {
    isCustomMatrixOpen = !isCustomMatrixOpen;
    const container = document.getElementById('customMatrixContainer');
    const toggle = document.getElementById('customMatrixToggle');
    const dot = document.getElementById('customMatrixDot');

    if (isCustomMatrixOpen) {
        container.classList.remove('hidden');
        toggle.classList.add('bg-indigo-600');
        toggle.classList.remove('bg-slate-800');
        dot.classList.add('translate-x-4', 'bg-white');
        dot.classList.remove('bg-slate-400');
        renderCustomMatrixCards();
    } else {
        container.classList.add('hidden');
        toggle.classList.remove('bg-indigo-600');
        toggle.classList.add('bg-slate-800');
        dot.classList.remove('translate-x-4', 'bg-white');
        dot.classList.add('bg-slate-400');
    }
}

function renderCustomMatrixCards() {
    const container = document.getElementById('customMatrixCards');
    const selectedList = allAccounts.filter(a => selectedAccountIds.has(a.id));

    if (!selectedList.length) {
        container.innerHTML = `
            <div class="text-xs text-slate-500 text-center py-4">
                Selecciona al menos una cuenta para personalizar su copy individualmente.
            </div>
        `;
        return;
    }

    const globalTitle = document.getElementById('globalTitle').value;
    const globalDesc = document.getElementById('globalDescription').value;
    const globalTags = document.getElementById('globalHashtags').value;

    container.innerHTML = selectedList.map(acc => {
        const iconConfig = getPlatformIcon(acc.platform);
        return `
            <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3" data-account-card="${acc.id}">
                <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded flex items-center justify-center text-xs ${iconConfig.bg} ${iconConfig.color}">
                        <i class="${iconConfig.icon}"></i>
                    </div>
                    <span class="text-xs font-semibold text-slate-200">${escapeHtml(acc.account_name)}</span>
                    <span class="text-[10px] text-slate-500 capitalize">(${acc.platform})</span>
                </div>

                <div class="space-y-2">
                    ${acc.platform === 'youtube' ? `
                        <div>
                            <label class="block text-[11px] text-slate-400 mb-1">Título personalizado (YouTube)</label>
                            <input type="text" id="customTitle_${acc.id}" placeholder="${escapeHtml(globalTitle || 'Título del video')}" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200">
                        </div>
                    ` : ''}

                    <div>
                        <label class="block text-[11px] text-slate-400 mb-1">Pie / Descripción personalizada</label>
                        <textarea id="customDesc_${acc.id}" rows="2" placeholder="${escapeHtml(globalDesc || 'Descripción personalizada...')}" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200 resize-none"></textarea>
                    </div>

                    <div>
                        <label class="block text-[11px] text-slate-400 mb-1">Hashtags específicos</label>
                        <input type="text" id="customTags_${acc.id}" placeholder="${escapeHtml(globalTags || '#tags')}" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs text-slate-200">
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ==================== ENVIAR PROGRAMACIÓN MASIVA ====================
async function submitBatchSchedule() {
    if (!currentVideo) {
        showToast('Debes subir un video maestro primero', 'error');
        return;
    }

    if (!selectedAccountIds.size) {
        showToast('Selecciona al menos una cuenta destino', 'error');
        return;
    }

    const globalTitle = document.getElementById('globalTitle').value.trim();
    const globalDescription = document.getElementById('globalDescription').value.trim();
    const globalHashtags = document.getElementById('globalHashtags').value.trim();
    const globalScheduledTime = document.getElementById('globalScheduledTime').value;

    if (!globalScheduledTime) {
        showToast('Selecciona la fecha y hora programada', 'error');
        return;
    }

    const targets = Array.from(selectedAccountIds).map(accId => {
        let title = null;
        let description = null;
        let hashtags = null;

        if (isCustomMatrixOpen) {
            const customTitleEl = document.getElementById(`customTitle_${accId}`);
            const customDescEl = document.getElementById(`customDesc_${accId}`);
            const customTagsEl = document.getElementById(`customTags_${accId}`);

            if (customTitleEl && customTitleEl.value.trim()) title = customTitleEl.value.trim();
            if (customDescEl && customDescEl.value.trim()) description = customDescEl.value.trim();
            if (customTagsEl && customTagsEl.value.trim()) hashtags = customTagsEl.value.trim();
        }

        return {
            account_id: accId,
            title: title,
            description: description,
            hashtags: hashtags
        };
    });

    const payload = {
        video_id: currentVideo.id,
        global_title: globalTitle || null,
        global_description: globalDescription || null,
        global_hashtags: globalHashtags || null,
        global_scheduled_time: new Date(globalScheduledTime).toISOString(),
        targets: targets
    };

    const submitBtn = document.getElementById('btnSubmitSchedule');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner animate-spin"></i><span>Programando...</span>';

    try {
        const res = await fetch('/api/posts/schedule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.status === 201) {
            showToast('¡Publicaciones programadas exitosamente!', 'success');
            loadDashboardStats();
            switchTab('tab-monitor');
        } else {
            const error = await res.json();
            showToast('Error: ' + (error.detail || 'Fallo al programar'), 'error');
        }
    } catch (e) {
        showToast('Error de red al conectar con el servidor', 'error');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-rocket"></i><span>Programar Publicación en Cuentas Seleccionadas</span>';
    }
}

// ==================== MONITOR DE PUBLICACIONES ====================
async function loadScheduledPosts(silent = false) {
    try {
        let url = '/api/posts?';
        if (statusFilter) url += `status=${statusFilter}&`;
        if (platformFilter) url += `platform=${platformFilter}&`;

        const res = await fetch(url);
        allPosts = await res.json();
        renderPostsTable();
    } catch (e) {
        if (!silent) showToast('Error cargando lista de publicaciones', 'error');
    }
}

function renderPostsTable() {
    const tbody = document.getElementById('postsTableBody');
    if (!allPosts.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="px-4 py-12 text-center text-slate-500">
                    <i class="fa-solid fa-calendar-xmark text-3xl mb-2 text-slate-600 block"></i>
                    No se encontraron publicaciones con los filtros seleccionados.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = allPosts.map(post => {
        const iconConfig = getPlatformIcon(post.platform);
        const statusConfig = getStatusBadge(post.status);
        const scheduledDate = new Date(post.scheduled_time).toLocaleString();

        return `
            <tr class="hover:bg-slate-800/30 transition">
                <!-- Plataforma y Cuenta -->
                <td class="px-4 py-3.5">
                    <div class="flex items-center gap-2.5">
                        <div class="w-7 h-7 rounded-lg flex items-center justify-center text-xs ${iconConfig.bg} ${iconConfig.color}">
                            <i class="${iconConfig.icon}"></i>
                        </div>
                        <div>
                            <div class="font-semibold text-xs text-white">${escapeHtml(post.account_name || 'Cuenta')}</div>
                            <div class="text-[10px] text-slate-400 capitalize">${post.platform}</div>
                        </div>
                    </div>
                </td>

                <!-- Video -->
                <td class="px-4 py-3.5 text-xs text-slate-300 max-w-[150px] truncate" title="${escapeHtml(post.video_filename || '')}">
                    <i class="fa-solid fa-file-video text-slate-500 mr-1"></i>
                    ${escapeHtml(post.video_filename || 'Video')}
                </td>

                <!-- Copy / Título -->
                <td class="px-4 py-3.5 max-w-[200px]">
                    <div class="text-xs font-medium text-slate-200 truncate">${escapeHtml(post.title || post.description || 'Sin título')}</div>
                    ${post.hashtags ? `<div class="text-[10px] text-indigo-400 truncate">${escapeHtml(post.hashtags)}</div>` : ''}
                </td>

                <!-- Fecha Programada -->
                <td class="px-4 py-3.5 text-xs text-slate-400 whitespace-nowrap">
                    ${scheduledDate}
                </td>

                <!-- Estado -->
                <td class="px-4 py-3.5 whitespace-nowrap">
                    <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.badgeClass}">
                        <i class="${statusConfig.icon}"></i>
                        <span>${statusConfig.label}</span>
                    </div>

                    ${post.status === 'PUBLISHED' && post.post_url ? `
                        <a href="${post.post_url}" target="_blank" class="ml-2 text-indigo-400 hover:text-indigo-300 text-xs inline-flex items-center gap-1 font-semibold underline">
                            <span>Ver post</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[10px]"></i>
                        </a>
                    ` : ''}

                    ${post.status === 'FAILED' ? `
                        <button onclick="openErrorModal(${post.id})" class="ml-2 text-rose-400 hover:text-rose-300 text-xs inline-flex items-center gap-1 underline font-semibold">
                            <span>Detalle error</span>
                        </button>
                    ` : ''}
                </td>

                <!-- Acciones -->
                <td class="px-4 py-3.5 text-right whitespace-nowrap">
                    <div class="flex items-center justify-end gap-1.5">
                        ${post.status === 'FAILED' ? `
                            <button onclick="retrySinglePost(${post.id})" title="Reintentar Publicación" class="p-1.5 rounded-lg bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 transition">
                                <i class="fa-solid fa-rotate-right"></i>
                            </button>
                        ` : ''}
                        
                        <button onclick="deleteSinglePost(${post.id})" title="Eliminar / Cancelar" class="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 transition">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function filterPosts(type, value) {
    if (type === 'status') {
        statusFilter = value;
        document.querySelectorAll('.status-filter-btn').forEach(btn => {
            btn.classList.remove('active', 'bg-indigo-600', 'text-white');
            btn.classList.add('bg-slate-800', 'text-slate-300');
        });
        event.target.classList.add('active', 'bg-indigo-600', 'text-white');
        event.target.classList.remove('bg-slate-800', 'text-slate-300');
    } else if (type === 'platform') {
        platformFilter = value;
    }
    loadScheduledPosts();
}

async function retrySinglePost(postId) {
    try {
        const res = await fetch(`/api/posts/${postId}/retry`, { method: 'POST' });
        if (res.ok) {
            showToast('Publicación reactivada para reintento inmediato', 'success');
            loadScheduledPosts();
            loadDashboardStats();
            closeErrorModal();
        } else {
            showToast('No se pudo reintentar la publicación', 'error');
        }
    } catch (e) {
        showToast('Error de red al reintentar', 'error');
    }
}

async function deleteSinglePost(postId) {
    if (!confirm('¿Estás seguro de cancelar o eliminar esta publicación?')) return;
    try {
        const res = await fetch(`/api/posts/${postId}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Publicación eliminada', 'info');
            loadScheduledPosts();
            loadDashboardStats();
        }
    } catch (e) {
        showToast('Error al eliminar', 'error');
    }
}

// ==================== GESTIÓN DE CUENTAS ====================
function renderAccountsGrid() {
    const grid = document.getElementById('accountsCardsGrid');
    if (!allAccounts.length) {
        grid.innerHTML = `
            <div class="col-span-full py-12 text-center text-slate-500">
                <i class="fa-solid fa-users-slash text-4xl mb-3 text-slate-600 block"></i>
                <p class="text-sm font-medium">Aún no tienes cuentas vinculadas.</p>
                <p class="text-xs text-slate-400 mt-1">Conecta tus cuentas de YouTube, Instagram Reels y TikTok usando los botones superiores.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = allAccounts.map(acc => {
        const iconConfig = getPlatformIcon(acc.platform);
        return `
            <div class="bg-slate-900 border border-slate-800 p-5 rounded-2xl shadow-sm space-y-4">
                <div class="flex items-start justify-between">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl flex items-center justify-center text-lg ${iconConfig.bg} ${iconConfig.color}">
                            <i class="${iconConfig.icon}"></i>
                        </div>
                        <div>
                            <h3 class="text-sm font-semibold text-white">${escapeHtml(acc.account_name)}</h3>
                            <span class="text-xs text-slate-400 capitalize">${acc.platform}</span>
                        </div>
                    </div>
                    <button onclick="deleteAccount(${acc.id})" title="Eliminar cuenta" class="text-slate-500 hover:text-rose-400 text-sm p-1 transition">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>

                <div class="bg-slate-950 p-3 rounded-xl border border-slate-800/80 space-y-1.5 text-xs">
                    <div class="flex justify-between text-slate-400">
                        <span>ID Plataforma:</span>
                        <span class="font-mono text-slate-200 truncate max-w-[130px]">${acc.platform_user_id || 'Autenticado'}</span>
                    </div>
                    <div class="flex justify-between items-center text-slate-400">
                        <span>Estado Token:</span>
                        <span class="px-2 py-0.5 rounded-full text-[10px] ${acc.has_valid_token ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}">
                            ${acc.has_valid_token ? 'Válido' : 'Requiere renovación'}
                        </span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

async function deleteAccount(accountId) {
    if (!confirm('¿Seguro que deseas desvincular esta cuenta? Las publicaciones pendientes para esta cuenta podrían fallar.')) return;
    try {
        const res = await fetch(`/api/accounts/${accountId}`, { method: 'DELETE' });
        if (res.ok) {
            showToast('Cuenta desvinculada', 'info');
            loadAccounts();
        }
    } catch (e) {
        showToast('Error al desvincular cuenta', 'error');
    }
}

// ==================== OAUTH Y TOKENS MANUALES ====================
function openOAuthConnectModal() {
    document.getElementById('oauthConnectModal').classList.remove('hidden');
}

function closeOAuthModal() {
    document.getElementById('oauthConnectModal').classList.add('hidden');
}

async function startOAuthFlow(platform) {
    try {
        const res = await fetch(`/api/auth/${platform}/url`);
        if (res.ok) {
            const data = await res.json();
            if (data.url) {
                window.location.href = data.url;
            }
        } else {
            const err = await res.json();
            showToast('Configura primero las credenciales en .env: ' + (err.detail || ''), 'error');
        }
    } catch (e) {
        showToast('Error de conexión con el endpoint de autenticación', 'error');
    }
}

function openManualAccountModal() {
    document.getElementById('manualAccountModal').classList.remove('hidden');
}

function closeManualAccountModal() {
    document.getElementById('manualAccountModal').classList.add('hidden');
}

async function saveManualAccount() {
    const platform = document.getElementById('manualPlatform').value;
    const accountName = document.getElementById('manualAccountName').value.trim();
    const userId = document.getElementById('manualUserId').value.trim();
    const token = document.getElementById('manualAccessToken').value.trim();
    const refresh = document.getElementById('manualRefreshToken').value.trim();

    if (!accountName || !token) {
        showToast('El nombre de la cuenta y el token son obligatorios', 'error');
        return;
    }

    try {
        const res = await fetch('/api/accounts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                platform: platform,
                account_name: accountName,
                platform_user_id: userId || null,
                access_token: token,
                refresh_token: refresh || null,
                is_active: true
            })
        });

        if (res.status === 201) {
            showToast('Cuenta añadida exitosamente', 'success');
            closeManualAccountModal();
            loadAccounts();
        } else {
            const err = await res.json();
            showToast('Error: ' + (err.detail || 'Fallo al guardar'), 'error');
        }
    } catch (e) {
        showToast('Error de red al registrar cuenta', 'error');
    }
}

// ==================== MODAL DE ERROR ====================
function openErrorModal(postId) {
    const post = allPosts.find(p => p.id === postId);
    if (!post) return;

    activeErrorPost = post;
    document.getElementById('errorModalContent').textContent = post.error_detail || 'No se registraron detalles del error.';
    document.getElementById('btnRetryFromModal').onclick = () => retrySinglePost(post.id);
    document.getElementById('errorDetailModal').classList.remove('hidden');
}

function closeErrorModal() {
    document.getElementById('errorDetailModal').classList.add('hidden');
    activeErrorPost = null;
}

// ==================== ESTADÍSTICAS Y CRON ====================
async function loadDashboardStats() {
    try {
        const res = await fetch('/api/posts/stats');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('statAccounts').textContent = data.total_accounts;
            document.getElementById('statVideos').textContent = data.total_videos;
            document.getElementById('statPending').textContent = data.pending_posts;
            document.getElementById('statPublishing').textContent = data.publishing_posts;
            document.getElementById('statPublished').textContent = data.published_posts;
            document.getElementById('statFailed').textContent = data.failed_posts;
        }
    } catch (e) {}
}

function updateAccountsStat() {
    document.getElementById('statAccounts').textContent = allAccounts.length;
}

async function triggerCronManually() {
    try {
        showToast('Ejecutando revisión forzada de publicaciones...', 'info');
        const res = await fetch('/api/cron/trigger?secret=supersecret_cron_key_cambiame');
        if (res.ok) {
            const data = await res.json();
            const r = data.result || {};
            showToast(`Revisión completada: ${r.found_due_posts || 0} publicaciones procesadas (${r.success || 0} exitosas, ${r.failed || 0} errores)`, 'success');
            loadScheduledPosts();
            loadDashboardStats();
        } else {
            showToast('Fallo al ejecutar disparador de cron', 'error');
        }
    } catch (e) {
        showToast('Error conectando al webhook de cron', 'error');
    }
}

// ==================== HELPERS ====================
function getPlatformIcon(platform) {
    switch ((platform || '').toLowerCase()) {
        case 'youtube':
            return { icon: 'fa-brands fa-youtube', bg: 'bg-red-500/10', color: 'text-red-500' };
        case 'instagram':
            return { icon: 'fa-brands fa-instagram', bg: 'bg-pink-500/10', color: 'text-pink-500' };
        case 'tiktok':
            return { icon: 'fa-brands fa-tiktok', bg: 'bg-cyan-500/10', color: 'text-cyan-400' };
        default:
            return { icon: 'fa-solid fa-share-nodes', bg: 'bg-slate-800', color: 'text-slate-400' };
    }
}

function getStatusBadge(status) {
    switch (status) {
        case 'PENDING':
            return { label: 'Pendiente', icon: 'fa-solid fa-clock', badgeClass: 'bg-amber-500/10 text-amber-300 border border-amber-500/20' };
        case 'PUBLISHING':
            return { label: 'Publicando', icon: 'fa-solid fa-spinner animate-spin', badgeClass: 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/20 anim-pulse' };
        case 'PUBLISHED':
            return { label: 'Publicado', icon: 'fa-solid fa-circle-check', badgeClass: 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/20' };
        case 'FAILED':
            return { label: 'Fallido', icon: 'fa-solid fa-triangle-exclamation', badgeClass: 'bg-rose-500/10 text-rose-300 border border-rose-500/20' };
        default:
            return { label: status, icon: 'fa-solid fa-circle-info', badgeClass: 'bg-slate-800 text-slate-400' };
    }
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMsg = document.getElementById('toastMessage');
    const toastIcon = document.getElementById('toastIcon');

    toastMsg.textContent = message;

    if (type === 'success') {
        toastIcon.className = 'fa-solid fa-circle-check text-emerald-400 text-lg';
    } else if (type === 'error') {
        toastIcon.className = 'fa-solid fa-circle-xmark text-rose-400 text-lg';
    } else {
        toastIcon.className = 'fa-solid fa-circle-info text-cyan-400 text-lg';
    }

    toast.classList.remove('translate-y-24', 'opacity-0');
    setTimeout(() => {
        toast.classList.add('translate-y-24', 'opacity-0');
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.toString().replace(/[&<>"']/g, m => map[m]);
}
