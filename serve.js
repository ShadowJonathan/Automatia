const PJO = require('persisted-json-object');
const events = require('events');
const modules = require('./modules');
try {
    require('fs').mkdirSync('sessions');
} catch (err) {
}

class Serve extends events.EventEmitter {
    constructor(ws) {
        super();
        this.ws = ws;
        this.ws.onclose = () => this.emit('close');
        this.meta = {};
        this.r_uuid = null;
        this.send = (m) => this.ws.send(JSON.stringify(m));
        this.ws.on('message', m => {
            m = JSON.parse(m);
            m.reply = this.send;
            this.emit('m', m)
        });

        this.ON(['uuid'], (m) => {
            this.r_uuid = m.uuid;
            this.meta = PJO({file: './sessions/' + m.uuid + '.json'});
            this.emit('got_meta')
        });
        this.setupBasic()
    }

    setupBasic() {
        this.on('close', () => {
            console.log(this.ws.ip + " (" + this.r_uuid + ") disconnected.")
        });
        //this.ON([{test:true}], ()=>{console.log(this)})

        this.ffnet = new modules.ffnet(this);
        this.ON([{orig: 'ffnet'}], this.ffnet.handle.bind(this.ffnet), false)
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

}

module.exports = Serve;