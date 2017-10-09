const Job = require('./../job');
const SA = require('./../python').ffnet;
const {Pack} = require("./../workerlogic")

global.cron.on('6hour', () => {
    SA.Archive.getStamps().then(d => {
        let p = new Pack(6, true);
        for (let cat in d.stamps) {
            for (let a in d.stamps[cat]) {
                let url = `/${cat}/${a}/`;
                p.feed(async ()=> {
                    let A = new SA.Archive(url);
                    await A.simpleRefresh()
                })
            }
        }
        p.cork()
    })
});


module.exports = class ffnet {
    constructor(server) {
        this.s = server;
        this.meta = server.meta;
    }

    notify(data) {
        data.orig = 'ffnet';
        this.s.send(data)
    }

    /**
     * @param {Object} message
     * @param {Array} message.queue
     * @param {Function} message.reply
     * @param {String} message.story_id
     * @param {Boolean} message.meta
     * @param {Boolean} message.download
     * @param {Boolean|String} message.archive
     * @param {String} message.category
     * @param {Boolean} message.info
     * @param {Boolean} message.getinfo
     * @param {Boolean} message.getreg
     * @param {String} message.a_url
     * @param {Boolean} message.stamps
     * @param {Boolean} message.refresh
     * @param {?Object.<String, {meta: Date, cat: string, reg: ?Date}>} message.data
     */
    handle(message) {
        if (message.queue) {
            for (let s of message.queue) {
                if (s.id)
                    if (s.meta)
                        new SA.Story(s.id, this.s.send).meta();
                    else
                        this.download(s.id);
                else {
                    s.reply = message.reply;
                    this.handle(s)
                }
            }
            message.reply({
                orig: 'ffnet',
                reg: 'queue',
                queue: 'accepted'
            })
        } else if (message.story_id) {
            if (message.meta) {
                new SA.Story(message.story_id, this.s.send).meta()
            } else if (message.download) {
                this.download(message.story_id)
            }
        } else if (message.archive) {
            if (message.archive == "?") {
                SA.Archive.getArchives(message.category).then(
                    (data) => {
                        message.reply({
                            orig: 'ffnet',
                            meta: 'category',
                            category: message.category,
                            data: data.data,
                        })
                    }
                )
            } else {
                let a = new SA.Archive(message.a_url);
                if (message.info) {
                    a.info().then(message.reply)
                } else if (message.getinfo) {
                    a.getinfo().then(message.reply)
                } else if (message.getreg) {
                    a = new SA.Archive(message.a_url);
                    a.getEntries(message.reply).then(r => {
                        message.reply({orig: 'ffnet', archive: a.archive, category: a.cat, registry: r})
                    })
                } else if (message.refresh) {
                    a = new SA.Archive(message.a_url);
                    a.asyncRefresh(true).then(r => {
                        message.reply({orig: 'ffnet', archive: a.archive, category: a.cat, registry: r})
                    })
                }
            }
        } else if (message.stamps) {
            this.s.meta.FFCheckDate = new Date();
            SA.Archive.getStamps().then(d => {
                let ONE_HOUR = 60 * 60 * 1000;
                /**
                 * @type {Object.<String, Object.<String, Date>>}
                 */
                let stamps = d.stamps;
                for (let a of Object.keys(message.data)) {
                    let data = message.data[a];
                    if (!stamps[data.cat] || !stamps[data.cat][a]) {
                        console.error(data.cat + " > " + a + " HAS NEVER BEEN INITIALISED");
                        continue
                    }
                    if (data.reg)
                        data.reg = new Date(data.reg);
                    data.meta = new Date(data.meta);
                    stamps[data.cat][a] = new Date(stamps[data.cat][a]);
                    if (data.reg)
                        if ((data.reg - stamps[data.cat][a]) > ONE_HOUR) {
                            message.reply({orig: 'ffnet', archive: a, category: data.cat, registry: false})
                        }

                    if ((new Date().getTime() - (24 * 60 * 60 * 1000)) > data.meta) {
                        message.reply({orig: 'ffnet', archive: a, category: data.cat, meta: null, initialised: false})
                    }
                }
            })
        }
    }

    download(id) {
        let j = new Job(this.s.r_uuid, {
            type: 'dl',
            story: {
                id: id,
                dir: 'files/stories'
            },
            self: this
        }, 'ffnet');
        this.notify({
            s_id: id,
            j_id: j.jobID
        })
    }

    // noinspection JSUnusedGlobalSymbols, JSMethodCanBeStatic
    toJSON() {
        return {}
    }

    static async doJob(args) {
        switch (args.type) {
            case 'dl': {
                let s = new SA.Story(args.story.id, args.self && args.self.s.send || (() => {
                }));
                if (args.self) {
                    s.on('notification', (n) => {
                        args.self.notify(n)
                    });
                }
                return await s.download(args.story.dir);
            }
        }
    }
};