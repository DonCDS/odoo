(function(){
    "use strict";

    openerp.planner.PlannerDialog.include({
        prepare_planner_event: function() {
            var self = this;
            this._super.apply(this, arguments);
            if(self.planner['planner_application'] == 'planner_project') {
                var stages = {
                    'development_process': [
                        'Ideas', 'To Do', 'Done',
                        'Cancelled', '', '', '',
                        'Idea is fully explained',
                        'Idea has been transformed into concrete actions',
                        'Task is completed',
                        'Reason for cancellation has been documented', '', '', ''],
                    'marketing_department': [
                        'Backlog', 'In progress', 'Copywriting / Design', 'Distribute', 'Done', '',
                        '', 'Has a clear description', 'Work has started', 'Ready for layout / copywriting',
                        'Ready to be displayed, published or sent',
                        'Distribution is completed', '', ''],
                    'scrum_methodology': [
                        'Backlog', 'Sprint', 'Test', 'Documentation', 'Release', '', '',
                        'Clear description and purpose',
                        'Added in current sprit',
                        'Ready for testing', 'Test is OK, need to document',
                        'Ready for release', '', ''],
                    'customer_service': [
                        'Backlog', 'New', 'In progress', 'Wait. Customer', 'Wait. Expert', 'Done', 'Cancelled',
                        'Customer service has found new issue', 'Customer has reported new issue', 'Issue is being worked on',
                        'Customer feedback has been asked', 'Expert advice has been asked', 'Issue is solved',
                        'Reason for cancellation has been documented'],
                    'repair_workshop': [
                        'Incoming', 'In progress', 'Wait. Customer', 'Wait. Expert', 'Done', 'Cancelled', '',
                        'New repair added', 'Repair has started', 'Feedback from customer requested',
                        'Request for parts has been sent', 'Repair is completed', 'Customer has cancelled repair', ''],
                    'basic_management': [
                        'Ideas', 'To Do', 'Done',
                        'Cancelled', '', '', '',
                        'Idea is fully explained',
                        'Idea has been transformed into concrete actions',
                        'Task is completed',
                        'Reason for cancellation has been documented', '', '', '']
                }
                self.$el.on('change', '#input_element_pipeline', function(ev) {
                    var option = $(ev.target).find(":selected").val();
                    if (_.has(stages, option)) {
                        var values = stages[option];
                        for(var i=0; i<values.length; i++) {
                            $('#input_element_stage_'+i).val(values[i]);
                        }
                    }
                });
            }
        }
    });
})();
