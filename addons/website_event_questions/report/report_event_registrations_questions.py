# -*- coding: utf-8 -*-

from openerp import fields, models, tools


class report_event_registration_questions(models.Model):
    _name = "event.question.report"
    _auto = False

    event_id = fields.Many2one('event.event')
    attendee_id = fields.Many2one('event.registration')
    question_id = fields.Many2one('event.question')
    answer_id = fields.Many2one('event.answer')

    def init(self, cr):
        """ Event Question main report """
        tools.drop_view_if_exists(cr, 'event_question_report')
        cr.execute(""" CREATE VIEW event_question_report AS (
            SELECT
                att_answer.event_registration_id as attendee_id,
                answer.id as id,
                answer.question_id as question_id,
                answer.id as answer_id,
                question.event_id as event_id
            FROM
                event_registration_answer att_answer
            LEFT JOIN
                event_answer as answer ON answer.id = att_answer.event_answer_id
            LEFT JOIN
                event_question as question ON question.id = answer.question_id
            GROUP BY
                attendee_id,
                event_id,
                question_id,
                answer_id
        )""")
