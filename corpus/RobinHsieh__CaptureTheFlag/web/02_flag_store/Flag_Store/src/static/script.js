// static/script.js

document.addEventListener('DOMContentLoaded', function() {
    // 當 DOM 加載完成後執行以下代碼

    // 獲取所有 Buy 按鈕元素
    var buyButtons = document.querySelectorAll('.buy-button');

    // 為每個按鈕添加點擊事件監聽器
    buyButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            // 獲取商品 ID（使用 data 屬性）
            var productId = button.dataset.productId;

            // 執行購買邏輯，向後端發送購買請求
            purchaseProduct(productId);
        });
    });
});

// 定義向後端發送購買請求的函數
function purchaseProduct(productId, userType) {
    // 使用 fetch 函數向後端發送 POST 請求，將用戶類型添加到查詢字符串
    fetch(`/purchase?buyer=${userType}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ productId: productId }),
    })
    .then(response => response.json())
    .then(data => {
        // 在控制台上輸出後端的回應
        updateAmount(data.money);
        alert(data.message);
    })
    .catch(error => {
        console.error('發生錯誤:', error);
        alert("No enough money !!!!!!")
    });
}

// 定義更新顯示金額的函數
function updateAmount(message) {
    var moneyDisplay = document.getElementById('money-display');

    // 更新元素的內容
    moneyDisplay.textContent = message;
}