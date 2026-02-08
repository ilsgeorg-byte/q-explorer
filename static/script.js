/* --- SHARE & UI LOGIC --- */
/* (Toast functions removed) */

/* --- МОДАЛЬНОЕ ОКНО --- */
function openMusicModal(spotifyLink, appleCollectionId, appleTrackId, youtubeLink) {
    document.getElementById('modal-spotify').href = spotifyLink;
    let appleLink = `https://music.apple.com/album/${appleCollectionId}`;
    if (appleTrackId) appleLink += `?i=${appleTrackId}`;
    document.getElementById('modal-apple').href = appleLink;

    const ytBtn = document.getElementById('modal-youtube');
    if (ytBtn && youtubeLink) {
        ytBtn.href = youtubeLink;
    }

    document.getElementById('music-modal').style.display = 'flex';
}
function closeMusicModal() { document.getElementById('music-modal').style.display = 'none'; }

/* --- ИСТОРИЯ --- */
function getHistory() { return JSON.parse(localStorage.getItem('q_history') || '[]'); }
function saveHistory(query) {
    if (!query) return;
    let hist = getHistory();
    hist = hist.filter(h => h.toLowerCase() !== query.toLowerCase());
    hist.unshift(query);
    if (hist.length > 5) hist.pop();
    localStorage.setItem('q_history', JSON.stringify(hist));
}
function showHistory() {
    const hist = getHistory();
    const drop = document.getElementById('history-dropdown');
    if (hist.length === 0) { drop.style.display = 'none'; return; }
    drop.innerHTML = hist.map(item => `
        <div class="history-item" onclick="window.location.href='/?q=${encodeURIComponent(item)}'">
            <span>🕒 ${item}</span>
            <span class="history-remove" onclick="removeHistory(event, '${item}')">×</span>
        </div>`).join('');
    drop.style.display = 'block';
}
function removeHistory(e, item) {
    e.stopPropagation();
    let hist = getHistory();
    hist = hist.filter(h => h !== item);
    localStorage.setItem('q_history', JSON.stringify(hist));
    showHistory();
}
document.addEventListener('click', (e) => {
    if (!e.target.closest('.search-container')) {
        const drop = document.getElementById('history-dropdown');
        if (drop) drop.style.display = 'none';
    }
});

/* --- ИЗБРАННОЕ --- */
function getFavs() { return JSON.parse(localStorage.getItem('q_favs') || '[]'); }
function saveFavs(favs) { localStorage.setItem('q_favs', JSON.stringify(favs)); renderFavorites(); }
function clearFavs() { if (confirm('Clear all?')) { localStorage.removeItem('q_favs'); renderFavorites(); checkLikedStatus(); } }

function toggleLike(btn, type, id, title, img, sub, link) {
    event.stopPropagation(); event.preventDefault();
    let favs = getFavs();
    const index = favs.findIndex(f => f.id === id);
    if (index > -1) { favs.splice(index, 1); btn.classList.remove('liked'); }
    else { favs.unshift({ type, id, title, img, sub: sub || '', link }); btn.classList.add('liked'); }
    saveFavs(favs);
}
function checkLikedStatus() {
    let favs = getFavs();
    document.querySelectorAll('.btn-like').forEach(btn => {
        const idMatch = btn.getAttribute('onclick').match(/'(\d+)'/);
        if (idMatch && favs.find(f => f.id === idMatch[1])) btn.classList.add('liked');
    });
}

// ПЕРЕКЛЮЧЕНИЕ ВИДА ИЗБРАННОГО
let isFavExpanded = false;
function toggleFavsView() {
    isFavExpanded = !isFavExpanded;
    const container = document.getElementById('favorites-container');
    const btn = document.getElementById('fav-toggle-btn');
    if (!container || !btn) return;

    if (isFavExpanded) {
        container.classList.remove('scroll-row');
        container.classList.add('grid');
        btn.textContent = 'Collapse';
    } else {
        container.classList.remove('grid');
        container.classList.add('scroll-row');
        btn.textContent = 'See All';
    }
}

function renderFavorites() {
    const favs = getFavs();
    const section = document.getElementById('favorites-section');
    const container = document.getElementById('favorites-container');
    if (!section || !container) return;

    if (favs.length === 0) { section.style.display = 'none'; return; }
    section.style.display = 'block';

    container.innerHTML = favs.map(f => {
        let href = f.type === 'artist' ? `/artist/${f.id}` : (f.type === 'album' ? `/album/${f.id}` : '#');
        let clickAction = f.type === 'song' ? `onclick="openMusicModal('${f.link}', '${f.sub}', '')"` : '';
        let isArtist = f.type === 'artist';

        return `
        <a href="${href}" ${clickAction} class="card fav-card ${isArtist ? 'artist-card' : ''}">
             <div class="btn-like liked" onclick="toggleLike(this, '${f.type}', '${f.id}', '${f.title.replace(/'/g, "\\'")}', '${f.img}', '${(f.sub || '').replace(/'/g, "\\'")}', '${f.link}')">♥</div>
            <div class="card-img-wrapper"><img src="${f.img}" loading="lazy"></div>
            <div class="card-info">
                <div class="title">${f.title}</div>
                <div class="sub">${f.sub || ''}</div>
            </div>
        </a>
        `;
    }).join('');
}

document.addEventListener('DOMContentLoaded', () => {
    renderFavorites();
    checkLikedStatus();

    // Плейсхолдер с подсказками
    const hints = ["Pink Floyd", "Metallica", "Taylor Swift", "Queen", "Hans Zimmer", "The Beatles", "Eminem"];
    const input = document.querySelector('input[name="q"]');
    if (input) input.placeholder = "Try: " + hints[Math.floor(Math.random() * hints.length)];

    // Кнопка наверх
    const scrollTopBtn = document.getElementById('scroll-top');
    if (scrollTopBtn) {
        let ticking = false;
        window.addEventListener('scroll', () => {
            if (!ticking) {
                window.requestAnimationFrame(() => {
                    if (window.scrollY > 300) scrollTopBtn.classList.add('show');
                    else scrollTopBtn.classList.remove('show');
                    ticking = false;
                });
                ticking = true;
            }
        }, { passive: true });
    }

    // LAZY LOADING IMAGES (IntersectionObserver)
    const loadImage = (wrapper) => {
        const artistId = wrapper.getAttribute('data-artist-id');
        const artistName = wrapper.getAttribute('data-artist-name');

        if ((!artistId && !artistName) || wrapper.querySelector('img')) return;

        const url = artistId
            ? `/api/get-artist-image/${artistId}`
            : `/api/get-artist-image-by-name?name=${encodeURIComponent(artistName)}`;

        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.image) {
                    const img = document.createElement('img');
                    img.src = data.image;
                    img.style.opacity = '0'; // Скрыта
                    img.style.transition = 'opacity 0.5s'; // Плавное появление
                    img.onload = () => { img.style.opacity = '1'; };

                    wrapper.innerHTML = ''; // Убираем плейсхолдер
                    wrapper.appendChild(img);
                }
            })
            .catch(err => console.log('No image for', artistId || artistName));
    };

    // Используем Observer вместо setTimeout для реальной ленивой загрузки
    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                loadImage(entry.target);
                obs.unobserve(entry.target);
            }
        });
    }, { rootMargin: '100px' });

    document.querySelectorAll('.artist-img-wrapper').forEach(wrapper => {
        observer.observe(wrapper);
    });
});

// ЛОАДЕР
const loader = document.getElementById('global-loader');
const form = document.querySelector('form');
if (form) form.addEventListener('submit', () => { if (loader) loader.style.display = 'flex'; });

// Делегирование событий для ссылок
document.body.addEventListener('click', (e) => {
    const link = e.target.closest('a');
    if (link) {
        const href = link.getAttribute('href');
        if (href && !href.startsWith('#') && !href.startsWith('javascript') && link.target !== '_blank') {
            if (loader) loader.style.display = 'flex';
        }
    }
});
window.addEventListener('pageshow', () => { if (loader) loader.style.display = 'none'; });