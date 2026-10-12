// ==UserScript==
// @name         philg-dev's settings template standalone
// @version      0.1
// @description  template for a basic settings panel with persistent storage
// @author       philg-dev
// @match        https://www.google.com/
// @grant        GM.setValue
// @grant        GM.getValue
// ==/UserScript==

(function () {
    "use strict";

    const textInputMaxLength = 128;
    const textareaMaxLength = 4096;

    /**
     * static DOM element IDs
     */
    const id_settingsIcon = "settingsIcon";
    const id_settingsPopup = "tmSettingsPopup";
    const id_settingsContent = "tmSettingsContent";
    const id_saveButton = "saveSettings";
    const id_cancelButton = "cancelSettings"

    /**
     * Variable names as strings to make them reusable when saving / loading settings.
     * Also used as IDs and names in the respective HTML DOM elements.
     */
    const var_sampleSelectElementValue = "sampleSelectElementValue";
    const var_sampleCheckbox1Value = "sampleCheckbox1Value";
    const var_sampleCheckbox2Value = "sampleCheckbox2Value";
    const var_sampleTextfieldValue = "sampleTextfieldValue";
    const var_sampleTextareaValue = "sampleTextareaValue";

    /**
     * Default values for settings that haven't been saved before.
     */
    const settingsDefaults = {};
    settingsDefaults[var_sampleSelectElementValue] = 2;
    settingsDefaults[var_sampleCheckbox1Value] = true;
    settingsDefaults[var_sampleCheckbox2Value] = false;
    settingsDefaults[var_sampleTextfieldValue] = "This is the default text.";
    settingsDefaults[var_sampleTextareaValue] = "I'm a multiline text.\nThis is the second line.";

    /**
     * The actual user specified settings values that are loaded from local storage or changed via the settings panel.
     */
    const settings = settingsDefaults;

    /**
     * UI state of the settings panel.
     */
    var isSettingsOpen = false;

    /**
     * Loads the settings from local storage using GM.getValue.
     * Can handle the following HTML elements:
     *  - select
     *  - input with type text
     *  - input with type checkbox
     *  - textarea
     */
    const loadSettings = async () => {
        for(var key of Object.keys(settingsDefaults)) {
            settings[key] = await GM.getValue(key, settingsDefaults[key]);
            var domElem = document.getElementById(key);
            if (!domElem) {
                console.warn(`Couldn't find a respective DOM element corresponding to key ${key}`);
                continue;
            }
            try {
                // special treatment needed for checkboxes, since their "value" attribute doesn't do the proper thing
                if (domElem.nodeName === "INPUT" && domElem.type === "checkbox") {
                    domElem.checked = settings[key];
                    continue;
                }
                // for text input, selects and textareas the value attribute works just fine
                domElem.value = settings[key];
            } catch(e) {
                // in case of unsupported DOM element types and other unspecified errors
                console.debug(`Sum Ting Wong... trying to get DOM element corresponding to key: ${key} and got DOM element: ${JSON.stringify(domElem)}`);
            }
        }
        console.debug("Loaded settings from local storage: " + JSON.stringify(settings));
    };

    /**
     * Saves the settings to local storage using GM.setValue.
     * Can handle the following HTML elements:
     *  - select
     *  - input with type text
     *  - input with type checkbox
     *  - textarea
     */
    const saveSettings = async () => {
        for(var key of Object.keys(settingsDefaults)) {
            var domElem = document.querySelector(`#${key}`);
            if (!domElem) {
                console.warn(`Couldn't find a respective DOM element corresponding to key ${key} - didn't save value for this key.`);
                continue;
            }
            try {
                // special treatment needed for checkboxes, since their "value" attribute doesn't do the proper thing
                if (domElem.nodeName === "INPUT" && domElem.type === "checkbox") {
                    settings[key] = domElem.checked;
                    await GM.setValue(key, settings[key]);
                    continue;
                }
                // for text input, selects and textareas the value attribute works just fine
                settings[key] = domElem.value;
                await GM.setValue(key, settings[key]);
            } catch(e) {
                // in case of unsupported DOM element types and other unspecified errors
                console.debug(`Sum Ting Wong... trying to get DOM element corresponding to key: ${key} and got DOM element: ${JSON.stringify(domElem)}`);
            }   
        }
    };

    /**
     * Utility function to create a DOM element from an HTML string.
     * As found here: https://stackoverflow.com/a/35385518
     * 
     * @param {String} HTML representing a single element.
     * @param {Boolean} flag representing whether or not to trim input whitespace, defaults to true.
     * @return {Element | HTMLCollection | null}
     */
    const fromHTML = function (html, trim = true) {
        // Process the HTML string.
        html = trim ? html.trim() : html;
        if (!html) return null;

        // Then set up a new template element.
        const template = document.createElement("template");
        template.innerHTML = html;
        const result = template.content.children;

        // Then return either an HTMLElement or HTMLCollection,
        // based on whether the input HTML had one or more roots.
        if (result.length === 1) return result[0];
        return result;
    };

    const toggleSettingsUi = function () {
        isSettingsOpen = !isSettingsOpen;
        if (isSettingsOpen)
            document.getElementById(id_settingsPopup).classList.add("show");
        else
            document.getElementById(id_settingsPopup).classList.remove("show");
    };

    const addSettingsUi = function () {
        // adds a gear wheel icon to open the settings panel
        // gear wheel icon from GitHub octicons https://github.com/primer/octicons/blob/master/icons/gear-24.svg
        document.body.prepend(fromHTML(
            `
            <svg xmlns="http://www.w3.org/2000/svg" class="tm-icon" id="settingsIcon" width="24" height="24" viewBox="0 0 24 24">
                <path fill-rule="evenodd" d="M16 12a4 4 0 11-8 0 4 4 0 018 0zm-1.5 0a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z"/>
                <path fill-rule="evenodd" d="M12 1c-.268 0-.534.01-.797.028-.763.055-1.345.617-1.512 1.304l-.352 1.45c-.02.078-.09.172-.225.22a8.45 8.45 0 00-.728.303c-.13.06-.246.044-.315.002l-1.274-.776c-.604-.368-1.412-.354-1.99.147-.403.348-.78.726-1.129 1.128-.5.579-.515 1.387-.147 1.99l.776 1.275c.042.069.059.185-.002.315-.112.237-.213.48-.302.728-.05.135-.143.206-.221.225l-1.45.352c-.687.167-1.249.749-1.304 1.512a11.149 11.149 0 000 1.594c.055.763.617 1.345 1.304 1.512l1.45.352c.078.02.172.09.22.225.09.248.191.491.303.729.06.129.044.245.002.314l-.776 1.274c-.368.604-.354 1.412.147 1.99.348.403.726.78 1.128 1.129.579.5 1.387.515 1.99.147l1.275-.776c.069-.042.185-.059.315.002.237.112.48.213.728.302.135.05.206.143.225.221l.352 1.45c.167.687.749 1.249 1.512 1.303a11.125 11.125 0 001.594 0c.763-.054 1.345-.616 1.512-1.303l.352-1.45c.02-.078.09-.172.225-.22.248-.09.491-.191.729-.303.129-.06.245-.044.314-.002l1.274.776c.604.368 1.412.354 1.99-.147.403-.348.78-.726 1.129-1.128.5-.579.515-1.387.147-1.99l-.776-1.275c-.042-.069-.059-.185.002-.315.112-.237.213-.48.302-.728.05-.135.143-.206.221-.225l1.45-.352c.687-.167 1.249-.749 1.303-1.512a11.125 11.125 0 000-1.594c-.054-.763-.616-1.345-1.303-1.512l-1.45-.352c-.078-.02-.172-.09-.22-.225a8.469 8.469 0 00-.303-.728c-.06-.13-.044-.246-.002-.315l.776-1.274c.368-.604.354-1.412-.147-1.99-.348-.403-.726-.78-1.128-1.129-.579-.5-1.387-.515-1.99-.147l-1.275.776c-.069.042-.185.059-.315-.002a8.465 8.465 0 00-.728-.302c-.135-.05-.206-.143-.225-.221l-.352-1.45c-.167-.687-.749-1.249-1.512-1.304A11.149 11.149 0 0012 1zm-.69 1.525a9.648 9.648 0 011.38 0c.055.004.135.05.162.16l.351 1.45c.153.628.626 1.08 1.173 1.278.205.074.405.157.6.249a1.832 1.832 0 001.733-.074l1.275-.776c.097-.06.186-.036.228 0 .348.302.674.628.976.976.036.042.06.13 0 .228l-.776 1.274a1.832 1.832 0 00-.074 1.734c.092.195.175.395.248.6.198.547.652 1.02 1.278 1.172l1.45.353c.111.026.157.106.161.161a9.653 9.653 0 010 1.38c-.004.055-.05.135-.16.162l-1.45.351a1.833 1.833 0 00-1.278 1.173 6.926 6.926 0 01-.25.6 1.832 1.832 0 00.075 1.733l.776 1.275c.06.097.036.186 0 .228a9.555 9.555 0 01-.976.976c-.042.036-.13.06-.228 0l-1.275-.776a1.832 1.832 0 00-1.733-.074 6.926 6.926 0 01-.6.248 1.833 1.833 0 00-1.172 1.278l-.353 1.45c-.026.111-.106.157-.161.161a9.653 9.653 0 01-1.38 0c-.055-.004-.135-.05-.162-.16l-.351-1.45a1.833 1.833 0 00-1.173-1.278 6.928 6.928 0 01-.6-.25 1.832 1.832 0 00-1.734.075l-1.274.776c-.097.06-.186.036-.228 0a9.56 9.56 0 01-.976-.976c-.036-.042-.06-.13 0-.228l.776-1.275a1.832 1.832 0 00.074-1.733 6.948 6.948 0 01-.249-.6 1.833 1.833 0 00-1.277-1.172l-1.45-.353c-.111-.026-.157-.106-.161-.161a9.648 9.648 0 010-1.38c.004-.055.05-.135.16-.162l1.45-.351a1.833 1.833 0 001.278-1.173 6.95 6.95 0 01.249-.6 1.832 1.832 0 00-.074-1.734l-.776-1.274c-.06-.097-.036-.186 0-.228.302-.348.628-.674.976-.976.042-.036.13-.06.228 0l1.274.776a1.832 1.832 0 001.734.074 6.95 6.95 0 01.6-.249 1.833 1.833 0 001.172-1.277l.353-1.45c.026-.111.106-.157.161-.161z"/>
            </svg>
            `));

        // adds the settings panel
        document.body.append(fromHTML(
            `
            <div id="${id_settingsPopup}">
                <div id="${id_settingsContent}">
                    <h2>Userscript Settings</h2>
                    <p>Note: Changes to the settings are only applied when hitting the save button!</p>
                    <form>
                        <p>
                            <label for="${var_sampleSelectElementValue}">Select a sample value:</label>
                            <select id="${var_sampleSelectElementValue}" name="${var_sampleSelectElementValue}">
                                <option value="1">Sample Value 1</option>
                                <option value="2">Sample Value 2</option>
                            </select>
                        </p>
                        <p>
                            <input type="checkbox" id="${var_sampleCheckbox1Value}" name="${var_sampleCheckbox1Value}">
                            <label for="${var_sampleCheckbox1Value}">Sample checkbox 1.</label>
                        </p>
                        <p>
                            <input type="checkbox" id="${var_sampleCheckbox2Value}" name="${var_sampleCheckbox2Value}">
                            <label for="${var_sampleCheckbox2Value}">Sample checkbox 2.</label>
                        </p>
                        <p>
                            <label for="${var_sampleTextfieldValue}">Sample text field:</label>
                            <input type="text" id="${var_sampleTextfieldValue}" name="${var_sampleTextfieldValue}" maxlength=${textInputMaxLength}></input>
                        </p>
                        <p>
                            <label for="${var_sampleTextareaValue}">Sample textarea:</label>
                            <textarea id="${var_sampleTextareaValue}" name="${var_sampleTextareaValue}" maxlength=${textareaMaxLength}></textarea>
                        </p>
                        <p>
                            <input type="button" id="${id_saveButton}" value="Save">
                            <input type="button" id="${id_cancelButton}" value="Cancel">
                        </p>
                    </form>
                </div>
            </div>
            `
        ));

        document.getElementById(id_settingsIcon).addEventListener("click", toggleSettingsUi);
        document.getElementById(id_saveButton).addEventListener("click", saveSettings);
        document.getElementById(id_cancelButton).addEventListener("click", toggleSettingsUi);
        // hide popup when clicking the background outside of main settings div
        document.getElementById(id_settingsPopup).addEventListener("click", toggleSettingsUi);
        // prevent child elements from bubbling the click event up to the parent (i.e. when clicking anything that's actually inside the settings panel)
        document.getElementById(id_settingsContent).addEventListener("click", (event) => {
            event.stopPropagation();
        });

        // adds basic CSS in order to be able to properly display the settings panel
        var customCss = document.createElement("style");
        customCss.innerHTML = `
            .tm-icon {
                stroke: magenta;
                position:absolute;
                top: 100px;
                left: 20px;
                cursor:pointer;
            }
            
            #tmSettingsPopup,
            #tmSettingsContent,
            #tmSettingsPopup input,
            #tmSettingsPopup button {
                color: black;
            }
        
        
            #tmSettingsContent {
                background: white;
                border-style: solid;
                border-width: 2px;
                border-radius: 5px;
                border-color: black;
                padding: 20px;
                z-index: 99999;
            }
            
            #tmSettingsPopup {
                align-items: center;
                justify-content: center;
                background: rgba(0, 0, 0, .25);
                z-index: 99990;
                position: fixed;
                top: 0%;
                left: 0%;
                right: 0%;
                bottom: 0%;
            }
        
            #tmSettingsPopup:not(.show) {
                display:none;
            }
        
            .show {
                display: flex;
            }
        `;

        document.body.append(customCss)
        
    };

    addSettingsUi();

    loadSettings();
})();
