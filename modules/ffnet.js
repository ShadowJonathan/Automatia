const Job = require('./../job');
const SA = require('./../python').ffnet;


module.exports = class ffnet {
    constructor(server) {
        this.s = server;
        this.meta = server.meta;
        if (!this.meta.ffnet_queue) {
            this.meta.ffnet_queue = []
        }
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
     * @param {String} message.a_url
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
                }
            }
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