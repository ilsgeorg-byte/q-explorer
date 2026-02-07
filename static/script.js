document.addEventListener("DOMContentLoaded", function() {
    
    // --- 1. ЛЕЙЗИ ЛОАДИНГ ПО ИМЕНИ ---
    const lazyNameImages = document.querySelectorAll('.lazy-load-by-name');
    
    if (lazyNameImages.length > 0) {
        const loadImage = (img) => {
            const name = img.getAttribute('data-name');
            if (!name) return;

            fetch(`/api/get-artist-image-by-name?name=${encodeURIComponent(name)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.image) {
                        img.src = data.image;
                        img.style.opacity = 0;
                        setTimeout(() => {
                            img.style.transition = 'opacity 0.5s ease';
                            img.style.opacity = 1;
                        }, 50);
                    } else {
                        generateGradient(img);
                    }
                })
                .catch(() => generateGradient(img));
        };

        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadImage(entry.target);
                    obs.unobserve(entry.target);
                }
            });
        });

        lazyNameImages.forEach(img => observer.observe(img));
    }

    // --- 2. ГРАДИЕНТЫ ---
    function generateGradient(element) {
        const hue = Math.floor(Math.random() * 360);
        element.style.background = `linear-gradient(135deg, hsl(${hue}, 40%, 20%), hsl(${hue + 40}, 50%, 40%))`;
        if (element.tagName === 'IMG') {
            element.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
        }
    }

    // --- 3. ЛАЙКИ ---
    const likeButtons = document.querySelectorAll('.btn-like');
    likeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            e.preventDefault();
            this.classList.toggle('liked');
            if (this.classList.contains('liked')) {
                this.innerHTML = '♥';
                this.style.color = '#e50914';
            } else {
                this.innerHTML = '♥';
                this.style.color = '#555';
            }
        });
    });

    // --- 4. МОДАЛЬНОЕ ОКНО ---
    window.openMusicModal = function(link) {
        const modal = document.getElementById('modal');
        const spotifyLink = document.getElementById('spotify-link');
        
        if (link && link !== '#') {
            spotifyLink.href = link;
            spotifyLink.style.display = 'inline-block';
            spotifyLink.innerText = 'Listen on Spotify';
        } else {
            spotifyLink.style.display = 'none';
        }
        modal.style.display = 'flex';
    };

    const modal = document.getElementById('modal');
    const closeBtn = document.getElementById('close-modal-btn');
    
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) modal.style.display = 'none';
        });
    }
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });
    }
});
