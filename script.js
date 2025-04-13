let currentPage = 1;
const memesPerPage = 10;

async function getCsrfToken() {
    const response = await fetch("/api/csrf_token");
    const data = await response.json();
    return data.csrf_token;
}

function showNotification(message, type) {
    const notification = document.getElementById("notification");
    notification.textContent = message;
    notification.className = `notification ${type}`;
    notification.style.display = "block";
    setTimeout(() => {
        notification.style.display = "none";
    }, 3000);
}

async function checkModerator() {
    const userId = window.Telegram.WebApp.initDataUnsafe.user.id;
    const response = await fetch(`/api/check_moderator?user_id=${userId}`);
    const data = await response.json();
    if (data.isModerator) {
        document.getElementById("moderationTab").style.display = "block";
    }
}

function showTab(tabId) {
    document.querySelectorAll(".tab-content").forEach(tab => tab.classList.remove("active"));
    document.getElementById(tabId).classList.add("active");
}

async function loadMemes(page = 1) {
    try {
        const response = await fetch(`/api/get_memes?page=${page}&limit=${memesPerPage}`);
        const memes = await response.json();
        const memeList = document.getElementById("memeList");
        if (page === 1) memeList.innerHTML = "";
        memes.forEach(meme => {
            const memeDiv = document.createElement("div");
            memeDiv.innerHTML = `
                <h3>${escapeHtml(meme.title)}</h3>
                <p>${escapeHtml(meme.description)}</p>
                <p>Тег: ${escapeHtml(meme.tag)}</p>
                ${meme.isAdult ? '<p>18+</p>' : ''}
                ${meme.mediaUrl ? `<${meme.mediaUrl.endsWith('.mp4') ? 'video' : 'img'} src="${meme.mediaUrl}" ${meme.mediaUrl.endsWith('.mp4') ? 'controls' : ''} alt="meme" style="max-width: 100%;">` : ''}
                <button onclick="likeMeme('${meme._id}')">Лайк (${meme.likes || 0})</button>
                <button onclick="dislikeMeme('${meme._id}')">Дизлайк (${meme.dislikes || 0})</button>
                <div>
                    <input type="text" id="comment_${meme._id}" placeholder="Комментарий">
                    <button onclick="addComment('${meme._id}')">Отправить</button>
                </div>
                <div>${meme.comments ? meme.comments.map(c => `<p>${escapeHtml(c)}</p>`).join("") : ""}</div>
            `;
            memeList.appendChild(memeDiv);
        });
        document.getElementById("loadMore").style.display = memes.length < memesPerPage ? "none" : "block";
    } catch (e) {
        showNotification("Ошибка загрузки мемов", "error");
    }
}

async function loadMoreMemes() {
    currentPage++;
    await loadMemes(currentPage);
}

async function loadModerationMemes() {
    try {
        const response = await fetch("/api/get_moderation_memes");
        const memes = await response.json();
        const moderationList = document.getElementById("moderationList");
        moderationList.innerHTML = "";
        memes.forEach(meme => {
            const memeDiv = document.createElement("div");
            memeDiv.innerHTML = `
                <h3>${escapeHtml(meme.title)}</h3>
                <p>${escapeHtml(meme.description)}</p>
                ${meme.mediaUrl ? `<${meme.mediaUrl.endsWith('.mp4') ? 'video' : 'img'} src="${meme.mediaUrl}" ${meme.mediaUrl.endsWith('.mp4') ? 'controls' : ''} alt="meme" style="max-width: 100%;">` : ''}
                <button onclick="approveMeme('${meme._id}')">Одобрить</button>
                <button onclick="rejectMeme('${meme._id}')">Отклонить</button>
            `;
            moderationList.appendChild(memeDiv);
        });
    } catch (e) {
        showNotification("Ошибка загрузки мемов для модерации", "error");
    }
}

async function likeMeme(memeId) {
    const csrfToken = await getCsrfToken();
    await fetch(`/api/like_meme?meme_id=${memeId}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken }
    });
    loadMemes();
}

async function dislikeMeme(memeId) {
    const csrfToken = await getCsrfToken();
    await fetch(`/api/dislike_meme?meme_id=${memeId}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken }
    });
    loadMemes();
}

async function addComment(memeId) {
    const comment = document.getElementById(`comment_${memeId}`).value;
    const csrfToken = await getCsrfToken();
    await fetch(`/api/add_comment?meme_id=${memeId}&comment=${comment}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken }
    });
    loadMemes();
}

async function approveMeme(memeId) {
    const csrfToken = await getCsrfToken();
    await fetch(`/api/approve_meme?meme_id=${memeId}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken }
    });
    loadModerationMemes();
}

async function rejectMeme(memeId) {
    const csrfToken = await getCsrfToken();
    await fetch(`/api/reject_meme?meme_id=${memeId}`, {
        method: "POST",
        headers: { "X-CSRF-Token": csrfToken }
    });
    loadModerationMemes();
}

function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

document.getElementById("memeForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const csrfToken = await getCsrfToken();
    const formData = new FormData();
    formData.append("title", document.getElementById("title").value);
    formData.append("description", document.getElementById("description").value);
    formData.append("tag", document.getElementById("tag").value);
    formData.append("isAdult", document.getElementById("isAdult").checked);
    formData.append("media", document.getElementById("media").files[0]);
    formData.append("userId", window.Telegram.WebApp.initDataUnsafe.user.id);

    try {
        const response = await fetch("/api/upload_meme", {
            method: "POST",
            headers: { "X-CSRF-Token": csrfToken },
            body: formData
        });
        const result = await response.json();
        if (result.error) {
            showNotification(result.error, "error");
        } else {
            showNotification(result.message, "success");
        }
    } catch (e) {
        showNotification("Ошибка при отправке мема", "error");
    }
});

document.getElementById("darkTheme").addEventListener("change", (e) => {
    document.body.classList.toggle("dark", e.target.checked);
    localStorage.setItem("darkTheme", e.target.checked);
});

window.onload = () => {
    checkModerator();
    showTab("upload");
    loadMemes();
    const darkTheme = localStorage.getItem("darkTheme") === "true";
    document.getElementById("darkTheme").checked = darkTheme;
    document.body.classList.toggle("dark", darkTheme);
};