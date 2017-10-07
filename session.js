const events = require("events");
const co = require("co");
const Channel = require("channel");
const PJO = require('persisted-json-object');
const modules = require('./modules');
const Job = require('./job');

var Sessions = {};

try {
    require('fs').mkdirSync('sessions');
} catch (err) {
}

class Session extends events.EventEmitter {
    constructor(ID) {
        super();
        this.ws = null;
        this.ID = ID;
        this.in = new Channel(1000);
        Sessions[ID] = this;

        this.meta = PJO({file: './sessions/' + ID + '.json'});
        this.tasks = new Tasks(this);
        this.setupBasic()
    }

    setupBasic() {
        this.on('close', () => {
            console.log(this.ws.ip + " (" + this.ID + ") disconnected.");
            this.in.send(null);
        });
        this.ffnet = new modules.ffnet(this);
        this.ON([{orig: 'ffnet'}], this.ffnet.handle.bind(this.ffnet), false);
        this.ON(['get_job'], m => m.reply({job_result: Job.getResults(m.j_id), j_id: m.j_id}))
    }

    /**
     * @param {WebSocket} ws
     * @return {Session}
     */
    attach(ws) {
        this.ws = ws;
        ws.onclose = () => {
            this.emit('close');
            this.ws = null;
        };
        ws.on('message', m => {
            m = JSON.parse(m);
            m.reply = this.send.bind(this);
            this.emit('m', m)
        });
        this._startprocess();
        console.debug(`Websocket attached to ${this.ID}`);
        return this;
    }

    _startprocess() {
        co(function* () {
            while (this.connected) {
                const v = yield this.in.recv();
                if (!v)
                    break;
                if (!this.connected) {
                    this.in.send(v);
                    break;
                }
                console.log(v);
                this.ws.send(JSON.stringify(v))
            }
        }.bind(this))
    }

    send(m) {
        this.in.send(m)
    }

    get connected() {
        return this.ws != null;
    }

    // EVENTS
    ON(event, cb, bind = true) {
        if (typeof event === 'string') {
            this.on(event, cb)
        } else {
            let f = m => {
                if (this.filter(event, m))
                    cb(m)
            };
            if (bind) {
                f.bind(this)
            }
            this.on('m', f);
            return f
        }
    }

    ONCE(event, cb) {
        if (typeof event === 'string') {
            this.once(event, cb)
        } else {
            let f = m => {
                if (this.filter(event, m)) {
                    this.removeListener('m', f);
                    cb(m);
                }
            };
            this.on('m', f.bind(this));
        }
    }

    /**
     * @param {Array.<String>} event
     * @param {Object} message
     */
    filter(event, message) {
        for (let p of event) {
            if (typeof p === "string") {
                if (message[p] === undefined) {
                    return false
                }
            } else {
                for (let k in p) {
                    if (message[k] != p[k]) {
                        return false
                    }
                }
            }
        }
        return true
    }

    // STATIC
    static get(ID) {
        if (Sessions[ID])
            return Sessions[ID];
        else
            return new Session(ID);

    }

    static get Sessions() {
        return Object.values(Sessions);
    }
}

class Tasks extends events.EventEmitter {
    constructor(Session) {
        super();
        /**
         * @type {Session}
         */
        this.session = Session;

        // checkFFDates
        let midnight = new Date();
        midnight.setHours(0, 0, 0, 0);
        if (!this.session.meta.FFCheckDate || new Date(this.session.meta.FFCheckDate) < midnight) {
            this.checkFFDates()
        }
        this.on('midnight', this.checkFFDates.bind(this));

        // DEBUG
        /*
        this.on('midnight', () => console.log("Midnight!"));
        this.on('hour', () => console.log("Hour!"));
        this.on('minute', () => console.log("Minute!"))
        */
    }


    checkFFDates() {
        this.session.send({orig: 'ffnet', get_stamps: true})
    }
}

module.exports = Session;