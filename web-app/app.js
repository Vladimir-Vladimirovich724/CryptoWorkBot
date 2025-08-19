function buyProduct(product_id) {
    // Выводим сообщение в консоль браузера, чтобы убедиться, что функция вызывается.
    console.log("Попытка отправить данные:", { action: "buy", product: product_id });

    // Отправляем данные в Telegram.
    Telegram.WebApp.sendData(JSON.stringify({
        action: "buy",
        product: product_id
    }));
}
