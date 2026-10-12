var hostname = process.argv[2] || "0.0.0.0";
var port = parseInt(process.argv[3]) || 80;

var finalhandler = require('finalhandler');
var http = require('http');
var serveStatic = require('serve-static');

// Serve up public/ftp folder
var serve = serveStatic('public_html/', {'setHeaders': setHeaders});

function setHeaders(res, path) {
  res.setHeader('Cache-Control', 'public, max-age=0');
}

// Create server
var server = http.createServer(function onRequest (req, res) {
  serve(req, res, finalhandler(req, res));
});

// Listen
server.listen(port, hostname);

var validPrograms = {level00: {path: "/home/level00", exec: "/home/level00/level00"}, 
  level01: {path: "/home/level01", exec: "/home/level01/level01"}, 
  level02: {path: "/home/level02", exec: "/home/level02/level02"}, 
  level03: {path: "/home/level03", exec: "/home/level03/level03"},
  level04: {path: "/home/level04", exec: "/home/level04/level04"}
};
var spawn = require('child_process').spawn;

var io = require('socket.io')(server, {
  extraHeaders: {
    'Access-Control-Allow-Origin': '*'
  }
});
io.on('connection', (socket) => {
  var proc;
  socket.on('query', (fn) => {
    var progs = [];
    for (var prog in validPrograms) {
      progs.push(prog);
    }
    fn(progs);
  })
  
  socket.on('start', (starting) => {
    if (proc) {
      socket.emit('stderr', 'bin-wrapper: Already running another program.');
      return;
    }
    
    if (!validPrograms[starting]) {
      socket.emit('stderr', 'bin-wrapper: ' + starting + ': command not found.');
      socket.disconnect();
      return;
    }
    
    proc = spawn(validPrograms[starting].exec, {cwd: validPrograms[starting].path});
    proc.on('exit', () => {
      proc = undefined;
      socket.disconnect();
    });
    proc.stdout.on('data', (data) => {
      socket.emit('stdout', data.toString());
    });
    proc.stderr.on('data', (data) => {
      socket.emit('stderr', data.toString());
    });
  });
  
  socket.on('interrupt', () => {
    proc.kill('SIGINT');
  })
  
  socket.on('end', () => {
    proc.stdin.end();
  });
  
  socket.on('disconnect', () => {
    if (proc) {
      proc.kill('SIGKILL');
      proc = undefined;
    }
  });
  
  socket.on('stdin', (data) => {
    if (typeof data !== 'string') {
      socket.emit('stderr', 'bin-wrapper: Invalid data sent.');
      return;
    }
    
    if (!proc) {
      socket.emit('stderr', 'bin-wrapper: Pipe has been unexpectedly closed.');
      return;
    }
    
    proc.stdin.write(data);
  });
});