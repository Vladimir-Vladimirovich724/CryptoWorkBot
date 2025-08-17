function buyProduct(product_id) {
    let url = `https://t.me/CryptoWorkBot?startapp=buy_` + product_id;
    Telegram.WebApp.openTelegramLink(url);
}
