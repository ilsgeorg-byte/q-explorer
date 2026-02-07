document.addEventListener("DOMContentLoaded", function() {
    
    // --- 1. ЛЕЙЗИ ЛОАДИНГ ПО ИМЕНИ (для страницы жанров) ---
    // Находит картинки, у которых есть класс 'lazy-load-by-name' и атрибут data-name
    const lazyNameImages = document.querySelectorAll('.lazy-load-by-name');
    
    if (lazyNameImages.length > 0) {
        // Функция загрузки одной картинки
        const loadImage = (img) => {
            const name = img.getAttribute('data-name');
            if (!name) return;

            // Спрашиваем у нашего сервера фото этого артиста
            fetch(`/api/get-artist-image-by-name?name=${encodeURIComponent(name)}`)
                .then(response => response.json())
                .then(data => {
                    if (data.image) {
                        img.src = data.image; // Подставляем фото
                        img.style.opacity = 0;
                        // Плавное появление
                        setTimeout(() => {
                            img.style.transition = 'opacity 0.5s ease';
                            img.style.opacity = 1;
                        }, 50);
                    } else {
                        // Если фото не нашлось - делаем красивый градиент
                        generateGradient(img);
                    }
                })
                .catch(() => {
                    // Ошибка сети - тоже градиент
                    generateGradient(img);
                });
        };

        // Запускаем наблюдателя (грузим только когда карточка видна на экране)
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    loadImage(entry.target);
                    obs.unobserve(entry.target); // Больше не следим за ней
                }
            });
        });

        lazyNameImages.forEach(img => observer.observe(img));
    }

    // --- 2. ГРАДИЕНТЫ ДЛЯ ПУСТЫХ АВАТАРОК ---
    function generateGradient(element) {
        const hue = Math.floor(Math.random() * 360);
        element.style.background = `linear-gradient(135deg, hsl(${hue}, 40%, 20%), hsl(${hue + 40}, 50%, 40%))`;
        // Если это img, ставим прозрачный пиксель, чтобы background был виден
        if (element.tagName === 'IMG') {
            element.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
        }
    }
    
    // Применяем градиенты сразу к тем, кто явно помечен как lazy-grad
    document.querySelectorAll('.lazy-grad').forEach(el => generateGradient(el));


    // --- 3. ЛАЙКИ (СЕРДЕЧКИ) ---
    const likeButtons = document.querySelectorAll('.btn-like');
    likeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Чтобы клик не открывал песню/альбом
            e.preventDefault();
            
            this.classList.toggle('liked'); // Меняем класс (в CSS он красит в зеленый/красный)
            
            if (this.classList.contains('liked')) {
                this.innerHTML = '♥'; 
                this.style.color = '#e50914'; // Красный лайк
                // Здесь можно добавить запрос на сервер для сохранения
                // console.log("Liked!");
            } else {
                this.innerHTML = '♥'; // Или ♡
                this.style.color = '#555';
            }
        });
    });

    // --- 4. МОДАЛЬНОЕ ОКНО ---
    // Глобальная функция, чтобы её можно было вызывать из HTML (onclick="openMusicModal(...)")
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

    // Закрытие модального окна по клику на фон
    const modal = document.getElementById('modal');
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                modal.style.display = 'none';
            }
        });
    }

});
