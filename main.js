if (parseInt(/v(\d+)/.exec(process.version)[1]) < 8) throw new Error("NODE VERSION UNDER 8");
const express = require('express');
const http = require('http');
const url = require('url');
const WebSocket = require('ws');
const app = express();
const uuid = require('uuid/v1');
const router = express.Router();
const server = http.createServer(app);
const wss = new WebSocket.Server({server});
const Serve = require('./serve');

try {
    require('fs').mkdirSync('files');
} catch (err) {
}

const s = JSON.stringify;
const us = JSON.parse;

app.use(router);

router.get('/', function (req, res) {
    res.send('Hello World!')
});
try {
    router.use('/files', express.static(__dirname + "/files"));
} catch(err) {
}

router.get('/register', function (req, res) {
    res.send(uuid())
});

server.listen(8080, function listening() {
    console.log('Listening on', server.address().port);
});

wss.on('connection', function connection(ws, req) {
    ws.isAlive = true;
    ws.on('message', m => {
        if (us(m).pong) ws.isAlive = true
    });
    ws.ip = req.headers['x-forwarded-for'] || req.connection.remoteAddress;

    console.log("Connection from %s", ws.ip);
    ws.on('message', function incoming(message) {
        if (message != '{"pong":true}')
            console.log('Received (' + this.ip + '):', message);
    });

    ws.send(s({login: true}));
    ws.S = new Serve(ws)
});

const beat = setInterval(function ping() {
    wss.clients.forEach(function each(ws) {
        if (!ws.isAlive) {
            return ws.terminate();
        }

        ws.isAlive = false;
        ws.send('{"ping":true}');
    });
}, 5000);