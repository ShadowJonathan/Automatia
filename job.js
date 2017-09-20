const PJO = require('persisted-json-object');
const random = require('randomstring');

var jobs = PJO({file: 'jobs.json'});

if (!jobs.queue) {
    jobs.queue = []
}

class Job {
    constructor(...args) {
        let uuid = args[0];
        let jobargs = args[1];
        let module_name = args[2];

        let jobID = this.jobID = uuid + random.generate(10);

        this.jobPacket = {jobID, uuid, args: jobargs, m_n: module_name, finished: false, results: null};
        jobs.queue.push(this.jobPacket);
        jobs.flush = true;

        this.run = new Promise((res) => {
            Job.doJob(this.jobPacket, res)
        });
    }

    static doJob(packet, res) {
        let r = function () {
            packet.results = [...arguments];
            packet.finished = true;
            jobs.flush = true;
            res(...arguments)
        };
        require('./modules')[packet.m_n].doJob(packet.args).then(r)
    }

    static processBacklog() {

    }

    static getResults(JobID) {
        for (let j of jobs) {
            if (j.jobID == JobID) {
                if (!j.finished) {
                    console.warn(j.jobID, 'was missed in the init sweep, module requested results of it');
                    return -1
                } else {
                    return j.results
                }
            }
        }
        return null
    }
};
module.exports = Job;