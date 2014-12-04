openerp.note = function(instance) {
    _t = instance.web._t;
    instance.web_kanban.KanbanGroup.include({
        init: function() {
            this._super.apply(this, arguments);
            this.title = ((this.dataset.model === 'note.note') && (this.title === _t('Undefined'))) ? _t('Shared') : this.title;
        },
    });
};
