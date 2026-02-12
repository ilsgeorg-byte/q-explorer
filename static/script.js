/* --- SHARE & UI LOGIC --- */
let currentModalTrack = null; // Store metadata for "Add to Playlist" from modal


/* --- MODAL WINDOW --- */
function openMusicModal(spotifyLink, appleCollectionId, appleTrackId, youtubeLink, trackTitle, artistName, imgUrl) {
    document.getElementById('modal-spotify').href = spotifyLink;
    let appleLink = `https://music.apple.com/album/${appleCollectionId}`;
    if (appleTrackId) appleLink += `?i=${appleTrackId}`;
    document.getElementById('modal-apple').href = appleLink;

    // Store metadata for playlist picker
    currentModalTrack = {
        id: appleTrackId || appleCollectionId,
        albumId: appleCollectionId,
        title: trackTitle,
        artist: artistName,
        img: imgUrl
    };

    // --- YOUTUBE BUTTON ---
    let ytBtn = document.getElementById('modal-youtube');

    if (ytBtn) {
        if (youtubeLink && youtubeLink !== '#' && youtubeLink !== 'None') {
            ytBtn.href = youtubeLink;
            ytBtn.style.display = 'block'; // Ensure it's visible if link exists
        } else {
            ytBtn.style.display = 'none';
        }
    }

    document.getElementById('music-modal').style.display = 'flex';
}
function closeMusicModal() { document.getElementById('music-modal').style.display = 'none'; }

/* --- HISTORY --- */
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

/* --- FAVORITES (API) --- */
function toggleLike(btn, type, id, title, img, sub, link) {
    event.stopPropagation(); event.preventDefault();

    // Animation for responsiveness
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
                // If not authorized -> redirect to login page
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
            // Rollback animation on error
            if (isLiked) btn.classList.add('liked');
            else btn.classList.remove('liked');
        });
}

function checkLikedStatus() {
    // Get favorites IDs from server
    fetch('/api/check_favorites')
        .then(res => res.json())
        .then(ids => {
            // ids = ['123', '456', ...]
            const likedSet = new Set(ids);
            document.querySelectorAll('.btn-like').forEach(btn => {
                // Extract ID from onclick attribute: toggleLike(this, '...', '123', ...)
                const match = btn.getAttribute('onclick').match(/toggleLike\(this, '[^']+', '([^']+)'/);
                if (match && likedSet.has(match[1])) {
                    btn.classList.add('liked');
                }
            });
        })
        .catch(err => console.log('Guest or error checking favorites'));
}

document.addEventListener('DOMContentLoaded', () => {
    // renderFavorites(); // Now rendered on server in profile.html
    checkLikedStatus();

    // Placeholder with hints
    const hints = ["Pink Floyd", "Metallica", "Taylor Swift", "Queen", "Hans Zimmer", "The Beatles", "Eminem"];
    const input = document.querySelector('input[name="q"]');
    if (input) input.placeholder = "Try: " + hints[Math.floor(Math.random() * hints.length)];

    // To top button
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
                    img.style.opacity = '0'; // Hidden
                    img.style.transition = 'opacity 0.5s'; // Smooth fade-in
                    img.onload = () => { img.style.opacity = '1'; };

                    wrapper.innerHTML = ''; // Remove placeholder
                    wrapper.appendChild(img);
                }
            })
            .catch(err => console.log('No image for', artistId || artistName));
    };

    // Use Observer instead of setTimeout for real lazy loading
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

// LOADER
const loader = document.getElementById('global-loader');
const form = document.querySelector('form');
if (form) form.addEventListener('submit', () => { if (loader) loader.style.display = 'flex'; });

// Event delegation for links
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
        // Encode spaces to %20 (Thrash Metal -> Thrash%20Metal)
        window.location.href = '/tag/' + encodeURIComponent(val);
    }
}
// Handle Enter key in genre field
document.addEventListener('keypress', (e) => {
    if (e.target.id === 'genre-input' && e.key === 'Enter') {
        goToGenre();
    }
});

/* --- PLAYLISTS --- */
function showCreatePlaylistModal() {
    const modal = document.getElementById('create-playlist-modal');
    if (modal) modal.style.display = 'flex';
}

function closeCreatePlaylistModal() {
    const modal = document.getElementById('create-playlist-modal');
    if (modal) modal.style.display = 'none';
}

function confirmCreatePlaylist() {
    const nameInput = document.getElementById('playlist-name');
    const descInput = document.getElementById('playlist-desc');
    const name = nameInput ? nameInput.value.trim() : "";
    const description = descInput ? descInput.value.trim() : "";

    if (!name) {
        alert('Please enter a playlist name');
        return;
    }

    fetch('/api/playlists/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                window.location.reload();
            } else {
                alert('Error creating playlist: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => console.error(err));
}

function deletePlaylist(playlistId, confirmFirst = false) {
    if (confirmFirst && !confirm('Are you sure you want to delete this playlist?')) return;

    fetch(`/api/playlists/delete/${playlistId}`, {
        method: 'POST'
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'deleted') {
                window.location.href = '/playlists';
            } else {
                alert('Error deleting playlist');
            }
        })
        .catch(err => console.error(err));
}

function removeFromPlaylist(playlistId, trackId) {
    if (!confirm('Remove track from playlist?')) return;

    fetch('/api/playlists/remove-track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playlist_id: playlistId, track_id: trackId })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'removed') {
                window.location.reload();
            } else {
                alert('Error removing track');
            }
        })
        .catch(err => console.error(err));
}

/* --- PLAYLIST PICKER --- */
function triggerPlaylistPickerFromModal() {
    if (!currentModalTrack) return;
    closeMusicModal();
    showPlaylistPicker(null, currentModalTrack.id, currentModalTrack.title, currentModalTrack.artist, currentModalTrack.img);
}

function showPlaylistPicker(btn, trackId, title, artist, img) {
    if (btn) event.stopPropagation(); // Stop navigation if clicked from a row

    // Store metadata globally for addToPlaylist
    window.pendingTrack = { id: trackId, title, artist, img };

    const modal = document.getElementById('playlist-picker-modal');
    const list = document.getElementById('playlist-picker-list');
    if (modal) modal.style.display = 'flex';
    if (list) list.innerHTML = '<div class="loader-inner">Loading playlists...</div>';

    fetch('/api/playlists/list')
        .then(res => {
            if (res.status === 401) {
                window.location.href = '/login';
                return;
            }
            return res.json();
        })
        .then(data => {
            if (!data || data.length === 0) {
                list.innerHTML = `<div style="padding:20px; text-align:center;">
                    You have no playlists.<br><br>
                    <button class="btn btn-primary" onclick="showCreatePlaylistModal(); closePlaylistPicker();">Create First Playlist</button>
                </div>`;
                return;
            }
            list.innerHTML = data.map(p => `
                <div class="playlist-picker-item" onclick="confirmAddToPlaylist(${p.id})">
                    <span>📁 ${p.name}</span>
                    <span class="count">${p.count} tracks</span>
                </div>
            `).join('');
        })
        .catch(err => {
            list.innerHTML = '<div style="padding:20px; color:red;">Error loading playlists</div>';
        });
}

function closePlaylistPicker() {
    const modal = document.getElementById('playlist-picker-modal');
    if (modal) modal.style.display = 'none';
}

function confirmAddToPlaylist(playlistId) {
    if (!window.pendingTrack) return;

    fetch('/api/playlists/add-track', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            playlist_id: playlistId,
            track: window.pendingTrack
        })
    })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'added') {
                alert('Track added to playlist!');
                closePlaylistPicker();
            } else if (data.status === 'already_exists') {
                alert('Track is already in this playlist');
            } else {
                alert('Error: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(err => console.error(err));
}
/* --- PLAYLIST STREAMING --- */
function playPlaylist(playlistId) {
    if (loader) loader.style.display = 'flex';

    fetch(`/api/playlists/list`)
        .then(res => res.json())
        .then(playlists => {
            const playlist = playlists.find(p => p.id === playlistId);
            if (!playlist) throw new Error('Playlist not found');

            // Get playlist details (tracks)
            return fetch(`/playlist/${playlistId}?json=1`)
                .then(res => res.json())
                .then(data => {
                    openPlaylistStreamingModal(playlist.name, data.tracks);
                });
        })
        .catch(err => {
            console.error(err);
            alert('Error loading playlist data');
        })
        .finally(() => {
            if (loader) loader.style.display = 'none';
        });
}

function openPlaylistStreamingModal(playlistName, songs) {
    const modal = document.getElementById('playlist-streaming-modal');
    document.getElementById('ps-title').innerText = playlistName;
    currentPlaylistSongs = songs || [];

    // 1. YouTube Music Search (by playlist name)
    const ytSearchBtn = document.getElementById('ps-yt-search');
    ytSearchBtn.href = `https://music.youtube.com/search?q=${encodeURIComponent(playlistName)}`;

    // 2. First Track options (Spotify, Apple Music)
    const spotifyBtn = document.getElementById('ps-spotify');
    const appleBtn = document.getElementById('ps-apple');

    if (songs && songs.length > 0) {
        const first = songs[0];

        // Spotify first track (search fallback if no link)
        spotifyBtn.style.display = 'block';
        spotifyBtn.href = `https://open.spotify.com/search/${encodeURIComponent(first.title + ' ' + first.artist_name)}`;

        // Apple Music first track
        appleBtn.style.display = 'block';
        const parts = first.track_id.split('|');
        const albumId = parts[0];
        const trackId = parts.length > 1 ? parts[1] : parts[0];
        appleBtn.href = `https://music.apple.com/album/${albumId}?i=${trackId}`;
    } else {
        spotifyBtn.style.display = 'none';
        appleBtn.style.display = 'none';
    }

    modal.style.display = 'flex';
}

function closePlaylistStreamingModal() {
    document.getElementById('playlist-streaming-modal').style.display = 'none';
}

/* --- TRACK LIST COPYING --- */
let currentPlaylistSongs = [];

function copyTrackList() {
    if (!currentPlaylistSongs || currentPlaylistSongs.length === 0) {
        alert("No tracks to copy");
        return;
    }

    const text = currentPlaylistSongs.map(s => `${s.artist_name} - ${s.title}`).join('\n');

    navigator.clipboard.writeText(text).then(() => {
        const status = document.getElementById('ps-copy-status');
        if (status) {
            status.style.opacity = '1';
            setTimeout(() => {
                status.style.opacity = '0';
            }, 2000);
        }
    }).catch(err => {
        console.error('Failed to copy: ', err);
        alert('Could not copy to clipboard');
    });
}
