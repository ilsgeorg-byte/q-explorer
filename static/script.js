 function openMusicModal(spotifyLink, appleCollectionId, appleTrackId) {
            document.getElementById('modal-spotify').href = spotifyLink;
            let appleLink = `https://music.apple.com/album/${appleCollectionId}`;
            if (appleTrackId) { appleLink += `?i=${appleTrackId}`; }
            document.getElementById('modal-apple').href = appleLink; 
            document.getElementById('music-modal').style.display = 'flex';
        }
        function closeMusicModal() { document.getElementById('music-modal').style.display = 'none'; }
        
        function getFavs() { return JSON.parse(localStorage.getItem('q_favs') || '[]'); }
        function saveFavs(favs) { localStorage.setItem('q_favs', JSON.stringify(favs)); renderFavorites(); }
        function toggleLike(btn, type, id, title, img, sub, link) {
            event.stopPropagation();
            let favs = getFavs();
            const index = favs.findIndex(f => f.id === id);
            if (index > -1) { favs.splice(index, 1); btn.classList.remove('liked'); } 
            else { favs.unshift({ type, id, title, img, sub, link }); btn.classList.add('liked'); }
            saveFavs(favs);
        }
        function checkLikedStatus() {
            let favs = getFavs();
            document.querySelectorAll('.btn-like').forEach(btn => {
                const idMatch = btn.getAttribute('onclick').match(/'(\d+)'/);
                if (idMatch && favs.find(f => f.id === idMatch[1])) { btn.classList.add('liked'); }
            });
        }
        function renderFavorites() {
            const favs = getFavs();
            const container = document.getElementById('favorites-section');
            const grid = document.getElementById('favorites-grid');
            if (favs.length === 0) { container.style.display = 'none'; return; }
            container.style.display = 'block';
            grid.innerHTML = favs.map(f => {
                let href = f.type === 'artist' ? `/artist/${f.id}` : (f.type === 'album' ? `/album/${f.id}` : '#');
                let imgStyle = f.type === 'artist' ? 'border-radius:50%; width:80%; margin:10% auto;' : 'width:100%';
                let onclick = f.type === 'song' ? `onclick="openMusicModal('${f.link}', '${f.sub}', '')"` : ''; // Note: Favs don't store collectionId, so we fallback to basic link or improve storage later
                return `<div class="card" style="position:relative;" ${onclick}><div class="btn-like liked" onclick="toggleLike(this, '${f.type}', '${f.id}', '', '', '', '')">♥</div><a href="${href}" style="text-decoration:none; color:inherit; display:block;"><img src="${f.img || ''}" style="${imgStyle}"><div class="info"><div class="title">${f.title}</div><div class="sub">${f.sub || ''}</div></div></a></div>`;
            }).join('');
        }
        function clearFavorites() { if(confirm('Clear?')) saveFavs([]); }
        function getHistory() { return JSON.parse(localStorage.getItem('q_history') || '[]'); }
        function saveHistory() { const val = document.getElementById('search-input').value.trim(); if (!val) return; let hist = getHistory(); hist = hist.filter(h => h !== val); hist.unshift(val); if (hist.length > 5) hist.pop(); localStorage.setItem('q_history', JSON.stringify(hist)); }
        function showHistory() { const hist = getHistory(); const dd = document.getElementById('history-dropdown'); if (hist.length === 0) { dd.style.display = 'none'; return; } dd.innerHTML = hist.map(h => `<div class="history-item" onclick="setSearch('${h}')"><span class="history-text">🕒 ${h}</span><span class="history-remove" onclick="removeHistory(event, '${h}')">×</span></div>`).join(''); dd.style.display = 'block'; }
        function hideHistory() { document.getElementById('history-dropdown').style.display = 'none'; }
        function setSearch(val) { document.getElementById('search-input').value = val; document.querySelector('.search-form').submit(); }
        function removeHistory(e, val) { e.stopPropagation(); let hist = getHistory().filter(h => h !== val); localStorage.setItem('q_history', JSON.stringify(hist)); if(hist.length === 0) document.getElementById('history-dropdown').style.display = 'none'; else showHistory(); document.getElementById('search-input').focus(); }
        document.addEventListener('DOMContentLoaded', () => { renderFavorites(); checkLikedStatus(); });