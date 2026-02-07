document.addEventListener("DOMContentLoaded", function() {
    
    // 1. Генерация случайных градиентов для артистов без фото (Tag Page)
    // Находит все картинки с классом lazy-grad и дает им уникальный цвет
    const lazyImages = document.querySelectorAll('.lazy-grad');
    lazyImages.forEach(img => {
        // Генерируем случайный оттенок (Hue) от 0 до 360
        const hue = Math.floor(Math.random() * 360);
        // Создаем градиент
        img.style.background = `linear-gradient(135deg, hsl(${hue}, 40%, 20%), hsl(${hue + 40}, 50%, 40%))`;
    });

    // 2. Обработка клика по лайку (чтобы не запускать песню)
    const likeButtons = document.querySelectorAll('.btn-like');
    likeButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation(); // Останавливаем всплытие (чтобы не сработал клик по строке)
            this.classList.toggle('liked'); // Меняем цвет
            
            // Здесь можно добавить AJAX запрос для сохранения лайка
            // fetch('/api/like', { method: 'POST', body: ... })
            
            if (this.classList.contains('liked')) {
                // Анимация или логика для лайка
                console.log("Liked!");
            }
        });
    });

});

// 3. Логика модального окна
function openMusicModal(link) {
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
}

function closeModal(event) {
    // Закрываем, если кликнули по темному фону (id="modal")
    if (event.target.id === 'modal') {
        document.getElementById('modal').style.display = 'none';
    }
}
