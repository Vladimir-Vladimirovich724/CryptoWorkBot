// Это пример функции для закрытия приложения
document.getElementById('closeButton').addEventListener('click', () => {
    // Это специальная функция из библиотеки Telegram Web App
    if (window.Telegram.WebApp) {
        window.Telegram.WebApp.close();
    }
});
