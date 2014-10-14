# -*- coding: utf-8 -*-
import datetime
import time
from dateutil.relativedelta import relativedelta

from openerp import models, fields, api
from openerp import tools
from openerp.exceptions import UserError
from openerp.tools.translate import _
from openerp.exceptions import Warning


class fleet_vehicle_cost(models.Model):
    _name = 'fleet.vehicle.cost'
    _description = 'Cost related to a vehicle'
    _order = 'date desc, vehicle_id asc, id desc'

    @api.one
    @api.depends('odometer_id')
    def _get_odometer(self):
        self.odometer = self.odometer_id and self.odometer_id.value

    @api.one
    def _set_odometer(self):
        if not self.odometer:
            raise UserError(_('Emptying the odometer value of a vehicle is not allowed.'))
        odometer_id = self.env['fleet.vehicle.odometer'].create({
            'value': self.odometer,
            'date': self.date or fields.Date.today(),
            'vehicle_id': self.vehicle_id.id})
        return self.write({'odometer_id': odometer_id.id})

    name = fields.Char(related='vehicle_id.name', string='Name', store=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', required=True,
                                 help='Vehicle concerned by this log')
    cost_subtype_id = fields.Many2one('fleet.service.type', string='Type',
                                      help='Cost type purchased with this cost')
    amount = fields.Float('Total Price')
    cost_type = fields.Selection(selection=[('contract', 'Contract'), ('services', 'Services'),
                                            ('fuel', 'Fuel'), ('other', 'Other')],
                                 string='Category of the cost', help='For internal purpose only',
                                 required=True, default='other')
    parent_id = fields.Many2one('fleet.vehicle.cost', string='Parent', help='Parent cost to this current cost')
    cost_ids = fields.One2many('fleet.vehicle.cost', 'parent_id', string='Included Services')
    odometer_id = fields.Many2one('fleet.vehicle.odometer', string='Odometer',
                                  help='Odometer measure of the vehicle at the moment of this log')
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Odometer Value',
                            help='Odometer measure of the vehicle at the moment of this log', store=True)
    odometer_unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)
    date = fields.Date('Date', help='Date when the cost has been executed')
    contract_id = fields.Many2one('fleet.vehicle.log.contract', string='Contract',
                                  help='Contract attached to this cost')
    auto_generated = fields.Boolean('Automatically Generated', readonly=True, required=True)

    @api.model
    def create(self, data):
        # make sure that the data are consistent with values of parent and contract records given
        if 'parent_id' in data and data['parent_id']:
            parent = self.browse(data['parent_id'])
            data['vehicle_id'] = parent.vehicle_id.id
            data['date'] = parent.date
            data['cost_type'] = parent.cost_type
        if data.get('contract_id'):
            contract = self.env['fleet.vehicle.log.contract'].browse(data['contract_id'])
            data['vehicle_id'] = contract.vehicle_id.id
            data['cost_subtype_id'] = contract.cost_subtype_id.id
            data['cost_type'] = contract.cost_type
        if 'odometer' in data and not data['odometer']:
            # if received value for odometer is 0, then remove it from the data as it would result to the creation of a
            # odometer log with 0, which is to be avoided
            del(data['odometer'])
        return super(fleet_vehicle_cost, self).create(data)


class fleet_vehicle_tag(models.Model):
    _name = 'fleet.vehicle.tag'

    name = fields.Char('Name', required=True, translate=True)


class fleet_vehicle_stage(models.Model):
    _name = 'fleet.vehicle.stage'
    _order = 'sequence asc, id asc'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer('Sequence', help="Used to order the vehicle stages")

    _sql_constraints = [('fleet_stage_name_unique', 'unique(name)', _('Stage name already exists'))]


class fleet_vehicle_model(models.Model):

    _name = 'fleet.vehicle.model'
    _description = 'Model of a vehicle'
    _order = 'name asc, id asc'

    @api.multi
    def name_get(self):
        result = []
        for model in self:
            name = model.name
            if model.make_id.name:
                name = model.make_id.name + ' / ' + name if name else ''
            result.append((model.id, name))
        return result

    @api.onchange('make_id')
    def on_change_make(self):
        self.image = self.make_id.image

    name = fields.Char(string='Name', store=True, required=True)
    make_id = fields.Many2one('fleet.make', string='Make', oldname='brand_id', required=True, help='Make of the vehicle')
    vendors = fields.Many2many('res.partner', 'fleet_vehicle_model_vendors', 'model_id', 'partner_id', string='Vendors')
    image = fields.Binary(related='make_id.image', string="Logo", store=True)
    image_medium = fields.Binary(related='make_id.image_medium', string="Logo (medium)", store=True)
    image_small = fields.Binary(related='make_id.image_small', string="Logo (small)", store=True)


class fleet_make(models.Model):
    _name = 'fleet.make'
    _description = 'Make of the vehicle'
    _order = 'name asc, id asc'

    @api.multi
    @api.depends('image')
    def _get_image(self):
        all_image = tools.image_get_resized_images(self.image)
        self.image_medium = all_image.get('image_medium')
        self.image_small = all_image.get('image_small')

    @api.one
    def _set_image(self):
        self.write({'image': tools.image_resize_image_big(self.image_medium)})

    name = fields.Char('Make', required=True)
    image = fields.Binary("Logo", help="This field holds the image used as logo for the brand,limited to 1024x1024px.")
    image_medium = fields.Binary(compute='_get_image', inverse='_set_image', string="Medium-sized photo", store=True,
                                 help="Medium-sized logo of the brand. It is automatically "
                                      "resize as a 128x128px image, with aspect ratio preserved. "
                                      "Use this field in form views or some kanban views.")
    image_small = fields.Binary(compute='_get_image', inverse='_set_image', string="Small-sized photo", store=True,
                                help="Small-sized photo of the brand. It is automatically "
                                     "resize as a 64x64px image, with aspect ratio preserved. "
                                     "Use this field anywhere a small image is required.")


class fleet_vehicle(models.Model):

    _name = 'fleet.vehicle'
    _description = 'Information on a vehicle'
    _order = 'license_plate asc'
    _inherit = 'mail.thread'

    @api.multi
    @api.depends('license_plate')
    def _vehicle_name_get_fnc(self):
        for record in self:
            if record.model_id:
                record.name = record.model_id.make_id.name + ' / ' + record.model_id.name + ' / ' \
                    + record.license_plate
            else:
                record.name = record.license_plate

    @api.multi
    def return_action_to_open(self):
        """ This opens the xml view specified in xml_id for the current vehicle """
        if self._context.get('xml_id'):
            res = self.env.ref('fleet.' + self._context['xml_id']).read()[0]
            res['context'] = self._context or {}
            res['context'] = dict(res['context'], default_vehicle_id=self[0].id)
            res['domain'] = [('vehicle_id', '=', self[0].id)]
            return res
        return False

    @api.multi
    def act_show_log_cost(self):
        """ This opens log view to view and add new log for this vehicle,
            groupBy default to only show effective costs
            @return: the costs log view
        """
        res = self.env.ref('fleet.fleet_vehicle_costs_act').read()[0]
        res['context'] = self._context or {}
        res['context'] = dict(res['context'], default_vehicle_id=self.id, search_default_parent_false=True)
        res['domain'] = [('vehicle_id', '=', self[0].id)]
        return res

    @api.multi
    def _get_odometer(self):
        fleet_odo_obj = self.env['fleet.vehicle.odometer']
        for record in self:
            last_odometer = fleet_odo_obj.search([('vehicle_id', '=', record.id)], limit=1, order='value desc')
            if last_odometer:
                record.odometer = last_odometer[0].value

    def _set_odometer(self):
        if self.odometer:
            date = fields.Date.today()
            data = {'value': self.odometer, 'date': date, 'vehicle_id': self.id}
            return self.env['fleet.vehicle.odometer'].create(data)

    @api.model
    def _search_get_overdue_contract_reminder(self, operator, value):
        contract = self.env['fleet.vehicle.log.contract']
        if not (operator in ('=', '!=', '<>') and value in (True, False)):
            raise Exception("Operation not supported")
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.today()
        overdue_contracts = contract.read_group([('expiration_date', '<', today)], fields=['vehicle_id'],
                                                groupby=['vehicle_id'])
        list_overdue_contract = []
        for overdue_contract in overdue_contracts:
            vehicle_id = str(overdue_contract['vehicle_id'][0])
            list_overdue_contract.append(vehicle_id)
        return [('id', search_operator, list_overdue_contract)]

    @api.model
    def _search_contract_renewal_due_soon(self, operator, value):
        contract = self.env['fleet.vehicle.log.contract']
        if not (operator in ('=', '!=', '<>') and value in (True, False)):
            raise Exception("Operation not supported")
        if (operator == '=' and value is True) or (operator in ('<>', '!=') and value is False):
            search_operator = 'in'
        else:
            search_operator = 'not in'
        today = fields.Date.today()
        datetime_today = fields.Datetime.from_string(today)
        limit_date = str((datetime_today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
        renewal_contracts = contract.read_group([('expiration_date', '>', today),
                                                 ('expiration_date', '<', limit_date)],
                                                fields=['vehicle_id'], groupby=['vehicle_id'])
        list_renewal_contract = []
        for renewal_contract in renewal_contracts:
            vehicle_id = str(renewal_contract['vehicle_id'][0])
            list_renewal_contract.append(vehicle_id)
        return [('id', search_operator, list_renewal_contract)]

    @api.multi
    def _get_contract_reminder_fnc(self):
        log_cont_obj = self.env['fleet.vehicle.log.contract']
        for record in self:
            overdue = False
            due_soon = False
            total = 0
            name = ''
            for element in record.log_contracts:
                if element.state in ('open', 'toclose') and element.expiration_date:
                    current_date = fields.Datetime.from_string(fields.Date.today())
                    due_time = fields.Datetime.from_string(element.expiration_date)
                    diff_time = (due_time-current_date).days
                    if diff_time < 0:
                        overdue = True
                        total += 1
                    if diff_time < 15 and diff_time >= 0:
                            due_soon = True
                            total += 1
                    if overdue or due_soon:
                        ids = log_cont_obj.search([('vehicle_id', '=', record.id),
                                                   ('state', 'in', ('open', 'toclose'))],
                                                  limit=1, order='expiration_date asc')
                        if len(ids._ids) > 0:
                            # we display only the name of the oldest overdue/due soon contract
                            name = (ids[0].cost_subtype_id.name)

            record.contract_renewal_overdue = overdue
            record.contract_renewal_due_soon = due_soon
            record.contract_renewal_total = (total - 1)  # we remove 1 from the real total for display purposes
            record.contract_renewal_name = name

    @api.model
    def _get_default_stage(self):
        try:
            model_id = self.env.ref('fleet.vehicle_stage_active').id
        except ValueError:
            model_id = False
        return model_id

    @api.multi
    def _count_all(self):
        odometer = self.env['fleet.vehicle.odometer']
        logFuel = self.env['fleet.vehicle.log.fuel']
        logService = self.env['fleet.vehicle.log.services']
        logContract = self.env['fleet.vehicle.log.contract']
        cost = self.env['fleet.vehicle.cost']
        for vehicle_id in self:
            vehicle_id.odometer_count = odometer.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.fuel_logs_count = logFuel.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.service_count = logService.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.contract_count = logContract.search_count([('vehicle_id', '=', vehicle_id.id)])
            vehicle_id.cost_count = cost.search_count([('vehicle_id', '=', vehicle_id.id), ('parent_id', '=', False)])

    name = fields.Char(compute='_vehicle_name_get_fnc', string='Name', store=True)
    company_id = fields.Many2one('res.company', string='Company')
    license_plate = fields.Char(string='License Plate', required=True, track_visibility='onchange',
                                help='License plate number of the vehicle (ie: plate number for a car)')
    vin_sn = fields.Char(string='Chassis Number', help='Unique number written on the vehicle motor (VIN/SN number)',
                         copy=False)
    driver_id = fields.Many2one('res.partner', string='Driver', track_visibility='onchange',
                                help='Driver of the vehicle')
    model_id = fields.Many2one('fleet.vehicle.model', string='Model', required=True, track_visibility='onchange',
                               help='Model of the vehicle')
    log_fuel = fields.One2many('fleet.vehicle.log.fuel', 'vehicle_id', string='Fuel Logs')
    log_services = fields.One2many('fleet.vehicle.log.services', 'vehicle_id', string='Services Logs')
    log_contracts = fields.One2many('fleet.vehicle.log.contract', 'vehicle_id', string='Contracts')
    cost_count = fields.Integer(compute='_count_all', string="Costs")
    contract_count = fields.Integer(compute='_count_all', string='Contracts')
    service_count = fields.Integer(compute='_count_all', string='Services')
    fuel_logs_count = fields.Integer(compute='_count_all', string='Fuel Logs')
    odometer_count = fields.Integer(compute='_count_all', string='Odometer')
    acquisition_date = fields.Date('Acquisition Date', help='Date when the vehicle has been bought')
    color = fields.Char(string='Color', help='Color of the vehicle')
    stage_id = fields.Many2one('fleet.vehicle.stage', string='Stage', oldname='state_id', track_visibility='onchange',
                               help='Current state of the vehicle', default=_get_default_stage)
    location = fields.Char(string='Location', help='Location of the vehicle (garage, ...)')
    seats = fields.Integer('Seats Number', help='Number of seats of the vehicle')
    doors = fields.Integer('Doors Number', help='Number of doors of the vehicle', default=5)
    tag_ids = fields.Many2many('fleet.vehicle.tag', 'fleet_vehicle_vehicle_tag_rel', 'vehicle_tag_id', 'tag_id',
                               string='Tags', copy=False)
    odometer = fields.Float(compute='_get_odometer', inverse='_set_odometer', string='Last Odometer',
                            help='Odometer measure of the vehicle at the moment of this log')
    odometer_unit = fields.Selection(selection=[('kilometers', 'Kilometers'), ('miles', 'Miles')],
                                     string='Odometer Unit', help='Unit of the odometer',
                                     required=True, default='kilometers')
    transmission = fields.Selection(selection=[('manual', 'Manual'), ('automatic', 'Automatic')],
                                    string='Transmission', help='Transmission Used by the vehicle')
    fuel_type = fields.Selection(selection=[('gasoline', 'Gasoline'), ('diesel', 'Diesel'),
                                            ('electric', 'Electric'), ('hybrid', 'Hybrid')],
                                 string='Fuel Type', help='Fuel Used by the vehicle')
    horsepower = fields.Integer('Horsepower')
    horsepower_tax = fields.Float('Horsepower Taxation')
    power = fields.Integer('Power', help='Power in kW of the vehicle')
    co2 = fields.Float('CO2 Emissions', help='CO2 emissions of the vehicle')
    image = fields.Binary(related='model_id.make_id.image', string="Logo", store=True)
    image_medium = fields.Binary(related='model_id.make_id.image_medium', string="Logo (medium)", store=True)
    image_small = fields.Binary(related='model_id.make_id.image_small', string="Logo (small)", store=True)
    contract_renewal_due_soon = fields.Boolean(compute='_get_contract_reminder_fnc',
                                               search='_search_contract_renewal_due_soon',
                                               string='Has Contracts to renew')
    contract_renewal_overdue = fields.Boolean(compute='_get_contract_reminder_fnc',
                                              search='_search_get_overdue_contract_reminder',
                                              string='Has Contracts Overdue')
    contract_renewal_name = fields.Text(compute='_get_contract_reminder_fnc', string='Name of contract to renew soon')
    contract_renewal_total = fields.Integer(compute='_get_contract_reminder_fnc',
                                            string='Total of contracts due or overdue minus one')
    car_value = fields.Float('Car Value', help='Value of the bought vehicle')

    _sql_constraints = [('unique_chassis_number', 'unique(vin_sn)', 'Same Chassis Number is already exists.')]

    @api.onchange('model_id')
    def on_change_model(self):
        self.image = self.model_id.image

    @api.model
    def create(self, data):
        vehicle_id = super(fleet_vehicle, self).create(data)
        vehicle_id.message_post(body=_('%s %s has been added to the fleet!') % (vehicle_id.model_id.name,
                                                                                vehicle_id.license_plate))
        return vehicle_id


class fleet_vehicle_odometer(models.Model):

    _name = 'fleet.vehicle.odometer'
    _description = 'Odometer log for a vehicle'
    _order = 'date desc'

    @api.depends('vehicle_id')
    def _vehicle_log_name_get_fnc(self):
        name = self.vehicle_id.name if self.vehicle_id.name else ''
        if self.date:
            name = name + ' / ' + str(self.date)
        self.name = name

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.unit = self.vehicle_id.odometer_unit

    name = fields.Char(compute='_vehicle_log_name_get_fnc', string='Name', store=True)
    date = fields.Date('Date', default=fields.Date.today())
    value = fields.Float('Odometer Value', group_operator="max")
    vehicle_id = fields.Many2one('fleet.vehicle', 'Vehicle', required=True)
    unit = fields.Selection(related='vehicle_id.odometer_unit', string="Unit", readonly=True)


class fleet_vehicle_log_fuel(models.Model):

    _name = 'fleet.vehicle.log.fuel'
    _description = 'Fuel log for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id

    @api.onchange('liter', 'price_per_liter', 'amount')
    def on_change_liter(self):
        """
        need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)

    @api.onchange('price_per_liter')
    def on_change_price_per_liter(self):
        """
        need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)

    @api.onchange('amount')
    def on_change_amount(self):
        """
        need to cast in float because the value receveid from web client maybe an integer (Javascript and JSON do not
        make any difference between 3.0 and 3). This cause a problem if you encode, for example, 2 liters at 1.5 per
        liter => total is computed as 3.0, then trigger an onchange that recomputes price_per_liter as 3/2=1 (instead
        of 3.0/2=1.5)
        If there is no change in the result, we return an empty dict to prevent an infinite loop due to the 3 intertwine
        onchange. And in order to verify that there is no change in the result, we have to limit the precision of the
        computation to 2 decimal
        """
        liter = float(self.liter)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        elif amount > 0 and price_per_liter > 0 and round(amount / price_per_liter, 2) != liter:
            self.liter = round(amount / price_per_liter, 2)
        elif liter > 0 and price_per_liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)

    @api.model
    def _get_default_service_type(self):
        try:
            model_id = self.env.ref('fleet.type_service_refueling').id
        except ValueError:
            model_id = False
        return model_id

    liter = fields.Float('Liter')
    price_per_liter = fields.Float('Price Per Liter')
    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char(string='Invoice Reference', size=64)
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    notes = fields.Text('Notes')
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database

    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'fuel',
    }


class fleet_vehicle_log_services(models.Model):

    _name = 'fleet.vehicle.log.services'
    _description = 'Services for vehicles'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit
        self.purchaser_id = self.vehicle_id.driver_id

    @api.model
    def _get_default_service_type(self):
        try:
            model_id = self.env.ref('fleet.type_service_service_8').id
        except ValueError:
            model_id = False
        return model_id

    purchaser_id = fields.Many2one('res.partner', string='Purchaser',
                                   domain="['|', ('customer', '=', True), ('employee', '=', True)]")
    invoice_reference = fields.Char(string='Invoice Reference')
    vendor_id = fields.Many2one('res.partner', string='Supplier', domain="[('supplier', '=', True)]")
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to address
    # fields from inherited table and (2) fields that aren't stored in database
    notes = fields.Text('Notes')
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')

    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_service_type,
        'cost_type': 'services'
    }


class fleet_service_type(models.Model):

    _name = 'fleet.service.type'
    _description = 'Type of services available on a vehicle'

    name = fields.Char('Name', required=True, translate=True)
    category = fields.Selection(selection=[('contract', 'Contract'), ('service', 'Service'), ('both', 'Both')],
                                string='Category', required=True,
                                help='Choose whether the service refer to contracts, vehicle services or both')


class fleet_vehicle_log_contract(models.Model):

    _name = 'fleet.vehicle.log.contract'
    _description = 'Contract information on a vehicle'
    _order = 'state desc, expiration_date'
    _inherits = {'fleet.vehicle.cost': 'cost_id'}

    @api.model
    def scheduler_manage_auto_costs(self):
        """
        This method is called by a cron task
        It creates costs for contracts having the "recurring cost" field setted, depending on their frequency
        For example, if a contract has a reccuring cost of 200 with a weekly frequency, this method creates a cost of
        200 on the first day of each week, from the date of the last recurring costs in the database to today
        If the contract has not yet any recurring costs in the database, the method generates the recurring costs
        from the start_date to today
        The created costs are associated to a contract thanks to the many2one field contract_id
        If the contract has no start_date, no cost will be created, even if the contract has recurring costs
        """
        vehicle_cost_obj = self.env['fleet.vehicle.cost']
        today = fields.Datetime.from_string(fields.Date.today())
        contract_ids = self.env['fleet.vehicle.log.contract'].search([('state', '!=', 'closed'),
                                                                      '|', ('start_date', '=', None),
                                                                      ('cost_frequency', '!=', 'no')])
        deltas = {'yearly': relativedelta(years=+1), 'monthly': relativedelta(months=+1),
                  'weekly': relativedelta(weeks=+1), 'daily': relativedelta(days=+1)}
        for contract in contract_ids:
            last_cost_date = contract.start_date
            if contract.generated_cost_ids:
                last_autogenerated_cost = vehicle_cost_obj.search(['&', ('contract_id', '=', contract.id),
                                                                   ('auto_generated', '=', True)], order='date desc')[0]
                if last_autogenerated_cost:
                    last_cost_date = last_autogenerated_cost.date
            last_cost_date = datetime.datetime.strptime(last_cost_date, tools.DEFAULT_SERVER_DATE_FORMAT)
            last_cost_date += deltas.get(contract.cost_frequency)
            while (last_cost_date <= today) and (
                    last_cost_date <= fields.Datetime.from_string(contract.expiration_date)):
                data = {
                    'amount': contract.cost_generated,
                    'date': last_cost_date.strftime(tools.DEFAULT_SERVER_DATE_FORMAT),
                    'vehicle_id': contract.vehicle_id.id,
                    'cost_subtype_id': contract.cost_subtype_id.id,
                    'contract_id': contract.id,
                    'auto_generated': True
                }
                self.env['fleet.vehicle.cost'].create(data)
                last_cost_date += deltas.get(contract.cost_frequency)
        return True

    @api.model
    def scheduler_manage_contract_expiration(self):
        # This method is called by a cron task
        # It manages the state of a contract, possibly by posting a message on the vehicle concerned and
        # updating its status
        today = fields.Datetime.from_string(fields.Date.today())
        limit_date = (today + relativedelta(days=+15)).strftime(tools.DEFAULT_SERVER_DATE_FORMAT)
        ids = self.search(['&', ('state', '=', 'open'), ('expiration_date', '<', limit_date)])
        res = {}
        for contract in ids:
            if contract.vehicle_id.id in res:
                res[contract.vehicle_id.id] += 1
            else:
                res[contract.vehicle_id.id] = 1

        for vehicle, value in res.items():
            self.env['fleet.vehicle'].browse(vehicle).message_post(body=_('%s contract(s) need(s) to be renewed '
                                                                          'and/or closed!') % (str(value)))
        return self.write({'state': 'toclose'})

    @api.model
    def run_scheduler(self):
        self.scheduler_manage_auto_costs()
        self.scheduler_manage_contract_expiration()

    @api.multi
    @api.depends('cost_subtype_id')
    def _vehicle_contract_name_get_fnc(self):
        for record in self:
            name = record.vehicle_id.name if record.vehicle_id else ''
            if record.cost_subtype_id and record.cost_subtype_id.name:
                name += ' / ' + record.cost_subtype_id.name
            if record.date:
                name += ' / ' + record.date
            record.name = name

    @api.onchange('vehicle_id')
    def on_change_vehicle(self):
        self.odometer_unit = self.vehicle_id.odometer_unit

    @api.multi
    def compute_next_year_date(self, strdate):
        oneyear = relativedelta(years=+1)
        curdate = fields.Datetime.from_string(strdate)
        return fields.Datetime.to_string(curdate + oneyear)

    @api.multi
    def compute_days_left(self):
        """
        if contract is in an open state and is overdue, return 0
        if contract is in a closed state, return -1
        otherwise return the number of days before the contract expires
        """
        today = fields.Datetime.from_string(time.strftime(tools.DEFAULT_SERVER_DATE_FORMAT))
        for record in self:
            if record.expiration_date and (record.state in ('open', 'toclose')):
                renew_date = fields.Datetime.from_string(record.expiration_date)
                diff_time = (renew_date - today).days
                record.days_left = diff_time > 0 and diff_time or 0
            else:
                record.days_left = -1

    @api.one
    def act_renew_contract(self):
        if not (len(self._ids) == 1):
            raise Exception("This operation should only be done for 1 single contract at a time, "
                            "as it it suppose to open a window as result")
        # compute end date
        startdate = fields.Datetime.from_string(self.start_date)
        enddate = fields.Datetime.from_string(self.expiration_date)
        diffdate = (enddate - startdate)
        default = {
            'date': fields.Date.today(),
            'start_date': fields.Datetime.to_string(fields.Datetime.from_string(self.expiration_date) +
                                                    datetime.timedelta(days=1)),
            'expiration_date': fields.Datetime.to_string(enddate + diffdate),
        }
        newid = self.copy(default).id
        return {
            'name': _("Renew Contract"),
            'view_mode': 'form',
            'view_id': self.env.ref('fleet.fleet_vehicle_log_contract_form').id,
            'view_type': 'tree,form',
            'res_model': 'fleet.vehicle.log.contract',
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'domain': '[]',
            'res_id': newid,
            'context': {'active_id': newid},
        }

    @api.model
    def _get_default_contract_type(self):
        try:
            model_id = self.env.ref('fleet.type_contract_leasing').id
        except ValueError:
            model_id = False
        return model_id

    @api.onchange('cost_ids')
    def on_change_indic_cost(self):
        self.sum_cost = sum([element.amount for element in self.cost_ids])

    @api.multi
    def _get_sum_cost(self):
        for contract in self:
            contract.sum_cost = sum([cost.amount for cost in contract.cost_ids])

    name = fields.Text(compute='_vehicle_contract_name_get_fnc', string='Name', store=True)
    start_date = fields.Date('Contract Start Date', help='Date when the coverage of the contract begins',
                             default=fields.Date.today())
    expiration_date = fields.Date('Contract Expiration Date',
                                  default=lambda self: self.compute_next_year_date(fields.Date.today()),
                                  help='Date when the coverage of the contract expirates '
                                       '(by default, one year after begin date)')
    days_left = fields.Integer(compute='compute_days_left', string='Warning Date')
    insurer_id = fields.Many2one('res.partner', string='Supplier')
    purchaser_id = fields.Many2one('res.partner', string='Contractor',
                                   help='Person to which the contract is signed for',
                                   default=lambda self: self.env['res.users'].browse(self._uid).partner_id.id or False)
    contract_reference = fields.Char('Contract Reference', copy=False)
    state = fields.Selection(selection=[('open', 'In Progress'), ('toclose', 'To Close'), ('closed', 'Terminated')],
                             string='Status', readonly=True, help='Choose whether the contract is still valid or not',
                             copy=False, default='open')
    notes = fields.Text('Terms and Conditions',
                        help='Write here all supplementary information relative to this contract', copy=False)
    cost_generated = fields.Float('Recurring Cost Amount',
                                  help="Costs paid at regular intervals, depending on the cost frequency. "
                                       "If the cost frequency is set to unique, the cost will be logged at "
                                       "the start date")
    cost_frequency = fields.Selection(selection=[('no', 'No'), ('daily', 'Daily'), ('weekly', 'Weekly'),
                                                 ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                                      string='Recurring Cost Frequency',
                                      help='Frequency of the recurring cost', required=True, default='no')
    generated_cost_ids = fields.One2many('fleet.vehicle.cost', 'contract_id', string='Generated Costs')
    sum_cost = fields.Float(compute='_get_sum_cost', string='Indicative Costs Total')
    cost_id = fields.Many2one('fleet.vehicle.cost', string='Cost', required=True, ondelete='cascade')
    cost_amount = fields.Float(related='cost_id.amount', string='Amount', store=True)
    # we need to keep this field as a related with store=True because the graph view doesn't support (1) to
    # address fields from inherited table and (2) fields that aren't stored in database

    _defaults = {
        'date': fields.Date.today(),
        'cost_subtype_id': _get_default_contract_type,
        'cost_type': 'contract',
    }

    @api.multi
    def contract_close(self):
        return self.write({'state': 'closed'})

    @api.multi
    def contract_open(self):
        return self.write({'state': 'open'})
