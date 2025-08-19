function buyProduct(product_id) {
    // Отправляем данные в Telegram.
    // data.product будет содержать 'vip' или 'booster'.
    Telegram.WebApp.sendData(JSON.stringify({
        action: "buy",
        product: product_id
    }));
}
