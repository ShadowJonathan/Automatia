const PJO = require('persisted-json-object');
const events = require('events');
const modules = require('../modules/index');
const Job = require('../job');
try {
    require('fs').mkdirSync('sessions');
} catch (err) {
}


// TODO MAKE CENTERALISED SESSION CACHE SYSTEM
class Serve extends events.EventEmitter {
    constructor(ws) {
        super();
        this.ws = ws;
        this.ws.onclose = () => this.emit('close');
        this.meta = null;
        this.r_uuid = null;
        this.send = (m) => {
            try {
                this.ws.send(JSON.stringify(m))
            } catch (err) {
            }
        };
        this.ws.on('message', m => {
            m = JSON.parse(m);
            m.reply = this.send;
            this.emit('m', m)
        });

        this.ON(['uuid'], (m) => {
            this.r_uuid = m.uuid;
            this.meta = PJO({file: './sessions/' + m.uuid + '.json'});
            this.emit('got_meta');
            this.tasks = new Tasks(this);
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

        this.ON(['get_job'], m => {
            m.reply({job_result: Job.getResults(m.j_id), j_id: m.j_id})
        })
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

class Tasks extends events.EventEmitter {
    constructor(Server) {
        super();
        /**
         * @type {Serve}
         */
        this.session = Server;

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

module.exports = Serve;