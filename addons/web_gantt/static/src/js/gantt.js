/*---------------------------------------------------------
 * OpenERP web_gantt
 *---------------------------------------------------------*/
openerp.web_gantt = function (instance) {
var _t = instance.web._t,
   _lt = instance.web._lt;
var QWeb = instance.web.qweb;
instance.web.views.add('gantt', 'instance.web_gantt.GanttView');

instance.web_gantt.GanttView = instance.web.View.extend({
    display_name: _lt('Gantt'),
    template: "GanttView",
    view_type: "gantt",
    events: {
	'click .dates .fa-chevron-left': "change_focus_date_left",
	'click .dates .fa-chevron-right': "change_focus_date_right",
	'click .gantt_task_row .gantt_task_cell': "create_on_click",
	'click div.btn-group label': 'change_scale_button',
	'click .oe_gantt_button_create': function() {this.on_task_create({})},
    },     
    init: function() {
        var self = this;
        this._super.apply(this, arguments);
        this.has_been_loaded = $.Deferred();
        this.chart_id = _.uniqueId();

        // Gantt configuration
	gantt.config.autosize = "y";
        gantt.config.round_dnd_dates = false;
        gantt.config.drag_links = false,
        gantt.config.drag_progress = false,
        gantt.config.grid_width = 250;
        gantt.config.row_height = 30;
        gantt.config.duration_unit = "hour";
	gantt.config.initial_scroll = false;
        gantt.config.columns = [{name:"text", label:_t("Gantt View"), tree:true, width:'*' }];
        gantt.templates.grid_folder = function() { return ""; };
        gantt.templates.grid_file = function() { return ""; };
        gantt.templates.grid_indent = function() {
            return "<div class='gantt_tree_indent' style='width:20px;'></div>";
        };

	this.focus_date = moment(new Date());

	gantt.config.start_on_monday = moment().startOf("week").day();
	
	// Color from kanban
	this.kanban_colors = ["rgba(0, 128, 0, ","rgba(204, 204, 204, ","rgba(255, 199, 199, ",
			      "rgba(255, 229, 156, ","rgba(227, 255, 199 ","rgba(199, 255, 213, ",
			      "rgba(199, 255, 255, ","rgba(199, 213, 255, ","rgba(227, 199, 255, ",
			      "rgba(255, 199, 241, "]; 
    },
    view_loading: function(r) {
        return this.load_gantt(r);
    },
    load_gantt: function(fields_view_get, fields_get) {
        var self = this;
        this.fields_view = fields_view_get;
        this.$el.addClass(this.fields_view.arch.attrs['class']);

	// Use scale_zoom attribute in xml file to specify zoom timeline(day,week,month,year), By default month
        var scale = this.fields_view.arch.attrs.scale_zoom;
        if (!_.contains(['day', 'week', 'month', 'year'], scale)) {
            self.scale = "month";
        }

        // Get colors attribute from xml view file.
        if(this.fields_view.arch.attrs.colors) {
            this.colors = _(this.fields_view.arch.attrs.colors.split(';')).chain().compact().map(function(color_pair) {
                var pair = color_pair.split(':'), color = pair[0], expr = pair[1];
                var temp = py.parse(py.tokenize(expr));
                return {'color': color, 'field': temp.expressions[0].value, 'opt': temp.operators[0], 'value': temp.expressions[1].value};
            }).value();
        }

	// dnd by date
	if (self.fields_view.arch.attrs.round_dnd_dates) gantt.config.round_dnd_dates = self.fields_view.arch.attrs.round_dnd_dates;

	// Configure the duration_unit
	if (self.fields_view.arch.attrs.duration_unit) gantt.config.duration_unit = self.fields_view.arch.attrs.duration_unit;
	
	gantt.templates.task_class = function(start, end, task){
	    var classes = []; 
	    if (gantt.hasChild(task.id)){
		classes.push("has_child");
	    } else {
		classes.push("is_leaf");
	    }
	    if (self.fields_view.arch.attrs.consolidation){
		classes.push("consolidation");
	    }
	    return classes.join(" ");
	};

	gantt.templates.task_row_class = function(start, end, task){
	    var classes = ["level_"+task.$level];
	    return classes;
	};
	
        return self.alive(new instance.web.Model(this.dataset.model)
		   .call('fields_get')).then(function (fields) {
		       self.fields = fields;
		       self.has_been_loaded.resolve();
		   });
    },
    do_search: function (domains, contexts, group_bys) {
        var self = this;
        self.last_domains = domains;
        self.last_contexts = contexts;
        self.last_group_bys = group_bys;

	// range date
	// Format to display it
	switch(self.scale){
	case "day":
	    var date_display = self.focus_date.format("D MMM");
	    break;
	case "week":
	    var date_start = self.focus_date.clone().startOf("week").format("D MMM");
	    var date_end = self.focus_date.clone().endOf("week").format("D MMM");
	    var date_display = date_start + " - " + date_end;
	    break;
	case "month":
	    var date_display = self.focus_date.format("MMMM YYYY");
	    break;
	case "year":
	    var date_display = self.focus_date.format("YYYY");
	    break;
	}
	$(".chart_id_"+self.chart_id+" .dates .focus_date").html(date_display);
	// add the date range to the domain.
	var from_date = self.focus_date.clone().subtract(1, self.scale).startOf(self.scale);
	var to_date = self.focus_date.clone().add(3, self.scale).endOf(self.scale);
	domains = domains.concat([ [self.fields_view.arch.attrs.date_start, '<', to_date.format("YYYY-MM-DD")] ]);
	if (self.fields_view.arch.attrs.date_stop)
	    domains = domains.concat([ [self.fields_view.arch.attrs.date_stop, ">", from_date.format("YYYY-MM-DD")] ]);
	// define the width
	gantt.config.start_date = from_date;
	gantt.config.end_date = to_date.add(1, self.scale);

	// Initialize the gantt chart
        self.scale_zoom(self.scale);
        gantt.init(this.chart_id);
        gantt.clearAll();
	gantt._click.gantt_row = undefined; // Remove the focus on click
        gantt.detachAllEvents();

	// select the group by
        var n_group_bys = [];
        if (this.fields_view.arch.attrs.default_group_by) {
            n_group_bys = this.fields_view.arch.attrs.default_group_by.split(',');
        }
        if (group_bys.length) {
            n_group_bys = group_bys;
        }

        // gather the fields to get
        var fields = _.compact(_.map(["date_start", "date_delay", "date_stop",
				      "consolidation", "progress"], function(key) {
            return self.fields_view.arch.attrs[key] || '';
        }));
        fields = _.uniq(fields.concat(_.pluck(this.colors, "field").concat(n_group_bys)));
	fields.push("name");

	// Baseline per group_bys
	// ie : { project_id: (project_start_date, project_end_date), task_id: (task_start_date, task_end_date)}
	self.baseline_attr = false;
	if (self.fields_view.arch.attrs.baseline){
	    self.baseline_attr = JSON.parse(self.fields_view.arch.attrs.baseline);
	    _.each(self.baseline_attr, function(bl, group) {
		fields = fields.concat(bl);
	    });
	}

	// Consolidation maximum options
	self.consolidation_max = false;
	if (self.fields_view.arch.attrs.consolidation_max){
	    var max = JSON.parse(self.fields_view.arch.attrs.consolidation_max);
	    if (max[group_bys[0]]) { self.consolidation_max = max[group_bys[0]]; }
	}
	// Color if consolidation
	if(self.fields_view.arch.attrs.consolidation) {
	    fields.push("color");
	}
	// consolidation exclude, get the related fields
	if (self.fields_view.arch.attrs.consolidation_exclude) {
	    fields = fields.concat(self.fields_view.arch.attrs.consolidation_exclude);
	}

        return $.when(this.has_been_loaded).then(function() {
            return self.dataset.read_slice(fields, {
                domain: domains,
                context: contexts
            }).then(function(data) {
                return self.fetch_colors(data, n_group_bys);
            });
        });
    },
    change_focus_date_left: function(){
	this.focus_date = this.focus_date.subtract(1, this.scale);
	this.reload();
    },
    change_focus_date_right: function(){
	this.focus_date = this.focus_date.add(1, this.scale);
	this.reload();
    },
    change_scale_button: function(e){
	this.scale = this.$el.find(e.currentTarget).find("input").val();
	this.reload();
    },
    reload: function() {
        if (this.last_domains !== undefined){
            return this.do_search(this.last_domains, this.last_contexts, this.last_group_bys);
	}
    },
    fetch_colors: function(tasks, group_bys) {
	var self = this;
	if (!self.fields_view.arch.attrs.consolidation && group_bys.length === 0) return self.on_data_loaded(tasks, group_bys);
	// Load the color for the group_bys
	// Prepare an object with the model in key, and an array of ids in value
	var model_ids = {};
	_.each(tasks, function(task) {
	    _.each(group_bys, function(group) {
		var model = self.fields[group]["relation"];
		var id = task[group];
		if (model && id){
		    if (!model_ids[model]) model_ids[model] = [];
		    model_ids[model].push(id[0]);
		}
	    });
	});
	// remove duplicate
	_.each(model_ids, function(ids, model){
	    model_ids[model] = _.uniq(ids);
	});
	
	// Fetch the color for the specified ids in the specified model
	color_by_group = {};
	var fetch = function(keys){
	    if (keys.length === 0){
		return self.on_data_loaded(tasks, group_bys, color_by_group);
	    } else {
		var key = _.first(keys);
		if (!key) return fetch(_.rest(keys)); // not a relation field
		new instance.web.Model(key)
		    .query(["color"])
		    .filter([ ['id', 'in', model_ids[key]] ])
		    .all()
		    .then(function (colors) {
			if (!color_by_group[key]) color_by_group[key] = {};
			_.each(colors, function(color){
			    color_by_group[key][color.id] = color.color;
			});
			return fetch(_.rest(keys));
		    });
	    }
	};
	var keys = [];
	for(var k in model_ids) keys.push(k);
	fetch(keys);
    },
    on_data_loaded: function(tasks, group_bys, color_by_group) {
        var self = this;

        // if there is no group by, simulate it
        if (group_bys.length == 0) {
            group_bys = ["_pseudo_group_by"];
            _.each(tasks, function(el) {
                el._pseudo_group_by = "Gantt View";
            });
            this.fields._pseudo_group_by = {type: "string"};
        }

	// Prepare the tasks
	tasks = _.compact(_.map(tasks, function(task) {
	    var task_start = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_start]);
            if (!task_start)
                return false;
            var task_stop;
            if (self.fields_view.arch.attrs.date_stop) {
                task_stop = instance.web.auto_str_to_date(task[self.fields_view.arch.attrs.date_stop]);
                if (!task_stop)
                    task_stop = task_start;
            } else { // we assume date_duration is defined
                var tmp = instance.web.format_value(task[self.fields_view.arch.attrs.date_delay],
						    self.fields[self.fields_view.arch.attrs.date_delay]);
                if (!tmp)
                    return false;
                var m_task_start = moment(task_start).add(tmp, gantt.config.duration_unit);
                task_stop = m_task_start.toDate();
            }

	    if (_.isNumber(task[self.fields_view.arch.attrs.progress])) {
                var percent = task[self.fields_view.arch.attrs.progress] || 0;
            } else {
                var percent = 100;
            }
	    
	    task.task_start = task_start;
	    task.task_stop = task_stop;
	    task.percent = percent;

	    // Don't add the task that stops before the min_date
	    // Usefull if the field date_stop is not defined in the gantt view
	    if (self.min_date && task_stop < new Date(self.min_date)) return false;
	    
	    return task;
	}));
	
        // get the groups
        var split_groups = function(tasks, group_bys) {
            if (group_bys.length === 0)
		return tasks;
            var groups = [];
            _.each(tasks, function(task) {
                var group_name = task[_.first(group_bys)];
                var group = _.find(groups, function(group) { return _.isEqual(group.name, group_name); });
                if (group === undefined) {
                    group = {name:group_name, tasks: [], __is_group: true,
			     group_start: false, group_stop: false, percent: [],
			     open: true};
		    
		    // Add the group_by information for creation
		    group.create = [_.first(group_bys), task[_.first(group_bys)]];

		    // folded or not
		    if (self.fields_view.arch.attrs.fold_last_level && group_bys.length <= 1) group.open = false;

		    // the group color
		    var model = self.fields[_.first(group_bys)].relation;
		    if (model && _.has(color_by_group, model)){ 
			group.consolidation_color = color_by_group[model][group_name[0]];
		    }
			
		    // Baseline
		    if (self.baseline_attr){
			if (self.baseline_attr[_.first(group_bys)]){
			    var start = self.baseline_attr[_.first(group_bys)][0];
			    var stop = self.baseline_attr[_.first(group_bys)][1];
			    group.baseline_start = task[start];
			    group.baseline_stop = task[stop];
			}
		    }

                    groups.push(group);
                }
		if (!group.group_start || group.group_start > task.task_start) { group.group_start = task.task_start; }
		if (!group.group_stop || group.group_stop < task.task_stop) { group.group_stop = task.task_stop; }
		group.percent.push(task.percent);
		if (self.open_task_id === task.id) group.open = true; // Show the just created task
                group.tasks.push(task);
            });
            _.each(groups, function(group) {
                group.tasks = split_groups(group.tasks, _.rest(group_bys));
            });
            return groups;
        }
        var groups = split_groups(tasks, group_bys);
	
	// Creation of the chart
	var gantt_tasks = [];
	var generate_tasks = function(task, level, parent_id) {
	    if (task.__is_group) {
		if (task.tasks.length == 0) return
		var project_id = _.uniqueId("gantt_project_");
		var group_name = task.name ? instance.web.format_value(task.name, self.fields[group_bys[level]]) : "-";
		// progress
		var sum = _.reduce(task.percent, function(acc, num) { return acc+num; }, 0);
		var progress = sum / task.percent.length / 100;
		
		var t = {
		    'id': project_id,
		    'text': group_name,
		    'start_date': task.group_start,
		    'duration': gantt.calculateDuration(task.group_start, task.group_stop),
		    'progress': progress,
		    'baseline_start': task.baseline_start,
		    'baseline_stop': task.baseline_stop,
		    'create': task.create,
		    'open': task.open,
		    'consolidation_color': task.consolidation_color,
		};
		if (parent_id) { t.parent = parent_id; }
		gantt_tasks.push(t);
		_.each(task.tasks, function(subtask) {
		    generate_tasks(subtask, level+1, project_id);
		});
	    }
	    else {
		// check condition to apply color.
		var col = undefined;
		_.each(self.colors, function(color){
                    if(eval("'" + task[color.field] + "' " + color.opt + " '" + color.value + "'"))
                        col = color.color;
                });
		if (self.fields_view.arch.attrs.consolidation){
		    if (task.color === 0) task.color = 7; // The default white color for the kanban in blue for the gantt chart
		    col = self.kanban_colors[task.color] + "1)";
		}

		// Consolidation
		var consolidation_value = task[self.fields_view.arch.attrs.consolidation];
		gantt_tasks.push({
		    'id': "gantt_task_" + task.id,
		    'text': task.name,
		    'start_date': task.task_start,
		    'duration': gantt.calculateDuration(task.task_start, task.task_stop),
		    'progress': task.percent / 100,
		    'parent': parent_id,
		    'consolidation': consolidation_value,
		    'consolidation_exclude': task[self.fields_view.arch.attrs.consolidation_exclude],
		    'consolidation_color': task.color,
		    'color': col,
		});
	    }
	}
	_.each(groups, function(group) { generate_tasks(group, 0); });
        gantt.parse({"data": gantt_tasks});

	self.configure_gantt_chart(tasks, group_bys, groups);
	
    },
    configure_gantt_chart: function(tasks, group_bys, groups){
	var self = this;

        gantt.attachEvent("onTaskClick", function(id, e){
            if(gantt.hasChild(id)){ return true; }
            var attr = self.fields_view.arch.attrs;
            if(e.target.className == "gantt_task_content" || e.target.className == "gantt_task_drag task_left" || e.target.className == "gantt_task_drag task_right") {
                if(attr.action) {
                    var actual_id = parseInt(id.split("gantt_task_").slice(1)[0]);
                    if(attr.relative_field) {
                        new instance.web.Model("ir.model.data").call("xmlid_lookup", [attr.action]).done(function(result) {
                            var add_context = {};
                            add_context["search_default_" + attr.relative_field] = actual_id;
                            self.do_action(result[2], {'additional_context': add_context});
                        });
                    }
                    return false;
                }
            }
	    if (id.indexOf("unused") >= 0) {
		var task = gantt.getTask(id);
		var key = "default_"+task.create[0];
		var context = {};
		context[key] = task.create[1][0];
		self.on_task_create(context);
	    } else {
		self.on_task_display(gantt.getTask(id));
	    }
	    return true;
        });

        gantt.attachEvent("onTaskDblClick", function(){ return false; });
	// Fold and unfold project bar when click on it
	gantt.attachEvent("onBeforeTaskSelected", function(id) {
	    if(gantt.hasChild(id)){
		$("[task_id="+id+"] .gantt_tree_icon").click();
		return false;
	    }
            return true;
	});

	// Drag and drop
 	var update_date_parent = function(id) {
	    // Refresh parent when children are resize
            var start_date, stop_date;
            var parent = gantt.getTask(gantt.getTask(id).parent);
            _.each(gantt.getChildren(parent.id), function(task_id){
                var task_start_date = gantt.getTask(task_id).start_date;
                var task_stop_date = gantt.getTask(task_id).end_date;
                if(!start_date) start_date = task_start_date;
                if(!stop_date) stop_date = task_stop_date;
                if(start_date > task_start_date) start_date = task_start_date;
                if(stop_date < task_stop_date) stop_date = task_stop_date;
            });
            parent.start_date = start_date;
            parent.end_date = stop_date;
            gantt.updateTask(parent.id);
 	    if (parent.parent) update_date_parent(parent.id);
 	};
	gantt.attachEvent("onBeforeTaskDrag", function(id, mode, e){
	    var task = gantt.getTask(id);
	    var attr = e.target.attributes.getNamedItem("consolidation_ids");
	    this.lastX = e.pageX;
	    if (attr) {
		var children = attr.value.split(" ");
		this.drag_child = children;
		return true;
	    }
	    if (gantt.hasChild(id)) return false;
	    return true;

	});
        gantt.attachEvent("onTaskDrag", function(id, mode, task, original, e){
            if(gantt.hasChild(id)){
		// var d is the number of millisecond for one pixel
		if (self.scale === "day") var d = 72000;
		if (self.scale === "week") var d = 1728000;
		if (self.scale === "month") var d = 3456000;
		if (self.scale === "year") var d = 51840000;
		diff = (e.pageX - this.lastX) * d;
		this.lastX = e.pageX;
		
		if (task.start_date > original.start_date){ task.start_date = original.start_date; }
		if (task.end_date < original.end_date){ task.end_date = original.end_date; }

		if (this.drag_child){
		    _.each(this.drag_child, function(child_id){
			var child = gantt.getTask(child_id);
			var nstart = +child.start_date + diff;
			var nstop = +child.end_date + diff;
			if (nstart < gantt.config.start_date || nstop > gantt.config.end_date){
			    return false;
			}
			child.start_date = new Date(nstart);
			child.end_date = new Date(nstop);
			gantt.updateTask(child.id);
			update_date_parent(child_id);
		    });
		}
		gantt.updateTask(task.id);
		return false;
	    }
	    update_date_parent(id);
	    return true;
        });
        gantt.attachEvent("onAfterTaskDrag", function(id){
	    if (gantt.hasChild(id) && this.drag_child){
		_.each(this.drag_child, function(child_id){
		    var child = gantt.getTask(child_id);
		    gantt.roundTaskDates(child);
		    gantt.updateTask(child_id);
		    update_date_parent(child_id);
		    self.on_task_changed(gantt.getTask(child_id));
		});
		return false;
	    }
	    update_date_parent(id);
            self.on_task_changed(gantt.getTask(id));
	});

	gantt.attachEvent("onGanttRender", function() {
	    // On last create defined : open the popup
	    if (self.last_create_id && gantt.isTaskExists("gantt_task_"+self.last_create_id)){
		self.on_task_display(gantt.getTask("gantt_task_"+self.last_create_id));
	    }

	    // show the focus date
	    if(!self.open_task_id){
		gantt.showDate(self.focus_date);
	    } else {
		if (gantt.isTaskExists("gantt_task_"+self.open_task_id)) {
		    gantt.showTask("gantt_task_"+self.open_task_id);
		    gantt.selectTask("gantt_task_" + self.open_task_id);
		}
	    }

	    self.last_create_id = undefined;
	    self.task_open_id = undefined;

	    return true;
	});

	// Task text format
	gantt.templates.task_text=function(start, end, task){
	    // default
	    var text = "";
	    // consolidation
	    if (self.fields_view.arch.attrs.consolidation) {
		if (gantt.hasChild(task.id)){
		    text = self.consolidation_children(task, group_bys);
		}
		else { text = task.consolidation + "<span class=\"half_opacity\"> " + self.fields[self.fields_view.arch.attrs.consolidation]['string'] + "</span>"; }
	    }
	    // baseline
	    text += self.baseline(task);
	    return text;
	};
	
	// Load unused resource
	if (group_bys[0] !== "_pseudo_group_by"){
	    new instance.web.Model(self.dataset.model, self.last_contexts, self.last_domains)
		.query(['name'])
		.group_by(group_bys[0])
		.then(function(data){
		    data.forEach(function(elem) {
			if (!(_.find(groups, function(g) { return _.isEqual(g.name, elem.attributes.value); }))){
			    if (self.fields[elem.attributes.grouped_on].relation){
				var id = elem.attributes.value[0];
				var name = elem.attributes.value[1];
			    } else {
				var id  = _.uniqueId();
				var name = elem.attributes.value;
			    }
			    gantt.addTask({
				'id': "gantt_task_unused_" + id,
				'text': name,
				'create': [group_bys[0], [id, name]],
				'start_date': self.focus_date,
				'duration': 0,
			    });
			}
		    });
		});
	};
    },
    scale_zoom: function(value) {
        gantt.config.step = 1;
        gantt.config.min_column_width = 50;
        gantt.config.scale_height = 50;
	var today = new Date();
        gantt.templates.task_cell_class = function(item, date) {
	    var classes = "date_" + date.getTime();
            if(value !== "year" && (date.getDay() == 0 || date.getDay() == 6)) classes += " weekend_task";
	    if(value !== "day" && date.getDate() == today.getDate() && date.getMonth() == today.getMonth() && date.getYear() == today.getYear())
		classes += " today";
	    return classes;
        };
        gantt.templates.date_scale = null;
	
        switch (value) {
            case "day":
                gantt.templates.scale_cell_class = function(date) {
                    if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
                };
                gantt.config.scale_unit = "day";
                gantt.config.date_scale = "%d %M";
                gantt.config.subscales = [{unit:"hour", step:1, date:"%H h"}];
                gantt.config.scale_height = 27;
                break;
            case "week":
                var weekScaleTemplate = function(date){
                    var dateToStr = gantt.date.date_to_str("%d %M %Y");
                    var endDate = gantt.date.add(gantt.date.add(date, 1, "week"), -1, "day");
                        return dateToStr(date) + " - " + dateToStr(endDate);
                };
                gantt.config.scale_unit = "week";
                gantt.templates.date_scale = weekScaleTemplate;
                gantt.config.subscales = [
                    {unit:"day", step:1, date:"%d, %D", css:function(date) {
                        if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
			if(date.getMonth() === today.getMonth() && date.getDate() === today.getDate()) return "today";
                    } }
                ];
                break;
            case "month":
                gantt.config.scale_unit = "month";
                gantt.config.date_scale = "%F, %Y";
                gantt.config.subscales = [
                    {unit:"day", step:1, date:"%d", css:function(date) {
                        if(date.getDay() == 0 || date.getDay() == 6) return "weekend_scale";
			if(date.getMonth() === today.getMonth() && date.getDate() === today.getDate()) return "today";
                    } }
                ];
                gantt.config.min_column_width = 25;
                break;
            case "year":
                gantt.config.scale_unit = "year";
                gantt.config.date_scale = "%Y";
                gantt.config.subscales = [
                    {unit:"month", step:1, date:"%M" }
                ];
                break;
        }
    },
    on_task_changed: function(task_obj) {
        var self = this;
        var start = task_obj.start_date;
        var end = task_obj.end_date;
        var data = {};
        data[self.fields_view.arch.attrs.date_start] =
            instance.web.auto_date_to_str(start, self.fields[self.fields_view.arch.attrs.date_start].type);
        if (self.fields_view.arch.attrs.date_stop) {
            data[self.fields_view.arch.attrs.date_stop] = 
                instance.web.auto_date_to_str(end, self.fields[self.fields_view.arch.attrs.date_stop].type);
        } else { // we assume date_duration is defined
            var duration = gantt.calculateDuration(start, end);
            data[self.fields_view.arch.attrs.date_delay] = duration;
        }
        var task_id = parseInt(task_obj.id.split("gantt_task_").slice(1)[0]);
        this.dataset.write(task_id, data);
    },
    on_task_display: function(task) {
	var self = this;
        var task_id = parseInt(_.last(task.id.split("_")));
	console.log(task, task_id);
	self.open_task_id = task_id;
        var pop = new instance.web.form.FormOpenPopup(self);
        pop.on('write_completed', self, function(){
	    self.reload();
	    pop.destroy();
	});
        pop.show_element(
            self.dataset.model,
            task_id,
            null,
            {readonly: false, title: task.text}
        );
        var form_controller = pop.view_form;
        form_controller.on("load_record", self, function() {
            var footer = pop.$el.closest(".modal").find(".modal-footer");
            footer.find('.oe_form_button_edit,.oe_form_button_save').remove();
            footer.find(".oe_form_button_cancel").prev().remove();
            footer.find('.oe_form_button_cancel').before("<span> or </span>");
            button_edit = _.str.sprintf("<button class='oe_button oe_form_button_edit oe_bold oe_highlight'><span> %s </span></button>",_t("Edit"));
            button_save = _.str.sprintf("<button class='oe_button oe_form_button_save oe_bold oe_highlight'><span> %s </span></button>",_t("Save"));
	    //Delete
	    button_delete = _.str.sprintf("<button class='oe_button oe_form_button_delete delme'><span> %s </span></button>", _t("Delete"));
            footer.prepend(button_edit + button_save + button_delete);
            footer.find('.oe_form_button_edit').hide();
            footer.find('.oe_form_button_edit').on('click', function() {
                form_controller.to_edit_mode();
                footer.find('.oe_form_button_edit,.oe_form_button_save').toggle();
            });
            footer.find('.oe_form_button_save').on('click', function() {
                form_controller.save();
                form_controller.to_view_mode();
                footer.find('.oe_form_button_edit,.oe_form_button_save').toggle();
            });
	    footer.find('.oe_form_button_delete').on('click', function() {
		footer.find('.oe_form_button_cancel').trigger('click');
		if (confirm(_t("Are you sure you want to delete this record"))) {
		    $.when(self.dataset.unlink([task_id])).then(function() {
			$.when(self.dataset.remove_ids([task_id])).then(function() {
			    self.open_task_id = false;
			    self.reload();
			});
		    });
		}
	    });
	    
        });
    },
    on_task_create: function(context) {
        var self = this;
        var pop = new instance.web.form.SelectCreatePopup(this);
        pop.on("elements_selected", self, function(id) {
	    self.open_task_id = parseInt(id);
            self.reload();
        });
        pop.select_element(
            self.dataset.model,
            {
                title: _t("Create"),
                initial_view: "form",
            },
	    [],
	    context
        );
    },
    create_on_click: function(e){
	var self = this;
	var id = e.target.parentElement.attributes.task_id.value;
	var task = gantt.getTask(id);
	
	var class_date = _.find(e.target.classList, function(e){ return e.indexOf("date_") > -1; });
	var start_date = moment(new Date(parseInt(class_date.split("_")[1]))).utc();
	switch (self.scale){
	case "day":
	    var end_date = start_date.clone().add(4, "hour");
	    break;
	case "week":
	    var end_date = start_date.clone().add(2, "day");
	    break;
	case "month":
	    var end_date = start_date.clone().add(4, "day");
	    break;
	case "year":
	    var end_date = start_date.clone().add(2, "month");
	    break;
	}
	create = {};
	var get_create = function(item){
	    if (item.create && self.fields[item.create[0]].relation) {
		create["default_"+item.create[0]] = item.create[1][0];
	    }
	    if (item.parent){
		var parent = gantt.getTask(item.parent);
		get_create(parent);
	    }
	};
	get_create(task);
	create["default_"+self.fields_view.arch.attrs.date_start] = start_date.format("YYYY-MM-DD HH:mm:ss");
	if(self.fields_view.arch.attrs.date_stop) {
	    create["default_"+self.fields_view.arch.attrs.date_stop] = end_date.format("YYYY-MM-DD HH:mm:ss");
	} else { // We assume date_delay is given
	    create["default_"+self.fields_view.arch.attrs.date_delay] = gantt.calculateDuration(start_date, end_date);
	}

	self.on_task_create(create);
    },
    get_all_children: function(id) {
	var c = []
	gantt.eachTask(function(task){
	    if (!gantt.hasChild(task.id)) c.push(task.id);
	}, id);
	return c;
    },
    consolidation_children: function(parent, group_bys) {
	var self = this;
	var children = self.get_all_children(parent.id);
	// First step : create a list of object for the children. The contains (left, consolidation value, consolidation color) where left is position in the bar, and consolidation value is the number to add or remove, and the color is [color, sequence] from the last group_by with these information.
	var leftParent = gantt.getTaskPosition(parent, parent.start_date, parent.end_date).left;
	var getTuple = function(acc, task_id) {
	    var task = gantt.getTask(task_id);
	    var position = gantt.getTaskPosition(task, task.start_date, task.end_date);
	    var left = position.left - leftParent;
	    var right = left + position.width;
	    var start = {type: "start",
			 id: task_id,
			 left: left,
			 consolidation: task.consolidation,
			};
	    var stop = {type: "stop",
			id: task_id,
			left: right,
			consolidation: -(task.consolidation),
		       };
	    if (task.consolidation_exclude) {
		start.consolidation_exclude = true;
		start.color = task.consolidation_color;
		stop.consolidation_exclude = true;
		stop.color = task.consolidation_color;
	    }
	    acc.push(start);
	    acc.push(stop);
	    return acc;
	};
	var steps = _.reduce(children, getTuple, []);
	// Second step : Order it by "left"
	var orderSteps = _.sortBy(steps, function(el) {
	    return el.left;
	});
	// Third step : Create the html for the bar
	var html = "";
	var acc = 0;
	var last_left = 0;
	var exclude = [];
	var not_exclude = 0;
	var ids = [];
	orderSteps.forEach(function(el) {
	    var width = Math.max(el.left - last_left , 0);
	    var padding_left = (width === 0) ? 0:4;
	    if (not_exclude > 0 || exclude.length > 0){
		//content
		var content = acc + "<span class=\"half_opacity\"> " + self.fields[self.fields_view.arch.attrs.consolidation]['string'] + "</span>";
		if (acc === 0 || width < 15 || (self.consolidation_max && acc === self.consolidation_max)) content = "";
		//pointer
		var pointer = (exclude.length === 0 && acc === 0) ? "none" : "all";
		// Color 
		if (exclude.length > 0) {
		    var color = _.last(exclude)+"1)";
		    if (not_exclude) var classes = " exclude";
		    else var classes = "";
		} else {
		    var opacity = (self.consolidation_max) ? (((acc-1) / (self.consolidation_max-1))*0.5) + 0.5 : 1;
		    if (acc === 0){
			var color = "transparent";
		    } else if ((self.consolidation_max) && acc > self.consolidation_max){
			var color = "#CB1C1C";
		    } else if (self.consolidation_max && parent.create[0] === group_bys[0]) {
			var color = self.kanban_colors[0] + opacity + ")";
		    } else if (parent.consolidation_color){
			var color = self.kanban_colors[parent.consolidation_color] + opacity + ")";
		    } else {
			var color = self.kanban_colors[7] + opacity+")";
		    }
		    var classes = "";
		}
		html += "<div class=\"inside_task_bar"+ classes +"\" consolidation_ids=\""+ids.join(" ") +"\" style=\"pointer-events: "+pointer+"; padding-left: "+ padding_left + "px; background-color:"+color+"; left:"+(last_left )+"px; width:"+width+"px;\">"+content+"</div>";
	    }
	    acc = acc + el.consolidation;
	    last_left = el.left;
	    if(el.type === "start"){
		if (el.consolidation_exclude ) exclude.push(self.kanban_colors[el.color]);
		else not_exclude++;
		ids.push(el.id);
	    } else {
		if(el.consolidation_exclude) exclude.pop();
		else not_exclude--;
		ids = _.without(ids, el.id);
	    }
	});
	return html;
    },
    baseline: function(task) {
	var html = "";
	if (task.baseline_start && task.baseline_stop) {
	    var task_position = gantt.getTaskPosition(task, task.start_date, task.stop_date);
	    var start = instance.web.auto_str_to_date(task.baseline_start);
	    var stop = instance.web.auto_str_to_date(task.baseline_stop);
	    var baseline_position = gantt.getTaskPosition(task, start, stop);
	    var left = baseline_position.left - task_position.left;
	    html += "<div style=\"position:absolute; top:20px; width: "+ baseline_position.width + "px; height: 5px; background-color: #0B3A91; left: "+ left + "px; border-radius: 3px;\"></div>"
	}
	return html;
    },
});
};
