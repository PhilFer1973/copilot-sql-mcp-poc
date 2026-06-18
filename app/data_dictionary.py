"""WideWorldImporters business data dictionary.

This module is mechanically extracted from the legacy working server.
"""

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
