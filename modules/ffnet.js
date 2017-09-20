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

    upstreamKick() {
        if (this.meta.ffnet_queue.length > 0) {

        }
    }

    handle(message) {
        if (message.queue) {
            for (let s of message.queue) {
                this.download(s.id)
            }
            message.reply({
                orig: 'ffnet',
                reg: 'queue',
                queue: 'accepted'
            })
        } else if (message.story_id) {
            if (message.meta) {
                new SA.Story(message.story_id, this.s.send).meta().then(this.s.send)
            } else if (message.download) {
                this.download(message.story_id)
            } else if (message.cache) {

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

        j.run.then((finished) => {
            this.notify(finished)
        })
    }

    toJSON() {
        return {}
    }

    static doJob(args) {
        return (async () => {
            switch (args.type) {
                case 'dl': {
                    let s = new SA.Story(args.story.id, args.self && args.self.s.send || (() => {
                    }));
                    if (args.self) {
                        s.on('notification', (n) => {
                            args.self.notify(n)
                        });
                        s.on('got_meta', (m) => {
                            args.self.notify({meta: m})
                        })
                    }
                    return await s.download(args.story.dir)
                }
            }
        })()
    }
};