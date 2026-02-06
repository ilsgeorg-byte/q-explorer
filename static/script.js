/* --- МОДАЛЬНОЕ ОКНО --- */
function openMusicModal(spotifyLink, appleCollectionId, appleTrackId) {
    document.getElementById('modal-spotify').href = spotifyLink;
    
    let appleLink = `https://music.apple.com/album/${appleCollectionId}`;
    if (appleTrackId) {
        appleLink += `?i=${appleTrackId}`;
    }
    document.getElementById('modal-apple').href = appleLink;
    
    document.getElementById('music-modal').style.display = 'flex';
}

function closeMusicModal() {
    document.getElementById('music-modal').style.display = 'none';
}

/* --- ИЗБРАННОЕ (FAVORITES) --- */
function getFavs() {
    return JSON.parse(localStorage.getItem('q_favs') || '[]');
}

function saveFavs(favs) {
    localStorage.setItem('q_favs', JSON.stringify(favs));
    renderFavorites();
}

function toggleLike(btn, type, id, title, img, sub, link) {
    event.stopPropagation();
    event.preventDefault(); // Чтобы не переходило по ссылке
    
    let favs = getFavs();
    const index = favs.findIndex(f => f.id === id);
    
    if (index > -1) {
        favs.splice(index, 1);
        btn.classList.remove('liked');
    } else {
        favs.unshift({ type, id, title, img, sub, link });
        btn.classList.add('liked');
    }
    saveFavs(favs);
}

function clearFavs() {
    if(confirm('Clear all favorites?')) {
        localStorage.removeItem('q_favs');
        renderFavorites();
        document.querySelectorAll('.liked').forEach(b => b.classList.remove('liked'));
    }
}

function checkLikedStatus() {
    let favs = getFavs();
    document.querySelectorAll('.btn-like').forEach(btn => {
        // Достаем ID из onclick атрибута (немного хардкорно, но работает)
        const onclickStr = btn.getAttribute('onclick');
        const idMatch = onclickStr.match(/'(\d+)'/); 
        if (idMatch && favs.find(f => f.id === idMatch[1])) {
            btn.classList.add('liked');
        }
    });
}

function renderFavorites() {
    const favs = getFavs();
    const container = document.getElementById('favorites-section');
    const grid = document.getElementById('favorites-grid');
    
    if (favs.length === 0) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    grid.innerHTML = favs.map(f => {
        let href = f.type === 'artist' ? `/artist/${f.id}` : (f.type === 'album' ? `/album/${f.id}` : '#');
        let imgStyle = f.type === 'artist' ? 'border-radius:50%; width:80%; margin:10% auto; display:block;' : 'width:100%';
        let clickAction = f.type === 'song' ? `onclick="openMusicModal('${f.link}', '${f.sub}', '')"` : ''; // sub тут используется как collectionId для песен
        
        return `
        <a href="${href}" ${clickAction} class="card ${f.type === 'artist' ? 'artist-card' : ''}">
             <div class="btn-like liked" onclick="toggleLike(this, '${f.type}', '${f.id}', '${f.title.replace(/'/g, "\\'")}', '${f.img}', '${f.sub.replace(/'/g, "\\'")}', '${f.link}')">♥</div>
            <img src="${f.img}" style="${imgStyle}">
            <div class="info">
                <div class="title">${f.title}</div>
                <div class="sub">${f.sub}</div> <!-- sub хранит жанр или имя артиста -->
            </div>
        </a>
        `;
    }).join('');
}

/* --- ИСТОРИЯ ПОИСКА (НОВОЕ) --- */
function getHistory() {
    return JSON.parse(localStorage.getItem('q_history') || '[]');
}

function saveHistory(query) {
    if (!query) return;
    let hist = getHistory();
    hist = hist.filter(h => h.toLowerCase() !== query.toLowerCase()); // Убираем дубли
    hist.unshift(query);
    if (hist.length > 5) hist.pop();
    localStorage.setItem('q_history', JSON.stringify(hist));
}

function showHistory() {
    const hist = getHistory();
    const drop = document.getElementById('history-dropdown');
    
    if (hist.length === 0) {
        drop.style.display = 'none';
        return;
    }
    
    drop.innerHTML = hist.map(item => `
        <div class="history-item" onclick="window.location.href='/?q=${encodeURIComponent(item)}'">
            <span class="history-text">🕒 ${item}</span>
            <span class="history-remove" onclick="removeHistory(event, '${item}')">×</span>
        </div>
    `).join('');
    
    drop.style.display = 'block';
}

function removeHistory(e, item) {
    e.stopPropagation();
    let hist = getHistory();
    hist = hist.filter(h => h !== item);
    localStorage.setItem('q_history', JSON.stringify(hist));
    showHistory(); // Обновляем список
}

// Скрываем историю при клике вне
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
        document.getElementById('history-dropdown').style.display = 'none';
    }
});
