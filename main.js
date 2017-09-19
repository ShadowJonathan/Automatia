const express = require('express');
const http = require('http');
const url = require('url');
const WebSocket = require('ws');
const app = express();
const router = express.Router();
const server = http.createServer(app);
const wss = new WebSocket.Server({server});

const s = JSON.stringify;
const us = JSON.parse;

app.use(router);
app.use('/client', express.static(__dirname + '/client'));

router.get('/', function (req, res) {
    res.send('Hello World!')
});

router.get('/test', function (req, res) {
    res.send('Hello World Too!')
});

server.listen(8080, function listening() {
    console.log('Listening on', server.address().port);
});

wss.on('connection', function connection(ws, req) {
    ws.isAlive = true;
    ws.on('message', m => m['pong'] && (this.isAlive = true));
    ws.ip = req.headers['x-forwarded-for'] || req.connection.remoteAddress;

    ws.on('message', function incoming(message) {
        console.log('received: %s', message);
    });

    ws.send(s({'msg': 'login'}));
});

const beat = setInterval(function ping() {
    wss.clients.forEach(function each(ws) {
        if (ws.isAlive === false) {
            console.log(ws.ip + " terminated.")
            return ws.terminate();
        } else {
            console.log(ws.ip + " alive.")
        }

        ws.isAlive = false;
        ws.send('{"ping":true}');
    });
}, 5000);