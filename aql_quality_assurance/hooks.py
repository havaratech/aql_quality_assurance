app_name = "aql_quality_assurance"
app_title = "AQL Quality Assurance By HavaraTech"
app_publisher = "HavaraTech"
app_description = "An AQL-based Quality Assurance extension for ERPNext’s Quality Inspection module, with the objective of consolidating and replacing the existing standalone quality management system."
app_email = "elan.k@havaratech.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["fieldname", "like", "custom_aql_%"]
        ]
    }
]


# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "aql_quality_assurance",
# 		"logo": "/assets/aql_quality_assurance/logo.png",
# 		"title": "AQL Quality Assurance By HavaraTech",
# 		"route": "/aql_quality_assurance",
# 		"has_permission": "aql_quality_assurance.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/aql_quality_assurance/css/aql_quality_assurance.css"
# app_include_js = "/assets/aql_quality_assurance/js/aql_quality_assurance.js"

# include js, css files in header of web template
# web_include_css = "/assets/aql_quality_assurance/css/aql_quality_assurance.css"
# web_include_js = "/assets/aql_quality_assurance/js/aql_quality_assurance.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "aql_quality_assurance/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "aql_quality_assurance/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "aql_quality_assurance.utils.jinja_methods",
# 	"filters": "aql_quality_assurance.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "aql_quality_assurance.install.before_install"
# after_install = "aql_quality_assurance.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "aql_quality_assurance.uninstall.before_uninstall"
# after_uninstall = "aql_quality_assurance.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "aql_quality_assurance.utils.before_app_install"
# after_app_install = "aql_quality_assurance.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "aql_quality_assurance.utils.before_app_uninstall"
# after_app_uninstall = "aql_quality_assurance.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "aql_quality_assurance.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
    "Supplier": {
        "validate": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.supplier.supplier.set_aql_defaults_from_config"
    },
    "Item": {
        "validate": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.item.item.set_aql_defaults_from_config"
    },
    "Purchase Receipt": {
        "before_save": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.purchase_receipt.purchase_receipt.copy_aql_from_supplier"
    },
    "Purchase Invoice": {
        "before_save": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.purchase_invoice.purchase_invoice.copy_aql_from_supplier"
    },
    "Customer": {
        "validate": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.customer.customer.set_aql_defaults_from_config"
    },
    "Sales Invoice": {
        "before_save": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.sales_invoice.sales_invoice.copy_aql_from_customer"
    },
    "Delivery Note": {  
        "before_save": "aql_quality_assurance.aql_quality_assurance_by_havaratech.doctype.delivery_note.delivery_note.copy_aql_from_customer"
    }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"aql_quality_assurance.tasks.all"
# 	],
# 	"daily": [
# 		"aql_quality_assurance.tasks.daily"
# 	],
# 	"hourly": [
# 		"aql_quality_assurance.tasks.hourly"
# 	],
# 	"weekly": [
# 		"aql_quality_assurance.tasks.weekly"
# 	],
# 	"monthly": [
# 		"aql_quality_assurance.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "aql_quality_assurance.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "aql_quality_assurance.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "aql_quality_assurance.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["aql_quality_assurance.utils.before_request"]
# after_request = ["aql_quality_assurance.utils.after_request"]

# Job Events
# ----------
# before_job = ["aql_quality_assurance.utils.before_job"]
# after_job = ["aql_quality_assurance.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"aql_quality_assurance.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

