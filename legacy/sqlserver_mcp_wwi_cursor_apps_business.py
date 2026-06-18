"""
SQL Server MCP Server
=====================
Connects Cursor or another MCP client to a local SQL Server instance via ODBC (STDIO transport).

Three tools:
  1. sqlserver_get_schema  – reads live table/column structure from SQL Server
  2. sqlserver_query       – executes a read-only SELECT and returns results

The DATA DICTIONARY below is the critical semantic layer you maintain.
It tells Claude three things SQL Server cannot:
  - what each table is actually used for
  - which columns join tables together (especially undeclared joins)
  - what the code/flag values in lookup columns actually mean

Fill in the DATA DICTIONARY for your own database before using this server.
The template below uses realistic example names to show the pattern.

Dependencies:
  pip install mcp pyodbc

Connection:
  Set environment variables before running, or replace defaults below.
  SQLSERVER_HOST  – server name or IP  (default: localhost)
  SQLSERVER_DB    – database name      (default: SalesDB)
  SQLSERVER_USER  – SQL login username
  SQLSERVER_PASS  – SQL login password
"""

import json
import os
import re
from typing import Any, Literal, Optional
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

import pyodbc
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# CONNECTION — edit environment variables, not this file
# ─────────────────────────────────────────────────────────────────────────────
DB_SERVER   = os.environ.get("SQLSERVER_HOST", "050027346-3")
DB_NAME     = os.environ.get("SQLSERVER_DB",   "WideWorldImporters")
DB_USER     = os.environ.get("SQLSERVER_USER",  "")
DB_PASSWORD = os.environ.get("SQLSERVER_PASS",  "")

if DB_USER and DB_PASSWORD:
    # SQL Server authentication (username + password)
    CONN_STRING = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
else:
    # Windows authentication (Trusted Connection) - default for local dev
    CONN_STRING = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_NAME};"
        f"Trusted_Connection=yes;"
        f"TrustServerCertificate=yes;"
    )


# ─────────────────────────────────────────────────────────────────────────────
# FILE PATHS — memory and logging
# These files sit alongside the MCP server script.
# Change the paths if you want them stored elsewhere.
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
MEMORY_FILE  = BASE_DIR / "mcp_memory.txt"
PENDING_FILE = BASE_DIR / "mcp_pending_suggestions.txt"
LOG_FILE     = BASE_DIR / "mcp_queries.log"

CHART_VIEW_URI = "ui://sqlserver-mcp/chart-view.html"


# ─────────────────────────────────────────────────────────────────────────────
# LOGGING HELPER
# Writes a timestamped entry to the query log every time a query runs.
# ─────────────────────────────────────────────────────────────────────────────
def log_query(sql: str, row_count: int) -> None:
    """Append a timestamped query record to the log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] ROWS: {row_count} | SQL: {sql.strip()}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)


# ─────────────────────────────────────────────────────────────────────────────
# DATA DICTIONARY
#
# This is the layer YOU own. SQL Server gives Claude the structure (table names,
# column names, data types). This dictionary gives Claude the meaning.
#
# Three sections — fill in all three for your own database:
#   1. TABLES        — what each table represents in business terms
#   2. JOINS         — how tables relate, especially undeclared FK relationships
#   3. SYSTEM VALUES — the meaning of code/flag columns
#
# Claude reads this on every invocation alongside the live schema.
# The more complete this is, the more accurate Claude's SQL will be.
# ─────────────────────────────────────────────────────────────────────────────
DATA_DICTIONARY = r"""
================================================================================
DATA DICTIONARY — WideWorldImporters general NL-to-SQL dictionary
================================================================================
Purpose: This MCP server is a general natural-language-to-SQL assistant for the WideWorldImporters SQL Server database. It is NOT only a debtor-reporting assistant.
Always call sqlserver_get_schema first. Use the live schema for exact table/column names. Use this dictionary for business meaning, safe table choice, join intent, and common reporting rules.

--------------------------------------------------------------------------------
SECTION 0 — CORE SQL GENERATION RULES
--------------------------------------------------------------------------------
- Use two-part names wherever possible, e.g. Sales.Customers, Sales.Invoices, Warehouse.StockItems.
- Do not assume every table lives in dbo. WideWorldImporters uses schemas such as Application, Sales, Purchasing, Warehouse and Website.
- Prefer base tables for canonical answers. Use Website.* views only when the user asks for simplified website-facing data.
- Archive tables ending _Archive contain historical/system-versioned history. Do not use them unless the user asks for historical versions, old values, audit history or valid-time analysis.
- Temporal/system-versioned tables have ValidFrom and ValidTo columns; these are row validity timestamps, not business transaction dates.
- For sales analysis, start with Sales.Invoices/Sales.InvoiceLines for invoiced sales, Sales.Orders/Sales.OrderLines for orders, and Sales.CustomerTransactions for customer financial transaction balances.
- For purchasing analysis, start with Purchasing.PurchaseOrders/Purchasing.PurchaseOrderLines for purchasing activity, and Purchasing.SupplierTransactions for supplier financial transactions.
- For stock/inventory analysis, start with Warehouse.StockItems, Warehouse.StockItemHoldings and Warehouse.StockItemTransactions.
- For lookup/code meanings, join to lookup tables such as Application.TransactionTypes, Application.PaymentMethods, Sales.CustomerCategories, Sales.BuyingGroups, Warehouse.PackageTypes, Warehouse.Colors and Warehouse.StockGroups.
- When unsure of lookup values, query the lookup table live rather than guessing IDs or names.
- Return TOP rows for exploratory queries unless the user asks for a full aggregation.
- Never write INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, MERGE, TRUNCATE or EXEC statements.

--------------------------------------------------------------------------------
SECTION 1 — SCHEMA / DOMAIN GUIDE
--------------------------------------------------------------------------------
Application = Shared reference/master data used across the database: people, cities, countries, delivery methods, payment methods, transaction types and system parameters.
Sales = Customer-facing commercial data: customers, buying groups, orders, order lines, invoices, invoice lines, customer transactions and special deals.
Purchasing = Supplier-facing procurement data: suppliers, purchase orders, purchase order lines and supplier transactions.
Warehouse = Inventory and logistics data: stock items, stock groups, stock holdings, stock item transactions, package types, colours and temperature readings.
Website = Convenience views/procedures used by the example web application. Useful for simplified customer/supplier/vehicle-temperature views but not the canonical transaction source.

--------------------------------------------------------------------------------
SECTION 2 — TABLES: BUSINESS MEANING
--------------------------------------------------------------------------------
Application.Cities = Cities that are part of any address (including geographic location)
Application.Cities_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.Countries = Countries that contain the states or provinces (including geographic boundaries)
Application.Countries_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.DeliveryMethods = Ways that stock items can be delivered (ie: truck/van, post, pickup, courier, etc.
Application.DeliveryMethods_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.PaymentMethods = Ways that payments can be made (ie: cash, check, EFT, etc.
Application.PaymentMethods_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.People = People known to the application (staff, customer contacts, supplier contacts)
Application.People_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.StateProvinces = States or provinces that contain cities (including geographic location)
Application.StateProvinces_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Application.SystemParameters = Any configurable parameters for the whole system
Application.TransactionTypes = Types of customer, supplier, or stock transactions (ie: invoice, credit note, etc.)
Application.TransactionTypes_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Purchasing.PurchaseOrderLines = Detail lines from supplier purchase orders
Purchasing.PurchaseOrders = Details of supplier purchase orders
Purchasing.SupplierCategories = Categories for suppliers (ie novelties, toys, clothing, packaging, etc.)
Purchasing.SupplierCategories_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Purchasing.SupplierTransactions = All financial transactions that are supplier-related
Purchasing.Suppliers = Main entity table for suppliers (organizations)
Purchasing.Suppliers_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Sales.BuyingGroups = Customer organizations can be part of groups that exert greater buying power
Sales.BuyingGroups_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Sales.CustomerCategories = Categories for customers (ie restaurants, cafes, supermarkets, etc.)
Sales.CustomerCategories_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Sales.CustomerTransactions = All financial transactions that are customer-related
Sales.Customers = Main entity tables for customers (organizations or individuals)
Sales.Customers_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Sales.InvoiceLines = Detail lines from customer invoices
Sales.Invoices = Details of customer invoices
Sales.OrderLines = Detail lines from customer orders
Sales.Orders = Detail of customer orders
Sales.SpecialDeals = Special pricing (can include fixed prices, discount $ or discount %)
Warehouse.ColdRoomTemperatures = No natural-language description was extracted. Use live schema and relationships to infer cautiously.
Warehouse.ColdRoomTemperatures_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Warehouse.Colors = Stock items can (optionally) have colors
Warehouse.Colors_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Warehouse.PackageTypes = Ways that stock items can be packaged (ie: each, box, carton, pallet, kg, etc.
Warehouse.PackageTypes_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Warehouse.StockGroups = Groups for categorizing stock items (ie: novelties, toys, edible novelties, etc.)
Warehouse.StockGroups_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Warehouse.StockItemHoldings = Non-temporal attributes for stock items
Warehouse.StockItemStockGroups = Which stock items are in which stock groups
Warehouse.StockItemTransactions = Transactions covering all movements of all stock items
Warehouse.StockItems = Main entity table for stock items
Warehouse.StockItems_Archive = No natural-language description was extracted. Use live schema and relationships to infer cautiously. This is an archive/history table; use only for historical/valid-time analysis.
Warehouse.VehicleTemperatures = No natural-language description was extracted. Use live schema and relationships to infer cautiously.

--------------------------------------------------------------------------------
SECTION 3 — IMPORTANT TABLE CHOICE RULES
--------------------------------------------------------------------------------
Sales.Customers = customer master. Use for customer name, credit limit, payment terms, credit hold and customer category.
Sales.Orders = sales order header. Use when the user asks about orders placed, picked orders, expected delivery or order lifecycle.
Sales.OrderLines = sales order detail. Use for ordered stock item quantities/prices before invoicing.
Sales.Invoices = invoice header. Use for invoice date, customer, bill-to customer, salesperson, delivery and credit-note flag.
Sales.InvoiceLines = invoice line detail. Use for invoiced items, quantities, unit prices, tax, extended price and line profit.
Sales.CustomerTransactions = customer financial transactions. Use for customer-related invoices, payments, outstanding balances, finalization status and transaction dates.
Purchasing.Suppliers = supplier master. Use for supplier names, payment terms and supplier category.
Purchasing.PurchaseOrders = purchase order header. Use for supplier orders and expected delivery.
Purchasing.PurchaseOrderLines = purchase order line detail. Use for ordered stock item quantities and expected receipt.
Purchasing.SupplierTransactions = supplier financial transactions. Use for supplier invoices/payments/amounts outstanding.
Warehouse.StockItems = stock item/product master. Use for product names, supplier, brand, size, tax, recommended price and custom fields.
Warehouse.StockItemHoldings = current stock holding metrics. Use for quantity on hand, bin location, reorder levels and target stock levels.
Warehouse.StockItemTransactions = inventory movements. Use for stock movement analysis and links to customer/supplier/invoice/purchase activity.
Application.People = people/contact/employee records used by customer contacts, supplier contacts, salespeople, packers and last-edited fields.

--------------------------------------------------------------------------------
SECTION 4 — COMMON JOIN GUIDE
--------------------------------------------------------------------------------
Use declared foreign keys from sqlserver_get_schema as the source of truth. Common joins are:
Sales.Customers.CustomerID → Sales.Invoices.CustomerID / Sales.Orders.CustomerID / Sales.CustomerTransactions.CustomerID
Sales.Customers.CustomerID → Sales.Customers.BillToCustomerID (parent/bill-to customer relationship)
Sales.Invoices.InvoiceID → Sales.InvoiceLines.InvoiceID / Sales.CustomerTransactions.InvoiceID / Warehouse.StockItemTransactions.InvoiceID
Sales.Orders.OrderID → Sales.OrderLines.OrderID / Sales.Invoices.OrderID
Application.TransactionTypes.TransactionTypeID → Sales.CustomerTransactions.TransactionTypeID / Purchasing.SupplierTransactions.TransactionTypeID / Warehouse.StockItemTransactions.TransactionTypeID
Application.PaymentMethods.PaymentMethodID → Sales.CustomerTransactions.PaymentMethodID / Purchasing.SupplierTransactions.PaymentMethodID
Warehouse.StockItems.StockItemID → Sales.InvoiceLines.StockItemID / Sales.OrderLines.StockItemID / Purchasing.PurchaseOrderLines.StockItemID / Warehouse.StockItemTransactions.StockItemID / Warehouse.StockItemHoldings.StockItemID
Purchasing.Suppliers.SupplierID → Purchasing.PurchaseOrders.SupplierID / Purchasing.SupplierTransactions.SupplierID / Warehouse.StockItems.SupplierID
Application.People.PersonID is reused for contact people, salespeople, packers, buyers and LastEditedBy fields. Alias each join clearly.

--------------------------------------------------------------------------------
SECTION 5 — LOOKUPS / SYSTEM VALUES
--------------------------------------------------------------------------------
Do not hard-code lookup IDs. Query lookup tables live because IDs and names are clearer from the database itself.
Useful lookup queries:
SELECT TransactionTypeID, TransactionTypeName FROM Application.TransactionTypes ORDER BY TransactionTypeID;
SELECT PaymentMethodID, PaymentMethodName FROM Application.PaymentMethods ORDER BY PaymentMethodID;
SELECT CustomerCategoryID, CustomerCategoryName FROM Sales.CustomerCategories ORDER BY CustomerCategoryID;
SELECT BuyingGroupID, BuyingGroupName FROM Sales.BuyingGroups ORDER BY BuyingGroupID;
SELECT PackageTypeID, PackageTypeName FROM Warehouse.PackageTypes ORDER BY PackageTypeID;
SELECT ColorID, ColorName FROM Warehouse.Colors ORDER BY ColorID;
SELECT StockGroupID, StockGroupName FROM Warehouse.StockGroups ORDER BY StockGroupID;

--------------------------------------------------------------------------------
SECTION 6 — REPORTING PATTERNS
--------------------------------------------------------------------------------
Sales revenue / invoiced sales: use Sales.Invoices joined to Sales.InvoiceLines. ExtendedPrice and LineProfit are invoice-line measures; InvoiceDate is the invoice date.
Orders not invoices: use Sales.Orders joined to Sales.OrderLines. Do not use orders as revenue unless the user explicitly asks for orders/bookings rather than invoices/revenue.
Customer debtor/open balance: use Sales.CustomerTransactions.OutstandingBalance and join to Sales.Customers and Application.TransactionTypes. Invoice status is derived, not stored on Sales.Invoices.
Supplier payable/open balance: use Purchasing.SupplierTransactions.OutstandingBalance and join to Purchasing.Suppliers and Application.TransactionTypes.
Inventory on hand: use Warehouse.StockItemHoldings.QuantityOnHand joined to Warehouse.StockItems.
Inventory movement: use Warehouse.StockItemTransactions, transaction dates and transaction types.
Customer payment terms: Sales.Customers.PaymentDays. Due date can be estimated as InvoiceDate + PaymentDays when no explicit due date exists.
Supplier payment terms: use the supplier master payment-days field if present in the live schema.
Credit notes: Sales.Invoices has IsCreditNote and CreditNoteReason. Treat credit notes separately from standard invoices when calculating net sales or outstanding values.
Bill-to reporting: Sales.Invoices has both CustomerID and BillToCustomerID. Use BillToCustomerID for head-office billing analysis, CustomerID for the actual customer being invoiced.

--------------------------------------------------------------------------------
SECTION 7 — COLUMN DICTIONARY
--------------------------------------------------------------------------------
Format: Schema.Table.Column — data type — description. Use this for business meaning; use live schema for exact current existence/nullability.

[Application.Cities]
- CityID — int — Numeric ID used for reference to a city within the database
- CityName — nvarchar(100) — Formal name of the city
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — Latest available population for the City
- Location — geography — Geographic location of the city
- StateProvinceID — int — State or province for this city
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.Cities_Archive]
- CityID — int — No description extracted.
- CityName — nvarchar(100) — No description extracted.
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — No description extracted.
- Location — geography — No description extracted.
- StateProvinceID — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.Countries]
- Border — geography — Geographic border of the country as described by the United Nations
- Continent — nvarchar(60) — Name of the continent
- CountryID — int — Numeric ID used for reference to a country within the database
- CountryName — nvarchar(120) — Name of the country
- CountryType — nvarchar(40) — Type of country or administrative region
- FormalName — nvarchar(120) — Full formal name of the country as agreed by United Nations
- IsoAlpha3Code — nvarchar(6) — 3 letter alphabetic code assigned to the country by ISO
- IsoNumericCode — int — Numeric code assigned to the country by ISO
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — Latest available population for the country
- Region — nvarchar(60) — Name of the region
- Subregion — nvarchar(60) — Name of the subregion
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.Countries_Archive]
- Border — geography — No description extracted.
- Continent — nvarchar(60) — No description extracted.
- CountryID — int — No description extracted.
- CountryName — nvarchar(120) — No description extracted.
- CountryType — nvarchar(40) — No description extracted.
- FormalName — nvarchar(120) — No description extracted.
- IsoAlpha3Code — nvarchar(6) — No description extracted.
- IsoNumericCode — int — No description extracted.
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — No description extracted.
- Region — nvarchar(60) — No description extracted.
- Subregion — nvarchar(60) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.DeliveryMethods]
- DeliveryMethodID — int — Numeric ID used for reference to a delivery method within the database
- DeliveryMethodName — nvarchar(100) — Full name of methods that can be used for delivery of customer orders
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.DeliveryMethods_Archive]
- DeliveryMethodID — int — No description extracted.
- DeliveryMethodName — nvarchar(100) — No description extracted.
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.PaymentMethods]
- LastEditedBy — int — No description extracted.
- PaymentMethodID — int — Numeric ID used for reference to a payment type within the database
- PaymentMethodName — nvarchar(100) — Full name of ways that customers can make payments or that suppliers can be paid
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.PaymentMethods_Archive]
- LastEditedBy — int — No description extracted.
- PaymentMethodID — int — No description extracted.
- PaymentMethodName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.People]
- CustomFields — nvarchar — Custom fields for employees and salespeople
- EmailAddress — nvarchar(512) — Email address for this person
- FaxNumber — nvarchar(40) — Fax number  
- FullName — nvarchar(100) — Full name for this person
- HashedPassword — varbinary — Hash of password for users without external logon tokens
- IsEmployee — bit — Is this person an employee?
- IsExternalLogonProvider — bit — Is logon token provided by an external system?
- IsPermittedToLogon — bit — Is this person permitted to log on?
- IsSalesperson — bit — Is this person a staff salesperson?
- IsSystemUser — bit — Is the currently permitted to make online access?
- LastEditedBy — int — No description extracted.
- LogonName — nvarchar(100) — Person's system logon name
- OtherLanguages — nvarchar — Other languages spoken (computed column from custom fields)
- PersonID — int — Numeric ID used for reference to a person within the database
- PhoneNumber — nvarchar(40) — Phone number
- Photo — varbinary — Photo of this person
- PreferredName — nvarchar(100) — Name that this person prefers to be called
- SearchName — nvarchar(202) — Name to build full text search on (computed column)
- UserPreferences — nvarchar — User preferences related to the website (holds JSON data)
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.People_Archive]
- CustomFields — nvarchar — No description extracted.
- EmailAddress — nvarchar(512) — No description extracted.
- FaxNumber — nvarchar(40) — No description extracted.
- FullName — nvarchar(100) — No description extracted.
- HashedPassword — varbinary — No description extracted.
- IsEmployee — bit — No description extracted.
- IsExternalLogonProvider — bit — No description extracted.
- IsPermittedToLogon — bit — No description extracted.
- IsSalesperson — bit — No description extracted.
- IsSystemUser — bit — No description extracted.
- LastEditedBy — int — No description extracted.
- LogonName — nvarchar(100) — No description extracted.
- OtherLanguages — nvarchar — No description extracted.
- PersonID — int — No description extracted.
- PhoneNumber — nvarchar(40) — No description extracted.
- Photo — varbinary — No description extracted.
- PreferredName — nvarchar(100) — No description extracted.
- SearchName — nvarchar(202) — No description extracted.
- UserPreferences — nvarchar — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.StateProvinces]
- Border — geography — Geographic boundary of the state or province
- CountryID — int — Country for this StateProvince
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — Latest available population for the StateProvince
- SalesTerritory — nvarchar(100) — Sales territory for this StateProvince
- StateProvinceCode — nvarchar(10) — Common code for this state or province (such as WA - Washington for the USA)
- StateProvinceID — int — Numeric ID used for reference to a state or province within the database
- StateProvinceName — nvarchar(100) — Formal name of the state or province
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.StateProvinces_Archive]
- Border — geography — No description extracted.
- CountryID — int — No description extracted.
- LastEditedBy — int — No description extracted.
- LatestRecordedPopulation — bigint — No description extracted.
- SalesTerritory — nvarchar(100) — No description extracted.
- StateProvinceCode — nvarchar(10) — No description extracted.
- StateProvinceID — int — No description extracted.
- StateProvinceName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.SystemParameters]
- ApplicationSettings — nvarchar — JSON-structured application settings
- DeliveryAddressLine1 — nvarchar(120) — First address line for the company
- DeliveryAddressLine2 — nvarchar(120) — Second address line for the company
- DeliveryCityID — int — ID of the city for this address
- DeliveryLocation — geography — Geographic location for the company office
- DeliveryPostalCode — nvarchar(20) — Postal code for the company
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- PostalAddressLine1 — nvarchar(120) — First postal address line for the company
- PostalAddressLine2 — nvarchar(120) — Second postaladdress line for the company
- PostalCityID — int — ID of the city for this postaladdress
- PostalPostalCode — nvarchar(20) — Postal code for the company when sending via mail
- SystemParameterID — int — Numeric ID used for row holding system parameters

[Application.TransactionTypes]
- LastEditedBy — int — No description extracted.
- TransactionTypeID — int — Numeric ID used for reference to a transaction type within the database
- TransactionTypeName — nvarchar(100) — Full name of the transaction type
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Application.TransactionTypes_Archive]
- LastEditedBy — int — No description extracted.
- TransactionTypeID — int — No description extracted.
- TransactionTypeName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Purchasing.PurchaseOrderLines]
- Description — nvarchar(200) — Description of the item to be supplied (Often the stock item name but could be supplier description)
- ExpectedUnitPricePerOuter — decimal — The unit price that we expect to be charged
- IsOrderLineFinalized — bit — Is this purchase order line now considered finalized? (Receipted quantities and weights are often not precise)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- LastReceiptDate — date — The last date on which this stock item was received for this purchase order
- OrderedOuters — int — Quantity of the stock item that is ordered
- PackageTypeID — int — Type of package received
- PurchaseOrderID — int — Purchase order that this line is associated with
- PurchaseOrderLineID — int — Numeric ID used for reference to a line on a purchase order within the database
- ReceivedOuters — int — Total quantity of the stock item that has been received so far
- StockItemID — int — Stock item for this purchase order line

[Purchasing.PurchaseOrders]
- Comments — nvarchar — Any comments related this purchase order (comments sent to the supplier)
- ContactPersonID — int — The person who is the primary contact for this purchase order
- DeliveryMethodID — int — How this purchase order should be delivered
- ExpectedDeliveryDate — date — Expected delivery date for this purchase order
- InternalComments — nvarchar — Any internal comments related this purchase order (comments for internal reference only and not sent to the supplier)
- IsOrderFinalized — bit — Is this purchase order now considered finalized?
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OrderDate — date — Date that this purchase order was raised
- PurchaseOrderID — int — Numeric ID used for reference to a purchase order within the database
- SupplierID — int — Supplier for this purchase order
- SupplierReference — nvarchar(40) — Supplier reference for our organization (might be our account number at the supplier)

[Purchasing.SupplierCategories]
- LastEditedBy — int — No description extracted.
- SupplierCategoryID — int — Numeric ID used for reference to a supplier category within the database
- SupplierCategoryName — nvarchar(100) — Full name of the category that suppliers can be assigned to
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Purchasing.SupplierCategories_Archive]
- LastEditedBy — int — No description extracted.
- SupplierCategoryID — int — No description extracted.
- SupplierCategoryName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Purchasing.SupplierTransactions]
- AmountExcludingTax — decimal — Transaction amount (excluding tax)
- FinalizationDate — date — Date that this transaction was finalized (if it has been)
- IsFinalized — bit — Is this transaction finalized (invoices, credits and payments have been matched)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OutstandingBalance — decimal — Amount still outstanding for this transaction
- PaymentMethodID — int — ID of a payment method (for transactions involving payments)
- PurchaseOrderID — int — ID of an purchase order (for transactions associated with a purchase order)
- SupplierID — int — Supplier for this transaction
- SupplierInvoiceNumber — nvarchar(40) — Invoice number for an invoice received from the supplier
- SupplierTransactionID — int — Numeric ID used to refer to a supplier transaction within the database
- TaxAmount — decimal — Tax amount calculated
- TransactionAmount — decimal — Transaction amount (including tax)
- TransactionDate — date — Date for the transaction
- TransactionTypeID — int — Type of transaction

[Purchasing.Suppliers]
- AlternateContactPersonID — int — Alternate contact
- BankAccountBranch — nvarchar(100) — Supplier's bank branch
- BankAccountCode — nvarchar(40) — Supplier's bank account code (usually a numeric reference for the bank branch)
- BankAccountName — nvarchar(100) — Supplier's bank account name (ie name on the account)
- BankAccountNumber — nvarchar(40) — Supplier's bank account number
- BankInternationalCode — nvarchar(40) — Supplier's bank's international code (such as a SWIFT code)
- DeliveryAddressLine1 — nvarchar(120) — First delivery address line for the supplier
- DeliveryAddressLine2 — nvarchar(120) — Second delivery address line for the supplier
- DeliveryCityID — int — ID of the delivery city for this address
- DeliveryLocation — geography — Geographic location for the supplier's office/warehouse
- DeliveryMethodID — int — Standard delivery method for stock items received from this supplier
- DeliveryPostalCode — nvarchar(20) — Delivery postal code for the supplier
- FaxNumber — nvarchar(40) — Fax number  
- InternalComments — nvarchar — Internal comments (not exposed outside organization)
- LastEditedBy — int — No description extracted.
- PaymentDays — int — Number of days for payment of an invoice (ie payment terms)
- PhoneNumber — nvarchar(40) — Phone number
- PostalAddressLine1 — nvarchar(120) — First postal address line for the supplier
- PostalAddressLine2 — nvarchar(120) — Second postal address line for the supplier
- PostalCityID — int — ID of the mailing city for this address
- PostalPostalCode — nvarchar(20) — Postal code for the supplier when sending by mail
- PrimaryContactPersonID — int — Primary contact
- SupplierCategoryID — int — Supplier's category
- SupplierID — int — Numeric ID used for reference to a supplier within the database
- SupplierName — nvarchar(200) — Supplier's full name (usually a trading name)
- SupplierReference — nvarchar(40) — Supplier reference for our organization (might be our account number at the supplier)
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.
- WebsiteURL — nvarchar(512) — URL for the website for this supplier

[Purchasing.Suppliers_Archive]
- AlternateContactPersonID — int — No description extracted.
- BankAccountBranch — nvarchar(100) — No description extracted.
- BankAccountCode — nvarchar(40) — No description extracted.
- BankAccountName — nvarchar(100) — No description extracted.
- BankAccountNumber — nvarchar(40) — No description extracted.
- BankInternationalCode — nvarchar(40) — No description extracted.
- DeliveryAddressLine1 — nvarchar(120) — No description extracted.
- DeliveryAddressLine2 — nvarchar(120) — No description extracted.
- DeliveryCityID — int — No description extracted.
- DeliveryLocation — geography — No description extracted.
- DeliveryMethodID — int — No description extracted.
- DeliveryPostalCode — nvarchar(20) — No description extracted.
- FaxNumber — nvarchar(40) — No description extracted.
- InternalComments — nvarchar — No description extracted.
- LastEditedBy — int — No description extracted.
- PaymentDays — int — No description extracted.
- PhoneNumber — nvarchar(40) — No description extracted.
- PostalAddressLine1 — nvarchar(120) — No description extracted.
- PostalAddressLine2 — nvarchar(120) — No description extracted.
- PostalCityID — int — No description extracted.
- PostalPostalCode — nvarchar(20) — No description extracted.
- PrimaryContactPersonID — int — No description extracted.
- SupplierCategoryID — int — No description extracted.
- SupplierID — int — No description extracted.
- SupplierName — nvarchar(200) — No description extracted.
- SupplierReference — nvarchar(40) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.
- WebsiteURL — nvarchar(512) — No description extracted.

[Sales.BuyingGroups]
- BuyingGroupID — int — Numeric ID used for reference to a buying group within the database
- BuyingGroupName — nvarchar(100) — Full name of a buying group that customers can be members of
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Sales.BuyingGroups_Archive]
- BuyingGroupID — int — No description extracted.
- BuyingGroupName — nvarchar(100) — No description extracted.
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Sales.CustomerCategories]
- CustomerCategoryID — int — Numeric ID used for reference to a customer category within the database
- CustomerCategoryName — nvarchar(100) — Full name of the category that customers can be assigned to
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Sales.CustomerCategories_Archive]
- CustomerCategoryID — int — No description extracted.
- CustomerCategoryName — nvarchar(100) — No description extracted.
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Sales.CustomerTransactions]
- AmountExcludingTax — decimal — Transaction amount (excluding tax)
- CustomerID — int — Customer for this transaction
- CustomerTransactionID — int — Numeric ID used to refer to a customer transaction within the database
- FinalizationDate — date — Date that this transaction was finalized (if it has been)
- InvoiceID — int — ID of an invoice (for transactions associated with an invoice)
- IsFinalized — bit — Is this transaction finalized (invoices, credits and payments have been matched)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OutstandingBalance — decimal — Amount still outstanding for this transaction
- PaymentMethodID — int — ID of a payment method (for transactions involving payments)
- TaxAmount — decimal — Tax amount calculated
- TransactionAmount — decimal — Transaction amount (including tax)
- TransactionDate — date — Date for the transaction
- TransactionTypeID — int — Type of transaction

[Sales.Customers]
- AccountOpenedDate — date — Date this customer account was opened
- AlternateContactPersonID — int — Alternate contact
- BillToCustomerID — int — Customer that this is billed to (usually the same customer but can be another parent company)
- BuyingGroupID — int — Customer's buying group (optional)
- CreditLimit — decimal — Credit limit for this customer (NULL if unlimited)
- CustomerCategoryID — int — Customer's category
- CustomerID — int — Numeric ID used for reference to a customer within the database
- CustomerName — nvarchar(200) — Customer's full name (usually a trading name)
- DeliveryAddressLine1 — nvarchar(120) — First delivery address line for the customer
- DeliveryAddressLine2 — nvarchar(120) — Second delivery address line for the customer
- DeliveryCityID — int — ID of the delivery city for this address
- DeliveryLocation — geography — Geographic location for the customer's office/warehouse
- DeliveryMethodID — int — Standard delivery method for stock items sent to this customer
- DeliveryPostalCode — nvarchar(20) — Delivery postal code for the customer
- DeliveryRun — nvarchar(10) — Normal delivery run for this customer
- FaxNumber — nvarchar(40) — Fax number  
- IsOnCreditHold — bit — Is this customer on credit hold? (Prevents further deliveries to this customer)
- IsStatementSent — bit — Is a statement sent to this customer? (Or do they just pay on each invoice?)
- LastEditedBy — int — No description extracted.
- PaymentDays — int — Number of days for payment of an invoice (ie payment terms)
- PhoneNumber — nvarchar(40) — Phone number
- PostalAddressLine1 — nvarchar(120) — First postal address line for the customer
- PostalAddressLine2 — nvarchar(120) — Second postal address line for the customer
- PostalCityID — int — ID of the postal city for this address
- PostalPostalCode — nvarchar(20) — Postal code for the customer when sending by mail
- PrimaryContactPersonID — int — Primary contact
- RunPosition — nvarchar(10) — Normal position in the delivery run for this customer
- StandardDiscountPercentage — decimal — Standard discount offered to this customer
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.
- WebsiteURL — nvarchar(512) — URL for the website for this customer

[Sales.Customers_Archive]
- AccountOpenedDate — date — No description extracted.
- AlternateContactPersonID — int — No description extracted.
- BillToCustomerID — int — No description extracted.
- BuyingGroupID — int — No description extracted.
- CreditLimit — decimal — No description extracted.
- CustomerCategoryID — int — No description extracted.
- CustomerID — int — No description extracted.
- CustomerName — nvarchar(200) — No description extracted.
- DeliveryAddressLine1 — nvarchar(120) — No description extracted.
- DeliveryAddressLine2 — nvarchar(120) — No description extracted.
- DeliveryCityID — int — No description extracted.
- DeliveryLocation — geography — No description extracted.
- DeliveryMethodID — int — No description extracted.
- DeliveryPostalCode — nvarchar(20) — No description extracted.
- DeliveryRun — nvarchar(10) — No description extracted.
- FaxNumber — nvarchar(40) — No description extracted.
- IsOnCreditHold — bit — No description extracted.
- IsStatementSent — bit — No description extracted.
- LastEditedBy — int — No description extracted.
- PaymentDays — int — No description extracted.
- PhoneNumber — nvarchar(40) — No description extracted.
- PostalAddressLine1 — nvarchar(120) — No description extracted.
- PostalAddressLine2 — nvarchar(120) — No description extracted.
- PostalCityID — int — No description extracted.
- PostalPostalCode — nvarchar(20) — No description extracted.
- PrimaryContactPersonID — int — No description extracted.
- RunPosition — nvarchar(10) — No description extracted.
- StandardDiscountPercentage — decimal — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.
- WebsiteURL — nvarchar(512) — No description extracted.

[Sales.InvoiceLines]
- Description — nvarchar(200) — Description of the item supplied (Usually the stock item name but can be overridden)
- ExtendedPrice — decimal — Extended line price charged
- InvoiceID — int — Invoice that this line is associated with
- InvoiceLineID — int — Numeric ID used for reference to a line on an invoice within the database
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- LineProfit — decimal — Profit made on this line item at current cost price
- PackageTypeID — int — Type of package supplied
- Quantity — int — Quantity supplied
- StockItemID — int — Stock item for this invoice line
- TaxAmount — decimal — Tax amount calculated
- TaxRate — decimal — Tax rate to be applied
- UnitPrice — decimal — Unit price charged

[Sales.Invoices]
- AccountsPersonID — int — Customer accounts contact for this invoice
- BillToCustomerID — int — Bill to customer for this invoice (invoices might be billed to a head office)
- Comments — nvarchar — Any comments related to this invoice (sent to customer)
- ConfirmedDeliveryTime — datetime2 — Confirmed delivery date and time promoted from JSON delivery data
- ConfirmedReceivedBy — nvarchar(8000) — Confirmed receiver promoted from JSON delivery data
- ContactPersonID — int — Customer contact for this invoice
- CreditNoteReason — nvarchar — Reason that this credit note needed to be generated (if applicable)
- CustomerID — int — Customer for this invoice
- CustomerPurchaseOrderNumber — nvarchar(40) — Purchase Order Number received from customer
- DeliveryInstructions — nvarchar — Any comments related to delivery (sent to customer)
- DeliveryMethodID — int — How these stock items are beign delivered
- DeliveryRun — nvarchar(10) — Delivery run for this shipment
- InternalComments — nvarchar — Any internal comments related to this invoice (not sent to the customer)
- InvoiceDate — date — Date that this invoice was raised
- InvoiceID — int — Numeric ID used for reference to an invoice within the database
- IsCreditNote — bit — Is this a credit note (rather than an invoice)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OrderID — int — Sales order (if any) for this invoice
- PackedByPersonID — int — Person who packed this shipment (or checked the packing)
- ReturnedDeliveryData — nvarchar — JSON-structured data returned from delivery devices for deliveries made directly by the organization
- RunPosition — nvarchar(10) — Position in the delivery run for this shipment
- SalespersonPersonID — int — Salesperson for this invoice
- TotalChillerItems — int — Total number of chiller packages (information for the delivery driver)
- TotalDryItems — int — Total number of dry packages (information for the delivery driver)

[Sales.OrderLines]
- Description — nvarchar(200) — Description of the item supplied (Usually the stock item name but can be overridden)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OrderID — int — Order that this line is associated with
- OrderLineID — int — Numeric ID used for reference to a line on an Order within the database
- PackageTypeID — int — Type of package to be supplied
- PickedQuantity — int — Quantity picked from stock
- PickingCompletedWhen — datetime2 — When was picking of this line completed?
- Quantity — int — Quantity to be supplied
- StockItemID — int — Stock item for this order line (FK not indexed as separate index exists)
- TaxRate — decimal — Tax rate to be applied
- UnitPrice — decimal — Unit price to be charged

[Sales.Orders]
- BackorderOrderID — int — If this order is a backorder, this column holds the original order number
- Comments — nvarchar — Any comments related to this order (sent to customer)
- ContactPersonID — int — Customer contact for this order
- CustomerID — int — Customer for this order
- CustomerPurchaseOrderNumber — nvarchar(40) — Purchase Order Number received from customer
- DeliveryInstructions — nvarchar — Any comments related to order delivery (sent to customer)
- ExpectedDeliveryDate — date — Expected delivery date
- InternalComments — nvarchar — Any internal comments related to this order (not sent to the customer)
- IsUndersupplyBackordered — bit — If items cannot be supplied are they backordered?
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- OrderDate — date — Date that this order was raised
- OrderID — int — Numeric ID used for reference to an order within the database
- PickedByPersonID — int — Person who picked this shipment
- PickingCompletedWhen — datetime2 — When was picking of the entire order completed?
- SalespersonPersonID — int — Salesperson for this order

[Sales.SpecialDeals]
- BuyingGroupID — int — ID of the buying group that the special pricing applies to (optional)
- CustomerCategoryID — int — ID of the customer category that the special pricing applies to (optional)
- CustomerID — int — ID of the customer that the special pricing applies to (if NULL then all customers)
- DealDescription — nvarchar(60) — Description of the special deal
- DiscountAmount — decimal — Discount per unit to be applied to sale price (optional)
- DiscountPercentage — decimal — Discount percentage per unit to be applied to sale price (optional)
- EndDate — date — Date that the special pricing ends on
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- SpecialDealID — int — ID (sequence based) for a special deal
- StartDate — date — Date that the special pricing starts from
- StockGroupID — int — ID of the stock group that the special pricing applies to (optional)
- StockItemID — int — Stock item that the deal applies to (if NULL, then only discounts are permitted not unit prices)
- UnitPrice — decimal — Special price per unit to be applied instead of sale price (optional)

[Warehouse.ColdRoomTemperatures]
- ColdRoomSensorNumber — int — No description extracted.
- ColdRoomTemperatureID — bigint — No description extracted.
- RecordedWhen — datetime2 — No description extracted.
- Temperature — decimal — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.ColdRoomTemperatures_Archive]
- ColdRoomSensorNumber — int — No description extracted.
- ColdRoomTemperatureID — bigint — No description extracted.
- RecordedWhen — datetime2 — No description extracted.
- Temperature — decimal — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.Colors]
- ColorID — int — Numeric ID used for reference to a color within the database
- ColorName — nvarchar(40) — Full name of a color that can be used to describe stock items
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.Colors_Archive]
- ColorID — int — No description extracted.
- ColorName — nvarchar(40) — No description extracted.
- LastEditedBy — int — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.PackageTypes]
- LastEditedBy — int — No description extracted.
- PackageTypeID — int — Numeric ID used for reference to a package type within the database
- PackageTypeName — nvarchar(100) — Full name of package types that stock items can be purchased in or sold in
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.PackageTypes_Archive]
- LastEditedBy — int — No description extracted.
- PackageTypeID — int — No description extracted.
- PackageTypeName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.StockGroups]
- LastEditedBy — int — No description extracted.
- StockGroupID — int — Numeric ID used for reference to a stock group within the database
- StockGroupName — nvarchar(100) — Full name of groups used to categorize stock items
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.StockGroups_Archive]
- LastEditedBy — int — No description extracted.
- StockGroupID — int — No description extracted.
- StockGroupName — nvarchar(100) — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.StockItemHoldings]
- BinLocation — nvarchar(40) — Bin location (ie location of this stock item within the depot)
- LastCostPrice — decimal — Unit cost price the last time this stock item was purchased
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- LastStocktakeQuantity — int — Quantity at last stocktake (if tracked)
- QuantityOnHand — int — Quantity currently on hand (if tracked)
- ReorderLevel — int — Quantity below which reordering should take place
- StockItemID — int — ID of the stock item that this holding relates to (this table holds non-temporal columns for stock)
- TargetStockLevel — int — Typical quantity ordered

[Warehouse.StockItemStockGroups]
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- StockGroupID — int — StockGroup assigned to this stock item (FK indexed via unique constraint)
- StockItemID — int — Stock item assigned to this stock group (FK indexed via unique constraint)
- StockItemStockGroupID — int — Internal reference for this linking row

[Warehouse.StockItemTransactions]
- CustomerID — int — Customer for this transaction (if applicable)
- InvoiceID — int — ID of an invoice (for transactions associated with an invoice)
- LastEditedBy — int — No description extracted.
- LastEditedWhen — datetime2 — No description extracted.
- PurchaseOrderID — int — ID of an purchase order (for transactions associated with a purchase order)
- Quantity — decimal — Quantity of stock movement (positive is incoming stock, negative is outgoing)
- StockItemID — int — StockItem for this transaction
- StockItemTransactionID — int — Numeric ID used to refer to a stock item transaction within the database
- SupplierID — int — Supplier for this stock transaction (if applicable)
- TransactionOccurredWhen — datetime2 — Date and time when the transaction occurred
- TransactionTypeID — int — Type of transaction

[Warehouse.StockItems]
- Barcode — nvarchar(100) — Barcode for this stock item
- Brand — nvarchar(100) — Brand for the stock item (if the item is branded)
- ColorID — int — Color (optional) for this stock item
- CustomFields — nvarchar — Custom fields added by system users
- InternalComments — nvarchar — Internal comments (not exposed outside organization)
- IsChillerStock — bit — Does this stock item need to be in a chiller?
- LastEditedBy — int — No description extracted.
- LeadTimeDays — int — Number of days typically taken from order to receipt of this stock item
- MarketingComments — nvarchar — Marketing comments for this stock item (shared outside the organization)
- OuterPackageID — int — Usual package for selling outers of this stock item (ie cartons, boxes, etc.)
- Photo — varbinary — Photo of the product
- QuantityPerOuter — int — Quantity of the stock item in an outer package
- RecommendedRetailPrice — decimal — Recommended retail price for this stock item
- SearchDetails — nvarchar — Combination of columns used by full text search
- Size — nvarchar(40) — Size of this item (eg: 100mm)
- StockItemID — int — Numeric ID used for reference to a stock item within the database
- StockItemName — nvarchar(200) — Full name of a stock item (but not a full description)
- SupplierID — int — Usual supplier for this stock item
- Tags — nvarchar — Advertising tags associated with this stock item (JSON array retrieved from CustomFields)
- TaxRate — decimal — Tax rate to be applied
- TypicalWeightPerUnit — decimal — Typical weight for one unit of this product (packaged)
- UnitPackageID — int — Usual package for selling units of this stock item
- UnitPrice — decimal — Selling price (ex-tax) for one unit of this product
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.StockItems_Archive]
- Barcode — nvarchar(100) — No description extracted.
- Brand — nvarchar(100) — No description extracted.
- ColorID — int — No description extracted.
- CustomFields — nvarchar — No description extracted.
- InternalComments — nvarchar — No description extracted.
- IsChillerStock — bit — No description extracted.
- LastEditedBy — int — No description extracted.
- LeadTimeDays — int — No description extracted.
- MarketingComments — nvarchar — No description extracted.
- OuterPackageID — int — No description extracted.
- Photo — varbinary — No description extracted.
- QuantityPerOuter — int — No description extracted.
- RecommendedRetailPrice — decimal — No description extracted.
- SearchDetails — nvarchar — No description extracted.
- Size — nvarchar(40) — No description extracted.
- StockItemID — int — No description extracted.
- StockItemName — nvarchar(200) — No description extracted.
- SupplierID — int — No description extracted.
- Tags — nvarchar — No description extracted.
- TaxRate — decimal — No description extracted.
- TypicalWeightPerUnit — decimal — No description extracted.
- UnitPackageID — int — No description extracted.
- UnitPrice — decimal — No description extracted.
- ValidFrom — datetime2 — No description extracted.
- ValidTo — datetime2 — No description extracted.

[Warehouse.VehicleTemperatures]
- ChillerSensorNumber — int — No description extracted.
- CompressedSensorData — varbinary — No description extracted.
- FullSensorData — nvarchar(2000) — No description extracted.
- IsCompressed — bit — No description extracted.
- RecordedWhen — datetime2 — No description extracted.
- Temperature — decimal — No description extracted.
- VehicleRegistration — nvarchar(40) — No description extracted.
- VehicleTemperatureID — bigint — No description extracted.

"""


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def get_connection():
    """Open and return a pyodbc connection."""
    return pyodbc.connect(CONN_STRING, timeout=15)


def run_query(sql: str, max_rows: int = 500) -> list[dict]:
    """Execute a SELECT query and return rows as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql)
    columns = [col[0] for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchmany(max_rows)]
    cursor.close()
    conn.close()
    log_query(sql, len(rows))
    return rows


def to_markdown_table(rows: list[dict]) -> str:
    """Convert a list of dicts to a markdown table."""
    if not rows:
        return "_No rows returned._"
    headers   = list(rows[0].keys())
    separator = " | ".join(["---"] * len(headers))
    header    = " | ".join(headers)
    body      = "\n".join(
        " | ".join(str(row.get(h, "")) for h in headers)
        for row in rows
    )
    return f"{header}\n{separator}\n{body}"


# ─────────────────────────────────────────────────────────────────────────────
# MCP SERVER
# The instructions parameter injects the data dictionary into every session.
# Claude reads this before deciding what SQL to write.
# ─────────────────────────────────────────────────────────────────────────────
mcp = FastMCP(
    "sqlserver_mcp",
    instructions=(
        "You are a conversational business analytics assistant connected to the "
        "WideWorldImporters SQL Server database.\n"
        "The user is not assumed to have technical knowledge of SQL, databases, "
        "schemas, MCP, or software development. Translate ordinary business "
        "questions into internal SQL and return only the useful business answer.\n\n"

        "INTERNAL WORKFLOW\n"
        "Perform this workflow automatically and silently. Do not require the "
        "user to describe these steps.\n"
        "1. Call sqlserver_get_schema for the relevant part of the database.\n"
        "2. Call sqlserver_memory_read.\n"
        "3. Use the DATA DICTIONARY to choose the correct tables, joins and "
        "business interpretation.\n"
        "4. Generate and execute one read-only SQL query.\n"
        "5. Inspect the actual returned columns, values and row count.\n"
        "6. Decide whether the result is best communicated as an interactive "
        "visual, KPI, or detailed table.\n"
        "7. For visual or KPI results, call sqlserver_visual_query automatically "
        "using the same SQL and exact returned column names.\n\n"

        "DEFAULT PRESENTATION BEHAVIOUR\n"
        "Automatically use sqlserver_visual_query when the result represents:\n"
        "- a KPI or one principal numeric value;\n"
        "- a ranking or top/bottom N comparison;\n"
        "- a comparison across categories;\n"
        "- a trend or change over time;\n"
        "- a relationship between numeric measures;\n"
        "- a small part-to-whole composition.\n\n"

        "Use a table when:\n"
        "- the user asks for detailed records, transactions, invoices, orders, "
        "customers, suppliers, or another row-level list;\n"
        "- there are many descriptive columns;\n"
        "- exact values matter more than visual comparison;\n"
        "- no valid chart pattern exists;\n"
        "- the user explicitly requests text, JSON, or table-only output.\n\n"

        "VISUAL SELECTION\n"
        "- KPI: one principal numeric result.\n"
        "- Line: ordered date or period with one or more numeric measures.\n"
        "- Horizontal bar: rankings, top/bottom N, or long category labels.\n"
        "- Bar: comparisons across a small number of independent categories.\n"
        "- Scatter: relationship between two numeric measures.\n"
        "- Pie or doughnut: no more than six categories forming a meaningful "
        "whole, with no negative values.\n"
        "- Table: detailed records or an unsuitable result shape.\n\n"

        "USER-FACING RESPONSE RULES\n"
        "- Do not show SQL unless the user explicitly asks to see it.\n"
        "- Do not expose schema names, table names, column names, joins, JSON "
        "payloads, tool names, or internal workflow unless explicitly requested.\n"
        "- Do not narrate schema inspection, query generation, or tool execution.\n"
        "- Lead with the answer, not the method.\n"
        "- Present results in plain business language.\n"
        "- For analytical questions, return the interactive visual or KPI plus "
        "one or two concise business observations.\n"
        "- For detailed-record questions, return the interactive table plus a "
        "brief business summary.\n"
        "- Keep SQL only in the server query log for audit and troubleshooting.\n"
        "- If the user explicitly asks for SQL, provide it separately after the "
        "business answer.\n"
        "- Do not ask which chart type to use unless two materially different "
        "interpretations are equally valid. Choose the best visual yourself.\n"
        "- Do not require the user to request an interactive chart explicitly.\n"
        "- Keep the underlying result table available inside every interactive "
        "visual.\n\n"

        "SAFETY\n"
        "Only one read-only SELECT or CTE statement is permitted. Never modify "
        "data.\n\n"
        + DATA_DICTIONARY
    )
)


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1 — GET SCHEMA
# Reads live structure from SQL Server system views.
# Returns tables, columns, data types, and any formally declared FK constraints.
# Undeclared joins are in the DATA DICTIONARY, not here.
# ─────────────────────────────────────────────────────────────────────────────
class GetSchemaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    table_filter: Optional[str] = Field(
        default=None,
        description=(
            "Optional partial table name to narrow results. "
            "E.g. 'sales' returns all tables whose name contains 'sales'. "
            "Leave blank to return the full schema."
        )
    )

@mcp.tool(
    name="sqlserver_get_schema",
    annotations={
        "readOnlyHint":   True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint":  False
    }
)
async def sqlserver_get_schema(params: GetSchemaInput) -> str:
    """
    Read the live database schema from SQL Server system views.

    Returns all tables with their columns, data types, nullability, and primary
    keys. Also returns any foreign key relationships that were formally declared
    as FK constraints (note: many real-world joins are not declared as FK
    constraints — consult the DATA DICTIONARY for those).

    Always call this tool first before writing any SQL query.

    Args:
        params.table_filter (Optional[str]): filter by partial table name

    Returns:
        str: Markdown-formatted schema grouped by table, followed by FK list
    """
    try:
        filter_clause = ""
        if params.table_filter:
            safe = params.table_filter.replace("'", "")   # basic sanitise
            filter_clause = (
                f"AND (c.TABLE_SCHEMA LIKE '%{safe}%' "
                f"OR c.TABLE_NAME LIKE '%{safe}%' "
                f"OR CONCAT(c.TABLE_SCHEMA, '.', c.TABLE_NAME) LIKE '%{safe}%')"
            )

        column_sql = f"""
            SELECT
                c.TABLE_SCHEMA,
                c.TABLE_NAME,
                c.COLUMN_NAME,
                c.DATA_TYPE,
                c.CHARACTER_MAXIMUM_LENGTH  AS max_length,
                c.IS_NULLABLE,
                CASE
                    WHEN kcu.COLUMN_NAME IS NOT NULL THEN 'PK'
                    ELSE ''
                END AS key_type
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                ON  c.TABLE_NAME  = kcu.TABLE_NAME
                AND c.COLUMN_NAME = kcu.COLUMN_NAME
                AND EXISTS (
                    SELECT 1
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    WHERE tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                      AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                )
            WHERE c.TABLE_SCHEMA NOT IN ('sys', 'INFORMATION_SCHEMA')
            {filter_clause}
            ORDER BY c.TABLE_SCHEMA, c.TABLE_NAME, c.ORDINAL_POSITION
        """
        columns = run_query(column_sql, max_rows=2000)

        fk_sql = """
            SELECT
                sp.name  AS parent_schema,
                tp.name  AS parent_table,
                cp.name  AS parent_column,
                sr.name  AS referenced_schema,
                tr.name  AS referenced_table,
                cr.name  AS referenced_column
            FROM sys.foreign_keys           fk
            JOIN sys.tables              tp ON fk.parent_object_id      = tp.object_id
            JOIN sys.schemas             sp ON tp.schema_id             = sp.schema_id
            JOIN sys.tables              tr ON fk.referenced_object_id  = tr.object_id
            JOIN sys.schemas             sr ON tr.schema_id             = sr.schema_id
            JOIN sys.foreign_key_columns fc ON fk.object_id             = fc.constraint_object_id
            JOIN sys.columns             cp ON fc.parent_object_id      = cp.object_id
                                           AND fc.parent_column_id      = cp.column_id
            JOIN sys.columns             cr ON fc.referenced_object_id  = cr.object_id
                                           AND fc.referenced_column_id  = cr.column_id
            ORDER BY sp.name, tp.name, cp.name
        """
        fk_rows = run_query(fk_sql, max_rows=500)

        # Group columns by table and format
        tables: dict[str, list] = {}
        for row in columns:
            full_table_name = f"{row['TABLE_SCHEMA']}.{row['TABLE_NAME']}"
            tables.setdefault(full_table_name, []).append(row)

        output = ["# Live Schema\n"]
        for table_name, cols in tables.items():
            output.append(f"## {table_name}")
            for c in cols:
                length = f"({c['max_length']})" if c["max_length"] else ""
                pk     = " [PK]"   if c["key_type"] == "PK"  else ""
                null   = " NULL"   if c["IS_NULLABLE"] == "YES" else " NOT NULL"
                output.append(f"  - {c['COLUMN_NAME']}: {c['DATA_TYPE']}{length}{pk}{null}")
            output.append("")

        if fk_rows:
            output.append("## Declared FK Constraints")
            for fk in fk_rows:
                output.append(
                    f"  - {fk['parent_schema']}.{fk['parent_table']}.{fk['parent_column']} "
                    f"→ {fk['referenced_schema']}.{fk['referenced_table']}.{fk['referenced_column']}"
                )
            output.append("")

        output.append(
            "_Note: joins not listed above are documented in the DATA DICTIONARY._"
        )
        return "\n".join(output)

    except Exception as e:
        return f"Error reading schema: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2 — QUERY
# Claude writes the SQL based on live schema + data dictionary.
# Read-only — write operations are blocked.
# ─────────────────────────────────────────────────────────────────────────────
FORBIDDEN_KEYWORDS = {
    "alter",
    "bulk",
    "create",
    "delete",
    "drop",
    "exec",
    "execute",
    "insert",
    "merge",
    "truncate",
    "update",
}


def validate_read_only_sql(sql: str) -> tuple[bool, Optional[str]]:
    """Validate that SQL is one read-only SELECT or CTE statement."""
    cleaned = sql.strip()
    if not cleaned:
        return False, "The SQL statement is empty."

    # Permit one optional trailing semicolon, but reject multiple statements.
    without_trailing = cleaned[:-1].rstrip() if cleaned.endswith(";") else cleaned
    if ";" in without_trailing:
        return False, "Only one SQL statement is permitted."

    lowered = without_trailing.lower()
    if not (lowered.startswith("select") or lowered.startswith("with")):
        return False, "The query must begin with SELECT or WITH."

    # Word boundaries avoid false positives such as UpdatedWhen or CreatedDate.
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return False, f"'{keyword.upper()}' is not permitted."

    # Block comments to reduce opportunities to obscure a second statement.
    if "--" in without_trailing or "/*" in without_trailing or "*/" in without_trailing:
        return False, "SQL comments are not permitted."

    return True, None

class QueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sql: str = Field(
        ...,
        description="A valid SELECT statement. Write operations are not permitted.",
        min_length=10
    )
    max_rows: int = Field(
        default=100,
        description="Maximum number of rows to return (1–500)",
        ge=1,
        le=500
    )
    format: str = Field(
        default="markdown",
        description="Output format: 'markdown' for a readable table, 'json' for structured data"
    )

@mcp.tool(
    name="sqlserver_query",
    annotations={
        "readOnlyHint":   True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint":  False
    }
)
async def sqlserver_query(params: QueryInput) -> str:
    """
    Execute a read-only SELECT query against SQL Server.

    This is primarily an internal analytical step. Use it to inspect data and
    result shape before preparing the final business-facing answer.

    Before calling:
      1. Call sqlserver_get_schema for the relevant objects.
      2. Read MCP memory.
      3. Consult the DATA DICTIONARY for business meaning and joins.

    Do not show the generated SQL to the user unless they explicitly ask for it.
    Do not narrate this tool call or expose technical database details by default.

    Args:
        params.sql      (str): The read-only SELECT or CTE statement to execute.
        params.max_rows (int): Row limit, default 100, maximum 500.
        params.format   (str): 'markdown' or 'json'.

    Returns:
        str: Query results for internal interpretation and final presentation.
    """
    valid, validation_error = validate_read_only_sql(params.sql)
    if not valid:
        return f"Rejected: {validation_error}"

    try:
        rows = run_query(params.sql, max_rows=params.max_rows)

        row_count = f"_{len(rows)} row(s) returned"
        row_count += " (limit reached — refine your query to see more)" if len(rows) == params.max_rows else "._"

        if params.format == "json":
            return row_count + "\n\n" + json.dumps(rows, indent=2, default=str)
        else:
            return row_count + "\n\n" + to_markdown_table(rows)

    except pyodbc.Error as e:
        return (
            f"SQL Error: {e}\n\n"
            "Suggestions:\n"
            "- Run sqlserver_get_schema to verify table and column names\n"
            "- Check the DATA DICTIONARY for correct join columns\n"
            "- Confirm status filter values against the system values section"
        )
    except Exception as e:
        return f"Unexpected error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3 — MEMORY READ
# Claude calls this at the start of every session to load accumulated schema
# knowledge built up from previous sessions. This sits on top of the base
# DATA DICTIONARY and grows over time as suggestions are reviewed and approved.
# ─────────────────────────────────────────────────────────────────────────────
@mcp.tool(
    name="sqlserver_memory_read",
    annotations={
        "readOnlyHint":    True,
        "destructiveHint": False,
        "idempotentHint":  True,
        "openWorldHint":   False
    }
)
async def sqlserver_memory_read() -> str:
    """
    Load accumulated schema knowledge from previous sessions.

    Call this tool at the start of every session, immediately after
    sqlserver_get_schema. The knowledge here has been reviewed and approved
    by the user — treat it with the same confidence as the DATA DICTIONARY.

    If no memory file exists yet this tool returns a message saying so,
    which simply means no approved knowledge has been accumulated yet.

    Returns:
        str: All accumulated schema knowledge, or a message if none exists yet.
    """
    if not MEMORY_FILE.exists():
        return (
            "No accumulated memory found. This is normal for a first session. "
            "Use sqlserver_memory_suggest to flag any schema discoveries during "
            "this session for review."
        )

    content = MEMORY_FILE.read_text(encoding="utf-8").strip()

    if not content:
        return "Memory file exists but contains no entries yet."

    return (
        "=== ACCUMULATED SCHEMA KNOWLEDGE (reviewed and approved) ===\n\n"
        + content
        + "\n\n=== END OF ACCUMULATED MEMORY ==="
    )


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4 — MEMORY SUGGEST
# Claude calls this when it discovers something about the schema that isn't
# in the DATA DICTIONARY or accumulated memory. The suggestion is written to
# a pending file for the user to review. Nothing is committed automatically.
#
# Categories Claude can suggest:
#   - join:      a join path it discovered or inferred
#   - pattern:   a column value pattern observed from query results
#   - rule:      a business rule inferred from the data
#   - correction: a correction to an existing data dictionary entry
# ─────────────────────────────────────────────────────────────────────────────
class MemorySuggestInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: str = Field(
        ...,
        description=(
            "Category of the suggestion. Must be one of: "
            "'join' (a join path discovered or inferred), "
            "'pattern' (a column value pattern observed from results), "
            "'rule' (a business rule inferred from the data), "
            "'correction' (a correction to an existing data dictionary entry)."
        )
    )
    observation: str = Field(
        ...,
        description=(
            "What was observed. Be specific — include table names, column names, "
            "and values where relevant. Example: 'sales_dr_tran.sdr_entity appears "
            "to join to entity_head.ent_id — all values in query results matched "
            "valid ent_id values.'"
        ),
        min_length=20
    )
    confidence: str = Field(
        ...,
        description=(
            "How confident you are in this observation. Must be one of: "
            "'high' (observed directly in query results), "
            "'medium' (inferred from naming patterns and partial evidence), "
            "'low' (a guess based on limited evidence — flag clearly)."
        )
    )
    source_query: Optional[str] = Field(
        default=None,
        description="The SQL query that led to this observation, if applicable."
    )

@mcp.tool(
    name="sqlserver_memory_suggest",
    annotations={
        "readOnlyHint":    False,
        "destructiveHint": False,
        "idempotentHint":  False,
        "openWorldHint":   False
    }
)
async def sqlserver_memory_suggest(params: MemorySuggestInput) -> str:
    """
    Write a schema discovery to the pending suggestions file for user review.

    Call this whenever you observe something about the database that is not
    documented in the DATA DICTIONARY or accumulated memory. Do not wait until
    the end of the session — suggest as you discover.

    The suggestion is NOT added to active memory automatically. The user reviews
    the pending file, and approved entries are manually moved to mcp_memory.txt.
    This human review gate exists to prevent incorrect observations from
    corrupting the knowledge base.

    Suggest liberally — the user expects to filter and validate suggestions.
    It is better to suggest too much than to miss something useful.

    Args:
        params.category     (str):           join | pattern | rule | correction
        params.observation  (str):           what was observed, with specifics
        params.confidence   (str):           high | medium | low
        params.source_query (Optional[str]): the SQL that led to this observation

    Returns:
        str: Confirmation that the suggestion was written to the pending file.
    """
    # Validate category and confidence values
    valid_categories  = {"join", "pattern", "rule", "correction"}
    valid_confidences = {"high", "medium", "low"}

    if params.category not in valid_categories:
        return (
            f"Invalid category '{params.category}'. "
            f"Must be one of: {', '.join(sorted(valid_categories))}."
        )

    if params.confidence not in valid_confidences:
        return (
            f"Invalid confidence '{params.confidence}'. "
            f"Must be one of: {', '.join(sorted(valid_confidences))}."
        )

    # Build the suggestion entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"{'─' * 72}",
        f"DATE:       {timestamp}",
        f"CATEGORY:   {params.category.upper()}",
        f"CONFIDENCE: {params.confidence.upper()}",
        f"",
        f"OBSERVATION:",
        f"{params.observation}",
    ]

    if params.source_query:
        lines += [
            f"",
            f"SOURCE QUERY:",
            f"{params.source_query.strip()}",
        ]

    lines += [
        f"",
        f"STATUS: PENDING REVIEW",
        f"  → If correct, copy the OBSERVATION above into mcp_memory.txt",
        f"  → If incorrect, delete this entry",
        f"{'─' * 72}",
        f"",
    ]

    entry = "\n".join(lines)

    # Append to the pending file
    with open(PENDING_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

    return (
        f"Suggestion written to pending review file: {PENDING_FILE.name}\n"
        f"Category: {params.category} | Confidence: {params.confidence}\n\n"
        f"This will not affect active memory until you review and approve it."
    )



# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5 — INTERACTIVE VISUAL QUERY (MCP APP)
#
# The model first runs sqlserver_query(format="json"), inspects the actual result,
# chooses a suitable visual, then calls this tool using the same SQL.
# Cursor reads the linked ui:// resource and renders it in an iframe.
# ─────────────────────────────────────────────────────────────────────────────

VisualType = Literal[
    "table",
    "kpi",
    "bar",
    "horizontal_bar",
    "line",
    "scatter",
    "pie",
    "doughnut",
]


class VisualQueryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sql: str = Field(
        ...,
        min_length=10,
        description=(
            "The same single read-only SELECT or CTE statement already tested "
            "with sqlserver_query(format='json')."
        ),
    )
    visual_type: VisualType = Field(
        ...,
        description=(
            "Choose after inspecting the real query result: table, kpi, bar, "
            "horizontal_bar, line, scatter, pie, or doughnut."
        ),
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=140,
        description="Concise human-readable visual title.",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=400,
        description=(
            "Briefly explain why this visual suits the user's question and "
            "the returned data shape."
        ),
    )
    x_field: Optional[str] = Field(
        default=None,
        description=(
            "Exact returned column to use for categories, dates, periods or "
            "the scatter x-axis. Not required for table or KPI."
        ),
    )
    y_fields: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Exact returned numeric columns to plot.",
    )
    value_format: Literal["number", "currency", "percent"] = Field(
        default="number",
        description="Display format for plotted numeric values.",
    )
    currency_code: str = Field(
        default="USD",
        min_length=3,
        max_length=3,
        description="ISO currency code used when value_format is currency.",
    )
    max_rows: int = Field(default=200, ge=1, le=500)


def _is_numeric(value: Any) -> bool:
    """Return True when a value can safely be treated as numeric."""
    if value is None or isinstance(value, bool):
        return False
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


def _validate_visual_choice(
    requested_type: VisualType,
    rows: list[dict],
    x_field: Optional[str],
    y_fields: list[str],
) -> tuple[VisualType, Optional[str]]:
    """Validate an LLM-selected visual and return a safe fallback if needed."""
    if not rows:
        return "table", "No rows were returned, so a table fallback was used."

    columns = list(rows[0].keys())

    if requested_type == "table":
        return "table", None

    if requested_type == "kpi":
        if len(rows) == 1 and len(y_fields) == 1 and y_fields[0] in columns:
            if _is_numeric(rows[0].get(y_fields[0])):
                return "kpi", None
        return "table", (
            "KPI output requires one returned row and one numeric y-field."
        )

    if not x_field or x_field not in columns:
        return "table", "The selected x_field was not present in the result."

    if not y_fields:
        return "table", "At least one y-field is required for this visual."

    missing = [field for field in y_fields if field not in columns]
    if missing:
        return "table", (
            "The following y-fields were not present in the result: "
            + ", ".join(missing)
        )

    if requested_type == "scatter":
        if len(y_fields) != 1:
            return "table", "Scatter charts require one x-field and one y-field."
        if any(
            not _is_numeric(row.get(x_field))
            or not _is_numeric(row.get(y_fields[0]))
            for row in rows
        ):
            return "table", "Scatter x and y values must both be numeric."

    if requested_type in {
        "bar",
        "horizontal_bar",
        "line",
        "pie",
        "doughnut",
    }:
        for field in y_fields:
            if any(not _is_numeric(row.get(field)) for row in rows):
                return "table", f"Field '{field}' was not consistently numeric."

    if requested_type in {"pie", "doughnut"}:
        if len(y_fields) != 1:
            return "table", "Pie and doughnut charts require one y-field."
        if len(rows) > 8:
            return "horizontal_bar", (
                "More than eight categories were returned; a horizontal bar "
                "chart is more readable."
            )
        if any(float(row[y_fields[0]]) < 0 for row in rows):
            return "bar", (
                "Negative values cannot be represented meaningfully in a "
                "pie or doughnut chart."
            )

    if requested_type == "bar" and len(rows) >= 10:
        return "horizontal_bar", (
            "Ten or more categories were returned; horizontal bars are more readable."
        )

    return requested_type, None


def _build_visual_payload(
    params: VisualQueryInput,
    rows: list[dict],
) -> dict[str, Any]:
    """Build and validate the JSON payload consumed by the MCP App."""
    columns = list(rows[0].keys()) if rows else []
    final_type, fallback_reason = _validate_visual_choice(
        params.visual_type,
        rows,
        params.x_field,
        params.y_fields,
    )

    reason = params.reason
    if fallback_reason:
        reason = f"{reason} Server fallback: {fallback_reason}"

    return {
        "title": params.title,
        "reason": reason,
        "visual_type": final_type,
        "x_field": params.x_field,
        "y_fields": params.y_fields,
        "value_format": params.value_format,
        "currency_code": params.currency_code.upper(),
        "columns": columns,
        "row_count": len(rows),
        "rows": rows,
    }


@mcp.tool(
    name="sqlserver_visual_query",
    meta={
        "ui": {"resourceUri": CHART_VIEW_URI},
        "ui/resourceUri": CHART_VIEW_URI,
    },
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def sqlserver_visual_query(params: VisualQueryInput) -> CallToolResult:
    """
    Render the final business answer as an interactive analytical result.

    Use this tool automatically when an ordinary business question produces a
    KPI, ranking, categorical comparison, trend, composition, or relationship.
    The user does not need to ask for a chart explicitly.

    Internal workflow before calling:
      1. Inspect the relevant live schema.
      2. Read approved MCP memory and the data dictionary.
      3. Run the SQL with sqlserver_query(format='json').
      4. Inspect the actual returned columns, values and row count.
      5. Select the most suitable visual and exact field mappings.

    Use table output for detailed row-level records or where no meaningful chart
    pattern exists. The interactive app always includes the underlying data.

    Do not expose the SQL, schema details, tool sequence, or JSON payload to the
    user unless they explicitly ask for technical detail.
    """
    valid, validation_error = validate_read_only_sql(params.sql)
    if not valid:
        payload = {"error": validation_error}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload))],
            structuredContent=payload,
            isError=True,
        )

    try:
        rows = run_query(params.sql, max_rows=params.max_rows)
        payload = _build_visual_payload(params, rows)

        summary = (
            f"{payload['title']}: {payload['row_count']} row(s), "
            f"rendered as {payload['visual_type']}."
        )

        return CallToolResult(
            content=[
                TextContent(type="text", text=summary),
                TextContent(
                    type="text",
                    text=json.dumps(payload, default=str),
                ),
            ],
            structuredContent=payload,
        )

    except pyodbc.Error as error:
        payload = {"error": f"SQL Error: {error}"}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload))],
            structuredContent=payload,
            isError=True,
        )
    except Exception as error:
        payload = {"error": f"Unexpected error: {error}"}
        return CallToolResult(
            content=[TextContent(type="text", text=json.dumps(payload))],
            structuredContent=payload,
            isError=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# MCP APP HTML
#
# This first version uses CDN-hosted Chart.js and the official MCP Apps browser
# bridge. The CSP below explicitly permits those resource domains.
# ─────────────────────────────────────────────────────────────────────────────

CHART_VIEW_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="light dark">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SQL Server interactive result</title>

  <style>
    :root {
      font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                   BlinkMacSystemFont, "Segoe UI", sans-serif;
    }

    html, body {
      margin: 0;
      padding: 0;
      background: transparent;
    }

    body {
      padding: 14px;
    }

    .card {
      border: 1px solid rgba(127, 127, 127, 0.24);
      border-radius: 12px;
      padding: 14px;
      background: rgba(127, 127, 127, 0.06);
    }

    h2 {
      margin: 0 0 5px;
      font-size: 17px;
    }

    .subtitle,
    .reason {
      margin: 0 0 9px;
      font-size: 12px;
      opacity: 0.72;
    }

    .toolbar {
      display: flex;
      gap: 7px;
      margin: 10px 0;
    }

    button {
      border: 1px solid rgba(127, 127, 127, 0.26);
      border-radius: 7px;
      padding: 6px 10px;
      color: inherit;
      background: transparent;
      cursor: pointer;
    }

    button.active {
      background: rgba(127, 127, 127, 0.17);
    }

    .chart-wrap {
      position: relative;
      min-height: 355px;
    }

    canvas {
      width: 100% !important;
      height: 355px !important;
    }

    .kpi {
      margin: 32px 0 24px;
      font-size: 42px;
      font-weight: 750;
      letter-spacing: -0.035em;
    }

    .table-wrap {
      max-height: 440px;
      overflow: auto;
      border: 1px solid rgba(127, 127, 127, 0.22);
      border-radius: 8px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 12px;
    }

    th,
    td {
      padding: 8px 10px;
      border-bottom: 1px solid rgba(127, 127, 127, 0.16);
      text-align: left;
      white-space: nowrap;
    }

    th {
      position: sticky;
      top: 0;
      z-index: 1;
      background: Canvas;
    }

    .error {
      color: #b42318;
      white-space: pre-wrap;
    }

    .hidden {
      display: none;
    }
  </style>
</head>

<body>
  <div class="card">
    <h2 id="title">SQL Server result</h2>
    <p id="subtitle" class="subtitle"></p>
    <p id="reason" class="reason"></p>

    <div id="toolbar" class="toolbar hidden">
      <button id="visual-tab" class="active">Visual</button>
      <button id="data-tab">Data</button>
    </div>

    <section id="visual-panel">
      <div id="kpi" class="kpi hidden"></div>
      <div id="chart-wrap" class="chart-wrap hidden">
        <canvas id="chart"></canvas>
      </div>
    </section>

    <section id="data-panel" class="hidden">
      <div class="table-wrap">
        <table id="data-table"></table>
      </div>
    </section>

    <div id="error" class="error hidden"></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>

  <script type="module">
    import { App } from
      "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";

    const app = new App({
      name: "SQL Server interactive result",
      version: "1.0.0"
    });

    let chartInstance = null;
    const byId = id => document.getElementById(id);

    function setVisible(id, visible) {
      byId(id).classList.toggle("hidden", !visible);
    }

    function switchPanel(panel) {
      const visual = panel === "visual";
      setVisible("visual-panel", visual);
      setVisible("data-panel", !visual);
      byId("visual-tab").classList.toggle("active", visual);
      byId("data-tab").classList.toggle("active", !visual);
    }

    function formatValue(value, payload) {
      if (value === null || value === undefined) return "";
      const number = Number(value);

      if (payload.value_format === "currency" && !Number.isNaN(number)) {
        return new Intl.NumberFormat(undefined, {
          style: "currency",
          currency: payload.currency_code || "USD",
          maximumFractionDigits: 2
        }).format(number);
      }

      if (payload.value_format === "percent" && !Number.isNaN(number)) {
        return `${number.toLocaleString()}%`;
      }

      if (!Number.isNaN(number) && value !== "") {
        return number.toLocaleString();
      }

      return String(value);
    }

    function renderTable(payload) {
      const table = byId("data-table");
      table.innerHTML = "";

      const thead = document.createElement("thead");
      const headerRow = document.createElement("tr");

      for (const column of payload.columns) {
        const th = document.createElement("th");
        th.textContent = column;
        headerRow.appendChild(th);
      }

      thead.appendChild(headerRow);
      table.appendChild(thead);

      const tbody = document.createElement("tbody");

      for (const row of payload.rows) {
        const tr = document.createElement("tr");

        for (const column of payload.columns) {
          const td = document.createElement("td");
          td.textContent = row[column] === null || row[column] === undefined
            ? ""
            : String(row[column]);
          tr.appendChild(td);
        }

        tbody.appendChild(tr);
      }

      table.appendChild(tbody);
    }

    function renderKpi(payload) {
      setVisible("kpi", true);
      setVisible("chart-wrap", false);

      const field = payload.y_fields[0] || payload.columns[0];
      const value = payload.rows[0]?.[field];
      byId("kpi").textContent = formatValue(value, payload);
    }

    function renderChart(payload) {
      setVisible("kpi", false);
      setVisible("chart-wrap", true);

      if (chartInstance) {
        chartInstance.destroy();
        chartInstance = null;
      }

      const typeMap = {
        bar: "bar",
        horizontal_bar: "bar",
        line: "line",
        scatter: "scatter",
        pie: "pie",
        doughnut: "doughnut"
      };

      const chartType = typeMap[payload.visual_type] || "bar";
      let chartData;

      if (payload.visual_type === "scatter") {
        const xField = payload.x_field;
        const yField = payload.y_fields[0];

        chartData = {
          datasets: [{
            label: yField,
            data: payload.rows.map(row => ({
              x: Number(row[xField]),
              y: Number(row[yField])
            }))
          }]
        };
      } else if (
        payload.visual_type === "pie"
        || payload.visual_type === "doughnut"
      ) {
        const xField = payload.x_field;
        const yField = payload.y_fields[0];

        chartData = {
          labels: payload.rows.map(row => String(row[xField])),
          datasets: [{
            label: yField,
            data: payload.rows.map(row => Number(row[yField]))
          }]
        };
      } else {
        const xField = payload.x_field;

        chartData = {
          labels: payload.rows.map(row => String(row[xField])),
          datasets: payload.y_fields.map(field => ({
            label: field,
            data: payload.rows.map(row => Number(row[field])),
            borderWidth: payload.visual_type === "line" ? 2 : 1,
            tension: payload.visual_type === "line" ? 0.2 : 0,
            fill: false
          }))
        };
      }

      const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: "nearest",
          intersect: false
        },
        plugins: {
          legend: {
            display:
              payload.y_fields.length > 1
              || payload.visual_type === "pie"
              || payload.visual_type === "doughnut"
          },
          tooltip: {
            enabled: true
          }
        }
      };

      if (payload.visual_type === "horizontal_bar") {
        options.indexAxis = "y";
      }

      chartInstance = new Chart(byId("chart"), {
        type: chartType,
        data: chartData,
        options
      });
    }

    byId("visual-tab").addEventListener(
      "click",
      () => switchPanel("visual")
    );

    byId("data-tab").addEventListener(
      "click",
      () => switchPanel("data")
    );

    app.ontoolresult = result => {
      try {
        const payload = result.structuredContent;

        if (!payload) {
          throw new Error("No structured visual payload was returned.");
        }

        if (payload.error) {
          throw new Error(payload.error);
        }

        byId("title").textContent = payload.title || "SQL Server result";
        byId("subtitle").textContent =
          `${payload.row_count} row(s) · `
          + payload.visual_type.replaceAll("_", " ");
        byId("reason").textContent = payload.reason || "";

        renderTable(payload);
        setVisible("toolbar", payload.visual_type !== "table");

        if (payload.visual_type === "table") {
          switchPanel("data");
        } else if (payload.visual_type === "kpi") {
          renderKpi(payload);
          switchPanel("visual");
        } else {
          renderChart(payload);
          switchPanel("visual");
        }
      } catch (error) {
        setVisible("error", true);
        byId("error").textContent = String(error);
      }
    };

    await app.connect();
  </script>
</body>
</html>"""


@mcp.resource(
    CHART_VIEW_URI,
    mime_type="text/html;profile=mcp-app",
    meta={
        "ui": {
            "csp": {
                "resourceDomains": [
                    "https://unpkg.com",
                    "https://cdn.jsdelivr.net",
                ]
            }
        }
    },
)
def sqlserver_chart_view() -> str:
    """Return the interactive HTML used by sqlserver_visual_query."""
    return CHART_VIEW_HTML



# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# STDIO transport — Claude spawns this process on demand.
# No persistent background service. No open ports.
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
