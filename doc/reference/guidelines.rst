.. highlight:: python

=================
Coding Guidelines
=================

Python
======

- PEP8 ignore E501
- prefer % over format
- try to avoid generators and decorators


File naming
===========

Split the business logic by sets of models, in each sets select a main
model, this model gives its name to the set. If there is only one set of module
it's name is the same as the module name.

For each set named <main_model> the following files may be created:

data/<main_model>.xml
models/<main_model>.py
views/<main_model>_templates.xml
views/<main_model>_view.xml

Example set sale_order, sale_order_line where sale_order is dominant.

data/sale_order.xml
models/sale_order.py
views/sale_order_templates.xml
views/sale_order_view.xml

xml_id naming for views action and menu
=======================================

record id="model_name_view_form"

record id="model_name_view_list"

record id="model_name_view_kanban"

record id="model_name_action"

record id="model_name_menu"

