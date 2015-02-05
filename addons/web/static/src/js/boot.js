/*---------------------------------------------------------
 * OpenERP Web Boostrap Code
 *---------------------------------------------------------*/

/**
 * @name openerp
 * @namespace openerp
 */

(function() {
    "use strict";

    var inited = false,
        jobs = [],
        factories = Object.create(null),
        job_names = [],
        job_deps = [],
        counter = 0;

    var services = Object.create({
        qweb: new QWeb2.Engine(),
        $: $,
        _: _,
    });


    var odoo = window.odoo = {
        __DEBUG__: {
            get_dependencies: function (name) {
                return _.pluck(_.where(job_deps, {to: name}), 'from');
            },
            get_dependents: function (name) {
                return _.pluck(_.where(job_deps, {from: name}), 'to');            
            }
        },
        define: function () {
            var args = Array.prototype.slice.call(arguments),
                name = typeof args[0] === 'string' ? args.shift() : '__job' + counter++,
                deps = args[0] instanceof Array ? args.shift() : [],
                factory = args[0];

            if (!(deps instanceof Array)) {
                throw new Error ('Dependencies should be defined by an array', deps);
            }
            if (typeof factory !== 'function') {
                throw new Error ('Factory should be defined by a function', factory);
            }
            if (typeof name !== 'string') {
                throw new Error("Invalid name definition (should be a string", name);
            }            
            if (name in factories) {
                throw new Error("Service " + name + " already defined");                
            }

            factory.deps = deps;
            factories[name] = factory;

            jobs.push({
                name: name,
                factory: factory,
                deps: deps,
            });

            job_names.push(name);
            _.each(deps, function (dep) {
                job_deps.push({from:dep, to:name});
            });

            process_jobs();
        },
        init: function () {
            odoo.__DEBUG__.services = services;
            odoo.__DEBUG__.remaining_jobs = jobs;
            odoo.__DEBUG__.web_client = services['web.web_client'];

            if (jobs.length) {
                console.warn('Warning: not all jobs could be started.', jobs);
            }
        },
    };

    window.openerp = {};

    function process_jobs() {
        var job, require;
        while (jobs.length && (job = _.find(jobs, is_ready))) {
            require = make_require(job);

            services[job.name] = job.factory.call(null, require) || job;
            if (require.__require_calls !== job.deps.length) {
                console.warn('Job ' + job.name + ' did not require all its dependencies');
            }
            jobs = _.without(jobs, job);
            delete factories[job.name];
        }
    }

    function is_ready (job) {
        return _.every(job.factory.deps, function (name) { return name in services; });
    }

    function make_require (job) {
        var deps = _.pick(services, job.deps);

        function require (name) {
            if (!(name in deps)) {
                console.error('Undefined dependency: ', name);
            } else {
                require.__require_calls++;
            }
            return deps[name];
        }

        require.__require_calls = 0;
        return require;
    }

})();
