# -*- coding: utf-8 -*-
# Copyright (c) 2015, MN Technique and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt
from frappe.model.document import Document

class LPEBDispatchOrder(Document):
	
	def on_submit(self):
		self.validate_warehouse()
		self.validate_actual_qty()
		self.pre_submit_validation()

	def validate(self):
		self.validate_office_items()
		self.validate_shop_floor_items()

	def validate_actual_qty(self):
		# dispatch_warehouses = frappe.get_doc("LPEB settings", "LPEB settings").dispatch_warehouses
		# d_wh = None
		# for wh in dispatch_warehouses:
		# 	d_wh = wh.warehouse if wh.company == frappe.defaults.get_defaults().get("company") else None

		# if not d_wh:
		# 	frappe.throw("Please set Dispatch warehouse in LPEB Settings")

		for d in self.get('shop_floor_items'):
			if d.item_code:
				actual_qty = frappe.db.sql("""select actual_qty from `tabBin`
					where item_code = '{item_code}' and warehouse = '{warehouse}';""".format(item_code=d.item_code, warehouse=d.warehouse))

				if len(actual_qty) == 0 or flt(actual_qty[0][0]) < d.qty:
					frappe.throw("Insufficient stock for '{0}' in {1}".format(d.item_code, d.warehouse))

	def validate_warehouse(self):
		valid = False
		igm = {}
		warehouse1 = ""
		item_group = ""

		#abbr = frappe.db.get_value("Company",frappe.defaults.get_defaults().company, fieldname="abbr")

		for item in self.shop_floor_items:
			item_group = frappe.db.get_value("Item",{"item_code": item.item_code}, fieldname="item_group")
			
			if item_group == "Sub Assemblies":
				fg_wh = self.project + " - FG"
				warehouse1 = frappe.db.get_value("Warehouse", filters={
							"warehouse_name": fg_wh,
							"company": frappe.defaults.get_defaults().company
						}, fieldname="name")
				igm.update({item_group:warehouse1})
				if igm.get("Sub Assemblies") == item.warehouse:
					valid = True
			elif item_group == "Raw Material":
				warehouse1 = frappe.db.get_value("Warehouse", filters={
							"warehouse_name": "Raw Materials",
							"company": frappe.defaults.get_defaults().company
						},fieldname="name")
				igm.update({item_group:warehouse1})
				if igm.get("Raw Material") == item.warehouse:
					valid = True

			else:
				valid = False

			if not valid:
				frappe.throw("Enter valid warehouse in shop floor item")

	def validate_office_items(self):
		#Duplicates
		if len(self.office_items) != len(set(self.office_items)):
			frappe.throw("Please remove duplicate office items.")

		#Items not in SO, blank items and total SO Qty cap
		so = frappe.get_doc("Sales Order", self.sales_order)
		
		for oi in self.office_items:
			if not oi.item_code:
				frappe.throw("Office Item #{0}: Please select an item, or delete the row.".format(oi.idx))

			so_item = [soi for soi in so.items if soi.item_code == oi.item_code]
			if len(so_item) == 0:
				frappe.throw("Item '{0}' is not in Sales Order '{1}' and cannot be added here.".format(oi.item_code, self.sales_order))

			if not oi.weight:
				frappe.throw("Office Item #{0}: Please set weight for '{1}'.".format(oi.idx, oi.item_code))

			if oi.weight > so_item[0].qty: 
				frappe.throw("Weight of '{0}' should not exceed {1} kg(s).".format(oi.item_code, so_item[0].qty)) 


	def validate_shop_floor_items(self):
		#Duplicates
		if len(self.shop_floor_items) != len(set(self.shop_floor_items)):
			frappe.throw("Please remove duplicate shop floor items.")

		#Blank items, items without weight
		for sfi in self.shop_floor_items:
			if not sfi.item_code:
				frappe.throw("Shop Floor Item #{0}: Please select an item, or delete the row.".format(sfi.idx))
			if not sfi.weight:
				frappe.throw("Shop Floor Item #{0}: Please set weight for '{1}'".format(sfi.idx, sfi.item_code))

		#Total weight cap
		total_office_items_weight = sum([oi.weight or 0.0 for oi in self.office_items])
		total_shop_floor_items_weight = sum([sfi.weight or 0.0 for sfi in self.shop_floor_items])
		if total_shop_floor_items_weight > total_office_items_weight:
			frappe.throw("Total weight of shop floor items should not exceed total weight of office items.")

	def pre_submit_validation(self):
		if (len(self.office_items) == 0):
			frappe.throw("Please enter at least one item under Office Details Details.")

		if (len(self.shop_floor_items) == 0):
			frappe.throw("Please enter at least one item under Shop Floor Details.")
