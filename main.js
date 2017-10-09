if (parseInt(/v(\d+)/.exec(process.version)[1]) < 8) throw new Error("NODE VERSION UNDER 8");
const express = require('express');
const events = require("events");
global.cron = new events.EventEmitter();
const http = require('http');
const WebSocket = require('ws');
const app = express();
const uuid = require('uuid/v1');
const router = express.Router();
const server = http.createServer(app);
const wss = WSS = new WebSocket.Server({server: server});
//const Serve = require('./tresh/serve');
const scheduler = require('node-schedule');
const Session = require("./session");


// TODO SETUP AUTO-JOBS AND SYNCING (archives and stories)

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
} catch (err) {
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
        if (us(m).pong)
            ws.alive = 3
    });
    ws.ip = req.headers['x-forwarded-for'] || req.connection.remoteAddress;

    console.log("Connection from %s", ws.ip);
    console.log(req);
    ws.on('message', m => {
        if (m != '{"pong":true}')
            console.log('Received (' + ws.ip + '):', m);
    });

    ws.send(s({login: true}));
    ws.on('message', m => {
        if (us(m).uuid)
            Session.get(us(m).uuid).attach(ws);
    });
    ws.alive = 3
});

const beat = setInterval(function ping() {
    wss.clients.forEach(function each(ws) {
        if (ws.alive != 3)
            console.warn(ws.ip, (ws.sess ? "(" + ws.sess.ID + ")" : ""), "missed a tick: " + ws.alive);
        if (!(--ws.alive)) {
            console.log("Terminated " + (ws.sess ? "(" + ws.sess.ID + ") " : "") + ws.ip);
            return ws.terminate();
        }
        ws.send('{"ping":true}');
    });
}, 5000);

let Schedules = {
    midnight: scheduler.scheduleJob('0 0 0 * * *', () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('midnight')
        cron.emit('midnight')
    }),
    hour_after_midnight: scheduler.scheduleJob('0 0 1 * * *', () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('midnight_1h')
        cron.emit('midnight_1h')
    }),
    six_hour: scheduler.scheduleJob("0 */6 * * *", () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('6hour')
        cron.emit('6hour')
    }),

    three_hour: scheduler.scheduleJob("0 */3 * * *", () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('3hour')
        cron.emit('3hour')
    }),
    hour: scheduler.scheduleJob('0 0 * * * *', () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('hour')
        cron.emit('hour')
    }),
    min: scheduler.scheduleJob('0 * * * * *', () => {
        for (let s of Session.Sessions)
            s.tasks && s.tasks.emit('minute')
        cron.emit('minute')
    }),
};