"""CRM sales module -- sales documents, product catalogue, payment methods and analytics.

Customers are NOT owned here: every sale points at `customers.id` of the main customer
bank (app/modules/customers). See models.py.
"""
