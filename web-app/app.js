function buyProduct(product_id) {
    Telegram.WebApp.sendData(JSON.stringify({
        action: "buy",
        product: product_id
    }));
}
