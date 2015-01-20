# -*- coding: utf-8 -*-

from openerp import models, fields


class EventEvent(models.Model):
    """ Override Event model to add optional questions when buying tickets. """
    _inherit = 'event.event'

    question_ids = fields.One2many('event.question', 'event_id', 'Questions')
    general_question_ids = fields.One2many('event.question', 'event_id', 'Questions',
                                           domain=[('is_individual', '=', True)])
    specific_question_ids = fields.One2many('event.question', 'event_id', 'Questions',
                                            domain=[('is_individual', '=', False)])


class EventRegistration(models.Model):
    """ Store answers on attendees. """
    _inherit = 'event.registration'

    answer_ids = fields.Many2many('event.answer', 'event_registration_answer', string='Answers')


class EventQuestion(models.Model):
    _name = 'event.question'
    _rec_name = 'title'

    title = fields.Char("Title", required=True)
    event_id = fields.Many2one('event.event', required=True, ondelete='cascade')
    answer_ids = fields.One2many('event.answer', 'question_id', "Answers", required=True)
    is_individual = fields.Boolean('Ask each attendee',
                                   help="If True, this question will be asked for every attendee of a reservation. If "
                                        "not it will be asked only once and its value propagated to every attendees.")


class EventAnswer(models.Model):
    _name = 'event.answer'
    _order = 'name, id'

    name = fields.Char('Answer', required=True)
    question_id = fields.Many2one('event.question', required=True, ondelete='cascade')
    default = fields.Boolean('Default')
