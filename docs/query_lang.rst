.. Copyright 2017-2023 Lawrence Livermore National Security, LLC and other
   Hatchet Project Developers. See the top-level LICENSE file for details.

   SPDX-License-Identifier: MIT

**************
Query Language
**************

.. versionadded:: 1.2.0

One of the most important steps in identifying performance phenomena (e.g., bottlenecks) is data subselection
and reduction. In previous versions of Hatchet, users could only reduce their data using filters on the
pandas :code:`DataFrame` component of the :code:`GraphFrame` object. However, this type of data reduction
ignores the relational data encoded in the Graph component of the :code:`GraphFrame`.

Hatchet's Call Path Query Language (*query language* for short) provides a new way of reducing profiling
data that leverages this relational data. In the query language, users provide a *query*, or a
description of the properties of one or more paths in the Graph. Hatchet then uses this query to
select all nodes in the Graph that satisfy the query. These nodes are returned to the user as a new
:code:`GraphFrame`.

The following sections will describe the structure of a query, the syntaxes for constructing
queries, and the APIs for dealing with queries.

Query Structure
===============

The main input to the query language is a query. A *query* is defined as a sequence of *query nodes*.
A query node is a tuple of a *quantifier* and a *predicate*. A quantifier defines how many nodes in the
Graph should be matched to a single query node. A predicate defines what conditions must be satisfied
for a node in the Graph to match a query node.

Query Syntaxes and Dialects
===========================

Hatchet provides three ways of creating queries to simplify the use of the query language under
diverse circumstances (e.g., creating queries in JavaScript that will be moved into Python code).
The first way to create queries is the *base syntax*: a Python API for iteratively building a query
using method calls. Hatchet also provides two dialects for the query language:

- **Object-based Dialect**: uses Python built-in objects (i.e., :code:`list`, :code:`tuple`, :code:`dict`)
  to build queries
- **String-based Dialect**: uses strings to build queries. The syntax of this dialect is derived from
  the `Cypher <https://neo4j.com/product/cypher-graph-query-language/>`_ query language for graph databases.

Besides syntaxes, these three ways of creating queries differ in their capabilities. In general, the base syntax
is the most capable and most verbose. The object-based dialect is the least capable and least verbose, and the
string-based dialect is in-between. For a more complete breakdown of the capabilities, see the
:ref:`Syntax and Dialect Capabilities` section.

Base Syntax
-----------

.. note::
   In version 2023.1.0, the query language was refactored to work better with a new tool
   called `Thicket <https://thicket.readthedocs.io/en/latest/>`_. This refactor is explained in
   more detail in the :ref:`Query Language APIs` section.
   This section assumes the use of "new-style" queries. If you are using "old-style" queries, you
   can simply replace any use of :code:`Query` with :code:`QueryMatcher`.

Hatchet's :code:`Query` class defines how to construct a query using the base syntax. Using this class,
queries are built using the :code:`match` and :code:`rel` methods. The :code:`match` method sets the first
node of the query. The :code:`rel` method is called iteratively, each time adding a new node to the end
of the query. Both methods take a quantifier and a predicate as input.

A quantifier can have one of four possible values:

- :code:`"."`: match one node
- :code:`"*"`: match zero or more nodes
- :code:`+`: match one or more nodes
- An integer: match exactly that number of nodes

All queries can be constructed using just :code:`"."` and :code:`"*"`. The :code:`"+"` and integer quantifiers
are provided for convenience and are implemented as follows:

- :code:`"+"`: implemented as a node with a :code:`"."` quantifier followed by a node with a :code:`"*"` quantifier
- Integer: implemented as a sequence of nodes with :code:`"."` quantifiers

If no quantifier is provided to :code:`match` or :code:`rel`, the default :code:`"."` quantifier is used.

A predicate is represented as a Python :code:`Callable` that takes the data for a node in a :code:`GraphFrame`
as input and returns a Boolean. The returned Boolean is used internally to determine whether a :code:`GraphFrame`
node satisfies the predicate. If a predicate is to provided to :code:`match` or :code:`rel`, the default
predicate is a function that always returns :code:`True`.

The base syntax is illustrated by the query below. This query uses two query nodes to find all subgraphs in the
Graph rooted at MPI (or PMPI) function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = (
       Query()
       .match(
           ".",
           lambda row: re.match(
               "P?MPI_.*",
               row["name"]
           )
           is not None
           and row["PAPI_L2_TCM"] > 5
       )
       .rel("*")
   )

Object-based Dialect
--------------------

The object-based dialect allows users to construct queries using built-in Python objects. In this dialect, a
query is represented by a Python :code:`list` of query nodes. Each query node is represented by a Python
:code:`tuple` of a qunatifier and a predicate. Quantifiers are represented the same way as in the base syntax
(see :ref:`Base Syntax` for more information). Predicates are represented as key-value pairs where keys
are metric names and values are Boolean expressions generated using the following rules:

- If the metric is numeric, the value can be a be a number (checks for equality) or a string consisting of a
  comparison operator (one of :code:`<`, :code:`<=`, :code:`==`, :code:`>`, or :code:`>=`) followed by a number
- If the metric is a string, the value can be any regex string that is a valid input to `Python's re.match
  function <https://docs.python.org/3/library/re.html#re.match>`_.

Multiple predicates can be combined into a larger predicate by simply putting multiple key-value pairs into
the same Python :code:`dict`. When multiple predicates are in the same :code:`dict` in the object-base dialect,
they are all combined by conjunction (i.e., logical AND).

When using a default quantifier (i.e., :code:`"."`) or predicate (i.e., a function that always returns :code:`True`),
query nodes do not have to be represented as a Python :code:`tuple`. In these situations, a query node is represented
by simply adding the non-default component to the Python :code:`list` representing the query.

The object-based dialect is illustrated by the query below. This query is the same as the one introduced in the
:ref:`Base Syntax` section. It uses two query nodes to find all subgraphs in the Graph rooted at MPI (or PMPI)
function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = [
       (
           ".",
           {
               "name": "P?MPI_.*",
               "PAPI_L2_TCM": "> 5"
           }
       ),
       "*"
   ]

String-based Dialect
--------------------

The string-based dialect allows users to construct queries using strings. This allows the string-based dialect
to be the only way of creating queries that is not tied to Python. The syntax of the query strings in the
string-based dialect is derived from `Cypher <https://neo4j.com/product/cypher-graph-query-language/>`_.
A query in this dialect contains two main syntactic pieces: a :code:`MATCH` statement and a :code:`WHERE`
statement.

The :code:`MATCH` statement starts with the :code:`MATCH` keyword and defines the quantifiers and variable
names used to refer to query nodes in the predicates. Each node in the :code:`MATCH` statement takes the form
of :code:`([<quantifier>,] <variable>)`. Quantifiers in the string-based dialect have the same representation
as the base syntax and object-based dialect. Variables can be any valid combination of letters, numbers, and underscores
that does not start with a number (i.e., normal variable name rules). Multiple query nodes can be added to the
:code:`MATCH` statement by chaining the nodes with :code:`->`.

The :code:`WHERE` statement starts with the :code:`WHERE` keyword and defines one or more predicates.
Predicates in the string-based dialect are represented by expressions of the form :code:`<variable>."<metric>" <comparison operation>`.
In these expressions, :code:`<variable>` should be replaced by the variable associated with the desired query node
in the :code:`MATCH` statement, and :code:`<metric>` should be replaced by the name of the metric being considered.
:code:`<comparison operation>` should be replaced by one of the following:

- :code:`= <value>`: checks if the metric equals a value
- :code:`STARTS WITH <substring>`: checks if a string metric starts with a substring
- :code:`ENDS WITH <substring>`: checks if a string metric ends with a substring
- :code:`CONTAINS <substring>`: checks if a string metric contains a substring
- :code:`=~ <regex>`: checks if a string metric matches a regex
- :code:`< <value>`: checks if a numeric metric is less than a value
- :code:`<= <value>`: checks if a numeric metric is less than or equal to a value
- :code:`> <value>`: checks if a numeric metric is greater than a value
- :code:`>= <value>`: checks if a numeric metric is greater than or equal to a value
- :code:`IS NAN`: checks if a numeric metric is NaN
- :code:`IS NOT NAN`: checks if a numeric metric is not NaN
- :code:`IS INF`: checks if a numeric metric is infinity
- :code:`IS NOT INF`: checks if a numeric metric is not infinity
- :code:`IS NONE`: checks if a metric is Python's None value
- :code:`IS NOT NONE`: checks if a metric is not Python's None value

.. versionadded:: 2022.2.1

   Added two new comparison operations (i.e., :code:`IS LEAF` and :code:`IS NOT LEAF`) for determining
   whether a node is a leaf node of the Graph.

Multiple predicates can be combined using three Boolean operators: conjunction (i.e., :code:`AND` keyword),
disjunction (i.e., :code:`OR` keyword), and complement (i.e., :code:`NOT` keyword).

The string-based dialect is illustrated by the query below. This query is the same as the one introduced in the
:ref:`Base Syntax` section. It uses two query nodes to find all subgraphs in the Graph rooted at MPI (or PMPI)
function calls that have more than 5 L2 cache misses (as measured by PAPI).

.. code-block:: python

   query = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "MPI_" OR p."name" STARTS WTICH "PMPI_" AND
       p."PAPI_L2_TCM" > 5
   """

Query Language APIs
===================

In version 2023.1.0, the query language underwent a large refactor to enable support for :code:`GraphFrame` objects
containing a multi-indexed DataFrame. As a result, the query language now has two APIs:

- New-Style Queries: APIs for the query language starting with version 2023.1.0
- Old-Style Queries: APIs for the query language prior to version 2023.1.0

Old-style queries are discouraged for new users. However, these APIs are not deprecated at this time. For the time
being, old-style queries will be maintained as a thin wrapper around new-style queries.

Applying Queries to GraphFrames
-------------------------------

Whether using new-style queries or old-style queries, queries are applied to the data in a :code:`GraphFrame`
using the :code:`GraphFrame.filter()` method. This method takes a "filter object" as its first argument. A filter object can be
one of the following:

- A Python :code:`Callable`: filters the data in the :code:`GraphFrame` using a filter on the DataFrame (i.e., does not use the query language)
- A string: assumes the argument is a string-dialect query, builds a new-style query object from the argument,
  and applies that query to the :code:`GraphFrame`
- A Python :code:`list`: assumes the argument is an object-dialect query, builds a new-style query object from the argument,
  and applies that query to the :code:`GraphFrame`
- A new-sytle or old-style query object: applies the query to the :code:`GraphFrame`

As a result, the differences between new-style queries and old-style queries do not matter when using single
object- or string-dialect queries. Users only need to get into the differences between these APIs when using
base syntax queries or when combining queries.

New-Style Queries
-----------------

The new-style query API consists of 3 main classes:

- :code:`Query`: represents the base syntax
- :code:`ObjectQuery`: represents the object-based dialect
- :code:`StringQuery`: represents the string-based dialect

After creating objects of these classes, queries can be combined using the following "compound query" classes:

- :code:`ConjunctionQuery`: combines the results of each sub-query using set conjunction (i.e., logical AND)
- :code:`DisjunctionQuery`: combines the results of each sub-query using set disjunction (i.e., logical OR)
- :code:`ExclusiveDisjunctionQuery`: combines the results of each sub-query using set exclusive disjunction (i.e., logical XOR)
- :code:`NegationQuery`: combines the results of a single sub-query using set negation (i.e., logical NOT)

The rest of this section provides brief descriptions and examples of the usage of these classes.

Query Class
^^^^^^^^^^^

The :code:`Query` class is used to represent base syntax queries. To use it, simply create a :code:`Query`
object and call :code:`match` and :code:`rel` as described in the :ref:`Base Syntax` section.

An example of the use of this class can be found in the :ref:`Base Syntax` section.

ObjectQuery Class
^^^^^^^^^^^^^^^^^

The :code:`ObjectQuery` class is used to represent object-based dialect queries. To use it, create an object-based dialect
query (as described in the :ref:`Object-based Dialect` section), and pass that query to the constructor of
:code:`ObjectQuery`.

For example, the following code can be used to create an :code:`ObjectQuery` object from the query in the example from the :ref:`Object-based Dialect`
section:

.. code-block:: python

   query = [
       (
           ".",
           {
               "name": "P?MPI_.*",
               "PAPI_L2_TCM": "> 5"
           }
       ),
       "*"
   ]
   query_obj = hatchet.query.ObjectQuery(query)

StringQuery Class
^^^^^^^^^^^^^^^^^

The :code:`StringQuery` class is used to represent string-based dialect queries. To use it, first create
a string-based dialect query (as described in the :ref:`String-based Dialect` section). Then, a :code:`StringQuery`
object can be created from that string-based dialect query using either the :code:`StringQuery` constructor
or the :code:`parse_string_dialect` function. :code:`parse_string_dialect` is the recommended way of creating
a :code:`StringQuery` object because it allows users to write compound queries as strings (this functionality is not
yet documented).

For example, the following code can be used to create a :code:`StringQuery` object from the query in the example from the :ref:`String-based Dialect`
section:

.. code-block:: python

   query = """
   MATCH (".", p)->("*")
   WHERE p."name" STARTS WITH "MPI_" OR p."name" STARTS WTICH "PMPI_" AND
       p."PAPI_L2_TCM" > 5
   """
   query_obj = hatchet.query.parse_string_dialect(query)

ConjunctionQuery, DisjunctionQuery, and ExclusiveDisjunctionQuery Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

TBA

NegationQuery Class
^^^^^^^^^^^^^^^^^^^

TBA



Hatchet has a filtering query language that allows users to filter GraphFrames based on caller-callee relationships between nodes in the Graph. This query language contains two APIs: a high-level API that is expressed using built-in Python data types (e.g., lists, dictionaries, strings) and a low-level API that is expressed using Python callables.

Regardless of API, queries in Hatchet represent abstract paths, or path patterns, within the Graph being filtered. When filtering on a query, Hatchet will identify all paths in the Graph that match the query. Then, it will return a new GraphFrame object containing only the nodes contained in the matched paths. A query is represented as a list of *abstract graph nodes*. Each *abstract graph node* is made of two parts:

- A wildcard that specifies the number of real nodes to match to the abstract node
- A filter that is used to determine whether a real node matches the abstract node

The primary differences between the two APIs are the representation of filters, how wildcards and filters are combined into *abstract graph nodes*, and how *abstract graph nodes* are combined into a full query.

The following sections will describe the specifications for queries in both APIs and provide examples of how to use the query language.

High-Level API
==============

The high-level API for Hatchet's query language is designed to allow users to quickly write simple queries. It has a simple syntax based on built-in Python data types (e.g., lists, dictionaries, strings). The following subsections will describe each component of high-level queries. After creating a query, it can be used to filter a GraphFrame by passing it to the :code:`GraphFrame.filter` function as follows:

.. code-block:: python

  query = <QUERY GOES HERE>
  filtered_gf = gf.filter(query)

Wildcards
~~~~~~~~~

Wildcards in the high-level API are specified by one of four possible values:

- The string :code:`"."`, which means "match 1 node"
- The string :code:`"*"`, which means "match 0 or more nodes"
- The string :code:`"+"`, which means "match 1 or more nodes"
- An integer, which means "match exactly that number of nodes" (integer 1 is equivalent to :code:`"."`)

Filters
~~~~~~~

Filters in the high-level API are specified by Python dictionaries. These dictionaries are keyed on the names of *node attributes*. These attributes' names are the same as the column names from the DataFrame associated with the GraphFrame being filtered (which can be obtained with :code:`gf.dataframe`). There are also two special attribute names:

- `depth`, which filters on the depth of the node in the Graph
- `node_id`, which filters on the node's unique identifier within the GraphFrame

The values in a high-level API filter dictionary define the conditions that must be passed to pass the filter. Their data types depend on the data type of the corresponding attribute. The table below describes what value data types are valid for different attribute data types.

+----------------------------+--------------------------+------------------------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------+
| Attribute Data Type        | Example Attributes       | Valid Filter Value Types                                                                       | Description of Condition                                                                                       |
+============================+==========================+================================================================================================+================================================================================================================+
| Real (integer or float)    | `time`                   | Real (integer or float)                                                                        | Attribute value exactly equals filter value                                                                    |
+                            +                          +------------------------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------+
|                            | `time (inc)`             | String starting with comparison operator                                                       | Attribute value must pass comparison described in filter value                                                 |
+----------------------------+--------------------------+------------------------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------+
| String                     | `name`                   | Regex String (see `Python re module <https://docs.python.org/3/library/re.html>`_ for details) | Attribute must match filter value (passed to `re.match <https://docs.python.org/3/library/re.html#re.match>`_) |
+----------------------------+--------------------------+------------------------------------------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------+

The values in a high-level API filter dictionary can also be iterables (e.g., lists, tuples) of the valid values defined in the table above.

In the high-level API, all conditions (key-value pairs, including conditions contained in a list value) in a filter must pass for the a real node to match the corresponding *abstract graph node*.

Abstract Graph Nodes
~~~~~~~~~~~~~~~~~~~~

In the high-level API, *abstract graph nodes* are represented by Python tuples containing a single wildcard and a single filter. Alternatively, an *abstract graph node* can be represented by only a single . When only providing a wildcard or a filter (and not both), the default is used for the other component. The defaults are as follows:

- Wildcard: :code:`"."` (match 1 node)
- Filter: an "always-true" filter (any node passes this filter)

Full Queries
~~~~~~~~~~~~

In the high-level API, a query is represented as a Python list of *abstract graph nodes*. In general, the following code can be used as a template to build a low-level query.

.. code-block:: python

   query = [
       (wildcard1, query1),
       (wildcard2, query2),
       (wildcard3, query3)
   ]
   filtered_gf = gf.filter(query)

Low-Level API
=============

The low-level API for Hatchet's query language is designed to allow users to perform more complex queries. It's syntax is based on Python callables (e.g., functions, lambdas). The following subsections will describe each component of low-level queries. Like high-level queries, low-level queries can be used to filter a GraphFrame by passing it to the :code:`GraphFrame.filter` function as follows:

.. code-block:: python

  query = <QUERY GOES HERE>
  filtered_gf = gf.filter(query)

Wildcards
~~~~~~~~~

Wildcards in the low-level API are the exact same as wildcards in the high-level API. The following values are currently allowed for wildcards:

- The string :code:`"."`, which means "match 1 node"
- The string :code:`"*"`, which means "match 0 or more nodes"
- The string :code:`"+"`, which means "match 1 or more nodes"
- An integer, which means "match exactly that number of nodes" (integer 1 is equivalent to :code:`"."`)

Filters
~~~~~~~

The biggest difference between the high-level and low-level APIs are how filters are represented. In the low-level API, filters are represented by Python callables. These callables should take one argument representing a node in the graph and should return a boolean stating whether or not the node satisfies the filter. The type of the argument to the callable depends on whether the :code:`GraphFrame.drop_index_levels` function was previously called. If this function was called, the type of the argument will be a :code:`pandas.Series`. This :code:`Series` will be the row representing a node in the internal :code:`pandas.DataFrame`. If the :code:`GraphFrame.drop_index_levels` function was not called, the type of the argument will be a :code:`pandas.DataFrame`. This :code:`DataFrame` will contain the rows of the internal :code:`pandas.DataFrame` representing a node. Multiple rows are returned in this case because the internal :code:`DataFrame` will contain one row for every thread and function call.

For example, if you want to match nodes with an exclusive time (represented by "time" column) greater than 2 and an inclusive time (represented by "time (inc)" column) greater than 5, you could use the following filter. This filter assumes you have already called the :code:`GraphFrame.drop_index_levels` function.

.. code-block:: python

   filter = lambda row: row["time"] > 2 and row["time (inc)"] > 5

Abstract Graph Nodes
~~~~~~~~~~~~~~~~~~~~

To build *abstract graph nodes* in the low-level API, you will first need to import Hatchet's :code:`QueryMatcher` class. This can be done with the following import.

.. code-block:: python

   from hatchet import QueryMatcher

The :code:`QueryMatcher` class has two functions that can be used to build *abstract graph nodes*. The first function is :code:`QueryMatcher.match`, which resets the query and constructs a new *abstract graph node* as the root of the query. The second function is :code:`QueryMatcher.rel`, which constructs a new *abstract graph node* and appends it to the query. Both of these functions take two arguments: a wildcard and a low-level filter. If either the filter or wildcard are not provided, the default will be used. The defaults are as follows:

- Wildcard: :code:`"."` (match 1 node)
- Filter: an "always-true" filter (any node passes this filter)

Both of these functions also return a reference to the :code:`self` parameter of the :code:`QueryMatcher` object. This allows :code:`QueryMatcher.match` and :code:`QueryMatcher.rel` to be chained together.

Full Queries
~~~~~~~~~~~~

Full queries in the low-level API are built by making sucessive calls to the :code:`QueryMatcher.match` and :code:`QueryMatcher.rel` functions. In general, the following code can be used as a template to build a low-level query.

.. code-block:: python

   from hatchet import QueryMatcher

   query = QueryMatcher().match(wildcard1, filter1)
       .rel(wildcard2, filter2)
       .rel(wildcard3, filter3)
   filtered_gf = gf.filter(query)

Compound Queries
================

*Compound queries is currently a development feature.*

Compound queries allow users to apply some operation on the results of one or more queries. Currently, the following compound queries are available directly from :code:`hatchet.query`:

- :code:`AndQuery` and :code:`IntersectionQuery`
- :code:`OrQuery` and :code:`UnionQuery`
- :code:`XorQuery` and :code:`SymDifferenceQuery`

Additionally, the compound query feature provides the following abstract base classes that can be used by users to implement their own compound queries:

- :code:`AbstractQuery`
- :code:`NaryQuery`

The following subsections will describe each of these compound query classes.

AbstractQuery
~~~~~~~~~~~~~

:code:`AbstractQuery` is an interface (i.e., abstract base class with no implementation) that defines the basic requirements for a query in the Hatchet query language. All query types, including user-created compound queries, must inherit from this class.

NaryQuery
~~~~~~~~~

:code:`NaryQuery` is an abstract base class that inherits from :code:`AbstractQuery`. It defines the basic functionality and requirements for compound queries that perform one or more subqueries, collect the results of the subqueries, and performs some subclass defined operation to merge the results into a single result. Queries that inherit from :code:`NaryQuery` must implment the :code:`_perform_nary_op` function, which takes a list of results and should perform some operation on it.

AndQuery
~~~~~~~~

The :code:`AndQuery` class can be used to perform two or more subqueries and compute the intersection of all the returned lists of matched nodes. To create an :code:`AndQuery`, simply create your subqueries (which can be high-level, low-level, or compound), and pass them to the :code:`AndQuery` constructor. The following code can be used as a template for creating an :code:`AndQuery`.

.. code-block:: python

   from hatchet.query import AndQuery

   query1 = <QUERY GOES HERE>
   query2 = <QUERY GOES HERE>
   query3 = <QUERY GOES HERE>
   and_query = AndQuery(query1, query2, query3)
   filtered_gf = gf.filter(and_query)

:code:`IntersectionQuery` is also provided as an alias (i.e., renaming) of :code:`AndQuery`. The two can be used interchangably.

OrQuery
~~~~~~~~

The :code:`OrQuery` class can be used to perform two or more subqueries and compute the union of all the returned lists of matched nodes. To create an :code:`OrQuery`, simply create your subqueries (which can be high-level, low-level, or compound), and pass them to the :code:`OrQuery` constructor. The following code can be used as a template for creating an :code:`OrQuery`.

.. code-block:: python

   from hatchet.query import OrQuery

   query1 = <QUERY GOES HERE>
   query2 = <QUERY GOES HERE>
   query3 = <QUERY GOES HERE>
   or_query = OrQuery(query1, query2, query3)
   filtered_gf = gf.filter(or_query)

:code:`UnionQuery` is also provided as an alias (i.e., renaming) of :code:`OrQuery`. The two can be used interchangably.

XorQuery
~~~~~~~~

The :code:`XorQuery` class can be used to perform two or more subqueries and compute the symmetric difference (set theory equivalent to XOR) of all the returned lists of matched nodes. To create an :code:`XorQuery`, simply create your subqueries (which can be high-level, low-level, or compound), and pass them to the :code:`XorQuery` constructor. The following code can be used as a template for creating an :code:`XorQuery`.

.. code-block:: python

   from hatchet.query import XorQuery

   query1 = <QUERY GOES HERE>
   query2 = <QUERY GOES HERE>
   query3 = <QUERY GOES HERE>
   xor_query = XorQuery(query1, query2, query3)
   filtered_gf = gf.filter(xor_query)

:code:`SymDifferenceQuery` is also provided as an alias (i.e., renaming) of :code:`XorQuery`. The two can be used interchangably.
