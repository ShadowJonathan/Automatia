var PythonShell = require('python-shell');
var events = require('events');
/*var pyshell = new PythonShell('python/ffnet/__main__.py', {
    mode: "json",
    args: ['https://www.fanfiction.net/s/12652269/1/Real-Lucifer', '-m'],
    encoding: 'ascii'
});

pyshell.on('message', function (message) {
    console.log(message);
});

pyshell.end(function (err, results) {
    if (err)
        throw err;
    console.log('finished\n' + results);
});*/

class ffnetInterface extends events.EventEmitter {
    constructor() {
        super();
        this.nfunc = ()=>{};
        this.Args = {};
        this.script = null
    }

    arg(key, val = true) {
        this.Args[key] = val
    }

    del(key) {
        delete this.Args[key]
    }

    clear() {
        this.Args = {}
    }

    get args() {
        let l = [].concat(this.args_prefix);
        for (let k in this.Args) {
            l.push("-" + k);
            let v = this.Args[k];
            if (typeof(v) != "boolean") {
                l.push(v)
            }
        }
        return l
    }

    run() {
        this.script = new PythonShell('python/ffnet', {
            mode: "json",
            args: this.args,
            pythonOptions: ['-u'],
            encoding: 'ascii'
        });
        this.postInit(this.script);
        this.tsInit(this.script);
        console.log("Starting ffnet python with", this.args);
        this.script.on('message', m => {
            console.log("Script message:", m);
            this.handle(m);
            if (m.type == 'notification') {
                this.emit('notification', m)
            }
        })
    }

    /**
     * @param {PythonShell} script
     */
    postInit(script) {

    }

    tsInit(script) {

    }

    get args_prefix() {
        return []
    }

    handle(message) {
        if (message['failed']) {
            throw message['fail_code']
        }
    }
}

class Story extends ffnetInterface {
    constructor(ID, sendfunc) {
        super();
        this.nfunc = sendfunc;
        this.ID = /(?:(?:www|m)\.fanfiction\.net\/s\/)?(\d+)(?:\/\d+)?/i.exec(ID)[1];
        this.metaInfo = {}
    }

    get args_prefix() {
        return [this.ID]
    }

    meta() {
        return new Promise((res) => {
            this.arg('m');
            this.postInit = s => {
                s.on('message', m => {
                    if (m.meta) {
                        res(m)
                    }
                });
                s.on('message', m =>{
                    if (m.accepted) {
                        m.s_id = this.ID;
                        this.nfunc(m)
                    }
                })
            };
            this.run();
            this.clear();
        })
    }

    tsInit(s) {
        s.on('message', m => {
            if (m.meta) {
                this.metaInfo = m.meta;
                this.emit('got_meta', this.metaInfo)
            }
        })
    }

    download(dir = null) {
        return new Promise(() => {
            if (dir)
                this.arg('dir', dir);
            this.run()
        })
    }

    handle(message) {
        message.s_id = this.ID;
        this.nfunc(message)
    }
}

class Archive extends ffnetInterface {
    constructor() {
        super()
    }

    static getArchives(category) {
        let i = new ffnetInterface();
        i.arg('archive');
        i.arg('c', category);
    }
}

module.exports = {
    ffnet: {
        Archive,
        Story
    }
}