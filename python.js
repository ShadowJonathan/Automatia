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
        this.nfunc = () => {
        };
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
            // noinspection JSUnfilteredForInLoop
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
        return new Promise((res) => {
            if (dir)
                this.arg('dir', dir);
            this.postInit = (s) => {
                s.on('message', (m) => {
                    if (m.finished) {
                        res(m)
                    }
                })
            };
            this.run()
        })
    }

    handle(message) {
        message.s_id = this.ID;
        this.nfunc(message)
    }
}

class Archive extends ffnetInterface {
    constructor(url) {
        super();
        let r = /\/?(\w+)\/(.*?)\/?$/.exec(url);
        this.cat = r[1];
        this.archive = r[2];
        this.arg('c', this.cat);
        this.arg('a', this.archive)
    }

    update() {
        this.arg('action', 'update');
        this.run();
    }

    async asyncUpdate(replyFunc) {
        this.update();
        this.script.on("message", m => {
            if (m._progress_name)
                replyFunc({
                    orig: 'ffnet',
                    archive: a.archive,
                    category: a.cat,
                    registry_update: "Initialising data... (%d/%d)".format(m._current, m._total)
                })
        });
        await new Promise(r => this.script.on('message', m => {
            if (m.done) r(m)
        }))
    }

    refresh(all = false) {
        this.arg('action', 'refresh');
        if (all)
            this.arg('all');
        this.run()
    }

    info() {
        return new Promise((res) => {
            this.postInit = s => {
                s.on('message', m => {
                    if (m.meta !== undefined) {
                        res(m)
                    }
                });
            };
            this.run();
        })
    }

    getinfo() {
        this.arg('action', 'getinfo');
        return this.info()
    }

    get args_prefix() {
        return ['-archive']
    }

    async getEntries(replyFunc) {
        this.arg('action', 'dump');
        this.run();
        let m = await new Promise(r => {
            this.script.once('message', (m) => {
                if (m.file_path)
                    r(m)
            })
        });
        let o = require('persisted-json-object')({file: m.file_path});
        if (JSON.stringify(o) == "{}") {
            await new Promise(r => this.script.on('close', r));
            await this.asyncUpdate(replyFunc);
        }
        return require('persisted-json-object')({file: m.file_path})
    }

    static getArchives(category) {
        return new Promise((res) => {
                let i = new ffnetInterface();
                i.arg('archive');
                i.arg('c', category);
                i.run();
                i.script.on('message', res);
            }
        )
    }

    static getStamps() {
        return new Promise((res) => {
                let i = new ffnetInterface();
                i.arg('archive');
                i.arg('stamps');
                i.run();
                i.script.on('message', res);
            }
        )
    }
}

module.exports = {
    ffnet: {
        Archive,
        Story
    }
};