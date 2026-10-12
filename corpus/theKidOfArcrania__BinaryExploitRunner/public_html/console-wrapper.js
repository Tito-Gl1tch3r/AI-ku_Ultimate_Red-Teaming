$(function() {
  var binaries = [];
  var query = io('//' + window.location.hostname);
  query.on('connect', () => {
    query.emit('query', function(bins) {
      introduce();
      binaries = bins;
      term.resume();
      query.disconnect();
    });
  });
  
  var term = $('#terminal-panel').terminal((command, term) => {
    command = command.substr(0, command.length - 1);
    command = parseEscaped(command);
    if (!command)
      return;
    
    if (command == 'help') {
      term.echo('These are the binaries you can run: ');
      binaries.forEach((bin) => {
        term.echo('*\x1b[1;32m ' + bin + '\x1b[0m');
      });
      term.echo('You can also type `clear` to clear console.\n \n*Tip: you can type in "\\x??" ' +
      'to specify the\nhex-code of a character, and "\\\\" for escaping backslash\n \n');
    } else if (command == 'clear') {
      term.clear();
    } else if (command.startsWith('echo ')) {
      term.echo(command.replace('echo ', ''));
    } else if (command.length != 0) {
      if (binaries.includes(command)) {
        initConnection(command);
      } else {
        term.error('bin-wrapper: ' + command + ': command not found.');
      }
    }
  }, {
    clear: false,
    echoCommand: true,
    exit: false,
    greetings: '\x1b[1;36mBinary Wrapper\n\x1b[1;34mCopyright (c) 2017 theKidOfArcrania\x1b[0m\n',
    history: false,
    prompt: '> ',
    pauseEvents: false,
    onBlur: function() {
      return false;
    },
    onClear: introduce.bind(this, true),
  });
  
  term.pause();
  
  function introduce(cleared)
  {
    if (cleared)
      term.echo('Enter binary to run\nOr type in `help` to get a list of valid commands.');
    else
      term.echo('\n \nEnter binary to run\nOr type in `help` to get a list of valid commands.');
  }
  
  function initConnection(program) {
    term.push(function(command) {
      socket.emit('stdin', parseEscaped(command));
    }, {
      prompt: '',
      keymap: {
        'CTRL+D': function() {
          socket.emit("end");
        },
        'CTRL+C': function() {
          socket.emit("interrupt");
        }
      }
    });
      
    var socket = io('//' + window.location.hostname);
    socket.on('stdout', (msg) => {
      term.echo(msg);
    });
    socket.on('stderr', (msg) => {
      term.error(msg);
    });
    socket.on('connect', () => {
      socket.emit('start', program);
    });
    socket.on('connect_error', (error) => {
      term.error("Failure to connect to server: " + error);
    });
    socket.on('disconnect', () => {
      term.echo("\x1b[1;34mConnection has been terminated.\x1b[0m");
      socket.disconnect();
      term.pop();
      introduce();
    });
  }
  
  function parseEscaped(str)
  {
    var escaped = false;
    var tmp = str;
    str = '';
    
    for (var i = 0; i < tmp.length; i++) {
      var c = tmp.charAt(i);
      if (escaped) {
        var charSize = 4;
        escaped = false;
        switch (c) {
          case '"': str += '"'; break;
          case "'": str += "'"; break;
          case '\\': str += '\\'; break;
          case '0': str += '\x00'; break;
          case 'n': str += '\n'; break;
          case 'r': str += '\r'; break;
          case 't': str += '\t'; break;
          case 'x': 
            charSize = 2;
            //PASSTHROUGH
          case 'u': 
            if (tmp.length - i - 1 < charSize) {
              term.error('Invalid hexadecimal.');
              return;
            }
            try {
              var point = tmp.substr(i + 1, charSize);
              if (!/^[A-Fa-f0-9]+$/.test(point)) {
                term.error('Invalid hexadecimal.');
                return;
              }
              str += String.fromCodePoint(parseInt(point, 16));
              i += charSize;
            } catch (e) {
              term.error('Invalid character code point.');
              return;
            }
            break;
          default:
            term.error('Invalid escape code: ' + c);
            return;
        }
      } else if (c == '\\') {
        escaped = true;
      } else {
        str += c;
      }
    }
    if (escaped) {
      term.error('Unexpected end of input.');
      return;
    }
    return str;
  }
});