(function(){
    "use strict";
    var _t = openerp.web._t;

    openerp.planner.PlannerDialog.include({
        prepare_planner_event: function() {
            var self = this;
            this._super.apply(this, arguments);
            if(self.planner['planner_application'] == 'planner_project') {
                var stages = {
                    'development_process': [
                        _t('Specification'), _t('Validation'), _t('Development'),
                        _t('Testing'), _t('Deployment'), '', '',
                        _t('Specification of task is written'),
                        _t('Specification is validated'),
                        _t('Task is Developed'),
                        _t('Task is tested'), _t('Finally task is deployed'), '', ''],
                    'marketing_department': [
                        _t('Backlog'), _t('In progress'), _t('Copywriting / Design'), _t('Distribute'), _t('Done'), '',
                        '', _t('Has a clear description'), _t('Work has started'), _t('Ready for layout / copywriting'),
                        _t('Ready to be displayed, published or sent'),
                        _t('Distribution is completed'), '', ''],
                    'scrum_methodology': [
                        _t('Backlog'), _t('Sprint'), _t('Test'), _t('Documentation'), _t('Release'), '', '',
                        _t('Clear description and purpose'),
                        _t('Added in current sprit'),
                        _t('Ready for testing'), _t('Test is OK, need to document'),
                        _t('Ready for release'), '', ''],
                    'customer_service': [
                        _t('Backlog'), _t('New'), _t('In progress'), _t('Wait. Customer'), _t('Wait. Expert'), _t('Done'), 
                        _t('Cancelled'),_t('Customer service has found new issue'), _t('Customer has reported new issue'), 
                         _t('Issue is being worked on'),
                        _t('Customer feedback has been asked'), _t('Expert advice has been asked'), _t('Issue is solved'),
                        _t('Reason for cancellation has been documented')],
                    'repair_workshop': [
                        _t('Incoming'), _t('In progress'), _t('Wait. Customer'), _t('Wait. Expert'), _t('Done'), _t('Cancelled'), 
                        '', _t('New repair added'), _t('Repair has started'), _t('Feedback from customer requested'),
                        _t('Request for parts has been sent'), _t('Repair is completed'), _t('Customer has cancelled repair'), ''],
                    'basic_management': [
                        _t('Ideas'), _t('To Do'), _t('Done'),
                        _t('Cancelled'), '', '', '',
                        _t('Idea is fully explained'),
                        _t('Idea has been transformed into concrete actions'),
                        _t('Task is completed'),
                        _t('Reason for cancellation has been documented'), '', '', '']
                }
                self.$el.on('change', '#input_element_kanban_stage_pipeline', function(ev) {
                    var option = $(ev.target).find(":selected").val();
                    if (_.has(stages, option)) {
                        var values = stages[option];
                        for(var i=0; i<values.length; i++) {
                            $('#input_element_stage_'+i).val(values[i]);
                        }
                    }
                });
                $( ".user_project" ).on('change', function() {
                    $("#" + $(this).data("id")).val($(this).val());
                });
            }
        }
    });
})();
