(() => {
  displaySavedTexts();
  loadWPMFromStorage();

  getTextArea().addEventListener("input", () => {
    updateAllStats();
  });

  document.getElementById("save").addEventListener("click", onSaveClick);
  document.getElementById("wpm-input").addEventListener("input", () => {
    saveWPMToStorage();
    updateReadingTime();
  });
})();

/**
 * @returns {HTMLTextAreaElement} The textarea element where the user inputs text.
 */
function getTextArea() {
  return document.getElementById("text");
}

/**
 * @returns {HTMLSpanElement} The span element that displays the word count.
 */
function getWordCountSpan() {
  return document.getElementById("word-count");
}

/**
 * @returns {HTMLSpanElement} The span element that displays the line count.
 */
function getLinesCountSpan() {
  return document.getElementById("line-count");
}

/**
 * @returns {HTMLSpanElement} The span element that displays the character count.
 */
function getCharCountSpan() {
  return document.getElementById("char-count");
}

/**
 * @returns {HTMLSpanElement} The span element that displays the reading time.
 */
function getReadingTimeSpan() {
  return document.getElementById("reading-time");
}

/**
 * @returns {HTMLInputElement} The input element for words per minute.
 */
function getWPMInput() {
  return document.getElementById("wpm-input");
}

/**
 * @returns {HTMLDivElement} The div element that displays the count of saved texts.
 */
function getSavedTextsCount() {
  return document.querySelector(".saved-texts-count");
}

/**
 * @returns {void}
 */
function updateSavedTextsCount() {
  const savedTextsCount = getSavedTextsCount();
  savedTextsCount.textContent = document.querySelectorAll(".saved-text").length;
}

/**
 * Retrieve saved texts from local storage
 * @returns {{ text: string, date: number }[]} An array of saved texts from local storage.
 */
function getStoredSavedTexts() {
  const savedTexts = localStorage.getItem("word-counter__texts");
  return savedTexts ? JSON.parse(savedTexts) : [];
}

/**
 * Load saved texts from local storage
 * @returns {void}
 */
function displaySavedTexts() {
  const savedTextsContainer = document.getElementById("savedTexts");
  if (!savedTextsContainer) return;

  savedTextsContainer.innerHTML = ""; // Clear previous content

  getStoredSavedTexts()
    .reverse()
    .forEach((item) => {
      savedTextsContainer.appendChild(generateSavedTextElement(item));
    });

  updateSavedTextsCount();
}

function onSaveClick() {
  const text = getTextArea().value;
  if (!text) {
    alert("Please enter some text before saving.");
    return;
  }

  saveText(text);
}

/**
 * @param {string} text
 * @returns {void}
 */
function saveText(text) {
  const wordCounterTexts = getStoredSavedTexts();
  wordCounterTexts.push({ date: new Date().getTime(), text });

  localStorage.setItem("word-counter__texts", JSON.stringify(wordCounterTexts));
  alert("Text saved to local storage!");

  displaySavedTexts();
}

/**
 * @param {{ text: string, date: number }} item
 * @returns {HTMLDivElement} A div element containing the saved text and its date.
 */
function generateSavedTextElement(item) {
  const textDiv = document.createElement("div");
  textDiv.classList.add("saved-text");

  textDiv.innerHTML = `<strong>${new Date(
    item.date
  ).toLocaleString()} (${countWords(
    item.text
  )}):</strong> <br /> <br /> ${item.text.replace(/\n/g, "<br />")}`;

  textDiv.addEventListener("click", () => {
    getTextArea().value = item.text;
    updateAllStats();
  });

  return textDiv;
}

/**
 * @param {string} text
 * @returns {number} The number of words in the text.
 */
function countWords(text) {
  const parsedText = text.trim();
  const words = parsedText ? parsedText.split(/\s+/) : [];
  return words.length;
}

/**
 * @param {string} text
 * @returns {number} The number of lines in the text.
 */
function countLines(text) {
  const parsedText = text.trim();
  const lines = parsedText ? parsedText.split(/\n+/) : [];
  return lines.length;
}

/**
 * @param {string} text
 * @returns {number} The number of characters in the text.
 */
function countCharacters(text) {
  return text.length;
}

/**
 * @param {number} wordCount
 * @param {number} wpm
 * @returns {string} The estimated reading time formatted as string.
 */
function calculateReadingTime(wordCount, wpm) {
  if (!wordCount || !wpm || wpm <= 0) return "0 min";
  
  const minutes = Math.ceil(wordCount / wpm);
  
  if (minutes < 1) {
    return "< 1 min";
  } else if (minutes === 1) {
    return "1 min";
  } else if (minutes < 60) {
    return `${minutes} min`;
  } else {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}min` : `${hours}h`;
  }
}

/**
 * Update all statistics displays.
 * @returns {void}
 */
function updateAllStats() {
  const text = getTextArea().value;
  getWordCountSpan().textContent = countWords(text);
  getLinesCountSpan().textContent = countLines(text);
  getCharCountSpan().textContent = countCharacters(text);
  updateReadingTime();
}

/**
 * Update the reading time display.
 * @returns {void}
 */
function updateReadingTime() {
  const text = getTextArea().value;
  const wordCount = countWords(text);
  const wpm = parseInt(getWPMInput().value) || 200;
  getReadingTimeSpan().textContent = calculateReadingTime(wordCount, wpm);
}

/**
 * Save WPM value to localStorage.
 * @returns {void}
 */
function saveWPMToStorage() {
  const wpm = getWPMInput().value;
  localStorage.setItem("word-counter__wpm", wpm);
}

/**
 * Load WPM value from localStorage.
 * @returns {void}
 */
function loadWPMFromStorage() {
  const savedWPM = localStorage.getItem("word-counter__wpm");
  if (savedWPM) {
    getWPMInput().value = savedWPM;
  }
}
