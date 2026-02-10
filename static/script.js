/* --- SHARE & UI LOGIC --- */
/* (Toast functions removed) */

/* --- МОДАЛЬНОЕ ОКНО --- */
function openMusicModal(spotifyLink, appleCollectionId, appleTrackId, youtubeLink) {
    document.getElementById('modal-spotify').href = spotifyLink;
    let appleLink = `https://music.apple.com/album/${appleCollectionId}`;
    if (appleTrackId) appleLink += `?i=${appleTrackId}`;
    document.getElementById('modal-apple').href = appleLink;

    // --- DYNAMIC YOUTUBE BUTTON ---
    let ytBtn = document.getElementById('modal-youtube');

    // Если кнопки нет в HTML (пользователь не обновил modal.html), создаем её через JS
    if (!ytBtn) {
        const modalContainer = document.querySelector('.modal-card') || document.querySelector('.modal-content');
        if (modalContainer) {
            ytBtn = document.createElement('a');
            ytBtn.id = 'modal-youtube';
            ytBtn.target = '_blank';
            // Определяем класс кнопки в зависимости от структуры модалки
            ytBtn.className = modalContainer.classList.contains('modal-card') ? 'platform-btn p-youtube' : 'modal-btn m-youtube';
            ytBtn.textContent = 'YouTube Music';

            // Вставляем перед кнопкой отмены
            const cancelBtn = modalContainer.querySelector('.p-cancel') || modalContainer.querySelector('.m-cancel');
            if (cancelBtn) modalContainer.insertBefore(ytBtn, cancelBtn);
            else modalContainer.appendChild(ytBtn);
        }
    }

    if (ytBtn) {
        if (youtubeLink && youtubeLink !== '#' && youtubeLink !== 'None') {
            ytBtn.href = youtubeLink;
            ytBtn.style.display = ''; // Показываем (flex/block)
        } else {
            ytBtn.style.display = 'none';
        }
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

/* --- ИЗБРАННОЕ (API) --- */
function toggleLike(btn, type, id, title, img, sub, link) {
    event.stopPropagation(); event.preventDefault();

    // Анимация сразу для отзывчивости
    const isLiked = btn.classList.contains('liked');
    if (isLiked) btn.classList.remove('liked');
    else btn.classList.add('liked');

    fetch('/api/favorite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, id, title, img, sub, link })
    })
        .then(res => {
            if (res.status === 401) {
                // Если не авторизован -> на страницу входа
                window.location.href = '/login';
            }
            return res.json();
        })
        .then(data => {
            if (data.status === 'added') btn.classList.add('liked');
            else if (data.status === 'removed') btn.classList.remove('liked');
        })
        .catch(err => {
            console.error(err);
            // Откат анимации при ошибке
            if (isLiked) btn.classList.add('liked');
            else btn.classList.remove('liked');
        });
}

function checkLikedStatus() {
    // Получаем список ID избранного с сервера
    fetch('/api/check_favorites')
        .then(res => res.json())
        .then(ids => {
            // ids = ['123', '456', ...]
            const likedSet = new Set(ids);
            document.querySelectorAll('.btn-like').forEach(btn => {
                // Извлекаем ID из onclick атрибута: toggleLike(this, '...', '123', ...)
                const match = btn.getAttribute('onclick').match(/toggleLike\(this, '[^']+', '([^']+)'/);
                if (match && likedSet.has(match[1])) {
                    btn.classList.add('liked');
                }
            });
        })
        .catch(err => console.log('Guest or error checking favorites'));
}

document.addEventListener('DOMContentLoaded', () => {
    // renderFavorites(); // Теперь рендерится на сервере в profile.html
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

/* --- GENRE SEARCH --- */
function goToGenre() {
    const input = document.getElementById('genre-input');
    if (!input) return;
    const val = input.value.trim();
    if (val) {
        // Кодируем, чтобы пробелы превратились в %20 (Thrash Metal -> Thrash%20Metal)
        window.location.href = '/tag/' + encodeURIComponent(val);
    }
}
// Обработка нажатия Enter в поле жанра
document.addEventListener('keypress', (e) => {
    if (e.target.id === 'genre-input' && e.key === 'Enter') {
        goToGenre();
    }
});