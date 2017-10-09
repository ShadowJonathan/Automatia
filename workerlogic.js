const Channel = require("channel");
const co = require("co");

class Pack {
    constructor(size = 2, async = false) {
        this.in = new Channel(1000);
        for (let i = 0; i < size; i++) {
            if (async)
                co(function* () {
                    while (1) {
                        const cmd = yield this.in.recv();
                        if (!cmd)
                            break;
                        if (cmd == "stop") {
                            this.in.close();
                            continue;
                        }
                        let w = new Worker(cmd);
                        yield w.a()
                    }
                }.bind(this))
            else
                co(function* () {
                    while (1) {
                        const cmd = yield this.in.recv();
                        if (!cmd)
                            break;
                        if (cmd == "stop")
                            this.in.close();
                        let w = new Worker(cmd);
                        w.s()
                    }
                }.bind(this))
        }
    }

    feed(cmd) {
        this.in.send(cmd)
    }

    cork() {
        this.in.send("stop")
    }
}

class Worker {
    constructor(cmd) {
        this.cmd = cmd;
    }

    s() {
        this.cmd()
    }

    async a() {
        await this.cmd()
    }
}

module.exports = {Worker, Pack};